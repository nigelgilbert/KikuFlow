#!/bin/sh
# Build "Slopr Flow.app" into app/build/, with scripts/ and sidecar/ side by side in Resources.
set -eu
cd "$(dirname "$0")"
swift build -c release
app="build/Slopr Flow.app"
rm -rf "$app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
cp "$(swift build -c release --show-bin-path)/SloprFlow" "$app/Contents/MacOS/"
rsync -a --exclude .venv --exclude __pycache__ --exclude '.*_cache' --exclude tests \
    ../scripts ../sidecar "$app/Contents/Resources/"
cat > "$app/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key><string>SloprFlow</string>
    <key>CFBundleIdentifier</key><string>dev.slopr.flow</string>
    <key>CFBundleName</key><string>Slopr Flow</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>0.1.0</string>
    <key>CFBundleVersion</key><string>1</string>
    <key>LSMinimumSystemVersion</key><string>15.0</string>
    <key>LSUIElement</key><true/>
    <key>NSMicrophoneUsageDescription</key><string>Slopr Flow records while you hold the dictation key and transcribes on this Mac.</string>
</dict>
</plist>
EOF
# Signed with a "Slopr Flow Dev" certificate from the keychain, macOS keeps the Accessibility grant
# across rebuilds; an ad-hoc signature changes with every build, so the grant is lost each time.
identity="Slopr Flow Dev"
security find-certificate -c "$identity" >/dev/null 2>&1 || identity=-
codesign --force --sign "$identity" "$app"
echo "$PWD/$app"
