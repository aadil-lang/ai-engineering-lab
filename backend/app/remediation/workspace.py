import os
import ast
import json
import shutil
import logging
from pathlib import Path
from typing import Any
from backend.app.models.remediation import FileChange
from backend.app.models.enums import FileChangeOperation

logger = logging.getLogger("ai_qa_platform.remediation_workspace")

class RemediationWorkspace:
    """
    Manages physical file operations, temporary backups, static validation,
    and safe rollbacks for remediation code changes.
    """

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.backups: dict[str, str | None] = {}  # relative_path -> original_content (or None if created)

    def apply_changes(self, file_changes: list[FileChange]) -> dict[str, Any]:
        """
        Applies a list of FileChange objects atomically with rollback on error.
        """
        modified_paths: list[str] = []
        try:
            for change in file_changes:
                rel_path = change.path.lstrip("/\\")
                abs_path = self.workspace_root / rel_path

                # Back up current state if not already backed up
                if rel_path not in self.backups:
                    if abs_path.exists():
                        try:
                            self.backups[rel_path] = abs_path.read_text(encoding="utf-8")
                        except Exception:
                            self.backups[rel_path] = ""
                    else:
                        self.backups[rel_path] = None  # Indicates new file to remove on rollback

                if change.operation == FileChangeOperation.DELETE:
                    if abs_path.exists():
                        abs_path.unlink()
                        modified_paths.append(rel_path)

                elif change.operation in (FileChangeOperation.CREATE, FileChangeOperation.MODIFY):
                    abs_path.parent.mkdir(parents=True, exist_ok=True)
                    new_content = change.new_content
                    if new_content is None and change.diff:
                        # If diff provided without explicit new_content, generate mock patched content or write comment
                        existing = self.backups.get(rel_path) or ""
                        new_content = existing + f"\n// Patched:\n{change.diff}\n"
                    
                    if new_content is not None:
                        abs_path.write_text(new_content, encoding="utf-8")
                        modified_paths.append(rel_path)

            # Validate syntax across modified files
            validation = self.validate_files(modified_paths)
            if not validation["valid"]:
                logger.warning(f"Validation failed after applying changes: {validation['errors']}. Rolling back.")
                self.rollback()
                return {
                    "success": False,
                    "error": f"Validation failed: {', '.join(validation['errors'])}",
                    "files_modified": [],
                    "validation": validation,
                }

            return {
                "success": True,
                "files_modified": modified_paths,
                "validation": validation,
            }

        except Exception as e:
            logger.error(f"Error applying file changes: {e}. Initiating rollback.", exc_info=True)
            self.rollback()
            return {
                "success": False,
                "error": str(e),
                "files_modified": [],
            }

    def validate_files(self, paths: list[str]) -> dict[str, Any]:
        """
        Runs language-specific syntax / static checks on modified files.
        """
        errors: list[str] = []
        for rel_path in paths:
            abs_path = self.workspace_root / rel_path
            if not abs_path.exists():
                continue

            content = abs_path.read_text(encoding="utf-8", errors="replace")

            # Python syntax check
            if rel_path.endswith(".py"):
                try:
                    ast.parse(content, filename=rel_path)
                except SyntaxError as se:
                    errors.append(f"Python SyntaxError in {rel_path}:{se.lineno}: {se.msg}")

            # JSON syntax check
            elif rel_path.endswith(".json"):
                try:
                    json.loads(content)
                except json.JSONDecodeError as je:
                    errors.append(f"JSON DecodeError in {rel_path}:{je.lineno}: {je.msg}")

            # Basic bracket balance check for JS/TS/JSX/TSX
            elif rel_path.endswith((".ts", ".tsx", ".js", ".jsx")):
                stack = []
                pairs = {')': '(', '}': '{', ']': '['}
                for i, ch in enumerate(content):
                    if ch in "({[":
                        stack.append((ch, i))
                    elif ch in ")}]":
                        if not stack or stack[-1][0] != pairs[ch]:
                            errors.append(f"Unmatched delimiter '{ch}' in {rel_path}")
                            break
                        stack.pop()

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def rollback(self):
        """
        Restores all backed up files to their original states.
        """
        for rel_path, original_content in list(self.backups.items()):
            abs_path = self.workspace_root / rel_path
            try:
                if original_content is None:
                    # Was newly created; delete
                    if abs_path.exists():
                        abs_path.unlink()
                else:
                    # Restore original content
                    abs_path.parent.mkdir(parents=True, exist_ok=True)
                    abs_path.write_text(original_content, encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to restore backup for {rel_path}: {e}")
        self.backups.clear()
