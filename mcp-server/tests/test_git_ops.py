import os
import subprocess

import pytest
from gh_mcp.git_ops import (
    clone_or_pull,
    get_commit_info,
    read_agents_md,
    read_repo_file,
    verify_signature,
)

# GPG key constants — must match the constants in conftest.py
# Set TEST_SIGNING_KEY env var to your GPG fingerprint to run signed-commit tests
TEST_SIGNING_KEY = os.environ.get("TEST_SIGNING_KEY", "")  # gitleaks:allow
OTHER_KEY = "AAAA0000111122223333444455556666BBBB7777"  # gitleaks:allow — placeholder untrusted key


class TestCloneOrPull:
    def test_clones_when_dest_missing(self, local_bare_repo, tmp_path):
        """clone_or_pull should clone the repo when dest_dir does not exist."""
        dest = tmp_path / "cloned"
        assert not dest.exists()

        result = clone_or_pull(str(local_bare_repo), dest)

        assert dest.exists()
        assert (dest / ".git").is_dir()
        assert (dest / "README.md").exists()
        assert result == dest

    def test_pulls_not_reclones_when_dest_exists(self, local_bare_repo, tmp_path):
        """clone_or_pull should pull (not re-clone) when dest_dir already has a repo."""
        dest = tmp_path / "cloned"

        # Initial clone
        clone_or_pull(str(local_bare_repo), dest)

        # Add a new commit to the remote
        work = tmp_path / "work2"
        subprocess.run(
            ["git", "clone", str(local_bare_repo), str(work)], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(work), "config", "user.email", "test@example.com"], check=True
        )
        subprocess.run(["git", "-C", str(work), "config", "user.name", "Test User"], check=True)
        (work / "newfile.txt").write_text("added remotely\n")
        subprocess.run(["git", "-C", str(work), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(work), "commit", "--no-gpg-sign", "-m", "second commit"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(work), "push", "origin", "main"], check=True, capture_output=True
        )

        # Place an untracked sentinel — a re-clone would wipe this
        sentinel = dest / ".sentinel"
        sentinel.write_text("i must survive\n")

        # Second call — should pull
        clone_or_pull(str(local_bare_repo), dest)

        # New remote file is present (pull happened)
        assert (dest / "newfile.txt").exists()
        # Sentinel survived (no re-clone)
        assert sentinel.exists()


class TestGetCommitInfo:
    def test_returns_hash_and_branch(self, cloned_repo):
        """get_commit_info returns a short hash and the current branch name."""
        info = get_commit_info(cloned_repo)

        assert len(info["hash"]) == 7
        assert info["hash"].isalnum()
        assert info["branch"] == "main"

    def test_returns_sig_status_and_signer_key(self, cloned_repo):
        """get_commit_info returns sig_status and signer_key for unsigned commits."""
        info = get_commit_info(cloned_repo)

        assert "sig_status" in info
        assert "signer_key" in info
        assert info["sig_status"] == "N"  # git code for no signature
        assert info["signer_key"] == ""


class TestVerifySignature:
    def test_returns_true_when_signed_by_trusted_key(self, signed_cloned_repo):
        """verify_signature returns True when HEAD is signed by a key in trusted_keys."""
        result = verify_signature(signed_cloned_repo, [TEST_SIGNING_KEY])

        assert result is True

    def test_returns_failure_reason_when_key_not_in_trusted_keys(self, signed_cloned_repo):
        """verify_signature returns a string reason when the signer is not in trusted_keys."""
        result = verify_signature(signed_cloned_repo, [OTHER_KEY])

        assert result is not True
        assert isinstance(result, str)
        assert "not in trusted" in result.lower()

    def test_returns_failure_reason_when_unsigned(self, cloned_repo):
        """verify_signature returns a string reason when commit has no signature."""
        result = verify_signature(cloned_repo, [TEST_SIGNING_KEY])

        assert result is not True
        assert isinstance(result, str)
        assert "not signed" in result.lower()


class TestReadRepoFile:
    def test_returns_file_content_for_root_level_file(self, tmp_path):
        """read_repo_file returns the content of a file at the repo root."""
        expected = "tags:\n  memo-protocol: test\n"
        (tmp_path / "taxonomy.yml").write_text(expected)

        result = read_repo_file(tmp_path, "taxonomy.yml")

        assert result == expected

    def test_returns_file_content_from_subdirectory(self, tmp_path):
        """read_repo_file returns content of a file in a subdirectory."""
        memos_dir = tmp_path / "memos"
        memos_dir.mkdir()
        expected = "# Memo 001\n\nepisodic content\n"
        (memos_dir / "session-memo-001.md").write_text(expected)

        result = read_repo_file(tmp_path, "memos/session-memo-001.md")

        assert result == expected

    def test_raises_for_dotdot_path(self, tmp_path):
        """read_repo_file raises ValueError for paths containing '..'."""
        with pytest.raises(ValueError, match="not a safe relative path"):
            read_repo_file(tmp_path, "../etc/passwd")

    def test_raises_for_absolute_path(self, tmp_path):
        """read_repo_file raises ValueError for absolute paths."""
        with pytest.raises(ValueError, match="not a safe relative path"):
            read_repo_file(tmp_path, "/etc/passwd")

    def test_raises_when_file_not_found(self, tmp_path):
        """read_repo_file raises FileNotFoundError when the target file is absent."""
        with pytest.raises(FileNotFoundError, match="file not found in repo"):
            read_repo_file(tmp_path, "nonexistent.md")

    def test_raises_for_embedded_dotdot_in_subpath(self, tmp_path):
        """read_repo_file raises ValueError for paths with '..' embedded mid-path."""
        (tmp_path / "safe.txt").write_text("content")

        with pytest.raises(ValueError, match="not a safe relative path"):
            read_repo_file(tmp_path, "memos/../../../etc/passwd")


class TestReadAgentsMd:
    def test_returns_file_content_when_agents_md_exists(self, tmp_path):
        """read_agents_md returns the full text of AGENTS.md when the file is present."""
        expected = "# Claude Memos Index\n\nsome content\n"
        (tmp_path / "AGENTS.md").write_text(expected)

        result = read_agents_md(tmp_path)

        assert result == expected

    def test_raises_when_agents_md_absent(self, tmp_path):
        """read_agents_md raises FileNotFoundError when AGENTS.md does not exist."""
        with pytest.raises(FileNotFoundError):
            read_agents_md(tmp_path)
