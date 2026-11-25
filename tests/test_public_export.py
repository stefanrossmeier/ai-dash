import importlib.util
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/export-public-source.py"


@pytest.fixture
def export_repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "config", "user.name", "stefanrossmeier"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "github@rossmeier.info"], cwd=repo, check=True)
    (repo / "README.md").write_text("Public example source\n")
    (repo / "private-history.txt").write_text("SYNTHETIC_PRIVATE_HISTORY_MARKER\n")
    (repo / ".env").write_text("SYNTHETIC_UNTRACKED_RUNTIME_MARKER\n")
    (repo / "publication-files.txt").write_text("README.md\npublication-files.txt\n")
    spec = importlib.util.spec_from_file_location("public_export", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", repo)
    return repo, module


def commit(repo):
    subprocess.run(
        ["git", "add", "README.md", "publication-files.txt", "private-history.txt"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "Synthetic export fixture",
        ],
        cwd=repo,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "stefanrossmeier",
            "GIT_AUTHOR_EMAIL": "github@rossmeier.info",
            "GIT_COMMITTER_NAME": "stefanrossmeier",
            "GIT_COMMITTER_EMAIL": "github@rossmeier.info",
        },
    )


def invoke(module, tmp_path, monkeypatch, output, scanner_status=0):
    scanner = tmp_path / "scanner"
    scanner.write_text(f"#!/bin/sh\nexit {scanner_status}\n")
    scanner.chmod(0o700)
    monkeypatch.setattr(
        sys, "argv", [str(SCRIPT), "--output", str(output), "--gitleaks", str(scanner)]
    )
    module.main()


def test_export_omits_private_history_and_untracked_runtime_and_is_deterministic(
    export_repo, tmp_path, monkeypatch
):
    repo, module = export_repo
    commit(repo)
    first, second = tmp_path / "first.tar.gz", tmp_path / "second.tar.gz"
    invoke(module, tmp_path, monkeypatch, first)
    invoke(module, tmp_path, monkeypatch, second)
    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first) as archive:
        assert set(archive.getnames()) == {"ai-dash/README.md", "ai-dash/publication-files.txt"}
        text = "".join(archive.extractfile(p).read().decode() for p in archive.getnames())
    assert "SYNTHETIC_PRIVATE_HISTORY_MARKER" not in text
    assert "SYNTHETIC_UNTRACKED_RUNTIME_MARKER" not in text


def test_failed_secret_scan_creates_no_archive(export_repo, tmp_path, monkeypatch):
    repo, module = export_repo
    commit(repo)
    output = tmp_path / "blocked.tar.gz"
    with pytest.raises(SystemExit, match="secret scan failed"):
        invoke(module, tmp_path, monkeypatch, output, scanner_status=1)
    assert not output.exists() and not output.with_name(output.name + ".receipt.json").exists()


def test_export_rejects_links_to_files_outside_reviewed_source(export_repo, tmp_path, monkeypatch):
    repo, module = export_repo
    secret = tmp_path / "outside.txt"
    secret.write_text("SYNTHETIC_OUTSIDE_MARKER")
    (repo / "leak").symlink_to(secret)
    with (repo / "publication-files.txt").open("a") as file:
        file.write("leak\n")
    subprocess.run(["git", "add", "leak"], cwd=repo, check=True)
    commit(repo)
    output = tmp_path / "blocked.tar.gz"
    with pytest.raises(SystemExit, match="non-regular"):
        invoke(module, tmp_path, monkeypatch, output)
    assert not output.exists()


def test_existing_receipt_cannot_be_overwritten(export_repo, tmp_path, monkeypatch):
    repo, module = export_repo
    commit(repo)
    output = tmp_path / "source.tar.gz"
    receipt = output.with_name(output.name + ".receipt.json")
    receipt.write_text("preserve")
    with pytest.raises(SystemExit, match="already exists"):
        invoke(module, tmp_path, monkeypatch, output)
    assert not output.exists() and receipt.read_text() == "preserve"
