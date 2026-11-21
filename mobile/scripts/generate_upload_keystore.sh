#!/usr/bin/env bash
set -euo pipefail
umask 077

command -v keytool >/dev/null 2>&1 || {
  echo "JDK keytool is required. Install a JDK and retry." >&2
  exit 1
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
destination="${1:-${HOME}/.config/south-omo-market/upload-keystore.jks}"
destination="$(mkdir -p "$(dirname "$destination")" && cd "$(dirname "$destination")" && pwd)/$(basename "$destination")"
case "$destination" in
  "$repo_root"/*)
    echo "Refusing to create a production keystore inside the repository checkout." >&2
    exit 1
    ;;
esac

if [[ -e "$destination" ]]; then
  echo "Refusing to overwrite an existing keystore: $destination" >&2
  exit 1
fi

alias="${ANDROID_KEY_ALIAS:-south-omo-market-upload}"
keytool -genkeypair -v \
  -keystore "$destination" \
  -alias "$alias" \
  -keyalg RSA \
  -keysize 4096 \
  -validity 10000 \
  -dname "CN=South Omo Market, O=South Omo Market, L=Jinka, ST=South Omo, C=ET"

chmod 600 "$destination"
echo
echo "Keystore created outside the repository: $destination"
echo "Record and protect the following public certificate fingerprint:"
keytool -list -v -keystore "$destination" -alias "$alias" | awk '/SHA256:/{print; found=1; exit} END {if (!found) exit 1}'
echo
echo "Back up this file twice in encrypted offline storage. Store passwords separately."
