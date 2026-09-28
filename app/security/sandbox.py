import os
import sys
import json
import time
import shutil
import tempfile
import subprocess
from typing import Dict, Any, Tuple, Optional
from flask import current_app

from .code_validator import CodeValidator
from .resource_limits import EXECUTION_TIMEOUT_SECONDS, MAX_MEMORY_MB
from .security_logger import log_code_execution, log_sandbox_result, security_logger


class SandboxExecutionResult:
    def __init__(
        self,
        success: bool,
        result_data: Any = None,
        error: Optional[str] = None,
        execution_time: float = 0.0,
        mode: str = "subprocess"
    ):
        self.success = success
        self.result_data = result_data
        self.error = error
        self.execution_time = execution_time
        self.mode = mode

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "result_data": self.result_data,
            "error": self.error,
            "execution_time": self.execution_time,
            "mode": self.mode,
        }


class ExecutionSandbox:
    @staticmethod
    def _is_docker_available() -> bool:
        """Check if Docker CLI and daemon are responding."""
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3
            )
            return res.returncode == 0
        except Exception:
            return False

    @classmethod
    def execute(
        cls,
        code: str,
        data_files: Dict[str, str],
        user_id: int = None,
        timeout: int = EXECUTION_TIMEOUT_SECONDS
    ) -> SandboxExecutionResult:
        """
        Execute code within a secured sandbox environment.
        1. Pass through Security Gate (AST check).
        2. Try Docker container sandbox if configured and available.
        3. Fall back to restricted local subprocess sandbox.
        """
        # Step 1: Security Gate validation
        valid, violations = CodeValidator.validate_code(code, user_id=user_id)
        if not valid:
            err = f"Security Gate Violation: {'; '.join(violations)}"
            log_sandbox_result(False, 0.0, err)
            return SandboxExecutionResult(success=False, error=err, mode="security_gate")

        use_docker = False
        try:
            if current_app and current_app.config.get("USE_DOCKER_SANDBOX"):
                use_docker = cls._is_docker_available()
        except Exception:
            pass

        if use_docker:
            return cls._execute_docker(code, data_files, user_id=user_id, timeout=timeout)
        else:
            return cls._execute_subprocess(code, data_files, user_id=user_id, timeout=timeout)

    @classmethod
    def _execute_subprocess(
        cls,
        code: str,
        data_files: Dict[str, str],
        user_id: int = None,
        timeout: int = EXECUTION_TIMEOUT_SECONDS
    ) -> SandboxExecutionResult:
        """Isolated local subprocess sandbox execution with strict limits and sanitized environment."""
        log_code_execution(code, user_id=user_id, mode="local_isolated_subprocess")
        start_time = time.time()

        temp_dir = tempfile.mkdtemp(prefix="dataagent_sandbox_")
        payload_file = os.path.join(temp_dir, "payload.json")

        runner_script = os.path.join(
            os.path.dirname(__file__), "..", "..", "docker", "sandbox_runner.py"
        )
        runner_script = os.path.abspath(runner_script)

        try:
            payload = {
                "code": code,
                "data_files": data_files
            }
            with open(payload_file, "w", encoding="utf-8") as f:
                json.dump(payload, f)

            # Strip down environment variables to avoid leaking credentials but retain package discovery
            restricted_env = {
                "PATH": os.environ.get("PATH", ""),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
                "APPDATA": os.environ.get("APPDATA", ""),
                "USERPROFILE": os.environ.get("USERPROFILE", ""),
                "PYTHONPATH": os.pathsep.join(sys.path),
                "TEMP": temp_dir,
                "TMP": temp_dir,
                "PYTHONUNBUFFERED": "1",
                "PYTHONDONTWRITEBYTECODE": "1"
            }

            proc = subprocess.Popen(
                [sys.executable, runner_script, payload_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=temp_dir,
                env=restricted_env,
                text=True
            )

            stdout, stderr = proc.communicate(timeout=timeout)
            elapsed = round(time.time() - start_time, 4)

            if proc.returncode != 0 and not stdout:
                err_msg = stderr.strip() or f"Process exited with code {proc.returncode}"
                log_sandbox_result(False, elapsed, err_msg)
                return SandboxExecutionResult(success=False, error=err_msg, execution_time=elapsed, mode="subprocess")

            try:
                # Find JSON block in stdout
                res_json = json.loads(stdout.strip())
                success = res_json.get("success", False)
                result_data = res_json.get("result_data")
                error = res_json.get("error")
                log_sandbox_result(success, elapsed, error)
                return SandboxExecutionResult(
                    success=success,
                    result_data=result_data,
                    error=error,
                    execution_time=elapsed,
                    mode="subprocess"
                )
            except json.JSONDecodeError:
                err_msg = f"Invalid sandbox output: {stdout[:200]}"
                log_sandbox_result(False, elapsed, err_msg)
                return SandboxExecutionResult(success=False, error=err_msg, execution_time=elapsed, mode="subprocess")

        except subprocess.TimeoutExpired:
            proc.kill()
            elapsed = round(time.time() - start_time, 4)
            err_msg = f"Execution timed out after {timeout} seconds."
            log_sandbox_result(False, elapsed, err_msg)
            return SandboxExecutionResult(success=False, error=err_msg, execution_time=elapsed, mode="subprocess")
        except Exception as e:
            elapsed = round(time.time() - start_time, 4)
            log_sandbox_result(False, elapsed, str(e))
            return SandboxExecutionResult(success=False, error=str(e), execution_time=elapsed, mode="subprocess")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _execute_docker(
        cls,
        code: str,
        data_files: Dict[str, str],
        user_id: int = None,
        timeout: int = EXECUTION_TIMEOUT_SECONDS
    ) -> SandboxExecutionResult:
        """Containerized Docker sandbox execution."""
        log_code_execution(code, user_id=user_id, mode="docker_container")
        start_time = time.time()
        temp_dir = tempfile.mkdtemp(prefix="dataagent_docker_")
        payload_file = os.path.join(temp_dir, "payload.json")

        try:
            payload = {"code": code, "data_files": data_files}
            with open(payload_file, "w", encoding="utf-8") as f:
                json.dump(payload, f)

            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", f"{MAX_MEMORY_MB}m",
                "--cpus", "1.0",
                "-v", f"{temp_dir}:/sandbox/workspace",
                "dataagent-sandbox:latest",
                "/sandbox/workspace/payload.json"
            ]

            proc = subprocess.run(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True
            )

            elapsed = round(time.time() - start_time, 4)
            if proc.returncode != 0:
                err_msg = proc.stderr.strip() or f"Docker container exited with code {proc.returncode}"
                return SandboxExecutionResult(success=False, error=err_msg, execution_time=elapsed, mode="docker")

            res_json = json.loads(proc.stdout.strip())
            return SandboxExecutionResult(
                success=res_json.get("success", False),
                result_data=res_json.get("result_data"),
                error=res_json.get("error"),
                execution_time=elapsed,
                mode="docker"
            )
        except Exception as e:
            elapsed = round(time.time() - start_time, 4)
            return SandboxExecutionResult(success=False, error=str(e), execution_time=elapsed, mode="docker")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
