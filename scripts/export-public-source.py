"""Export reviewed committed source without private history or operational dossiers."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="HEAD", help="Committed revision to export")
    parser.add_argument(
        "--output", type=Path, required=True, help="New .tar.gz path; never overwritten"
    )
    parser.add_argument("--gitleaks", default="gitleaks", help="Reviewed Gitleaks executable")
    args = parser.parse_args()
    scanner = shutil.which(args.gitleaks)
    if not scanner:
        raise SystemExit("Gitleaks is required; no unscanned source archive was created")
    receipt_path = args.output.with_name(args.output.name + ".receipt.json")
    if args.output.exists() or receipt_path.exists():
        raise SystemExit("Output already exists; choose a new path")
    revision = (
        git("rev-parse", "--verify", "--end-of-options", args.revision + "^{commit}")
        .decode()
        .strip()
    )
    selectors = [
        line.strip()
        for line in git("show", revision + ":publication-files.txt").decode().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not selectors or any(p.startswith(("/", ":")) or ".." in Path(p).parts for p in selectors):
        raise SystemExit("Invalid publication path list")
    for path in selectors:
        git("cat-file", "-e", revision + ":" + path)
    archive = git("archive", "--format=tar", revision, "--", *selectors)
    epoch = int(git("show", "-s", "--format=%ct", revision))
    with tempfile.TemporaryDirectory(prefix="ai-dash-public-source-") as temporary:
        stage = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            for member in source.getmembers():
                parts = Path(member.name).parts
                if not (member.isfile() or member.isdir()) or any(
                    part in {".git", ".venv", "var", "secrets", ".env", "windmill-profile.json"}
                    for part in parts
                ):
                    raise SystemExit("Unexpected private path or non-regular export member")
                if member.name.endswith((".pem", ".key", ".p12", ".pfx", ".sqlite", ".sqlite3")):
                    raise SystemExit("Unexpected private-file extension in source export")
                if any(p.startswith(".env.") and p != ".env.example" for p in parts):
                    raise SystemExit("Unexpected environment configuration in source export")
            source.extractall(stage, filter="data")
        result = subprocess.run(
            [scanner, "dir", str(stage), "--redact=100", "--no-banner"], check=False
        )
        if result.returncode:
            raise SystemExit("Source secret scan failed; no archive was created")
        files = sorted(p for p in stage.rglob("*") if p.is_file())
        manifest = {
            p.relative_to(stage).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as output:
            with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w|") as target:
                    for path in files:
                        name = path.relative_to(stage).as_posix()
                        data = path.read_bytes()
                        info = tarfile.TarInfo("ai-dash/" + name)
                        info.size = len(data)
                        info.mtime = epoch
                        info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                        target.addfile(info, io.BytesIO(data))
        receipt = {
            "source_revision": revision,
            "archive_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
            "file_count": len(files),
            "secret_scan": "passed",
            "files_sha256": manifest,
        }
        with receipt_path.open("x") as output:
            output.write(json.dumps(receipt, indent=2) + "\n")
        print(
            json.dumps(
                {"archive": str(args.output), "receipt": str(receipt_path), "files": len(files)}
            )
        )


if __name__ == "__main__":
    main()
