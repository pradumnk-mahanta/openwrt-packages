# OpenWrt APK feed

GitHub Actions mirrors the upstream GitHub release APKs pinned in
[feed.json](feed.json) and commits the signed feed under `feed/` on `main`
after each push, including merges. Routers download it from GitHub's raw URLs.

The initial feed targets OpenWrt **25.12.6**.

| Router target | Package architecture | APK index |
| --- | --- | --- |
| `x86/64` | `x86_64` | [packages.adb](https://raw.githubusercontent.com/pradumnk-mahanta/openwrt-packages/main/feed/25.12.6/x86_64/packages.adb) |
| `mediatek/filogic` | `aarch64_cortex-a53` | [packages.adb](https://raw.githubusercontent.com/pradumnk-mahanta/openwrt-packages/main/feed/25.12.6/aarch64_cortex-a53/packages.adb) |


## Install on a router

APK expands `${APK_ARCH}` in the repository file to select the matching index.

```sh
(
    set -e
    # 1. Trust the feed signing key
    wget -O /etc/apk/keys/openwrt-packages-pm.pem \
        'https://raw.githubusercontent.com/pradumnk-mahanta/openwrt-packages/main/feed/keys/openwrt-packages-pm.pem'

    # 2. Add the feed
    printf '%s\n' 'https://raw.githubusercontent.com/pradumnk-mahanta/openwrt-packages/main/feed/25.12.6/${APK_ARCH}/packages.adb' \
        > /etc/apk/repositories.d/openwrt-packages-pm.list

    # 3. Refresh and install the bundle
    apk update
    apk add openwrt-packages-pm
)
```

`openwrt-packages-pm` installs MWAN3, its LuCI app, and the Fluent, Material 3,
Argon and Glass themes. Use `apk del openwrt-packages-pm` to remove the bundle.
APK keeps any packages you installed explicitly or that other packages require.

You can also install individual packages, for example
`apk add luci-app-mwan3 luci-theme-fluent`. The LuCI app pulls in `mwan3`.

### Available packages

- `mwan3` — MWAN3 multi-WAN service
- `luci-app-mwan3` — LuCI interface for MWAN3
- `luci-theme-fluent` — Fluent theme
- `luci-theme-material3` — Material 3 theme
- `luci-theme-argon` — Argon theme
- `luci-theme-glass` — Glass theme

## Upstream projects

- **mwan3** is the nftables port maintained by Ian Cooper (dl12345), based on
  OpenWrt's MultiWAN manager. [Upstream repository](https://github.com/dl12345/mwan3)
- **luci-app-mwan3** is the LuCI frontend for the nftables port.
  [Upstream repository](https://github.com/dl12345/luci-app-mwan3)
- **luci-theme-fluent** is the Fluent 2-inspired LuCI theme by LazuliKao.
  [Upstream repository](https://github.com/LazuliKao/luci-theme-fluent)
- **luci-theme-material3** is the Material 3 LuCI theme by michioxd.
  [Upstream repository](https://github.com/michioxd/luci-theme-material3)
- **luci-theme-argon** is the Argon LuCI theme by jerrykuku and contributors.
  [Upstream repository](https://github.com/jerrykuku/luci-theme-argon)
- **luci-theme-glass** is the Glass LuCI theme by rchen14b.
  [Upstream repository](https://github.com/rchen14b/luci-theme-glass)

The three-step setup and bundle were inspired by [UnTangled](https://github.com/bidhata/untangled#readme).
