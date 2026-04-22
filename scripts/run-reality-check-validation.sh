#!/usr/bin/env bash
# Automates an end-to-end reality-check validation run inside the
# reality-check-in-incus DTU profile.
#
# Flow:
#   1. Launch the DTU (amplifier-digital-twin launch <profile>).
#   2. Wait for readiness (all checks pass).
#   3. Inside the outer DTU, run:
#        amplifier run "<prompt>"
#      with stdout/stderr streamed to the terminal AND tee'd to a log.
#   4. When the run completes (or fails), pull out:
#        /root/home                 -> $OUT/home/
#        /root/.amplifier/projects  -> $OUT/sessions/
#   5. Print a summary.
#
# Output goes to a timestamped directory under $PWD (the directory
# from which the script is invoked), not the script's location.
#
# Usage:
#   ./run-reality-check-validation.sh [flags]
#
# Flags:
#   --profile PATH      Profile YAML (default: sibling of this script)
#   --name NAME         Friendly --name for the DTU (default: none)
#   --prompt TEXT       Prompt for `amplifier run` (default: see below)
#   --host-port PORT    Host TCP port to forward to the inner Chat UI
#                       (default: 8410). Pass a different value when
#                       running concurrent instances of this profile so
#                       they don't fight over the same port.
#   --destroy-on-finish Destroy the DTU after extraction (default: keep)
#   --help              Show this help
#
# Requirements: amplifier-digital-twin, incus, docker.
# The target profile pins those + Amplifier + agent-browser.
#
# Notes:
#   - Provisioning takes ~10-15 minutes on first run.
#   - The recipe itself takes another 10-30 minutes depending on depth.
#   - Logs are streamed live; also captured to run.log for later review.
#   - DTU is left running by default so you can exec in and inspect;
#     pass --destroy-on-finish to clean up automatically.
set -euo pipefail

# ---------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_PROFILE="${SCRIPT_DIR}/../.amplifier/digital-twin-universe/profiles/reality-check-in-incus.yaml"
DEFAULT_PROMPT='Run the reality-check-pipeline recipe against the software at /root/home/software with spec and conversation at /root/home/user. Output directory: /root/home/reality-check-output.'

PROFILE="${DEFAULT_PROFILE}"
PROMPT="${DEFAULT_PROMPT}"
DTU_NAME=""
DESTROY_ON_FINISH="false"
HOST_PORT="8410"   # forwarded to inner Chat UI; override per run with --host-port

READINESS_TIMEOUT_SEC=1200   # 20 min, for provisioning + warmup
READINESS_INTERVAL_SEC=10

# ---------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------
usage() {
  sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//;/^set -euo/d'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)             PROFILE="$2"; shift 2 ;;
    --name)                DTU_NAME="$2"; shift 2 ;;
    --prompt)              PROMPT="$2"; shift 2 ;;
    --host-port)           HOST_PORT="$2"; shift 2 ;;
    --destroy-on-finish)   DESTROY_ON_FINISH="true"; shift ;;
    --help|-h)             usage; exit 0 ;;
    *)                     echo "Unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! -f "${PROFILE}" ]]; then
  echo "ERROR: Profile not found: ${PROFILE}" >&2
  exit 1
fi

# ---------------------------------------------------------------------
# Output layout (under invocation CWD)
# ---------------------------------------------------------------------
TS="$(date -u +%Y%m%d-%H%M%S)"
OUT="${PWD}/reality-check-validation-${TS}"
LOG="${OUT}/run.log"
LAUNCH_JSON="${OUT}/launch-info.json"

mkdir -p "${OUT}"

log() { printf '[%(%H:%M:%S)T] %s\n' -1 "$*" | tee -a "${LOG}" >&2; }

log "Profile:    ${PROFILE}"
log "Output dir: ${OUT}"
log "Prompt:     ${PROMPT}"

# ---------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------
log "Launching DTU (provisioning, ~10-15 min on first run) ..."

LAUNCH_ARGS=(launch "${PROFILE}" --var "HOST_PORT=${HOST_PORT}")
if [[ -n "${DTU_NAME}" ]]; then
  LAUNCH_ARGS+=(--name "${DTU_NAME}")
fi

# Capture JSON to file; also mirror last line to stdout for visibility.
# launch prints progress on stderr and the final JSON on stdout.
amplifier-digital-twin "${LAUNCH_ARGS[@]}" \
  > "${LAUNCH_JSON}" \
  2> >(tee -a "${LOG}" >&2)

# Extract id from the last JSON line (robust against any leading noise).
DTU_ID="$(grep -oE '"id":[[:space:]]*"[^"]+"' "${LAUNCH_JSON}" \
          | tail -n1 \
          | sed -E 's/.*"id":[[:space:]]*"([^"]+)".*/\1/')"

