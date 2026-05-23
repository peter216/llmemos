import datetime
import os
import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# GPG key constants — used in Phase 2.3 signature verification fixtures/tests
# ---------------------------------------------------------------------------

# Your GPG signing key fingerprint — set TEST_SIGNING_KEY in the environment before running
# signed tests. Run: gpg --list-secret-keys --keyid-format LONG
# Signed fixtures and tests are skipped if this env var is not set.
TEST_SIGNING_KEY = os.environ.get("TEST_SIGNING_KEY", "")  # gitleaks:allow

# Placeholder "other" key — used as an untrusted key in negative tests.
# Does not need to exist in any keyring; just must be a different fingerprint.
OTHER_KEY = "AAAA0000111122223333444455556666BBBB7777"  # gitleaks:allow


def _require_signing_key():
    """Call at the top of any fixture that needs TEST_SIGNING_KEY — skips if absent."""
    if not TEST_SIGNING_KEY:
        pytest.skip("TEST_SIGNING_KEY env var not set — skipping signed-commit tests")


# ---------------------------------------------------------------------------
# Test log hook — writes output to tests/logs/<testname>.<timestamp>.log
# ---------------------------------------------------------------------------


def pytest_runtest_logreport(report):
    """Write a log file for each test after it runs."""
    if report.when != "call":
        return
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    safe_name = report.nodeid.replace("/", "_").replace("::", ".").replace(" ", "_")
    log_file = log_dir / f"{safe_name}.{timestamp}.log"
    with open(log_file, "w") as f:
        f.write(f"test:     {report.nodeid}\n")
        f.write(f"outcome:  {report.outcome}\n")
        f.write(f"duration: {report.duration:.3f}s\n")
        if report.longrepr:
            f.write(f"\n{report.longrepr!s}\n")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def local_bare_repo(tmp_path):
    """
    A local bare git repo acting as a fake remote, with one commit on main.
    Commits are unsigned — signature tests create their own signed fixtures.
    """
    env = {
        "HOME": str(tmp_path),
        "GIT_AUTHOR_NAME": "Test User",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }

    bare = tmp_path / "remote.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(bare)], check=True)

    work = tmp_path / "work"
    subprocess.run(["git", "clone", str(bare), str(work)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(work), "config", "user.name", "Test User"], check=True)
    (work / "README.md").write_text("test repo\n")
    subprocess.run(["git", "-C", str(work), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(work), "commit", "--no-gpg-sign", "-m", "initial commit"],
        check=True,
        env={**os.environ, **env},
    )
    subprocess.run(
        ["git", "-C", str(work), "push", "origin", "main"], check=True, capture_output=True
    )

    return bare


@pytest.fixture
def cloned_repo(local_bare_repo, tmp_path):
    """A working clone of local_bare_repo, ready for get_commit_info and friends."""
    from gh_mcp.git_ops import clone_or_pull

    dest = tmp_path / "cloned"
    clone_or_pull(str(local_bare_repo), dest)
    return dest


@pytest.fixture
def signed_bare_repo(tmp_path):
    """
    A local bare git repo whose single commit is GPG-signed with TEST_SIGNING_KEY.

    Does NOT override HOME — git and GPG must find the real keyring.
    Used for Phase 2.3 verify_signature tests.
    Skipped if TEST_SIGNING_KEY env var is not set.
    """
    _require_signing_key()
    bare = tmp_path / "signed_remote.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(bare)], check=True)

    work = tmp_path / "signed_work"
    subprocess.run(["git", "clone", str(bare), str(work)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(work), "config", "user.name", "Test User"], check=True)

    (work / "README.md").write_text("signed test repo\n")
    subprocess.run(["git", "-C", str(work), "add", "."], check=True)

    # Sign with TEST_SIGNING_KEY — no HOME override so GPG finds the real keyring
    subprocess.run(
        [
            "git",
            "-C",
            str(work),
            "commit",
            f"--gpg-sign={TEST_SIGNING_KEY}",
            "-m",
            "signed commit",
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(work), "push", "origin", "main"], check=True, capture_output=True
    )
    return bare


