import pytest
import hashlib
import time

from core.runner import run_python_code, run_python_file
from core import github_svc
from views.shared import chat
from views.shared.code_workspace import execute_terminal_command
from core.ledger import Ledger


def test_runner_executes_valid_code():
    """Verify that runner executes valid Python code in isolated subprocess."""
    code = 'print("Hello from CollabSpace Runner")\nx = 10 + 20\nprint(f"Result: {x}")'
    res = run_python_code(code, filename="test_calc.py", timeout_seconds=5)

    assert res["exit_code"] == 0
    assert res["timed_out"] is False
    assert "Hello from CollabSpace Runner" in res["stdout"]
    assert "Result: 30" in res["stdout"]
    assert res["stderr"] == ""
    assert res["execution_time"] >= 0.0


def test_runner_captures_runtime_errors_safely():
    """Verify that runner captures syntax and runtime exceptions without crashing."""
    code = 'def divide(): return 1 / 0\ndivide()'
    res = run_python_code(code, filename="test_error.py", timeout_seconds=5)

    assert res["exit_code"] != 0
    assert res["timed_out"] is False
    assert "ZeroDivisionError" in res["stderr"]


def test_runner_enforces_timeout_and_terminates():
    """Verify that runner strictly terminates subprocess when execution exceeds timeout."""
    code = 'import time\ntime.sleep(5)\nprint("Should not print")'
    res = run_python_code(code, filename="test_timeout.py", timeout_seconds=1)

    assert res["timed_out"] is True
    assert res["exit_code"] == -1
    assert "[TIMEOUT]" in res["stderr"]
    assert "Should not print" not in res["stdout"]


def test_runner_nonexistent_file():
    """Verify safe error response when file does not exist."""
    res = run_python_file("non_existent_script_12345.py")
    assert res["exit_code"] != 0
    assert "File not found" in res["stderr"]


def test_github_svc_file_tree_and_read():
    """Verify GitHub service returns file tree and reads content."""
    tree = github_svc.get_file_tree()
    assert isinstance(tree, list)
    assert "core/audit.py" in tree
    assert "README.md" in tree

    content = github_svc.read_file("core/audit.py")
    assert content is not None
    assert "verify_block" in content


def test_github_svc_commit_and_log():
    """Verify committing file updates repository state and prepends to commit log."""
    new_content = 'print("Updated validator code for test")\n'
    result = github_svc.commit_file(
        path="core/audit.py",
        content=new_content,
        message="test: update validator logic",
        branch="student/m3-validator",
        author="Alex Chen"
    )

    assert "sha" in result
    assert len(result["sha"]) == 7
    assert result["message"] == "test: update validator logic"

    read_back = github_svc.read_file("core/audit.py")
    assert read_back == new_content

    commits = github_svc.get_commit_log(limit=5)
    assert len(commits) > 0
    assert commits[0]["sha"] == result["sha"]
    assert commits[0]["message"] == "test: update validator logic"


def test_github_svc_branches():
    """Verify branches list includes expected branches."""
    branches = github_svc.get_branches()
    assert "main" in branches
    assert "student/m3-validator" in branches


def test_chat_channel_permissions_matrix():
    """Verify that Student is blocked from sponsor channel and Sponsor blocked from team channel."""
    assert chat.can_access_channel("Student", "team") is True
    assert chat.can_access_channel("Student", "sponsor") is False

    assert chat.can_access_channel("Mentor", "team") is True
    assert chat.can_access_channel("Mentor", "sponsor") is True

    assert chat.can_access_channel("Sponsor", "team") is False
    assert chat.can_access_channel("Sponsor", "sponsor") is True


def test_chat_student_cannot_access_sponsor_channel():
    """Verify that Student querying sponsor channel raises PermissionError."""
    with pytest.raises(PermissionError) as exc_get:
        chat.get_messages("sponsor", "Student")
    assert "Access Denied" in str(exc_get.value)

    with pytest.raises(PermissionError) as exc_send:
        chat.send_message("sponsor", "Student", "Alex Chen", "Unauthorized message")
    assert "Access Denied" in str(exc_send.value)


def test_chat_send_and_ledger_hashing():
    """Verify sending message hashes content into ledger without exposing raw private text in ledger payload."""
    storage = []
    ledger = Ledger(storage=storage)

    secret_text = "Private discussion regarding milestone 3 verification criteria."
    res = chat.send_message(
        channel="team",
        role="Student",
        author="Alex Chen",
        text=secret_text,
        ledger=ledger
    )

    expected_hash = hashlib.sha256(secret_text.encode("utf-8")).hexdigest()
    assert res["msg_hash"] == expected_hash

    msgs = chat.get_messages("team", "Student")
    assert any(m["text"] == secret_text for m in msgs)

    hashed_entries = [e for e in storage if e["entry_type"] == "MESSAGE_HASHED"]
    assert len(hashed_entries) >= 1

    last_hashed = hashed_entries[-1]
    assert last_hashed["payload"]["msg_hash"] == expected_hash
    assert last_hashed["payload"]["channel"] == "team"
    assert secret_text not in str(last_hashed["payload"].values())


def test_terminal_commands_execution():
    """Verify terminal commands: help, ls, branch, status, log, and run."""
    storage = []
    ledger = Ledger(storage=storage)

    out_help = execute_terminal_command("help")
    assert "CollabSpace Terminal" in out_help
    assert "run <file.py>" in out_help

    out_ls = execute_terminal_command("ls")
    assert "core/audit.py" in out_ls

    out_branch = execute_terminal_command("branch")
    assert "* student/m3-validator" in out_branch

    out_status = execute_terminal_command("status")
    assert "On branch student/m3-validator" in out_status

    out_log = execute_terminal_command("log")
    assert "commit" in out_log

    sample_code = 'import hashlib\nprint("SANDBOX TEST: OK")\nprint(hashlib.sha256(b"abc").hexdigest()[:8])'
    out_run = execute_terminal_command("run core/audit.py", editor_code=sample_code, active_file="core/audit.py")
    assert "SANDBOX TEST: OK" in out_run
    assert "ba7816bf" in out_run
    assert "exit code 0" in out_run

    out_commit = execute_terminal_command(
        "commit chore: terminal commit test",
        editor_code=sample_code,
        active_file="core/audit.py",
        ledger=ledger
    )
    assert "chore: terminal commit test" in out_commit
    assert len(storage) >= 2
    assert storage[-1]["entry_type"] == "COMMIT"
