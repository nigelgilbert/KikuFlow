#!/bin/sh
# Install or update Kiku Flow:
#   curl -fsSL https://raw.githubusercontent.com/nigelgilbert/KikuFlow/main/install.sh | sh
# Downloads the latest release, puts the app in /Applications, installs the speech engine and
# downloads the models, then opens the app. Run it again to update; your config and hooks stay.
set -eu

zip_url="${KIKU_FLOW_ZIP:-https://github.com/nigelgilbert/KikuFlow/releases/latest/download/KikuFlow.zip}"
support="$HOME/Library/Application Support/KikuFlow"

# In a function, so a download cut short runs nothing.
main() {
    # Asks the chip, not the shell: uname says x86_64 in a Terminal that runs under Rosetta.
    [ "$(sysctl -n hw.optional.arm64 2>/dev/null)" = 1 ] || fail "Kiku Flow needs an Apple Silicon Mac."
    [ "$(sw_vers -productVersion | cut -d. -f1)" -ge 15 ] || fail "Kiku Flow needs macOS 15 or later."

    # ~/Applications for an account that can't write to /Applications.
    apps=/Applications
    [ -w "$apps" ] || { apps="$HOME/Applications"; mkdir -p "$apps"; }
    app="$apps/Kiku Flow.app"

    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    say "Downloading Kiku Flow"
    curl -fL --progress-bar "$zip_url" -o "$tmp/KikuFlow.zip"
    ditto -x -k "$tmp/KikuFlow.zip" "$tmp"
    [ -d "$tmp/Kiku Flow.app" ] || fail "The download holds no Kiku Flow.app."

    pkill -x KikuFlow 2>/dev/null || true  # a running copy, when this is an update
    rm -rf "$app"
    mv "$tmp/Kiku Flow.app" "$app"
    # A build from source links hooks to its repo; mkdir fails on the link once that repo is gone.
    if [ -L "$support/hooks" ] && [ ! -e "$support/hooks" ]; then rm "$support/hooks"; fi
    mkdir -p "$support/hooks"

    say "Installing the speech engine"
    /bin/sh "$app/Contents/Resources/scripts/bootstrap.sh"

    # The app would download these at its first launch, without a progress bar.
    say "Downloading the models, several GB"
    "$support/venv/bin/python" -I -c '
from kiku_sidecar.config import load_config
c = load_config()
print(c.stt_model, c.cleanup_model, sep="\n")' | while read -r model; do
        "$support/venv/bin/hf" download "$model" >/dev/null ||
            echo "Couldn't download $model. Kiku Flow tries again when it starts." >&2
    done

    open "$app"
    cat <<EOF

Kiku Flow is in $apps and running in the menu bar.
1. Grant Accessibility when asked. The hotkey and the paste need it.
2. Hold Right Option. The first time, macOS asks for the Microphone; allow it and hold again.
3. Say something and let go.
EOF
}

say() { printf '\n==> %s\n' "$1"; }
fail() { echo "$1" >&2; exit 1; }

main
