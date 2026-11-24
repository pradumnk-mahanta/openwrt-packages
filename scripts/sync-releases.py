import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import quote


def download_package(apk, package, arch, path):
    asset = package["assets"][arch]
    name = package["name"]
    tag = quote(package["version"], safe="")
    filename = quote(asset["file"], safe="")
    url = f'{package["repo"]}/releases/download/{tag}/{filename}'
    print(f"Fetching {name} ({arch}) from {url}", flush=True)
    subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location",
         "--retry", "3", "--connect-timeout", "20", "--max-time", "120",
         "--output", str(path), url],
        check=True,
    )
    with path.open("rb") as archive:
        if hashlib.file_digest(archive, "sha256").hexdigest() != asset["sha256"]:
            raise ValueError(f"SHA-256 mismatch for {url}")

    metadata = subprocess.check_output(
        [apk, "adbdump", "--format", "json", "--allow-untrusted", str(path)],
        text=True,
    )
    info = json.loads(metadata)["info"]
    if info["name"] != name or info["arch"] != arch:
        raise ValueError(f"{url} has package {info['name']} ({info['arch']}), expected {name} ({arch})")
    version = info["version"]
    if not re.fullmatch(r"[A-Za-z0-9._+~-]+", version):
        raise ValueError(f"Invalid APK version {version!r} in {url}")

    # APK looks up archives using the name and version from index metadata.
    return f"{name}-{version}.apk"


def sync(config, apk, output):
    for package in config["packages"]:
        destinations = {}
        for target_arch in config["architectures"]:
            arch = target_arch if target_arch in package["assets"] else "noarch"
            if arch not in package["assets"]:
                raise ValueError(f"{package['name']} has no APK for {target_arch}")
            destination = output / config["openwrt"] / target_arch
            destinations.setdefault(arch, []).append(destination)

        with tempfile.TemporaryDirectory() as work:
            source = Path(work) / "release.apk"
            for arch, directories in destinations.items():
                filename = download_package(apk, package, arch, source)
                for directory in directories:
                    directory.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, directory / filename)


def main():
    parser = argparse.ArgumentParser(description="Mirror pinned OpenWrt APK release assets")
    parser.add_argument("config", type=Path)
    parser.add_argument("apk", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    try:
        sync(json.loads(args.config.read_text(encoding="utf-8")), args.apk.resolve(), args.output)
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Release sync failed: {error}\n")


if __name__ == "__main__":
    main()