@pytest.fixture
def signed_cloned_repo(signed_bare_repo, tmp_path):
    """A working clone of signed_bare_repo. Used in verify_signature tests."""
    from gh_mcp.git_ops import clone_or_pull

    dest = tmp_path / "signed_cloned"
    clone_or_pull(str(signed_bare_repo), dest)
    return dest


@pytest.fixture
def signed_bare_repo_with_agents(tmp_path):
    """
    A signed bare repo whose initial commit includes AGENTS.md.
    Used by Phase 4 fetch_memos happy-path tests.
    Skipped if TEST_SIGNING_KEY env var is not set.
    """
    _require_signing_key()
    bare = tmp_path / "signed_agents_remote.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(bare)], check=True)

    work = tmp_path / "signed_agents_work"
    subprocess.run(["git", "clone", str(bare), str(work)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(work), "config", "user.name", "Test User"], check=True)

    (work / "AGENTS.md").write_text("# Test AGENTS.md\n\ncontent\n")
    subprocess.run(["git", "-C", str(work), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(work),
            "commit",
            f"--gpg-sign={TEST_SIGNING_KEY}",
            "-m",
            "signed with agents",
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(work), "push", "origin", "main"], check=True, capture_output=True
    )
    return bare


@pytest.fixture
def signed_bare_repo_with_files(tmp_path):
    """
    A signed bare repo whose initial commit includes AGENTS.md, taxonomy.yml,
    and memos/session-memo-001.md. Used by read_repo_file tests.
    Skipped if TEST_SIGNING_KEY env var is not set.
    """
    _require_signing_key()
    bare = tmp_path / "signed_files_remote.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(bare)], check=True)

    work = tmp_path / "signed_files_work"
    subprocess.run(["git", "clone", str(bare), str(work)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(work), "config", "user.name", "Test User"], check=True)

    (work / "AGENTS.md").write_text("# Test AGENTS.md\n\ncontent\n")
    (work / "taxonomy.yml").write_text("tags:\n  memo-protocol: test\n")
    memos_dir = work / "memos"
    memos_dir.mkdir()
    (memos_dir / "session-memo-001.md").write_text("# Memo 001\n\nepisodic content\n")

    subprocess.run(["git", "-C", str(work), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(work),
            "commit",
            f"--gpg-sign={TEST_SIGNING_KEY}",
            "-m",
            "signed with files",
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(work), "push", "origin", "main"], check=True, capture_output=True
    )
    return bare


@pytest.fixture
def two_branch_bare_repo(tmp_path):
    """
    A local bare repo with both 'main' and 'dev' branches.
    Used in Phase 3 cache key isolation tests.
    """
    env = {
        "HOME": str(tmp_path),
        "GIT_AUTHOR_NAME": "Test User",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }

    bare = tmp_path / "two_branch.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(bare)], check=True)

    work = tmp_path / "two_branch_work"
    subprocess.run(["git", "clone", str(bare), str(work)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(work), "config", "user.name", "Test User"], check=True)

    # Initial commit on main
    (work / "README.md").write_text("main branch\n")
    subprocess.run(["git", "-C", str(work), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(work), "commit", "--no-gpg-sign", "-m", "initial on main"],
        check=True,
        env={**os.environ, **env},
    )
    subprocess.run(
        ["git", "-C", str(work), "push", "origin", "main"], check=True, capture_output=True
    )

    # Create dev branch and push
    subprocess.run(["git", "-C", str(work), "checkout", "-b", "dev"], check=True)
    (work / "dev.txt").write_text("dev branch\n")
    subprocess.run(["git", "-C", str(work), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(work), "commit", "--no-gpg-sign", "-m", "initial on dev"],
        check=True,
        env={**os.environ, **env},
    )
    subprocess.run(
        ["git", "-C", str(work), "push", "origin", "dev"], check=True, capture_output=True
    )

    return bare
