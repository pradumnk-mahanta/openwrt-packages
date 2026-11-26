import argparse
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen


def latest_release(repo):
    match = re.fullmatch(r"https://github[.]com/([\w.-]+/[\w.-]+)", repo)
    if not match:
        raise ValueError(f"Expected a GitHub repository URL, got {repo}")
    request = Request(
        f"https://api.github.com/repos/{match[1]}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "openwrt-feed-updater"},
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def version_key(tag):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:-(\d+))?", tag)
    if match:
        return tuple(int(part or 0) for part in match.groups())
    return None


def match_assets(package, assets, series):
    selected = {}
    for arch, pin in package["assets"].items():
        pattern = pin.get("match", re.escape(pin["file"]))
        pattern = pattern.replace("{openwrt_series}", re.escape(series))
        matches = [
            asset for asset in assets
            if asset["state"] == "uploaded" and re.fullmatch(pattern, asset["name"])
        ]
        if len(matches) != 1:
            print(f"{package['name']}: expected one release asset for {arch}, found {len(matches)}")
            return None
        asset = matches[0]
        digest = re.fullmatch(r"sha256:([0-9a-fA-F]{64})", asset.get("digest") or "")
        if not digest:
            print(f"{package['name']}: missing SHA-256 digest for {asset['name']}")
            return None
        selected[arch] = {**pin, "file": asset["name"], "sha256": digest[1].lower()}
    return selected


def update(config):
    series = config["openwrt"].rsplit(".", 1)[0]
    changed = False
    for package in config["packages"]:
        release = latest_release(package["repo"])
        current = package["version"]
        tag = release["tag_name"]
        if tag == current or release["draft"] or release["prerelease"]:
            continue
        current_version, new_version = version_key(current), version_key(tag)
        if current_version is None or new_version is None:
            print(f"{package['name']}: cannot compare tags {current!r} and {tag!r}")
            continue
        if new_version <= current_version:
            continue
        assets = match_assets(package, release["assets"], series)
        if assets is not None:
            package.update(version=tag, assets=assets)
            print(f"{package['name']}: {current} -> {tag}")
            changed = True
    return changed


def main():
    parser = argparse.ArgumentParser(description="Refresh feed pins from stable GitHub releases")
    parser.add_argument("config", type=Path)
    args = parser.parse_args()

    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if update(config):
            args.config.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        else:
            print("No compatible package updates found.")
    except (KeyError, OSError, ValueError) as error:
        parser.exit(1, f"Release update failed: {error}\n")


if __name__ == "__main__":
    main()
