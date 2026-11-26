# OpenWrt APK feed

GitHub Actions prepares APKs from the upstream GitHub release assets pinned in
[feed.json](feed.json) and commits the signed feed under `feed/` on `main`
after each push, including merges. Routers download it from GitHub's raw URLs.

The initial feed targets OpenWrt **25.12.6**.

| Router target | Package architecture | APK index |
| --- | --- | --- |
| `x86/64` | `x86_64` | [packages.adb](https://raw.githubusercontent.com/pradumnk-mahanta/openwrt-packages/main/feed/25.12.6/x86_64/packages.adb) |
| `mediatek/filogic` | `aarch64_cortex-a53` | [packages.adb](https://raw.githubusercontent.com/pradumnk-mahanta/openwrt-packages/main/feed/25.12.6/aarch64_cortex-a53/packages.adb) |

## Update package versions

In GitHub Actions, run **Check for OpenWrt Package Updates** on `main`. It
checks each upstream project's latest stable release. A newer release needs
one matching asset with a SHA-256 digest for each architecture listed for the
package. The workflow verifies the updated feed, commits `feed.json`, and
starts **Publish OpenWrt APK Feed**. If no pins change, the run ends after the check.

## Install on a router

APK expands `${APK_ARCH}` in the repository file to select the matching index.

```sh
(
    set -e
    # 1. Trust the feed signing key
    wget -O /etc/apk/keys/openwrt-packages-pm.pem \
        'https://raw.githubusercontent.com/pradumnk-mahanta/openwrt-packages/main/feed/keys/openwrt-packages-pm.pem'

    # 2. Add the feed
    printf '%s\n' 'https://raw.githubusercontent.com/pradumnk-mahanta/openwrt-packages/main/feed/25.12.6/${APK_ARCH}/packages.adb' > /etc/apk/repositories.d/openwrt-packages-pm.list

    # To pin the feed to Filogic, replace ${APK_ARCH} above with aarch64_cortex-a53.

    # 3. Refresh the package index
    apk update
)
```

Install the packages you want individually. For example,
`apk add luci-theme-fluent` installs the Fluent theme, and
`apk add luci-app-mwan3` installs the LuCI app and its `mwan3` dependency.

### Available packages

- `mwan3` — MWAN3 multi-WAN service
- `luci-app-mwan3` — LuCI interface for MWAN3
- `luci-theme-fluent` — Fluent theme
- `pangolin-cli` — Pangolin CLI and site connector

## Move a Newt site to Pangolin CLI

With the feed configured, install the APK and create the site environment file
with root-only permissions.

```sh
apk -U add pangolin-cli
mkdir -p /etc/pangolin
(umask 077; touch /etc/pangolin/pangolin-site.env)
chmod 600 /etc/pangolin/pangolin-site.env
vi /etc/pangolin/pangolin-site.env
```

Add these shell assignments using your existing Newt site ID and secret.

```sh
SITE_ID='replace-with-site-id'
SITE_SECRET='replace-with-site-secret'
PANGOLIN_ENDPOINT='https://pangolin.itryto.win'
```

If Newt is installed, stop and disable it before starting Pangolin with the
same credentials.

```sh
/etc/init.d/newt stop
/etc/init.d/newt disable
/etc/init.d/pangolin enable
/etc/init.d/pangolin start
logread -e pangolin
```

Run `/etc/init.d/pangolin restart` after editing the environment file.

### Firmware upgrades

The APK adds the site environment file, feed repository entry, and feed signing
key to the sysupgrade backup list. Before upgrading with **Keep settings**
enabled, verify the files are listed.

```sh
sysupgrade -l | grep -E 'pangolin-site\.env|openwrt-packages-pm\.'
```

After flashing stock firmware, reinstall `pangolin-cli` from a feed matching
the new OpenWrt release, then enable and start the service again. An image
built with this APK can carry the service through the upgrade. The sysupgrade
backup contains the site secret.

## Upstream projects

- **mwan3** is the nftables port maintained by Ian Cooper (dl12345), based on
  OpenWrt's MultiWAN manager. [Upstream repository](https://github.com/dl12345/mwan3)
- **luci-app-mwan3** is the LuCI frontend for the nftables port.
  [Upstream repository](https://github.com/dl12345/luci-app-mwan3)
- **luci-theme-fluent** is the Fluent 2-inspired LuCI theme by LazuliKao.
  [Upstream repository](https://github.com/LazuliKao/luci-theme-fluent)
- **pangolin-cli** repackages the upstream Linux binaries.
  [Release and source](https://github.com/fosrl/cli/releases/tag/0.23.0)

The feed setup was inspired by [UnTangled](https://github.com/bidhata/untangled#readme).
