import asyncio
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.models.enums import (
    RunnerType,
    ExecutionSource,
    RunStatus,
    TestMode,
    TargetType,
    PopulationType,
)
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_case import TestCase
from backend.app.models.test_run import TestRun, TestRunCreate
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.services.run_manager import RunManager
from backend.app.execution.playwright_runner import PlaywrightTestRunner
from backend.app.execution.ai_agent_runner import AIAgentTestRunner
from backend.app.agents.ollama_agent import OllamaReasoner
from backend.app.evidence.storage import LocalEvidenceBlobStorage
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.prediction.walk_forward_evaluator import PopulationSeparator


async def main():
    print("=" * 80)
    print("SLICE 6.6 — REAL APPLICATION RELIABILITY TELEMETRY CAMPAIGN")
    print("=" * 80)

    db_path = settings.DATABASE_PATH
    print(f"[DB] Initializing repository: {db_path}")
    init_db(db_path)
    repo = SQLiteRepository(db_path=db_path)
    blob_storage = LocalEvidenceBlobStorage()

    # Verify target application health
    target_url = "http://127.0.0.1:8088/docs"
    health_url = "http://127.0.0.1:8088/"
    print(f"\n[PHASE 0] Verifying target application health at {health_url}...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(health_url)
            print(f"  -> Health check response: HTTP {resp.status_code} - {resp.json()}")
            assert resp.status_code == 200, "Target application did not return 200"
    except Exception as e:
        print(f"[FATAL] Cannot connect to target application at {health_url}: {e}")
        sys.exit(1)

    # Phase 1: Real Target Registration
    print("\n[PHASE 1] Registering Real Target: Engineering Design Automation...")
    target_id = "real_eda_local"
    existing_target = repo.get_target(target_id)
    if not existing_target:
        target = ApplicationTarget(
            target_id=target_id,
            name="Engineering Design Automation",
            target_type=TargetType.WEB_APPLICATION,
            base_url=target_url,
            environment="local-development",
            version="1.0.0",
            description="Deterministic Python/FastAPI mechanical drawing and engineering design intelligence application",
            metadata={
                "framework": "FastAPI / Uvicorn",
                "interactive_docs_url": target_url,
                "api_root": health_url,
            },
        )
        repo.create_target(target)
        print(f"  -> Created target: {target.name} ({target.target_id})")
    else:
        target = existing_target
        print(f"  -> Reusing existing target: {target.name} ({target.target_id})")

    # Phase 2: Real Test Case Registration
    print("\n[PHASE 2] Registering Deterministic Smoke Test Case...")
    test_case_id = "tc_eda_health_smoke"
    existing_tc = repo.get_test_case(test_case_id)
    if not existing_tc:
        tc = TestCase(
            test_case_id=test_case_id,
            target_id=target_id,
            name="EDA Health & Swagger Verification",
            test_mode=TestMode.FUNCTIONAL_QA,
            description="Verify Swagger UI loads, expands GET / operation, executes live query, and receives healthy service status",
            steps=[
                {"type": "NAVIGATE", "target": target_url},
                {"type": "LOCATE", "selector": ".opblock-get"},
                {"type": "CLICK", "selector": ".opblock-get button.opblock-summary-control"},
                {"type": "CLICK", "selector": ".opblock-get button.try-out__btn"},
                {"type": "CLICK", "selector": ".opblock-get button.execute"},
                {"type": "ASSERT", "selector": ".opblock-get td.response-col_status", "expected": "200"}
            ],
            assertions=[
                {"field": "status", "operator": "equals", "value": 200},
                {"field": "body.status", "operator": "equals", "value": "healthy"}
            ],
            tags=["real_eda", "smoke", "swagger_ui", "deterministic"],
        )
        repo.create_test_case(tc)
        print(f"  -> Created test case: {tc.name} ({tc.test_case_id})")
    else:
        tc = existing_tc
        print(f"  -> Reusing test case: {tc.name} ({tc.test_case_id})")

    # Initialize Runners
    pw_runner = PlaywrightTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        blob_storage=blob_storage,
    )
    ai_reasoner = OllamaReasoner(
        base_url="http://localhost:11434",
        model="qwen2.5-coder:7b-instruct",
        timeout_seconds=60.0,
    )
    ai_runner = AIAgentTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        blob_storage=blob_storage,
        reasoner=ai_reasoner,
    )

    run_manager = RunManager(
        run_repo=repo,
        target_repo=repo,
        test_case_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        runners={
            RunnerType.PLAYWRIGHT: pw_runner,
            RunnerType.AI_AGENT: ai_runner,
        },
    )

    # Check if audit-only mode is requested
    audit_only = "--audit-only" in sys.argv
    if audit_only:
        print("\n[INFO] --audit-only flag detected: Skipping execution phases, evaluating database directly.")
    else:
        # ----------------------------------------------------
        # Phase 3 & 4: Execute Real Playwright Workflow #1
        # ----------------------------------------------------
        print("\n" + "-" * 60)
        print("[PHASE 3 & 4] Executing Campaign Run 1: REAL_PLAYWRIGHT (Execution 1)")
        print("-" * 60)
        req1 = TestRunCreate(
            application_id=target_id,
            test_case_id=test_case_id,
            runner_type=RunnerType.PLAYWRIGHT,
            execution_source=ExecutionSource.REAL_PLAYWRIGHT,
            test_mode=TestMode.FUNCTIONAL_QA,
            target_url_override=target_url,
        )
        run1 = await run_manager.initiate_run(req1)
        print(f"  -> Run 1 Completed: ID={run1.run_id}, Status={run1.status.value}, Duration={run1.duration_ms}ms")
        print(f"  -> Execution Source: {run1.execution_source.value}")
        print(f"  -> Actions ({len(run1.actions)}): {[a.action_type.value for a in run1.actions]}")
        print(f"  -> Metrics Summary: {json.dumps(run1.metrics_summary, indent=2)}")
        print(f"  -> Evidence Count: {len(run1.evidence_ids)}")

        # ----------------------------------------------------
        # Longitudinal Collection: Execute Real Playwright Workflow #2
        # ----------------------------------------------------
        print("\n" + "-" * 60)
        print("[LONGITUDINAL] Executing Campaign Run 2: REAL_PLAYWRIGHT (Execution 2, Longitudinal Sequence)")
        print("-" * 60)
        req2 = TestRunCreate(
            application_id=target_id,
            test_case_id=test_case_id,
            runner_type=RunnerType.PLAYWRIGHT,
            execution_source=ExecutionSource.REAL_PLAYWRIGHT,
            test_mode=TestMode.FUNCTIONAL_QA,
            target_url_override=target_url,
        )
        run2 = await run_manager.initiate_run(req2)
        print(f"  -> Run 2 Completed: ID={run2.run_id}, Status={run2.status.value}, Duration={run2.duration_ms}ms")
        print(f"  -> Execution Source: {run2.execution_source.value}")
        print(f"  -> Actions ({len(run2.actions)}): {[a.action_type.value for a in run2.actions]}")
        print(f"  -> Metrics Summary: {json.dumps(run2.metrics_summary, indent=2)}")

        # ----------------------------------------------------
        # Phase 5: Execute Real AI-Agent Browser Workflow #3
        # ----------------------------------------------------
        print("\n" + "-" * 60)
        print("[PHASE 5] Executing Campaign Run 3: REAL_AI_AGENT (Qwen2.5-Coder Autonomous Agent)")
        print("-" * 60)
        goal = "Open the Engineering Design Automation documentation, explore the available endpoints, locate the GET / operation, and verify that the service is running."
        req3 = TestRunCreate(
            application_id=target_id,
            test_case_id=test_case_id,
            runner_type=RunnerType.AI_AGENT,
            execution_source=ExecutionSource.REAL_AI_AGENT,
            test_mode=TestMode.EXPLORATORY_DOGFOODING,
            natural_language_goal=goal,
            max_agent_steps=4,
            target_url_override=target_url,
        )
        run3 = await run_manager.initiate_run(req3)
        print(f"  -> Run 3 Completed: ID={run3.run_id}, Status={run3.status.value}, Duration={run3.duration_ms}ms")
        print(f"  -> Execution Source: {run3.execution_source.value}")
        print(f"  -> Thought Trace Steps: {len(run3.agent_thought_trace)}")
        print(f"  -> Actions ({len(run3.actions)}): {[a.action_type.value for a in run3.actions]}")
        print(f"  -> Metrics Summary: {json.dumps(run3.metrics_summary, indent=2)}")

    # ----------------------------------------------------
    # Phase 6 & 7: Provenance & Population Audit Verification
    # ----------------------------------------------------
    print("\n" + "=" * 80)
    print("[PHASE 6 & 7] DATASET POPULATION AUDIT & CONTAMINATION VERIFICATION")
    print("=" * 80)

    # Load all runs from database
    total_runs_count = repo.count_runs()
    all_runs = repo.list_runs(limit=total_runs_count, offset=0)
    print(f"Total Runs in Persistent DB: {len(all_runs)}")

    # Extract reliability records without synthetic fabrication
    records = []
    for r in all_runs:
        evi = repo.get_evidence_by_run(r.run_id)
        fails = repo.get_failures_by_run(r.run_id)
        records.append(ReliabilityFeatureExtractor.extract_record_from_run(r, evi, fails))

    # Build chronological temporal transitions dataset
    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)
    print(f"Total Usable Vectors across all data: {len(vectors)}")

    # Audit each population
    pop_order = [
        PopulationType.ALL_HISTORICAL,
        PopulationType.REAL_EXECUTIONS_ONLY,
        PopulationType.REAL_PLAYWRIGHT_ONLY,
        PopulationType.REAL_AI_AGENT_ONLY,
        PopulationType.CONTROLLED_AND_DEMO,
    ]

    for pop in pop_order:
        audit = PopulationSeparator.audit_population(pop, records, vectors)
        print(f"\nPopulation: {pop.value}")
        print(f"  Name:               {audit.population_name}")
        print(f"  Total Runs:         {audit.total_runs}")
        print(f"  Transitions:        {audit.total_transitions}")
        print(f"  Passes / Failures:  {audit.passes_count} passes / {audit.failures_count} failures")
        print(f"  Failure Rate:       {audit.failure_rate:.1%}")
        print(f"  Status:             {audit.status.value}")
        print(f"  Status Reason:      {audit.status_reason}")
        print(f"  Included Sources:   {[s.value for s in audit.included_sources]}")

    # Contamination & Integrity Assertions
    real_records = PopulationSeparator.filter_records_by_population(records, PopulationType.REAL_EXECUTIONS_ONLY)
    demo_records = PopulationSeparator.filter_records_by_population(records, PopulationType.CONTROLLED_AND_DEMO)
    pw_records = PopulationSeparator.filter_records_by_population(records, PopulationType.REAL_PLAYWRIGHT_ONLY)
    ai_records = PopulationSeparator.filter_records_by_population(records, PopulationType.REAL_AI_AGENT_ONLY)

    assert len(real_records) >= 3, f"Expected at least 3 real records, got {len(real_records)}"
    assert all(r.execution_source in (ExecutionSource.REAL_PLAYWRIGHT, ExecutionSource.REAL_AI_AGENT) for r in real_records), "Contamination in REAL_EXECUTIONS_ONLY!"
    assert all(r.execution_source in (ExecutionSource.SYNTHETIC_MOCK, ExecutionSource.DEMO_HARNESS, ExecutionSource.CONTROLLED_DEFECT) for r in demo_records), "Contamination in CONTROLLED_AND_DEMO!"
    assert len(pw_records) >= 2, f"Expected at least 2 real playwright records, got {len(pw_records)}"
    assert len(ai_records) >= 1, f"Expected at least 1 real AI agent record, got {len(ai_records)}"

    print("\n" + "=" * 80)
    print("CAMPAIGN COMPLETED SUCCESSFULLY — PROVENANCE INTEGRITY VERIFIED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
