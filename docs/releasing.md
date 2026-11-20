# Releasing

Pushing a tag publishes a release:

```sh
git tag v0.2.0 && git push origin v0.2.0
```

[The workflow](../.github/workflows/release.yml) runs the tests, builds the app with the tag as its version, signs it, and attaches `KikuFlow.zip` to a new GitHub release. [install.sh](../install.sh) always downloads the latest release, so that is the whole rollout.

## The signing certificate

macOS ties the Accessibility grant to the app's signature. Every release is signed with the same self-signed certificate, named "Kiku Flow Dev", so the grant survives an update. Users need nothing in their keychain.

Set it up once. Create the certificate and its key, good for ten years:

```sh
/usr/bin/openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=Kiku Flow Dev" \
    -addext "keyUsage=critical,digitalSignature" -addext "extendedKeyUsage=critical,codeSigning" \
    -keyout key.pem -out cert.pem
/usr/bin/openssl pkcs12 -export -inkey key.pem -in cert.pem -name "Kiku Flow Dev" -out kiku.p12
```

The second command asks for a password. Give both to the repo as secrets:

```sh
base64 -i kiku.p12 | gh secret set SIGNING_P12
gh secret set SIGNING_P12_PASSWORD
```

Keep `kiku.p12` and its password somewhere safe, and delete `key.pem`. A release signed with a different certificate is a new app to macOS, and every user has to grant Accessibility again.

To sign your own builds with it too, open `kiku.p12` to add it to your login keychain. [app/bundle.sh](../app/bundle.sh) then signs with it, and your builds and the releases share one Accessibility grant.

## Not notarized

The app has no Apple Developer ID. It opens without a warning because `curl` doesn't mark its downloads as quarantined. The same zip downloaded in a browser is blocked by Gatekeeper, so the install script is the only supported way in.
