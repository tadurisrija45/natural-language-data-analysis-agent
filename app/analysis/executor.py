from typing import Dict, Any, Tuple
from ..security.sandbox import ExecutionSandbox, SandboxExecutionResult
from ..utils.logger import get_logger

logger = get_logger("DataAgent.Executor")

class CodeExecutor:
    @staticmethod
    def run_analysis_code(
        code: str,
        data_files: Dict[str, str],
        user_id: int = None
    ) -> SandboxExecutionResult:
        """
        Execute generated Python analysis code in the sandbox.
        """
        logger.info(f"Dispatching code execution for user_id={user_id} with {len(data_files)} datasets.")
        result = ExecutionSandbox.execute(
            code=code,
            data_files=data_files,
            user_id=user_id
        )
        return result
