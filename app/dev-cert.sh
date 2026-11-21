#!/bin/sh
# Put a "Kiku Flow Dev" certificate of your own in your login keychain, once. bundle.sh signs with
# it, so macOS keeps the Accessibility grant across your builds.
set -eu
name="Kiku Flow Dev"
if security find-certificate -c "$name" >/dev/null 2>&1; then
    echo "Your keychain already has a \"$name\" certificate."
    exit 0
fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
# The system's openssl, whose p12 the keychain can read. The password only covers the file on its
# way into the keychain.
/usr/bin/openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=$name" \
    -addext "keyUsage=critical,digitalSignature" -addext "extendedKeyUsage=critical,codeSigning" \
    -keyout "$tmp/key.pem" -out "$tmp/cert.pem" 2>/dev/null
/usr/bin/openssl pkcs12 -export -inkey "$tmp/key.pem" -in "$tmp/cert.pem" -name "$name" \
    -out "$tmp/dev.p12" -passout pass:kiku
security import "$tmp/dev.p12" -k "$HOME/Library/Keychains/login.keychain-db" -P kiku \
    -T /usr/bin/codesign
echo "Added \"$name\". Builds from app/bundle.sh are now signed with it."
