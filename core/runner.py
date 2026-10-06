import os
import sys
import subprocess
import tempfile
import time
from typing import Dict, Any, Optional

DEFAULT_TIMEOUT_SECONDS = 10

def run_python_code(
    code: str,
    filename: str = "main.py",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    extra_files: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Executes Python code in an isolated subprocess inside a temporary directory.
    Enforces a strict execution timeout (default 10s).
    
    Returns a dictionary:
    {
        "stdout": str,
        "stderr": str,
        "exit_code": int,
        "timed_out": bool,
        "execution_time": float
    }
    """
    start_time = time.time()
    with tempfile.TemporaryDirectory() as tmpdir:
        if extra_files:
            for extra_name, extra_content in extra_files.items():
                extra_path = os.path.join(tmpdir, extra_name)
                os.makedirs(os.path.dirname(extra_path), exist_ok=True)
                with open(extra_path, "w", encoding="utf-8") as ef:
                    ef.write(extra_content)

        target_path = os.path.join(tmpdir, filename)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            result = subprocess.run(
                [sys.executable, target_path],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False
            )
            elapsed = time.time() - start_time
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "timed_out": False,
                "execution_time": round(elapsed, 3)
            }
        except subprocess.TimeoutExpired as exc:
            elapsed = time.time() - start_time
            stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout.decode("utf-8", "replace") if exc.stdout else "")
            stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr.decode("utf-8", "replace") if exc.stderr else "")
            return {
                "stdout": stdout,
                "stderr": f"{stderr}\n[TIMEOUT] Execution exceeded {timeout_seconds}s limit." if stderr else f"[TIMEOUT] Execution exceeded {timeout_seconds}s limit.",
                "exit_code": -1,
                "timed_out": True,
                "execution_time": round(elapsed, 3)
            }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "stdout": "",
                "stderr": f"[ERROR] Subprocess launch error: {str(e)}",
                "exit_code": 1,
                "timed_out": False,
                "execution_time": round(elapsed, 3)
            }


def run_python_file(
    file_path: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    """
    Executes an existing Python file from disk in a subprocess with timeout.
    """
    start_time = time.time()
    if not os.path.exists(file_path):
        return {
            "stdout": "",
            "stderr": f"[ERROR] File not found: {file_path}",
            "exit_code": 1,
            "timed_out": False,
            "execution_time": 0.0
        }

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code_content = f.read()
        return run_python_code(
            code=code_content,
            filename=os.path.basename(file_path),
            timeout_seconds=timeout_seconds
        )
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "stdout": "",
            "stderr": f"[ERROR] Could not read or execute file: {str(e)}",
            "exit_code": 1,
            "timed_out": False,
            "execution_time": round(elapsed, 3)
        }
