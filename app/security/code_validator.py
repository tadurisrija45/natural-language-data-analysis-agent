import ast
from typing import Tuple, List
from .security_logger import log_security_violation

FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "urllib", "requests", "http",
    "ftplib", "pickle", "ctypes", "threading", "multiprocessing", "pty", "commands",
    "posix", "nt", "builtins", "__builtin__", "importlib", "gc", "winreg", "webbrowser"
}

FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "__import__", "open", "breakpoint", "input",
    "exit", "quit", "help"
}

FORBIDDEN_ATTRIBUTES = {
    "__subclasses__", "__globals__", "__code__", "__bases__", "__class__",
    "__mro__", "__dict__", "__closure__", "__builtins__"
}

class SecurityGateVisitor(ast.NodeVisitor):
    def __init__(self):
        self.violations: List[str] = []

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.name.split(".")[0]
            if name in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden module import: '{name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            root = node.module.split(".")[0]
            if root in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden module import from: '{root}'")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.violations.append(f"Forbidden function call: '{node.func.id}()'")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr in FORBIDDEN_ATTRIBUTES:
            self.violations.append(f"Forbidden attribute access: '{node.attr}'")
        self.generic_visit(node)


class CodeValidator:
    @staticmethod
    def validate_code(code: str, user_id: int = None) -> Tuple[bool, List[str]]:
        """
        Statically inspect Python code using AST to ensure it contains no malicious
        or unsafe patterns before it is passed to sandbox execution.
        """
        if not code or not code.strip():
            return False, ["Code string is empty."]

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"Syntax error in generated code: {e.msg} at line {e.lineno}"]

        visitor = SecurityGateVisitor()
        visitor.visit(tree)

        if visitor.violations:
            for v in visitor.violations:
                log_security_violation(v, code, user_id=user_id)
            return False, visitor.violations

        return True, []
