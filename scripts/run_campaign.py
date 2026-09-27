import argparse
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
    CampaignStatus,
)
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_case import TestCase
from backend.app.models.campaign import CampaignCreate
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.services.run_manager import RunManager
from backend.app.services.campaign_service import CampaignService
from backend.app.execution.playwright_runner import PlaywrightTestRunner
from backend.app.execution.ai_agent_runner import AIAgentTestRunner
from backend.app.execution.mock_runner import MockTestRunner
from backend.app.agents.ollama_agent import OllamaReasoner
from backend.app.evidence.storage import LocalEvidenceBlobStorage
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.prediction.walk_forward_evaluator import PopulationSeparator


async def main():
    parser = argparse.ArgumentParser(description="Repeatable Real-World QA Campaign Runner")
    parser.add_argument("--target", default="real_eda_local", help="Target ID to test")
    parser.add_argument("--test-case", default="tc_eda_health_smoke", help="Test Case ID")
    parser.add_argument("--iterations", type=int, default=2, help="Number of repetitions per test case")
    parser.add_argument("--runner", choices=["PLAYWRIGHT", "AI_AGENT", "BOTH", "MOCK"], default="PLAYWRIGHT", help="Runner engine")
    parser.add_argument("--delay-ms", type=int, default=500, help="Delay between consecutive runs in ms")
    parser.add_argument("--stop-on-first-failure", action="store_true", help="Stop campaign upon first failure")
    parser.add_argument("--stop-on-consecutive-failures", type=int, default=None, help="Stop after N consecutive failures")
    parser.add_argument("--target-url", default="http://127.0.0.1:8088/docs", help="Target URL override")
    parser.add_argument("--name", default=None, help="Custom campaign name")
    parser.add_argument("--audit-only", action="store_true", help="Audit database and print latest campaign summary without executing new runs")

    args = parser.parse_args()

    print("=" * 80)
    print("AI APPLICATION RELIABILITY — QA CAMPAIGN RUNNER")
    print("=" * 80)

    db_path = settings.DATABASE_PATH
    init_db(db_path)
    repo = SQLiteRepository(db_path=db_path)
    blob_storage = LocalEvidenceBlobStorage()

    if args.audit_only:
        print("\n[INFO] --audit-only flag set. Listing recent campaigns and dataset audit:")
        campaigns = repo.list_campaigns(limit=5)
        for c in campaigns:
            print(f"  Campaign: {c.campaign_id} | Name: {c.name} | Status: {c.status.value} | Completed: {c.completed_runs}/{c.requested_runs} (Passed: {c.passed_runs}, Failed: {c.failed_runs})")

        all_runs = repo.list_runs(limit=repo.count_runs())
        records = []
        for r in all_runs:
            evi = repo.get_evidence_by_run(r.run_id)
            fails = repo.get_failures_by_run(r.run_id)
            records.append(ReliabilityFeatureExtractor.extract_record_from_run(r, evi, fails))
        vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)

        print("\n--- Current Population Status ---")
        for pop in [
            PopulationType.ALL_HISTORICAL,
            PopulationType.REAL_EXECUTIONS_ONLY,
            PopulationType.REAL_PLAYWRIGHT_ONLY,
            PopulationType.REAL_AI_AGENT_ONLY,
            PopulationType.CONTROLLED_AND_DEMO,
        ]:
            audit = PopulationSeparator.audit_population(pop, records, vectors)
            print(f"  {pop.value:<25}: {audit.total_runs} runs, {audit.total_transitions} transitions -> {audit.status.value}")
        return

    # Verify target application health
    health_url = "http://127.0.0.1:8088/"
    print(f"\n[PRE-CHECK] Verifying target application connectivity at {health_url}...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(health_url)
            print(f"  -> Target application response: HTTP {resp.status_code}")
            assert resp.status_code == 200, f"Target application returned status {resp.status_code}"
    except Exception as e:
        print(f"[FATAL] Cannot connect to target application at {health_url}: {e}")
        print("Please ensure the target application daemon is running.")
        sys.exit(1)

    # Ensure target exists
    target = repo.get_target(args.target)
    if not target:
        target = ApplicationTarget(
            target_id=args.target,
            name="Engineering Design Automation",
            target_type=TargetType.WEB_APPLICATION,
            base_url=args.target_url,
            environment="local-development",
            version="1.0.0",
            description="Deterministic Python/FastAPI mechanical drawing and engineering design intelligence application",
            metadata={
                "framework": "FastAPI / Uvicorn",
                "interactive_docs_url": args.target_url,
                "api_root": health_url,
            },
        )
        repo.create_target(target)
        print(f"  -> Created target: {target.name} ({target.target_id})")

    # Ensure test case exists if provided
    tc = repo.get_test_case(args.test_case)
    if not tc and args.test_case:
        tc = TestCase(
            test_case_id=args.test_case,
            target_id=args.target,
            name="EDA Health & Swagger Verification",
            test_mode=TestMode.FUNCTIONAL_QA,
            description="Verify Swagger UI loads, expands GET / operation, executes live query, and receives healthy service status",
            steps=[
                {"type": "NAVIGATE", "target": args.target_url},
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

    # Build runners
    mock_runner = MockTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
    )
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
            RunnerType.MOCK: mock_runner,
            RunnerType.PLAYWRIGHT: pw_runner,
            RunnerType.AI_AGENT: ai_runner,
        },
    )

    campaign_service = CampaignService(
        campaign_repo=repo,
        run_manager=run_manager,
        target_repo=repo,
        test_case_repo=repo,
    )

    # Determine runner types and sources
    if args.runner == "PLAYWRIGHT":
        runner_types = [RunnerType.PLAYWRIGHT]
        sources = [ExecutionSource.REAL_PLAYWRIGHT]
    elif args.runner == "AI_AGENT":
        runner_types = [RunnerType.AI_AGENT]
        sources = [ExecutionSource.REAL_AI_AGENT]
    elif args.runner == "BOTH":
        runner_types = [RunnerType.PLAYWRIGHT, RunnerType.AI_AGENT]
        sources = [ExecutionSource.REAL_PLAYWRIGHT, ExecutionSource.REAL_AI_AGENT]
    else:
        runner_types = [RunnerType.MOCK]
        sources = [ExecutionSource.SYNTHETIC_MOCK]

    campaign_name = args.name or f"Campaign: {args.target} ({args.runner} x {args.iterations})"

    campaign_req = CampaignCreate(
        name=campaign_name,
        target_id=args.target,
        test_case_ids=[args.test_case] if args.test_case else [],
        runner_types=runner_types,
        execution_sources=sources,
        iterations_per_test_case=args.iterations,
        target_url_override=args.target_url,
        natural_language_goal="Verify Swagger UI loads and GET / operation executes successfully.",
        max_agent_steps=4,
        delay_between_runs_ms=args.delay_ms,
        stop_on_first_failure=args.stop_on_first_failure,
        stop_on_consecutive_failures=args.stop_on_consecutive_failures,
        environment_id=target.environment,
        description=f"Longitudinal QA campaign executing {len(runner_types) * args.iterations} runs on {args.target}",
    )

    print(f"\n[CAMPAIGN CREATION] Registering campaign '{campaign_name}'...")
    created_campaign = campaign_service.create_campaign(campaign_req)
    print(f"  -> Campaign ID:        {created_campaign.campaign_id}")
    print(f"  -> Total Requested:    {created_campaign.requested_runs} runs")
    print(f"  -> Runner Types:       {[rt.value for rt in created_campaign.configuration.runner_types]}")
    print(f"  -> Execution Sources:  {[s.value for s in created_campaign.execution_sources]}")

    print(f"\n[CAMPAIGN EXECUTION] Starting execution loop...")
    executed_campaign = await campaign_service.execute_campaign(created_campaign.campaign_id)

    print("\n" + "=" * 80)
    print("CAMPAIGN EXECUTION COMPLETE")
    print("=" * 80)
    report = executed_campaign.summary_report
    print(f"Campaign ID:       {executed_campaign.campaign_id}")
    print(f"Name:              {executed_campaign.name}")
    print(f"Final Status:      {executed_campaign.status.value}")
    print(f"Completed / Total: {executed_campaign.completed_runs} / {executed_campaign.requested_runs}")
    print(f"Passed / Failed:   {executed_campaign.passed_runs} / {executed_campaign.failed_runs}")
    print(f"Pass Rate:         {report.get('pass_rate', 0.0):.1%}")
    print(f"Total Duration:    {report.get('total_duration_ms', 0)} ms")
    print(f"Average Duration:  {report.get('average_duration_ms', 0.0)} ms")
    print(f"Sources Breakdown: {json.dumps(report.get('sources_breakdown', {}))}")
    print(f"Runners Breakdown: {json.dumps(report.get('runners_breakdown', {}))}")

    # Print run details
    runs = campaign_service.get_campaign_runs(executed_campaign.campaign_id)
    print(f"\nRuns Generated ({len(runs)}):")
    for r in runs:
        print(f"  - Run {r.run_id}: {r.runner_type.value} | {r.execution_source.value} | {r.status.value} ({r.duration_ms}ms)")

    # Print population impact
    print("\n--- Dataset Population Impact ---")
    pop_impact = report.get("population_impact", {})
    for pop_key, pop_data in pop_impact.items():
        if isinstance(pop_data, dict):
            print(f"  {pop_key:<25}: {pop_data.get('total_runs', 0)} runs, {pop_data.get('total_transitions', 0)} transitions -> {pop_data.get('status', 'UNKNOWN')}")

    print("\n" + "=" * 80)
    print("CAMPAIGN AUDIT & PROVENANCE VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
