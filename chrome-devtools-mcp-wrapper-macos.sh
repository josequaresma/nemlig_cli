#!/bin/sh
# macOS wrapper for chrome-devtools-mcp (counterpart to the Nix-based
# chrome-devtools-mcp-wrapper.sh, which requires nix-shell).
# Uses the system Google Chrome and a project-local profile so browsing
# state stays out of the personal Chrome profile.

set -eu
cd "$(dirname "$0")"

CHROME_PROFILE_DIR="$(pwd)/.chrome-profile"
mkdir -p "$CHROME_PROFILE_DIR"

# Same pinned version as the Nix wrapper, for reproducibility
exec npx chrome-devtools-mcp@0.10.1 \
    --executablePath "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --userDataDir "$CHROME_PROFILE_DIR"
