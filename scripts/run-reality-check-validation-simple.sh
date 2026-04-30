#!/usr/bin/env bash
# Smoke-test wrapper for the reality-check pipeline.
#
# Wraps run-reality-check-validation.sh with extra setup so that the
# DTU pulls amplifier-bundle-reality-check from a LOCAL Gitea instance
# containing the developer's local working tree (committed, staged,
# AND untracked) instead of GitHub upstream. This is what makes the
# DTU actually test the local pipeline changes, not the upstream code.
#
# Pattern follows amplifier-tester:setup-digital-twin:
#   1. Check (or create) a local amplifier-gitea instance.
#   2. Mirror amplifier-bundle-reality-check from GitHub if missing.
#   3. Capture the local working tree via `git stash create -u` and push
#      that stash commit to Gitea's main. NO local commits, NO local
#      refs are modified — `stash create` returns a commit object
#      without updating any reference.
#   4. Launch the simple profile with --var GITEA_URL/GITEA_TOKEN so
#      the profile's url_rewrites redirect reality-check clones to Gitea.
#   5. Use --exec-timeout 3600 (1h) since the recipe takes longer than
#      the inner script's default 1800s when running inside a DTU.
#
# After the inner script finishes, the extracted /root/home contents
# are also copied to /tmp/reality-check-home-<ts> for easy inspection.
#
# Flags forwarded to run-reality-check-validation.sh:
#   --name NAME           Friendly --name for the DTU
#   --destroy-on-finish   Destroy the DTU after extraction (default: keep)
#   --help                Show help (delegates to inner script)
#
# Profile, prompt, exec-timeout, GITEA_* vars are pinned by this wrapper.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROFILE="${REPO_DIR}/.amplifier/digital-twin-universe/profiles/reality-check-in-incus-simple.yaml"

PROMPT='Run the reality-check-pipeline recipe with these context inputs (pass each as a recipe context variable):
- software_path: /root/home/software/add-two-numbers
- spec_path: /root/home/user/spec.md
- conversation_path: ""
- output_dir: /root/home/reality-check-output
- acceptance_tests_path: /root/home/reality-check-output/acceptance-tests

All paths are absolute. acceptance_tests_path MUST be passed explicitly so the validate-tests bash step looks at the same directory the intent-analyzer writes to.'

GITEA_PORT="${GITEA_PORT:-10110}"
EXEC_TIMEOUT_SEC="${EXEC_TIMEOUT_SEC:-3600}"   # 1h: outer DTU + recipe + nested DTU launches
DTU_NAME="${DTU_NAME:-simple-test}"            # name of the DTU we manage; auto-destroyed at start

if [[ ! -f "${PROFILE}" ]]; then
  echo "ERROR: Simple profile not found: ${PROFILE}" >&2
  exit 1
fi

# ---------------------------------------------------------------------
# 0. Self-contained: destroy any pre-existing DTU with our managed name
#
# Every invocation spins up a fresh DTU. If a previous run left one
# behind, remove it before launching so the user never has to do
# manual cleanup between runs.
# ---------------------------------------------------------------------
if amplifier-digital-twin list 2>/dev/null \
     | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if any(x['id']=='${DTU_NAME}' for x in d) else 1)" 2>/dev/null; then
  echo "[$(date +%H:%M:%S)] Found existing DTU '${DTU_NAME}', destroying for fresh launch..." >&2
  amplifier-digital-twin destroy "${DTU_NAME}" 2>&1 \
    | python3 -c 'import json,sys; print("  destroyed:", json.load(sys.stdin).get("destroyed", False))' >&2 \
    || echo "  WARN: destroy failed (continuing anyway)" >&2
else
  echo "[$(date +%H:%M:%S)] No existing DTU '${DTU_NAME}'. Proceeding with fresh launch." >&2
fi

# ---------------------------------------------------------------------
# 1. Gitea setup: reuse first running instance, else create one
# ---------------------------------------------------------------------
echo "[$(date +%H:%M:%S)] Checking for existing Gitea instance..." >&2
GITEA_LIST="$(amplifier-gitea list 2>/dev/null || echo '[]')"

if echo "${GITEA_LIST}" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d else 1)' 2>/dev/null; then
  GITEA_ID="$(echo "${GITEA_LIST}" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')"
  GITEA_PORT_USED="$(echo "${GITEA_LIST}" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["port"])')"
  GITEA_TOKEN="$(amplifier-gitea token "${GITEA_ID}" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
  echo "[$(date +%H:%M:%S)] Reusing Gitea instance: ${GITEA_ID} (port ${GITEA_PORT_USED})" >&2
