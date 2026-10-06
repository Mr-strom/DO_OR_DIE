import os
import streamlit as st
from typing import Dict, Any, Optional

from core.runner import run_python_code
from core import github_svc
from core.ui import notify_ledger_action


def execute_terminal_command(
    cmd_str: str,
    editor_code: str = "",
    active_file: str = "core/audit.py",
    ledger: Any = None
) -> str:
    """
    Executes terminal commands: ls, cat, log, branch, status, commit, run, help.
    Returns output string to display in terminal.
    """
    tokens = cmd_str.strip().split()
    if not tokens:
        return ""

    cmd = tokens[0].lower()
    args = tokens[1:]

    if cmd == "help":
        return """CollabSpace Terminal v1.0
Commands:
  ls                  - List files in current repository
  cat <file>          - Display contents of a file
  run <file.py>       - Run python script in isolated sandbox (10s timeout)
  log                 - View recent commit log
  branch              - View repository branches
  status              - Show current workspace and git status
  commit <message>    - Commit current buffer to repository and audit ledger
  help                - Display this help message"""

    elif cmd == "ls":
        tree = github_svc.get_file_tree()
        lines = ["├── " + f for f in tree]
        return "\n".join(lines)

    elif cmd == "cat":
        if not args:
            return "Usage: cat <file_path>"
        target_path = args[0]
        if target_path == active_file or target_path == os.path.basename(active_file):
            return editor_code
        content = github_svc.read_file(target_path)
        if content:
            return content
        return f"cat: {target_path}: No such file or directory"

    elif cmd == "branch":
        branches = github_svc.get_branches()
        out = []
        for b in branches:
            prefix = "* " if b == "student/m3-validator" else "  "
            out.append(f"{prefix}{b}")
        return "\n".join(out)

    elif cmd == "status":
        tree = github_svc.get_file_tree()
        return f"""On branch student/m3-validator
Your branch is up to date with 'origin/student/m3-validator'.

Changes to be committed:
  modified:   {active_file}

Tracked files in workspace: {len(tree)} files"""

    elif cmd == "log":
        commits = github_svc.get_commit_log(limit=6)
        out = []
        for c in commits:
            out.append(f"commit {c['sha']} ({c.get('branch', 'main')})\nAuthor: {c['author']}\nDate:   {c['date']}\n\n    {c['message']}\n")
        return "\n".join(out)

    elif cmd == "commit":
        if not args:
            return "Usage: commit <commit_message>"
        message = " ".join(args)
        result = github_svc.commit_file(
            path=active_file,
            content=editor_code,
            message=message,
            branch="student/m3-validator",
            author="Alex Chen"
        )
        ledger_h = ""
        if ledger:
            ledger_h = ledger.append("Student", "COMMIT", {
                "sha": result["sha"],
                "file": active_file,
                "message": message
            })
            notify_ledger_action(f"Committed {result['sha']}", ledger_h)
        return f"[student/m3-validator {result['sha']}] {message}\n 1 file changed, {len(editor_code.splitlines())} insertions(+)\nLedger Hash: {ledger_h[:16]}..."

    elif cmd == "run":
        if not args:
            return "Usage: run <file.py>"
        target = args[0]
        if target in (active_file, os.path.basename(active_file), "audit.py", "core/audit.py"):
            code_to_run = editor_code
            filename = os.path.basename(target)
        else:
            file_content = github_svc.read_file(target)
            if not file_content:
                return f"python: can't open file '{target}': [Errno 2] No such file or directory"
            code_to_run = file_content
            filename = os.path.basename(target)

        res = run_python_code(code_to_run, filename=filename, timeout_seconds=10)
        output_parts = []
        if res["stdout"]:
            output_parts.append(res["stdout"].strip())
        if res["stderr"]:
            output_parts.append(res["stderr"].strip())
        
        status_line = f"Process finished with exit code {res['exit_code']} (took {res['execution_time']}s)"
        output_parts.append(status_line)
        return "\n".join(output_parts)

    else:
        return f"terminal: command not found: {cmd}. Type 'help' for available commands."


