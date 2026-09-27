"""
Verifies that all 6 test cases across the 3 applications execute cleanly
with PlaywrightTestRunner and produce PASSED runs with real actions and evidence.
"""

import os
import sys
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.models.enums import RunnerType, TestMode, ExecutionSource, CampaignType
from backend.app.models.test_run import TestRunCreate
from backend.app.api.deps import get_run_manager

async def main():
    run_manager = get_run_manager()

    test_runs_to_try = [
        ("real_eda_local", "tc_eda_health_smoke"),
        ("real_eda_local", "tc_eda_calculation_workflow"),
        ("real_inventory_local", "tc_inventory_create_edit"),
        ("real_inventory_local", "tc_inventory_validation_flow"),
        ("real_booking_local", "tc_booking_complete_wizard"),
        ("real_booking_local", "tc_booking_edge_validation_flow"),
    ]

    print("Executing smoke trial across all 6 test cases:")
    for target_id, tc_id in test_runs_to_try:
        req = TestRunCreate(
            application_id=target_id,
            test_mode=TestMode.FUNCTIONAL_QA,
            runner_type=RunnerType.PLAYWRIGHT,
            execution_source=ExecutionSource.REAL_PLAYWRIGHT,
            test_case_id=tc_id,
            environment_id="local_smoke_test",
            campaign_type=CampaignType.REAL_RELIABILITY,
            simulate_failure=False,
        )
        run = await run_manager.initiate_run(req)
        print(f"[{run.status.value}] Target: {target_id} | Test Case: {tc_id} | Run ID: {run.run_id} | Actions: {len(run.actions)} | Duration: {run.duration_ms}ms")
        assert run.status.value == "PASSED", f"Run failed for {tc_id}: {run.logs[-3:]}"
        assert len(run.actions) >= 5, f"Expected at least 5 actions, got {len(run.actions)}"

    print("ALL 6 TEST CASES PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
