import logging
from ..utils.logger import get_logger

security_logger = get_logger("DataAgent.Security")

def log_code_execution(code: str, user_id: int = None, mode: str = "sandbox"):
    security_logger.info(f"Execution request by user={user_id} via mode={mode}. Code length={len(code)} chars.")

def log_security_violation(reason: str, code: str, user_id: int = None):
    security_logger.warning(f"SECURITY GATE BLOCKED user={user_id}. Reason: {reason}. Snippet: {code[:100]}...")

def log_sandbox_result(success: bool, execution_time: float, error: str = None):
    if success:
        security_logger.info(f"Sandbox execution passed in {execution_time}s.")
    else:
        security_logger.error(f"Sandbox execution failed in {execution_time}s: {error}")
