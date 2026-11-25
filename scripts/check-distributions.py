"""Fail builds that include files outside the reviewed publication paths."""

import tarfile
import tomllib
import zipfile
from email.parser import Parser
from pathlib import Path

root = Path(__file__).resolve().parents[1]
project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
distribution = project["name"].replace("-", "_")
version = project["version"]
dist_info = f"{distribution}-{version}.dist-info"
selectors = [
    line.strip()
    for line in (root / "publication-files.txt").read_text().splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]


def selected(path: str) -> bool:
    return path == "PKG-INFO" or any(
        path == s or path.startswith(s.rstrip("/") + "/") for s in selectors
    )


def license_metadata(raw: bytes) -> None:
    metadata = Parser().parsestr(raw.decode())
    if metadata["License-Expression"] != "Apache-2.0" or not {
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
    }.issubset(metadata.get_all("License-File", [])):
        raise SystemExit("Distribution lacks the reviewed application license metadata")


source = root / f"dist/{distribution}-{version}.tar.gz"
wheel = root / f"dist/{distribution}-{version}-py3-none-any.whl"
with tarfile.open(source) as archive:
    for member in archive.getmembers():
        if member.isdir():
            continue
        path = member.name.split("/", 1)[1]
        if not member.isfile() or not selected(path):
            raise SystemExit(f"Unreviewed source distribution member: {path}")
        if path == "PKG-INFO":
            license_metadata(archive.extractfile(member).read())
with zipfile.ZipFile(wheel) as archive:
    for path in archive.namelist():
        if not (path.startswith("ai_dash/") or path.startswith(dist_info + "/")):
            raise SystemExit(f"Unexpected wheel member: {path}")
    license_metadata(archive.read(dist_info + "/METADATA"))
    for name in ["LICENSE", "THIRD_PARTY_NOTICES.md"]:
        if f"{dist_info}/licenses/{name}" not in archive.namelist():
            raise SystemExit(f"Wheel omits license file: {name}")
print("Source and wheel contain only reviewed publication paths and license metadata")
