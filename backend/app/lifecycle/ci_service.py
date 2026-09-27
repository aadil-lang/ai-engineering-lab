import os
import time
import uuid
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.app.lifecycle.models import CIRun, CIStatus
from backend.app.lifecycle.repository import LifecycleRepository


class CIService:
    """
    Deterministic CI Service for executing and evaluating automated test suites.
    Core Invariant: CI gates are 100% deterministic. An LLM cannot override a failed CI check.
    Supports local execution of pytest, npm test, and npm run build.
    """

    def __init__(
        self,
        repository: Optional[LifecycleRepository] = None,
        workspace_root: Optional[Path] = None,
    ):
        self.repo = repository or LifecycleRepository()
        self.workspace_root = workspace_root or Path(__file__).resolve().parents[3]

    def trigger_ci_run(
        self,
        commit_sha: str,
        workflow: str = "pytest_unit",
        target_path: Optional[str] = None,
    ) -> CIRun:
        """
        Executes a deterministic CI workflow and records the run record.
        """
        run_id = f"ci-{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        start_iso = datetime.now(timezone.utc).isoformat()

        tests_total = 0
        tests_passed = 0
        tests_failed = 0
        logs = ""
        status = CIStatus.RUNNING

        if workflow == "pytest_unit":
            # Deterministic pytest run
            test_target = target_path or "backend/tests/test_tool_redaction.py"
            cmd = ["python", "-m", "pytest", test_target, "-q"]
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(self.workspace_root),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                logs = proc.stdout + "\n" + proc.stderr
                if proc.returncode == 0:
                    status = CIStatus.PASSED
                    # Approximate passed count from quiet pytest output
                    tests_passed = logs.count("passed") or 1
                    tests_total = tests_passed
                else:
                    status = CIStatus.FAILED
                    tests_failed = 1
                    tests_total = 1
            except subprocess.TimeoutExpired:
                status = CIStatus.FAILED
                logs = "CI workflow timed out after 60 seconds."
            except Exception as e:
                status = CIStatus.FAILED
                logs = f"Execution error: {e}"

        elif workflow == "npm_build":
            # Deterministic npm run build
            cmd = ["npm", "run", "build"]
            frontend_dir = self.workspace_root / "frontend"
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(frontend_dir),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    shell=True,
                )
                logs = proc.stdout + "\n" + proc.stderr
                status = CIStatus.PASSED if proc.returncode == 0 else CIStatus.FAILED
                tests_total = 1
                if status == CIStatus.PASSED:
                    tests_passed = 1
                else:
                    tests_failed = 1
            except Exception as e:
                status = CIStatus.FAILED
                logs = f"Build error: {e}"

        elif workflow == "simulated_pass":
            # Deterministic simulated pass for testing pipelines
            status = CIStatus.PASSED
            tests_total = 10
            tests_passed = 10
            logs = "Simulated unit test suite: 10/10 passed."

        elif workflow == "simulated_fail":
            # Deterministic simulated failure for testing failure loops
            status = CIStatus.FAILED
            tests_total = 10
            tests_passed = 8
            tests_failed = 2
            logs = "Simulated unit test suite: 2 failures detected (AssertionError)."

        else:
            status = CIStatus.FAILED
            logs = f"Unknown CI workflow: {workflow}"

        duration_ms = int((time.time() - start_time) * 1000)
        completed_iso = datetime.now(timezone.utc).isoformat()

        ci_run = CIRun(
            id=run_id,
            commit_sha=commit_sha,
            workflow=workflow,
            status=status,
            started_at=start_iso,
            completed_at=completed_iso,
            duration_ms=duration_ms,
            tests_total=tests_total,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            artifacts=[f"logs/{run_id}.log"],
            logs=logs.strip()[-1000:],  # Tail of logs
        )

        self.repo.save_ci_run(ci_run)
        return ci_run

    def get_ci_run(self, run_id: str) -> Optional[CIRun]:
        return self.repo.get_ci_run(run_id)

    def get_latest_for_commit(self, commit_sha: str) -> Optional[CIRun]:
        return self.repo.get_latest_ci_run_for_commit(commit_sha)
