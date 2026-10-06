import hashlib
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    from github import Github, GithubException
    HAS_PYGITHUB = True
except ImportError:
    HAS_PYGITHUB = False


DEFAULT_FILES = {
    "core/audit.py": """import hashlib

def verify_block(prev_hash: str, payload_str: str) -> str:
    raw = f"{prev_hash}{payload_str}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

if __name__ == "__main__":
    test_h = verify_block("0"*64, "genesis")
    print("Validator Loaded.")
    print(f"Sample Digest: {test_h[:16]}...")
""",
    "core/test.py": """def run_audit_suite():
    print("Starting Audit Test Suite...")
    print("Test 1: Hash chain integrity -> PASS")
    print("Test 2: Schema drift check -> PASS")
    print("Status: 2/2 tests passed successfully.")

if __name__ == "__main__":
    run_audit_suite()
""",
    "README.md": """# sponsor-org/audit-core
Automated Audit Engine v1.0
Cryptographic ledger validation for realtime escrow milestones.

## Branches
- `main`: Production release
- `student/m3-validator`: Student milestone active branch
"""
}

DEFAULT_COMMITS = [
    {
        "sha": "8f10b3a",
        "message": "feat: ledger validator initial implementation",
        "author": "Alex Chen",
        "date": "2026-10-06 09:30:00",
        "branch": "student/m3-validator"
    },
    {
        "sha": "5e2b109",
        "message": "feat: anomaly detection model isolation forest",
        "author": "Marcus Shaw",
        "date": "2026-10-05 16:45:00",
        "branch": "main"
    },
    {
        "sha": "1c7a42d",
        "message": "init: data ingestion engine setup",
        "author": "Marcus Shaw",
        "date": "2026-10-04 11:15:00",
        "branch": "main"
    }
]

_fallback_state = {
    "files": dict(DEFAULT_FILES),
    "commits": list(DEFAULT_COMMITS),
    "branches": ["main", "student/m3-validator", "feat/audit-parser"]
}


def _get_mock_state() -> Dict[str, Any]:
    """Retrieves session-persistent or fallback state for mock GitHub backend."""
    if HAS_STREAMLIT:
        try:
            if "mock_github_state" not in st.session_state:
                st.session_state["mock_github_state"] = {
                    "files": dict(DEFAULT_FILES),
                    "commits": list(DEFAULT_COMMITS),
                    "branches": ["main", "student/m3-validator", "feat/audit-parser"]
                }
            return st.session_state["mock_github_state"]
        except Exception:
            return _fallback_state
    return _fallback_state


def _get_github_client():
    """Attempts to initialize live PyGithub client from secrets, returning None on failure."""
    if not HAS_PYGITHUB or not HAS_STREAMLIT:
        return None, None
    try:
        secrets = getattr(st, "secrets", {})
        token = secrets.get("GITHUB_TOKEN")
        repo_name = secrets.get("GITHUB_REPO")
        if token and repo_name:
            gh = Github(token)
            repo = gh.get_repo(repo_name)
            return gh, repo
    except Exception:
        pass
    return None, None


def is_live_github() -> bool:
    """Returns True if live PyGithub client is authenticated and accessible."""
    gh, repo = _get_github_client()
    return repo is not None


def get_file_tree() -> List[str]:
    """Returns list of relative file paths in repository."""
    gh, repo = _get_github_client()
    if repo:
        try:
            tree = repo.get_git_tree("HEAD", recursive=True)
            return [element.path for element in tree.tree if element.type == "blob"]
        except Exception:
            pass
    state = _get_mock_state()
    return sorted(list(state["files"].keys()))


def read_file(path: str) -> Optional[str]:
    """Reads content of a file from repository."""
    gh, repo = _get_github_client()
    if repo:
        try:
            content_file = repo.get_contents(path)
            return content_file.decoded_content.decode("utf-8")
        except Exception:
            pass
    state = _get_mock_state()
    return state["files"].get(path, "")


def commit_file(path: str, content: str, message: str, branch: str = "student/m3-validator", author: str = "Alex Chen") -> Dict[str, Any]:
    """Commits or updates a file in the repository."""
    gh, repo = _get_github_client()
    if repo:
        try:
            try:
                contents = repo.get_contents(path, ref=branch)
                result = repo.update_file(contents.path, message, content, contents.sha, branch=branch)
                return {
                    "sha": result["commit"].sha[:7],
                    "message": message,
                    "branch": branch,
                    "live": True
                }
            except GithubException:
                result = repo.create_file(path, message, content, branch=branch)
                return {
                    "sha": result["commit"].sha[:7],
                    "message": message,
                    "branch": branch,
                    "live": True
                }
        except Exception:
            pass

    state = _get_mock_state()
    state["files"][path] = content
    raw_sig = f"{path}|{message}|{time.time()}".encode("utf-8")
    new_sha = hashlib.sha1(raw_sig).hexdigest()[:7]
    commit_record = {
        "sha": new_sha,
        "message": message,
        "author": author,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "branch": branch
    }
    state["commits"].insert(0, commit_record)
    return {
        "sha": new_sha,
        "message": message,
        "branch": branch,
        "live": False
    }


def get_commit_log(limit: int = 10) -> List[Dict[str, Any]]:
    """Returns list of recent commits."""
    gh, repo = _get_github_client()
    if repo:
        try:
            commits = repo.get_commits()[:limit]
            return [
                {
                    "sha": c.sha[:7],
                    "message": c.commit.message.split("\n")[0],
                    "author": c.commit.author.name if c.commit.author else "Unknown",
                    "date": c.commit.author.date.strftime("%Y-%m-%d %H:%M:%S") if c.commit.author else "",
                    "branch": "main"
                }
                for c in commits
            ]
        except Exception:
            pass
    state = _get_mock_state()
    return state["commits"][:limit]


def get_branches() -> List[str]:
    """Returns list of repository branches."""
    gh, repo = _get_github_client()
    if repo:
        try:
            return [b.name for b in repo.get_branches()]
        except Exception:
            pass
    state = _get_mock_state()
    return state.get("branches", ["main", "student/m3-validator"])
