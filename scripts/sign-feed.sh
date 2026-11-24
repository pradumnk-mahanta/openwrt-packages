#!/usr/bin/env bash
set -euo pipefail

config=$1
apk=$(realpath "$2")
output=$(realpath "$3")
release=$(jq -er '.openwrt' "$config")
architectures=$(jq -er '.architectures[]' "$config")
bundle_name=$(jq -er '.bundle.name' "$config")
bundle_version=$(jq -er '.bundle.version' "$config")
dependencies=$(jq -er '[.packages[].name] | join(" ")' "$config")
: "${APK_SIGNING_KEY:?Set APK_SIGNING_KEY to the private PEM key for this feed}"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
private_key="$work/private.pem"
public_key="$output/keys/openwrt-packages-pm.pem"
mkdir -p "$output/keys"
install -m 600 /dev/null "$private_key"
printf '%s\n' "$APK_SIGNING_KEY" > "$private_key"
unset APK_SIGNING_KEY
openssl pkey -in "$private_key" -passin pass: -pubout -out "$public_key"

bundle="$work/$bundle_name-$bundle_version.apk"
"$apk" mkpkg --info "name:$bundle_name" --info "version:$bundle_version" \
  --info "arch:noarch" --info "depends:$dependencies" \
  --info "description:All packages in the OpenWrt APK feed" --output "$bundle"

while IFS= read -r arch; do
  (
    cd "$output/$release/$arch"
    cp "$bundle" .
    "$apk" mkndx --allow-untrusted --sign-key "$private_key" --output packages.adb ./*.apk
    "$apk" verify --keys-dir "$output/keys" packages.adb
  )
done <<< "$architectures"
