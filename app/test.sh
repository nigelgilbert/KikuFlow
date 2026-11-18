#!/bin/sh
# swift test, also with Command Line Tools only, where Swift Testing sits outside the default paths.
set -eu
cd "$(dirname "$0")"
dev=/Library/Developer/CommandLineTools/Library/Developer
if [ -d /Applications/Xcode.app ] || [ ! -d "$dev/Frameworks/Testing.framework" ]; then exec swift test "$@"; fi
exec swift test -Xswiftc -F -Xswiftc "$dev/Frameworks" -Xlinker -rpath -Xlinker "$dev/Frameworks" \
    -Xlinker -rpath -Xlinker "$dev/usr/lib" "$@"
