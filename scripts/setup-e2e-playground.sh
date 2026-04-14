#!/usr/bin/env bash
set -euo pipefail

# Setup a reality-check e2e playground.
#
# Creates a directory with:
#   software/amplifier-chat/  — the "built artifact" (cloned from GitHub)
#   user/spec.md              — synthetic user requirements
#   user/conversation.md      — synthetic build conversation
#
# Usage:
#   ./setup-e2e-playground.sh [--with-bugs] [TARGET_DIR]
#
# Examples:
#   ./setup-e2e-playground.sh                          # clean
#   ./setup-e2e-playground.sh --with-bugs              # with all bugs injected
#   ./setup-e2e-playground.sh --with-bugs /tmp/pg      # bugs + custom dir
#
# Defaults:
#   TARGET_DIR  /tmp/reality-check-playground

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUGS_DIR="$REPO_DIR/fixtures/bugs"

# --- Parse args ---
WITH_BUGS=false
TARGET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-bugs) WITH_BUGS=true; shift ;;
    *)           TARGET="$1"; shift ;;
  esac
done

TARGET="${TARGET:-/tmp/reality-check-playground}"
CHAT_REPO="https://github.com/microsoft/amplifier-chat.git"
CHAT_COMMIT="2e83886b7989c69fa541e253b1bdcd9ceb716f76"

echo "Setting up reality-check playground..."
echo "  Target:  $TARGET"
echo "  Source:  $CHAT_REPO @ $CHAT_COMMIT"

# Clean and create
rm -rf "$TARGET"
mkdir -p "$TARGET/software" "$TARGET/user"

# Clone amplifier-chat from GitHub at a pinned commit
git clone "$CHAT_REPO" "$TARGET/software/amplifier-chat"
git -C "$TARGET/software/amplifier-chat" checkout "$CHAT_COMMIT" --quiet
rm -rf "$TARGET/software/amplifier-chat/.git"

# Copy fixtures
cp "$REPO_DIR/fixtures/amplifier-chat-spec.md"          "$TARGET/user/spec.md"
cp "$REPO_DIR/fixtures/amplifier-chat-conversation.md"   "$TARGET/user/conversation.md"

# --- Bug injection ---
if $WITH_BUGS; then
  patches=("$BUGS_DIR"/*.patch)
  if [[ -f "${patches[0]}" ]]; then
    echo ""
    echo "Injecting ${#patches[@]} bug(s)..."
    for patch_file in "${patches[@]}"; do
      name="$(basename "$patch_file" .patch)"
      patch -d "$TARGET/software/amplifier-chat" -p1 --no-backup-if-mismatch < "$patch_file"
      echo "  applied: $name"
    done
  fi
fi

echo ""
echo "Done! Playground created at: $TARGET"
$WITH_BUGS && echo "  Bugs injected: $(ls "$BUGS_DIR"/*.patch 2>/dev/null | xargs -I{} basename {} .patch | tr '\n' ' ')"
echo ""
echo "  cd $TARGET && amplifier"
