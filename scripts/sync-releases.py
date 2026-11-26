import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import quote


def download_asset(package, arch, path):
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
    return url


def build_binary_package(apk, package, arch, binary):
    spec = package["binary"]
    name = package["name"]
    version = f'{package["version"]}-r{spec["revision"]}'
    root = binary.parent / "root"
    shutil.copytree(Path(__file__).resolve().parent.parent / "packages" / name, root)
    executable = root / spec["path"]
    executable.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(binary, executable)
    executable.chmod(0o755)
    for init_script in (root / "etc/init.d").iterdir():
        init_script.chmod(0o755)

    archive = binary.parent / f"{name}-{version}.apk"
    subprocess.run(
        [apk, "mkpkg", "--files", str(root), "--output", str(archive),
         "--info", f"name:{name}", "--info", f"version:{version}",
         "--info", f"arch:{arch}", "--info", f"url:{package['repo']}",
         "--info", f"description:{spec['description']}",
         "--info", f"depends:{spec['depends']}"],
        check=True,
    )
    return archive


def package_filename(apk, name, arch, path, url):

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

        for arch, directories in destinations.items():
            with tempfile.TemporaryDirectory() as work:
                source = Path(work) / "release"
                url = download_asset(package, arch, source)
                if "binary" in package:
                    source = build_binary_package(apk, package, arch, source)
                    filename = source.name
                else:
                    filename = package_filename(apk, package["name"], arch, source, url)
                for directory in directories:
                    directory.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, directory / filename)


def main():
    parser = argparse.ArgumentParser(description="Prepare APKs from pinned release assets")
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
