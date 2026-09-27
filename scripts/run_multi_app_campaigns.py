"""
Executes Slice 6.8 Multi-Application Real Reliability Campaigns across:
1. Engineering Design Automation (EDA)
2. Industrial Inventory & Asset Management (CRUD Business)
3. QA Certification & Dispatch Booking Wizard (Stateful Workflow)

Strictly respects:
- Explicit campaign_type = REAL_RELIABILITY
- Zero fault injection (simulate_failure=False)
- Preserves all Slice 6.7.2 invariants
"""

import os
import sys
import asyncio
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.models.enums import RunnerType, ExecutionSource, CampaignType, PopulationType
from backend.app.models.campaign import CampaignCreate
from backend.app.api.deps import get_repository, get_run_manager
from backend.app.services.campaign_service import CampaignService
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.prediction.walk_forward_evaluator import PopulationSeparator

def check_app_health():
    apps = [
        ("EDA", "http://127.0.0.1:8088/"),
        ("Inventory", "http://127.0.0.1:8089/health"),
        ("Booking", "http://127.0.0.1:8090/health"),
    ]
    for name, url in apps:
        try:
            res = urllib.request.urlopen(url, timeout=3)
            print(f"[HEALTH OK] {name} at {url} returned HTTP {res.status}")
        except Exception as e:
            raise RuntimeError(f"Application {name} at {url} is not responding: {e}")

async def run_campaigns():
    print("=" * 70)
    print("SLICE 6.8: MULTI-APPLICATION REAL RELIABILITY CAMPAIGN RUNNER")
    print("=" * 70)
    check_app_health()

    repo = get_repository()
    run_manager = get_run_manager()
    campaign_service = CampaignService(
        campaign_repo=repo,
        run_manager=run_manager,
        target_repo=repo,
        test_case_repo=repo,
    )

    campaign_configs = [
        {
            "name": "Campaign EDA - Longitudinal Engineering Reliability",
            "target_id": "real_eda_local",
            "test_case_ids": ["tc_eda_health_smoke", "tc_eda_calculation_workflow"],
            "description": "Longitudinal execution of Swagger smoke probe and structural calculation workflows.",
            "iterations": 10,
        },
        {
            "name": "Campaign Inventory - Longitudinal CRUD Reliability",
            "target_id": "real_inventory_local",
            "test_case_ids": ["tc_inventory_create_edit", "tc_inventory_validation_flow"],
            "description": "Longitudinal execution of CRUD create/edit lifecycles and validation guardrails.",
            "iterations": 10,
        },
        {
            "name": "Campaign Booking - Longitudinal Stateful Workflow Reliability",
            "target_id": "real_booking_local",
            "test_case_ids": ["tc_booking_complete_wizard", "tc_booking_edge_validation_flow"],
            "description": "Longitudinal execution of multi-step wizard state transitions and edge validations.",
            "iterations": 10,
        },
    ]

    completed_campaigns = []
    for cfg in campaign_configs:
        print("\n" + "-" * 70)
        print(f"Creating {cfg['name']} ({cfg['target_id']}) with {cfg['iterations']} iterations...")
        req = CampaignCreate(
            name=cfg["name"],
            description=cfg["description"],
            target_id=cfg["target_id"],
            campaign_type=CampaignType.REAL_RELIABILITY,
            test_case_ids=cfg["test_case_ids"],
            runner_types=[RunnerType.PLAYWRIGHT],
            execution_sources=[ExecutionSource.REAL_PLAYWRIGHT],
            iterations_per_test_case=cfg["iterations"],
            delay_between_runs_ms=100,
            stop_on_first_failure=False,
            parameters={"simulate_failure": False},
        )
        created_camp = campaign_service.create_campaign(req)
        print(f"Campaign ID: {created_camp.campaign_id} (Requested: {created_camp.requested_runs} runs)")

        print(f"Executing campaign {created_camp.campaign_id}...")
        executed_camp = await campaign_service.execute_campaign(created_camp.campaign_id)
        completed_campaigns.append(executed_camp)
        print(f"Completed {executed_camp.name}:")
        print(f" - Status: {executed_camp.status.value}")
        print(f" - Runs: {executed_camp.completed_runs}/{executed_camp.requested_runs} (Passed: {executed_camp.passed_runs}, Failed: {executed_camp.failed_runs})")

    print("\n" + "=" * 70)
    print("ALL 3 MULTI-APPLICATION CAMPAIGNS FINISHED SUCCESSFULLY")
    print("=" * 70)

    # Perform instantaneous dataset audit
    all_runs = repo.list_runs(limit=3000)
    records = []
    for r in all_runs:
        ev = repo.get_evidence_by_run(r.run_id)
        fa = repo.get_failures_by_run(r.run_id)
        records.append(ReliabilityFeatureExtractor.extract_record_from_run(r, ev, fa))

    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)

    audit_all = PopulationSeparator.audit_population(PopulationType.ALL_HISTORICAL, records, vectors)
    audit_real = PopulationSeparator.audit_population(PopulationType.REAL_EXECUTIONS_ONLY, records, vectors)
    audit_pw = PopulationSeparator.audit_population(PopulationType.REAL_PLAYWRIGHT_ONLY, records, vectors)
    audit_ai = PopulationSeparator.audit_population(PopulationType.REAL_AI_AGENT_ONLY, records, vectors)
    audit_demo = PopulationSeparator.audit_population(PopulationType.CONTROLLED_AND_DEMO, records, vectors)

    print(f"Total Historical Runs: {len(all_runs)}")
    print(f"Total Temporal Transitions (All): {audit_all.total_transitions}")
    print(f"\nPopulation Separation Audit:")
    print(f" - REAL_EXECUTIONS_ONLY: {audit_real.total_runs} runs | {audit_real.total_transitions} transitions | Status: {audit_real.status.value}")
    print(f" - REAL_PLAYWRIGHT_ONLY: {audit_pw.total_runs} runs | {audit_pw.total_transitions} transitions | Status: {audit_pw.status.value}")
    print(f" - REAL_AI_AGENT_ONLY:   {audit_ai.total_runs} runs | {audit_ai.total_transitions} transitions | Status: {audit_ai.status.value}")
    print(f" - CONTROLLED_AND_DEMO:  {audit_demo.total_runs} runs | {audit_demo.total_transitions} transitions | Status: {audit_demo.status.value}")

    # Check conservation
    assert audit_real.total_transitions + audit_demo.total_transitions == audit_all.total_transitions, (
        f"Conservation mismatch: Real ({audit_real.total_transitions}) + Demo ({audit_demo.total_transitions}) != All ({audit_all.total_transitions})"
    )
    print("\n[VERIFIED] Transition Conservation Holds:")
    print(f"   {audit_real.total_transitions} (Real) + {audit_demo.total_transitions} (Controlled/Demo) == {audit_all.total_transitions} (Total)")

if __name__ == "__main__":
    asyncio.run(run_campaigns())
