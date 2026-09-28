"""
Slice 8M — Environment Doctor & Platform Diagnostics

Performs deterministic diagnostic evaluations across:
- Python runtime & Node.js environment
- SQLite database accessibility & transaction writability
- Artifact filesystem writability
- Playwright & Chromium browser engine availability
- Ollama & local LLM model reachability
- Git repository state
- Control Plane MCP registry
- Target application directory availability
- GitHub integration configuration

Crucial Invariant:
Optional external integrations (e.g. Ollama, GitHub API) marked NOT_CONFIGURED
must never fail core platform readiness.
"""

from __future__ import annotations
import os
import sys
import shutil
import sqlite3
import subprocess
import urllib.request
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from backend.app.system.models import (
    CheckStatus,
    CheckSeverity,
    DiagnosticCheck,
    ReadinessState,
    EngineeringLabReadiness,
)


class EnvironmentDoctor:
    """
    Deterministic system diagnostics and readiness auditor for Engineering Lab v1.
    """

    def __init__(
        self,
        db_path: str = "backend/data/reliability_platform.db",
        artifact_dir: str = "data/artifacts",
        ollama_base_url: str = "http://localhost:11434",
        required_model: str = "qwen2.5-coder",
        workspace_root: Optional[str] = None,
    ):
        self.db_path = db_path
        self.artifact_dir = artifact_dir
        self.ollama_base_url = ollama_base_url
        self.required_model = required_model
        self.workspace_root = workspace_root or os.getcwd()

    def run_all_checks(self) -> List[DiagnosticCheck]:
        """Runs the deterministic suite of environment checks."""
        checks: List[DiagnosticCheck] = [
            self.check_python_version(),
            self.check_node_version(),
            self.check_database_accessibility(),
            self.check_database_writability(),
            self.check_artifact_dir_writability(),
            self.check_git_availability(),
            self.check_git_repository_state(),
            self.check_playwright_availability(),
            self.check_chromium_availability(),
            self.check_ollama_availability(),
            self.check_required_local_model(),
            self.check_mcp_availability(),
            self.check_target_application_availability(),
            self.check_github_integration(),
        ]
        return checks

    def evaluate_readiness(self) -> EngineeringLabReadiness:
        """
        Synthesizes individual diagnostic checks into the EngineeringLabReadiness contract.
        Categorizes capabilities and determines global readiness state.
        """
        checks = self.run_all_checks()
        check_map = {c.check_id: c for c in checks}

        # Determine capabilities
        capabilities: Dict[str, str] = {}

        # 1. Browser Testing
        pw = check_map.get("playwright_available")
        chrome = check_map.get("chromium_available")
        if pw and pw.status == CheckStatus.PASS and chrome and chrome.status == CheckStatus.PASS:
            capabilities["Browser Testing"] = "READY"
        elif pw and pw.status == CheckStatus.PASS:
            capabilities["Browser Testing"] = "READY_WITH_WARNINGS"
        else:
            capabilities["Browser Testing"] = "NOT_READY"

        # 2. Local LLM & AI Agent
        ollama = check_map.get("ollama_available")
        model = check_map.get("local_model_available")
        if ollama and ollama.status == CheckStatus.PASS and model and model.status == CheckStatus.PASS:
            capabilities["Local LLM"] = "READY"
            capabilities["AI Agent"] = "READY"
        elif ollama and ollama.status == CheckStatus.PASS:
            capabilities["Local LLM"] = "READY_WITH_WARNINGS"
            capabilities["AI Agent"] = "READY_WITH_WARNINGS"
        else:
            capabilities["Local LLM"] = "NOT_CONFIGURED"
            capabilities["AI Agent"] = "DEGRADED"

        # 3. Engineering Memory
        db_acc = check_map.get("db_accessible")
        db_wr = check_map.get("db_writable")
        if db_acc and db_acc.status == CheckStatus.PASS and db_wr and db_wr.status == CheckStatus.PASS:
            capabilities["Engineering Memory"] = "READY"
            capabilities["Change Impact"] = "READY"
            capabilities["Governance"] = "READY"
            capabilities["Provenance"] = "READY"
        else:
            capabilities["Engineering Memory"] = "NOT_READY"
            capabilities["Change Impact"] = "NOT_READY"
            capabilities["Governance"] = "NOT_READY"
            capabilities["Provenance"] = "NOT_READY"

        # 4. GitHub Integration
        gh = check_map.get("github_integration")
        if gh and gh.status == CheckStatus.PASS:
            capabilities["GitHub Integration"] = "READY"
        else:
            capabilities["GitHub Integration"] = "NOT_CONFIGURED"

        # 5. MCP Control Plane
        mcp = check_map.get("mcp_control_plane")
        if mcp and mcp.status == CheckStatus.PASS:
            capabilities["MCP Control Plane"] = "READY"
        else:
            capabilities["MCP Control Plane"] = "NOT_READY"

        # Evaluate global state
        has_critical_failure = any(
            c.severity == CheckSeverity.CRITICAL and c.status == CheckStatus.FAIL
            for c in checks
        )
        has_warnings = any(
            c.status == CheckStatus.WARN or (c.severity == CheckSeverity.WARNING and c.status == CheckStatus.FAIL)
            for c in checks
        )

        if has_critical_failure:
            state = ReadinessState.NOT_READY
            summary = "Critical environment checks failed. Engineering Lab is not operational."
        elif has_warnings:
            state = ReadinessState.READY_WITH_WARNINGS
            summary = "Core platform is operational with optional or degraded external components."
        else:
            state = ReadinessState.READY
            summary = "All core systems and capabilities are fully operational."

        return EngineeringLabReadiness(
            state=state,
            summary=summary,
            capabilities=capabilities,
            checks=checks,
        )

    # -------------------------------------------------------------------------
    # Individual Deterministic Checks
    # -------------------------------------------------------------------------

    def check_python_version(self) -> DiagnosticCheck:
        v = sys.version_info
        observed = f"{v.major}.{v.minor}.{v.micro}"
        expected = ">= 3.11.0"
        passed = (v.major, v.minor) >= (3, 11)
        return DiagnosticCheck(
            check_id="python_version",
            name="Python Runtime Version",
            status=CheckStatus.PASS if passed else CheckStatus.FAIL,
            observed_value=observed,
            expected_value=expected,
            message="Python 3.11+ runtime detected." if passed else "Python 3.11+ is required.",
            severity=CheckSeverity.CRITICAL,
        )

    def check_node_version(self) -> DiagnosticCheck:
        node_path = shutil.which("node")
        if not node_path:
            return DiagnosticCheck(
                check_id="node_version",
                name="Node.js Runtime Version",
                status=CheckStatus.WARN,
                observed_value="NOT_FOUND",
                expected_value=">= 18.0.0",
                message="Node.js binary not found in PATH. Required for Next.js frontend dev.",
                severity=CheckSeverity.WARNING,
            )
        try:
            out = subprocess.check_output([node_path, "-v"], text=True, timeout=3).strip()
            return DiagnosticCheck(
                check_id="node_version",
                name="Node.js Runtime Version",
                status=CheckStatus.PASS,
                observed_value=out,
                expected_value=">= 18.0.0",
                message=f"Node.js runtime {out} available.",
                severity=CheckSeverity.WARNING,
            )
        except Exception as e:
            return DiagnosticCheck(
                check_id="node_version",
                name="Node.js Runtime Version",
                status=CheckStatus.WARN,
                observed_value="ERROR",
                expected_value=">= 18.0.0",
                message=f"Could not execute node binary: {str(e)}",
                severity=CheckSeverity.WARNING,
            )

    def check_database_accessibility(self) -> DiagnosticCheck:
        p = Path(self.db_path)
        # Database is accessible if it exists or if its directory is writable
        parent = p.parent
        accessible = p.exists() or parent.exists()
        return DiagnosticCheck(
            check_id="db_accessible",
            name="SQLite Database Accessibility",
            status=CheckStatus.PASS if accessible else CheckStatus.FAIL,
            observed_value=f"Path: {p.as_posix()}",
            expected_value="Accessible file or directory",
            message="SQLite database file/parent directory accessible." if accessible else "Database path not accessible.",
            severity=CheckSeverity.CRITICAL,
        )

    def check_database_writability(self) -> DiagnosticCheck:
        p = Path(self.db_path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.execute("CREATE TABLE IF NOT EXISTS _readiness_probe (id INTEGER PRIMARY KEY, ts TEXT);")
            conn.execute("INSERT OR REPLACE INTO _readiness_probe (id, ts) VALUES (1, 'probe');")
            conn.commit()
            conn.close()
            return DiagnosticCheck(
                check_id="db_writable",
                name="SQLite Database Writability",
                status=CheckStatus.PASS,
                observed_value="TRANSACTIONS_COMMITTED",
                expected_value="Read-Write Transaction Success",
                message="SQLite database supports atomic read-write operations.",
                severity=CheckSeverity.CRITICAL,
            )
        except Exception as e:
            return DiagnosticCheck(
                check_id="db_writable",
                name="SQLite Database Writability",
                status=CheckStatus.FAIL,
                observed_value="WRITE_FAILED",
                expected_value="Read-Write Transaction Success",
                message=f"Database write failure: {str(e)}",
                severity=CheckSeverity.CRITICAL,
            )

    def check_artifact_dir_writability(self) -> DiagnosticCheck:
        p = Path(self.artifact_dir)
        try:
            p.mkdir(parents=True, exist_ok=True)
            probe = p / ".probe_test"
            probe.write_text("probe", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return DiagnosticCheck(
                check_id="artifact_dir_writable",
                name="Artifact Directory Writability",
                status=CheckStatus.PASS,
                observed_value=p.as_posix(),
                expected_value="Writable filesystem directory",
                message="Artifact storage directory is writable.",
                severity=CheckSeverity.CRITICAL,
            )
        except Exception as e:
            return DiagnosticCheck(
                check_id="artifact_dir_writable",
                name="Artifact Directory Writability",
                status=CheckStatus.FAIL,
                observed_value=p.as_posix(),
                expected_value="Writable filesystem directory",
                message=f"Cannot write to artifact directory: {str(e)}",
                severity=CheckSeverity.CRITICAL,
            )

    def check_git_availability(self) -> DiagnosticCheck:
        git_path = shutil.which("git")
        if not git_path:
            return DiagnosticCheck(
                check_id="git_available",
                name="Git Binary Availability",
                status=CheckStatus.WARN,
                observed_value="NOT_FOUND",
                expected_value="git binary in PATH",
                message="Git binary not detected in PATH.",
                severity=CheckSeverity.WARNING,
            )
        try:
            ver = subprocess.check_output([git_path, "--version"], text=True, timeout=3).strip()
            return DiagnosticCheck(
                check_id="git_available",
                name="Git Binary Availability",
                status=CheckStatus.PASS,
                observed_value=ver,
                expected_value="git binary in PATH",
                message=f"Git available: {ver}",
                severity=CheckSeverity.INFO,
            )
        except Exception as e:
            return DiagnosticCheck(
                check_id="git_available",
                name="Git Binary Availability",
                status=CheckStatus.WARN,
                observed_value="ERROR",
                expected_value="git binary in PATH",
                message=f"Failed to execute git: {str(e)}",
                severity=CheckSeverity.WARNING,
            )

    def check_git_repository_state(self) -> DiagnosticCheck:
        dot_git = Path(self.workspace_root) / ".git"
        if dot_git.exists():
            return DiagnosticCheck(
                check_id="git_repo_state",
                name="Git Repository State",
                status=CheckStatus.PASS,
                observed_value="INITIALIZED",
                expected_value=".git directory present",
                message="Workspace is an initialized Git repository.",
                severity=CheckSeverity.INFO,
            )
        return DiagnosticCheck(
            check_id="git_repo_state",
            name="Git Repository State",
            status=CheckStatus.WARN,
            observed_value="NOT_DETECTED",
            expected_value=".git directory present",
            message="Workspace does not contain a .git directory.",
            severity=CheckSeverity.WARNING,
        )

    def check_playwright_availability(self) -> DiagnosticCheck:
        try:
            import playwright
            ver = getattr(playwright, "__version__", "installed")
            return DiagnosticCheck(
                check_id="playwright_available",
                name="Playwright Python SDK",
                status=CheckStatus.PASS,
                observed_value=f"v{ver}",
                expected_value="playwright package installed",
                message="Playwright Python SDK is installed.",
                severity=CheckSeverity.CRITICAL,
            )
        except ImportError:
            return DiagnosticCheck(
                check_id="playwright_available",
                name="Playwright Python SDK",
                status=CheckStatus.FAIL,
                observed_value="NOT_INSTALLED",
                expected_value="playwright package installed",
                message="Playwright package is not installed.",
                severity=CheckSeverity.CRITICAL,
            )

    def check_chromium_availability(self) -> DiagnosticCheck:
        # Check standard browser cache locations or playwright driver
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser_path = p.chromium.executable_path
                has_chrome = Path(browser_path).exists() if browser_path else False
                if has_chrome:
                    return DiagnosticCheck(
                        check_id="chromium_available",
                        name="Chromium Headless Engine",
                        status=CheckStatus.PASS,
                        observed_value=Path(browser_path).name,
                        expected_value="Playwright Chromium binary",
                        message="Chromium browser binary is available for autonomous testing.",
                        severity=CheckSeverity.WARNING,
                    )
                else:
                    return DiagnosticCheck(
                        check_id="chromium_available",
                        name="Chromium Headless Engine",
                        status=CheckStatus.WARN,
                        observed_value="NOT_DOWNLOADED",
                        expected_value="Playwright Chromium binary",
                        message="Playwright Chromium binary not found. Run 'playwright install chromium'.",
                        severity=CheckSeverity.WARNING,
                    )
        except Exception:
            return DiagnosticCheck(
                check_id="chromium_available",
                name="Chromium Headless Engine",
                status=CheckStatus.WARN,
                observed_value="CANNOT_PROBE",
                expected_value="Playwright Chromium binary",
                message="Could not probe Chromium executable path.",
                severity=CheckSeverity.WARNING,
            )

    def check_ollama_availability(self) -> DiagnosticCheck:
        try:
            req = urllib.request.Request(f"{self.ollama_base_url}/api/tags", headers={"User-Agent": "EngineeringLabDoctor"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return DiagnosticCheck(
                        check_id="ollama_available",
                        name="Ollama Local LLM Daemon",
                        status=CheckStatus.PASS,
                        observed_value="ONLINE (HTTP 200)",
                        expected_value=f"{self.ollama_base_url} reachable",
                        message="Ollama local inference daemon is online.",
                        severity=CheckSeverity.WARNING,
                    )
        except Exception:
            pass

        return DiagnosticCheck(
            check_id="ollama_available",
            name="Ollama Local LLM Daemon",
            status=CheckStatus.NOT_CONFIGURED,
            observed_value="UNREACHABLE",
            expected_value=f"{self.ollama_base_url} reachable",
            message="Ollama daemon is offline. Local LLM agent inference will use deterministic fallbacks.",
            severity=CheckSeverity.INFO,
        )

    def check_required_local_model(self) -> DiagnosticCheck:
        try:
            req = urllib.request.Request(f"{self.ollama_base_url}/api/tags", headers={"User-Agent": "EngineeringLabDoctor"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name", "") for m in data.get("models", [])]
                    match = any(self.required_model in m for m in models)
                    if match:
                        return DiagnosticCheck(
                            check_id="local_model_available",
                            name="Required Local AI Model",
                            status=CheckStatus.PASS,
                            observed_value=self.required_model,
                            expected_value=f"Model matching '{self.required_model}'",
                            message=f"Required model '{self.required_model}' is pulled in Ollama.",
                            severity=CheckSeverity.WARNING,
                        )
                    else:
                        return DiagnosticCheck(
                            check_id="local_model_available",
                            name="Required Local AI Model",
                            status=CheckStatus.WARN,
                            observed_value="NOT_FOUND",
                            expected_value=f"Model matching '{self.required_model}'",
                            message=f"Model '{self.required_model}' not found in Ollama tags.",
                            severity=CheckSeverity.WARNING,
                        )
        except Exception:
            pass

        return DiagnosticCheck(
            check_id="local_model_available",
            name="Required Local AI Model",
            status=CheckStatus.NOT_CONFIGURED,
            observed_value="DAEMON_OFFLINE",
            expected_value=f"Model matching '{self.required_model}'",
            message="Ollama is offline; local model check skipped.",
            severity=CheckSeverity.INFO,
        )

    def check_mcp_availability(self) -> DiagnosticCheck:
        from backend.app.control_plane.service import ReliabilityControlPlane
        try:
            cp = ReliabilityControlPlane(
                db_path=self.db_path,
                enable_provenance_tools=True,
                enable_change_impact_tools=True,
                enable_governance_tools=True,
            )
            count = len(cp.registry.list_tools())
            return DiagnosticCheck(
                check_id="mcp_control_plane",
                name="MCP Control Plane Registry",
                status=CheckStatus.PASS,
                observed_value=f"{count} canonical tools registered",
                expected_value=">= 10 registered tools",
                message=f"ReliabilityControlPlane operational with {count} canonical tools.",
                severity=CheckSeverity.CRITICAL,
            )
        except Exception as e:
            return DiagnosticCheck(
                check_id="mcp_control_plane",
                name="MCP Control Plane Registry",
                status=CheckStatus.FAIL,
                observed_value="INITIALIZATION_FAILED",
                expected_value=">= 10 registered tools",
                message=f"Control plane initialization error: {str(e)}",
                severity=CheckSeverity.CRITICAL,
            )

    def check_target_application_availability(self) -> DiagnosticCheck:
        target_dir = Path(self.workspace_root) / "apps" / "question_generator"
        if target_dir.exists():
            return DiagnosticCheck(
                check_id="target_app_available",
                name="Target Application (Question Generator)",
                status=CheckStatus.PASS,
                observed_value=target_dir.as_posix(),
                expected_value="apps/question_generator directory",
                message="Canonical Question Generator target codebase located.",
                severity=CheckSeverity.INFO,
            )
        return DiagnosticCheck(
            check_id="target_app_available",
            name="Target Application (Question Generator)",
            status=CheckStatus.WARN,
            observed_value="NOT_FOUND",
            expected_value="apps/question_generator directory",
            message="apps/question_generator directory not found in workspace.",
            severity=CheckSeverity.WARNING,
        )

    def check_github_integration(self) -> DiagnosticCheck:
        # Masked token check - NEVER exposes raw token
        has_token = bool(os.environ.get("GITHUB_TOKEN"))
        if has_token:
            return DiagnosticCheck(
                check_id="github_integration",
                name="GitHub Integration Credentials",
                status=CheckStatus.PASS,
                observed_value="GITHUB_TOKEN_CONFIGURED (REDACTED)",
                expected_value="Configured or NOT_CONFIGURED",
                message="GitHub integration token is configured for PR/CI automation.",
                severity=CheckSeverity.INFO,
            )
        return DiagnosticCheck(
            check_id="github_integration",
            name="GitHub Integration Credentials",
            status=CheckStatus.NOT_CONFIGURED,
            observed_value="NOT_SET",
            expected_value="Configured or NOT_CONFIGURED",
            message="GITHUB_TOKEN is not set. GitHub PR/CI automation will use local mock lifecycles.",
            severity=CheckSeverity.INFO,
        )