else
  echo "[$(date +%H:%M:%S)] Creating new Gitea instance on port ${GITEA_PORT}..." >&2
  CREATE_JSON="$(amplifier-gitea create --port "${GITEA_PORT}")"
  GITEA_ID="$(echo "${CREATE_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  GITEA_PORT_USED="$(echo "${CREATE_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["port"])')"
  GITEA_TOKEN="$(echo "${CREATE_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
  echo "[$(date +%H:%M:%S)] Created Gitea: ${GITEA_ID} (port ${GITEA_PORT_USED})" >&2
fi

GITEA_URL="http://localhost:${GITEA_PORT_USED}"
REPO_NAME="amplifier-bundle-reality-check"

# ---------------------------------------------------------------------
# 2. Mirror reality-check from GitHub if not already mirrored
# ---------------------------------------------------------------------
if curl -sf -H "Authorization: token ${GITEA_TOKEN}" \
     "${GITEA_URL}/api/v1/repos/admin/${REPO_NAME}" >/dev/null 2>&1; then
  echo "[$(date +%H:%M:%S)] Repo admin/${REPO_NAME} already mirrored." >&2
else
  echo "[$(date +%H:%M:%S)] Mirroring https://github.com/microsoft/${REPO_NAME} -> Gitea..." >&2
  amplifier-gitea mirror-from-github "${GITEA_ID}" \
    --github-repo "https://github.com/microsoft/${REPO_NAME}" >/dev/null
  echo "[$(date +%H:%M:%S)] Mirror complete." >&2
fi

# ---------------------------------------------------------------------
# 3. Push local working tree (committed + staged + untracked) to Gitea's main
#
# WHY NOT `git stash create -u`: with -u, untracked files go into a
# SEPARATE third-parent commit. Pushing the stash SHA as a branch HEAD
# only includes the main commit's tree, so untracked files (like our
# new intent-iteration.yaml) are silently dropped on the Gitea side.
#
# Instead: copy the index to a temp file, `git add -A` against the
# temp index (so the real index is untouched), `git write-tree` to
# materialize a tree object, then `git commit-tree` to make a real
# commit object with HEAD as parent. Push that commit SHA. No local
# refs are modified.
# ---------------------------------------------------------------------
echo "[$(date +%H:%M:%S)] Snapshotting local working tree (committed + staged + untracked)..." >&2
pushd "${REPO_DIR}" >/dev/null
GIT_DIR_REAL="$(git rev-parse --git-dir)"
TEMP_INDEX="$(mktemp -t reality-check-index.XXXXXX)"
cp "${GIT_DIR_REAL}/index" "${TEMP_INDEX}"
GIT_INDEX_FILE="${TEMP_INDEX}" git add -A
TREE_SHA="$(GIT_INDEX_FILE="${TEMP_INDEX}" git write-tree)"
SNAPSHOT_SHA="$(echo 'Local working tree snapshot for DTU testing' \
  | git commit-tree "${TREE_SHA}" -p HEAD)"
rm -f "${TEMP_INDEX}"
echo "[$(date +%H:%M:%S)] Snapshot commit ${SNAPSHOT_SHA:0:8} (tree ${TREE_SHA:0:8})." >&2
echo "[$(date +%H:%M:%S)] Pushing ${SNAPSHOT_SHA:0:8} -> Gitea admin/${REPO_NAME}:main (force)..." >&2
git push --force \
  "http://admin:${GITEA_TOKEN}@localhost:${GITEA_PORT_USED}/admin/${REPO_NAME}.git" \
  "${SNAPSHOT_SHA}":refs/heads/main 2>&1 \
  | sed 's/^/  /' >&2
popd >/dev/null

# Sanity check: confirm Gitea now serves the recipe with our changes
# (intent-loop is a step name we added in the local recipe).
if curl -sf -H "Authorization: token ${GITEA_TOKEN}" \
     "${GITEA_URL}/api/v1/repos/admin/${REPO_NAME}/contents/recipes/reality-check-pipeline.yaml?ref=main" \
     | python3 -c 'import json,sys,base64; print(base64.b64decode(json.load(sys.stdin)["content"]).decode())' \
     | grep -q "intent-loop"; then
  echo "[$(date +%H:%M:%S)] Verified: Gitea recipe contains 'intent-loop' (local changes pushed)." >&2
else
  echo "[$(date +%H:%M:%S)] WARN: Gitea recipe does NOT contain 'intent-loop'. Local changes may not be present." >&2
fi

# ---------------------------------------------------------------------
# 4. Launch via inner script with Gitea vars + extended exec-timeout
#
# We pick the timestamp + output dir HERE so we know exactly where the
# inner script wrote -- no `find -newer` heuristic, no dependence on
# invocation CWD. Output always lands under /tmp/reality-check-runs/
# so the repo working tree is never polluted.
# ---------------------------------------------------------------------
TS="$(date -u +%Y%m%d-%H%M%S)"
OUT_DIR="/tmp/reality-check-runs/reality-check-validation-${TS}"

set +e
"${SCRIPT_DIR}/run-reality-check-validation.sh" \
  --profile "${PROFILE}" \
  --prompt "${PROMPT}" \
  --name "${DTU_NAME}" \
  --out-dir "${OUT_DIR}" \
  --var "GITEA_URL=${GITEA_URL}" \
  --var "GITEA_TOKEN=${GITEA_TOKEN}" \
  --exec-timeout "${EXEC_TIMEOUT_SEC}" \
  "$@"
inner_rc=$?
set -e

# ---------------------------------------------------------------------
# 5. Copy extracted home dir to a second /tmp location for convenience
#
# (Original artifacts already live under /tmp/reality-check-runs/...,
# but a flat /tmp/reality-check-home-<TS>/ is friendlier to point
# editors / file browsers at.)
# ---------------------------------------------------------------------
if [[ -d "${OUT_DIR}/home" ]]; then
  TMP_DEST="/tmp/reality-check-home-${TS}"
  rm -rf "${TMP_DEST}"
  cp -r "${OUT_DIR}/home" "${TMP_DEST}"
  echo ""
  echo "=========================================================="
  echo "Home directory copied to /tmp for inspection:"
  echo "  ${TMP_DEST}"
  echo "(Original artifacts also under: ${OUT_DIR})"
  echo "=========================================================="
elif [[ -d "${OUT_DIR}" ]]; then
  echo ""
  echo "WARN: ${OUT_DIR} exists but no home/ subdir found." >&2
  echo "      Inner script may have failed before extracting /root/home." >&2
else
  echo ""
  echo "WARN: Output directory ${OUT_DIR} was not created." >&2
  echo "      Inner script may have failed before mkdir, or a forwarded" >&2
  echo "      --out-dir override pointed somewhere else." >&2
fi

exit "${inner_rc}"