def render_code_workspace(ledger: Any = None):
    """
    Renders the student code workspace with repository tree, code editor,
    commit buttons, and integrated terminal running isolated subprocesses.
    """
    if "editor_active_file" not in st.session_state:
        st.session_state["editor_active_file"] = "core/audit.py"

    active_file = st.session_state["editor_active_file"]

    if "editor_code_buffer" not in st.session_state:
        st.session_state["editor_code_buffer"] = github_svc.read_file(active_file) or ""

    if "terminal_history" not in st.session_state:
        st.session_state["terminal_history"] = [
            ("python core/audit.py", "Validator Loaded.\nProcess finished with exit code 0 (took 0.04s)")
        ]

    col_tree, col_editor = st.columns([1, 3])

    with col_tree:
        st.markdown("**Repo Tree**")
        tree_files = github_svc.get_file_tree()
        selected_file = st.selectbox(
            "Select File",
            options=tree_files,
            index=tree_files.index(active_file) if active_file in tree_files else 0,
            label_visibility="collapsed"
        )
        if selected_file != active_file:
            st.session_state["editor_active_file"] = selected_file
            st.session_state["editor_code_buffer"] = github_svc.read_file(selected_file) or ""
            st.rerun()

        st.caption("Active branch: `student/m3-validator`")
        is_live = github_svc.is_live_github()
        badge_color = "#16A34A" if is_live else "#F97316"
        badge_text = "Live GitHub" if is_live else "Local Git Store"
        st.markdown(
            f'<span style="font-size:0.75rem; background:#F1F5F9; color:{badge_color}; padding:2px 6px; border-radius:4px; font-weight:600;">● {badge_text}</span>',
            unsafe_allow_html=True
        )

    with col_editor:
        code_input = st.text_area(
            f"Editor: `{active_file}`",
            value=st.session_state["editor_code_buffer"],
            height=200,
            key="code_editor_textarea"
        )
        st.session_state["editor_code_buffer"] = code_input

        col_c1, col_c2, col_c3 = st.columns([1, 1, 2])
        with col_c1:
            if st.button("Commit to GitHub", key="btn_commit_github"):
                res = github_svc.commit_file(
                    path=active_file,
                    content=code_input,
                    message=f"feat: update {active_file}",
                    branch="student/m3-validator"
                )
                if ledger:
                    new_h = ledger.append("Student", "COMMIT", {"sha": res["sha"], "file": active_file})
                    notify_ledger_action(f"Committed {res['sha']}", new_h)
                st.rerun()

        with col_c2:
            if st.button("Submit M3 for Review", key="btn_submit_m3"):
                if ledger:
                    new_h = ledger.append("Student", "SUBMISSION", {"milestone": "M3", "sha": "9a3f21c"})
                    notify_ledger_action("Submitted M3", new_h)
                st.rerun()

        with col_c3:
            if st.button("Run in Sandbox (`run`)", key="btn_run_sandbox"):
                out = execute_terminal_command(
                    f"run {active_file}",
                    editor_code=code_input,
                    active_file=active_file,
                    ledger=ledger
                )
                st.session_state["terminal_history"].append((f"run {active_file}", out))
                st.rerun()

    st.markdown("---")
    st.markdown("**Interactive Terminal** *(Run `help`, `ls`, `cat <file>`, `run <file.py>`, `log`, `branch`, `status`, `commit <msg>`)*")

    with st.form("terminal_form", clear_on_submit=True):
        cmd_col, exec_col = st.columns([5, 1])
        with cmd_col:
            entered_cmd = st.text_input("Console Input", placeholder="run core/audit.py", label_visibility="collapsed")
        with exec_col:
            cmd_submitted = st.form_submit_button("Execute", use_container_width=True)

        if cmd_submitted and entered_cmd:
            cmd_out = execute_terminal_command(
                entered_cmd,
                editor_code=st.session_state["editor_code_buffer"],
                active_file=active_file,
                ledger=ledger
            )
            st.session_state["terminal_history"].append((entered_cmd, cmd_out))
            st.rerun()

    last_cmd, last_out = st.session_state["terminal_history"][-1] if st.session_state["terminal_history"] else ("", "")
    st.markdown(f"<div style='font-family: JetBrains Mono, monospace; font-size: 0.8rem; color: #64748B; margin-bottom: 4px;'>$ {last_cmd}</div>", unsafe_allow_html=True)
    st.code(last_out, language="bash")