if [[ -z "${DTU_ID}" ]]; then
  log "ERROR: Could not parse DTU id from launch output."
  cat "${LAUNCH_JSON}" >&2
  exit 1
fi
log "DTU launched: ${DTU_ID}"

# ---------------------------------------------------------------------
# Cleanup trap: always try to extract artifacts, even on failure
# ---------------------------------------------------------------------
extract_artifacts() {
  local dtu="$1"
  log "Extracting artifacts from ${dtu} ..."

  mkdir -p "${OUT}/home" "${OUT}/sessions"

  # /root/home -> home/
  if amplifier-digital-twin file-pull "${dtu}" \
       /root/home/ "${OUT}/home/" 2>>"${LOG}"; then
    log "  pulled /root/home"
  else
    log "  WARN: pull /root/home failed (continuing)"
  fi

  # Flatten the extra "home" directory that file-pull's rsync-style
  # copy creates (sources are copied with their basename).
  if [[ -d "${OUT}/home/home" ]]; then
    shopt -s dotglob nullglob
    mv "${OUT}/home/home/"* "${OUT}/home/" 2>/dev/null || true
    rmdir "${OUT}/home/home" 2>/dev/null || true
    shopt -u dotglob nullglob
  fi

  # /root/.amplifier/projects -> sessions/
  if amplifier-digital-twin file-pull "${dtu}" \
       /root/.amplifier/projects/ "${OUT}/sessions/" 2>>"${LOG}"; then
    log "  pulled /root/.amplifier/projects"
  else
    log "  WARN: pull /root/.amplifier/projects failed (continuing)"
  fi

  if [[ -d "${OUT}/sessions/projects" ]]; then
    shopt -s dotglob nullglob
    mv "${OUT}/sessions/projects/"* "${OUT}/sessions/" 2>/dev/null || true
    rmdir "${OUT}/sessions/projects" 2>/dev/null || true
    shopt -u dotglob nullglob
  fi
}

finish() {
  local rc=$?
  set +e
  if [[ -n "${DTU_ID:-}" ]]; then
    extract_artifacts "${DTU_ID}"
    if [[ "${DESTROY_ON_FINISH}" == "true" ]]; then
      log "Destroying DTU ${DTU_ID} ..."
      amplifier-digital-twin destroy "${DTU_ID}" 2>>"${LOG}" || true
    else
      log "DTU ${DTU_ID} left running."
      log "  Inspect:  amplifier-digital-twin exec ${DTU_ID}"
      log "  Destroy:  amplifier-digital-twin destroy ${DTU_ID}"
    fi
  fi
  log "Exit ${rc}. Output: ${OUT}"
  log "  home/      -> contents of /root/home in the DTU"
  log "  sessions/  -> .amplifier/projects session history"
  log "  run.log    -> full run transcript"
  exit "${rc}"
}
trap finish EXIT

# ---------------------------------------------------------------------
# Poll readiness
# ---------------------------------------------------------------------
log "Polling readiness (timeout ${READINESS_TIMEOUT_SEC}s) ..."
deadline=$(( SECONDS + READINESS_TIMEOUT_SEC ))
while (( SECONDS < deadline )); do
  rj="$(amplifier-digital-twin check-readiness "${DTU_ID}" 2>/dev/null || echo '{}')"
  ready="$(printf '%s' "${rj}" \
           | grep -oE '"ready":[[:space:]]*(true|false)' \
           | head -n1 \
           | sed -E 's/.*:[[:space:]]*//')"
  if [[ "${ready}" == "true" ]]; then
    log "Ready."
    break
  fi
  sleep "${READINESS_INTERVAL_SEC}"
done

if [[ "${ready:-}" != "true" ]]; then
  log "ERROR: DTU did not become ready within ${READINESS_TIMEOUT_SEC}s"
  exit 1
fi

# ---------------------------------------------------------------------
# Run the reality-check pipeline with streamed output
# ---------------------------------------------------------------------
log "Starting recipe run via 'amplifier run' (this takes 10-30 min) ..."
log "----- amplifier run output begins -----"

# --stream gives raw passthrough (no JSON envelope). Exit code
# propagates from the inner process. Tee to run.log for later review.
set +e
amplifier-digital-twin exec --stream "${DTU_ID}" \
  -- amplifier run "${PROMPT}" 2>&1 \
  | tee -a "${LOG}"
run_rc="${PIPESTATUS[0]}"
set -e

log "----- amplifier run output ends (exit=${run_rc}) -----"

if [[ "${run_rc}" -ne 0 ]]; then
  log "Recipe run exited non-zero. Extracting artifacts anyway."
fi

# Exit code is the recipe run's exit code; extraction happens in trap.
exit "${run_rc}"
