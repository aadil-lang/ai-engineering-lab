import ast
import os
from pathlib import Path


def test_no_mcp_imports_in_domain_and_control_plane():
    """
    Requirement 31:
    Proves backend/app/control_plane/ and backend/app/models/
    do NOT import 'mcp'.
    The MCP SDK must strictly remain an external adapter layer.
    """
    repo_root = Path(__file__).parent.parent
    prohibited_dirs = [
        repo_root / "app" / "control_plane",
        repo_root / "app" / "models",
        repo_root / "app" / "repositories",
        repo_root / "app" / "services",
        repo_root / "app" / "prediction",
    ]

    for target_dir in prohibited_dirs:
        assert target_dir.exists(), f"Target directory not found: {target_dir}"
        for py_file in target_dir.glob("**/*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith("mcp"), (
                            f"Prohibited MCP import in domain file '{py_file.name}': import {alias.name}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert not node.module.startswith("mcp"), (
                            f"Prohibited MCP import in domain file '{py_file.name}': from {node.module} import ..."
                        )
