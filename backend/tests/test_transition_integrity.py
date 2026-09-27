import pytest
import os
from datetime import datetime, timezone, timedelta

from backend.app.models.enums import (
    RunnerType,
    ExecutionSource,
    RunStatus,
    PopulationType,
    DatasetStatus,
)
from backend.app.models.test_run import TestRun
from backend.app.models.reliability import ReliabilityFeatureVector, ReliabilityRecord
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.prediction.walk_forward_evaluator import PopulationSeparator


def test_cross_runner_transition_isolation():
    """
    Regression Test for Slice 6.7.1 / 6.7.2:
    Ensures that runs with different execution_source values (e.g. REAL_PLAYWRIGHT vs REAL_AI_AGENT)
    never form a temporal transition between each other even when sharing the exact same test_case_id
    and even when their timestamps are tightly interleaved.
    """
    base_time = datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc)

    # Construct interleaved sequence on the exact same test case
    runs = [
        # t0: Playwright
        TestRun(
            run_id="run_pw_0",
            application_id="app_test",
            test_case_id="tc_shared_checkout",
            runner_type=RunnerType.PLAYWRIGHT,
            execution_source=ExecutionSource.REAL_PLAYWRIGHT,
            status=RunStatus.PASSED,
            started_at=(base_time + timedelta(minutes=0)).isoformat(),
        ),
        # t1: AI Agent (interleaved)
        TestRun(
            run_id="run_ai_0",
            application_id="app_test",
            test_case_id="tc_shared_checkout",
            runner_type=RunnerType.AI_AGENT,
            execution_source=ExecutionSource.REAL_AI_AGENT,
            status=RunStatus.FAILED,
            started_at=(base_time + timedelta(minutes=1)).isoformat(),
        ),
        # t2: Playwright
        TestRun(
            run_id="run_pw_1",
            application_id="app_test",
            test_case_id="tc_shared_checkout",
            runner_type=RunnerType.PLAYWRIGHT,
            execution_source=ExecutionSource.REAL_PLAYWRIGHT,
            status=RunStatus.FAILED,
            started_at=(base_time + timedelta(minutes=2)).isoformat(),
        ),
        # t3: AI Agent (interleaved)
        TestRun(
            run_id="run_ai_1",
            application_id="app_test",
            test_case_id="tc_shared_checkout",
            runner_type=RunnerType.AI_AGENT,
            execution_source=ExecutionSource.REAL_AI_AGENT,
            status=RunStatus.PASSED,
            started_at=(base_time + timedelta(minutes=3)).isoformat(),
        ),
        # t4: Synthetic Mock (interleaved)
        TestRun(
            run_id="run_mock_0",
            application_id="app_test",
            test_case_id="tc_shared_checkout",
            runner_type=RunnerType.MOCK,
            execution_source=ExecutionSource.SYNTHETIC_MOCK,
            status=RunStatus.PASSED,
            started_at=(base_time + timedelta(minutes=4)).isoformat(),
        ),
    ]

    records = [
        ReliabilityFeatureExtractor.extract_record_from_run(r, evidence_items=[], failures=[])
        for r in runs
    ]

    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)

    # PW stream: 2 runs -> 1 transition (pw_0 -> pw_1)
    # AI stream: 2 runs -> 1 transition (ai_0 -> ai_1)
    # Mock stream: 1 run -> 0 transitions
    # Total transitions = 2
    usable = [v for v in vectors if v.label_next_failed is not None]
    assert len(usable) == 2

    # Verify Playwright transition
    v_pw0 = next(v for v in vectors if v.run_id == "run_pw_0")
    assert v_pw0.label_next_failed == 1  # target pw_1 is FAILED
    assert v_pw0.target_run_id == "run_pw_1"
    assert v_pw0.execution_source == ExecutionSource.REAL_PLAYWRIGHT
    assert v_pw0.target_execution_source == ExecutionSource.REAL_PLAYWRIGHT

    # Verify AI transition
    v_ai0 = next(v for v in vectors if v.run_id == "run_ai_0")
    assert v_ai0.label_next_failed == 0  # target ai_1 is PASSED
    assert v_ai0.target_run_id == "run_ai_1"
    assert v_ai0.execution_source == ExecutionSource.REAL_AI_AGENT
    assert v_ai0.target_execution_source == ExecutionSource.REAL_AI_AGENT

    # Verify terminal runs have NO target labels
    for terminal_id in ["run_pw_1", "run_ai_1", "run_mock_0"]:
        v_term = next(v for v in vectors if v.run_id == terminal_id)
        assert v_term.label_next_failed is None
        assert v_term.target_run_id is None
        assert v_term.target_execution_source is None

    # Population Separator verifies exact counts
    audit_pw = PopulationSeparator.audit_population(PopulationType.REAL_PLAYWRIGHT_ONLY, records, vectors)
    assert audit_pw.total_runs == 2
    assert audit_pw.total_transitions == 1

    audit_ai = PopulationSeparator.audit_population(PopulationType.REAL_AI_AGENT_ONLY, records, vectors)
    assert audit_ai.total_runs == 2
    assert audit_ai.total_transitions == 1

    audit_real = PopulationSeparator.audit_population(PopulationType.REAL_EXECUTIONS_ONLY, records, vectors)
    assert audit_real.total_runs == 4
    assert audit_real.total_transitions == 2

    audit_demo = PopulationSeparator.audit_population(PopulationType.CONTROLLED_AND_DEMO, records, vectors)
    assert audit_demo.total_runs == 1
    assert audit_demo.total_transitions == 0


def test_feature_and_target_strict_chronological_ordering():
    """
    Validates that:
    1. Feature time must be strictly earlier than target time (t_feature < t_target).
    2. Out-of-order input records are correctly chronologically sorted.
    3. Distinct executions guarantee target_run_id != run_id.
    """
    base_time = datetime(2026, 9, 24, 10, 0, 0, tzinfo=timezone.utc)

    # Intentionally shuffle order
    runs = [
        TestRun(
            run_id="run_step_3",
            application_id="app_order",
            test_case_id="tc_order",
            runner_type=RunnerType.PLAYWRIGHT,
            execution_source=ExecutionSource.REAL_PLAYWRIGHT,
            status=RunStatus.FAILED,
            started_at=(base_time + timedelta(seconds=30)).isoformat(),
        ),
        TestRun(
            run_id="run_step_1",
            application_id="app_order",
            test_case_id="tc_order",
            runner_type=RunnerType.PLAYWRIGHT,
            execution_source=ExecutionSource.REAL_PLAYWRIGHT,
            status=RunStatus.PASSED,
            started_at=(base_time + timedelta(seconds=10)).isoformat(),
        ),
        TestRun(
            run_id="run_step_2",
            application_id="app_order",
            test_case_id="tc_order",
            runner_type=RunnerType.PLAYWRIGHT,
            execution_source=ExecutionSource.REAL_PLAYWRIGHT,
            status=RunStatus.PASSED,
            started_at=(base_time + timedelta(seconds=20)).isoformat(),
        ),
    ]

    records = [
        ReliabilityFeatureExtractor.extract_record_from_run(r, evidence_items=[], failures=[])
        for r in runs
    ]

    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)

    usable = [v for v in vectors if v.label_next_failed is not None]
    assert len(usable) == 2

    # Transition 1: step 1 -> step 2
    v1 = next(v for v in usable if v.run_id == "run_step_1")
    assert v1.target_run_id == "run_step_2"
    assert v1.label_next_failed == 0
    assert v1.target_execution_source == ExecutionSource.REAL_PLAYWRIGHT

    # Transition 2: step 2 -> step 3
    v2 = next(v for v in usable if v.run_id == "run_step_2")
    assert v2.target_run_id == "run_step_3"
    assert v2.label_next_failed == 1
    assert v2.target_execution_source == ExecutionSource.REAL_PLAYWRIGHT

    # Check timestamps: step 1 timestamp < step 2 timestamp
    record_map = {r.run_id: r.timestamp for r in records}
    for v in usable:
        assert v.run_id != v.target_run_id
        assert record_map[v.run_id] < record_map[v.target_run_id]


def test_dual_provenance_filter_rejects_contaminated_vectors():
    """
    Validates that PopulationSeparator strictly enforces dual provenance:
    If a vector has a real execution_source but a synthetic target_execution_source (or vice versa),
    it is strictly rejected from both populations to prevent transition contamination.
    """
    # 1. Artificially contaminated vector: real feature -> synthetic target
    v_leak = ReliabilityFeatureVector(
        run_id="run_contaminated_1",
        target_id="app_x",
        timestamp="2026-09-24T12:00:00Z",
        execution_source=ExecutionSource.REAL_PLAYWRIGHT,
        target_execution_source=ExecutionSource.SYNTHETIC_MOCK,  # Contaminated target!
        target_run_id="run_mock_next",
        label_next_failed=1,
    )

    # 2. Pure real vector
    v_pure_real = ReliabilityFeatureVector(
        run_id="run_pure_1",
        target_id="app_x",
        timestamp="2026-09-24T12:05:00Z",
        execution_source=ExecutionSource.REAL_PLAYWRIGHT,
        target_execution_source=ExecutionSource.REAL_PLAYWRIGHT,
        target_run_id="run_pure_2",
        label_next_failed=0,
    )

    # 3. Pure mock vector
    v_pure_mock = ReliabilityFeatureVector(
        run_id="run_mock_1",
        target_id="app_x",
        timestamp="2026-09-24T12:10:00Z",
        execution_source=ExecutionSource.SYNTHETIC_MOCK,
        target_execution_source=ExecutionSource.SYNTHETIC_MOCK,
        target_run_id="run_mock_2",
        label_next_failed=1,
    )

    vectors = [v_leak, v_pure_real, v_pure_mock]

    # Filter for REAL_PLAYWRIGHT_ONLY: must reject v_leak because target is SYNTHETIC_MOCK
    pw_vectors = PopulationSeparator.filter_vectors_by_population(
        vectors, PopulationType.REAL_PLAYWRIGHT_ONLY
    )
    assert len(pw_vectors) == 1
    assert pw_vectors[0].run_id == "run_pure_1"

    # Filter for REAL_EXECUTIONS_ONLY: must reject v_leak as well
    real_vectors = PopulationSeparator.filter_vectors_by_population(
        vectors, PopulationType.REAL_EXECUTIONS_ONLY
    )
    assert len(real_vectors) == 1
    assert real_vectors[0].run_id == "run_pure_1"

    # Filter for CONTROLLED_AND_DEMO: must reject v_leak because source is REAL_PLAYWRIGHT
    mock_vectors = PopulationSeparator.filter_vectors_by_population(
        vectors, PopulationType.CONTROLLED_AND_DEMO
    )
    assert len(mock_vectors) == 1
    assert mock_vectors[0].run_id == "run_mock_1"


def test_single_run_population_always_reports_zero_transitions_and_no_data():
    """
    Mathematical Invariant:
    A population or stream with N=1 run can never yield a temporal transition.
    It must report total_runs=1, total_transitions=0, and status=DatasetStatus.NO_DATA.
    """
    run = TestRun(
        run_id="run_single_lonely",
        application_id="target_isolated",
        test_case_id="tc_isolated_health",
        runner_type=RunnerType.AI_AGENT,
        execution_source=ExecutionSource.REAL_AI_AGENT,
        status=RunStatus.FAILED,
        started_at="2026-09-24T15:00:00Z",
    )

    records = [
        ReliabilityFeatureExtractor.extract_record_from_run(run, evidence_items=[], failures=[])
    ]
    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)

    assert len(vectors) == 1
    assert vectors[0].label_next_failed is None
    assert vectors[0].target_run_id is None
    assert vectors[0].target_execution_source is None

    audit = PopulationSeparator.audit_population(
        PopulationType.REAL_AI_AGENT_ONLY, records, vectors
    )
    assert audit.total_runs == 1
    assert audit.total_transitions == 0
    assert audit.status == DatasetStatus.NO_DATA
    assert "Zero usable temporal transitions" in audit.status_reason


def test_live_database_provenance_and_conservation_invariant():
    """
    Audit of the live database 'backend/data/reliability_platform.db':
    Verifies that:
    1. Zero cross-stream transitions exist.
    2. Sum of transitions in (REAL_EXECUTIONS_ONLY + CONTROLLED_AND_DEMO) == ALL_HISTORICAL transitions.
    3. REAL_AI_AGENT_ONLY has strictly 0 transitions and status NO_DATA.
    4. Every transition has target_run_id != run_id and execution_source == target_execution_source.
    """
    db_path = "backend/data/reliability_platform.db"
    if not os.path.exists(db_path):
        pytest.skip(f"Live database {db_path} not found; skipping live DB audit test.")

    repo = SQLiteRepository(db_path=db_path)
    runs = repo.list_runs(limit=2000)
    assert len(runs) >= 100, f"Expected substantial historical runs, found {len(runs)}"

    records = []
    for r in runs:
        ev = repo.get_evidence_by_run(r.run_id)
        fa = repo.get_failures_by_run(r.run_id)
        records.append(ReliabilityFeatureExtractor.extract_record_from_run(r, ev, fa))

    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)
    usable_transitions = [v for v in vectors if v.label_next_failed is not None]

    # Invariant 1: Every transition has target_run_id != run_id
    for v in usable_transitions:
        assert v.target_run_id is not None
        assert v.target_run_id != v.run_id
        # Invariant 2: Execution sources must match within isolated streams
        assert v.execution_source == v.target_execution_source, (
            f"Cross-source leak in vector {v.run_id}: "
            f"source={v.execution_source} -> target={v.target_execution_source}"
        )

    # Invariant 3: Population transition conservation
    audit_all = PopulationSeparator.audit_population(PopulationType.ALL_HISTORICAL, records, vectors)
    audit_real = PopulationSeparator.audit_population(PopulationType.REAL_EXECUTIONS_ONLY, records, vectors)
    audit_demo = PopulationSeparator.audit_population(PopulationType.CONTROLLED_AND_DEMO, records, vectors)
    audit_ai = PopulationSeparator.audit_population(PopulationType.REAL_AI_AGENT_ONLY, records, vectors)
    audit_pw = PopulationSeparator.audit_population(PopulationType.REAL_PLAYWRIGHT_ONLY, records, vectors)

    # Exact conservation: Transitions in Real + Transitions in Controlled/Demo == All Historical
    assert audit_real.total_transitions + audit_demo.total_transitions == audit_all.total_transitions, (
        f"Transition conservation violated: {audit_real.total_transitions} (Real) + "
        f"{audit_demo.total_transitions} (Demo) != {audit_all.total_transitions} (All)"
    )

    # Single-run AI Agent population has 0 transitions
    assert audit_ai.total_runs == 1
    assert audit_ai.total_transitions == 0
    assert audit_ai.status == DatasetStatus.NO_DATA

    # Real Playwright has transitions and matches Real Executions transitions
    assert audit_pw.total_transitions == audit_real.total_transitions


def test_demo_shop_excluded_from_real_population():
    """
    Regression Test for Slice 6.9:
    Ensures that demo shop runs/vectors (target_id=tgt_demo_shop or application_id=app_demo_shop)
    are strictly classified as DEMO campaign_type and are NEVER admitted into REAL_EXECUTIONS_ONLY
    or REAL_PLAYWRIGHT_ONLY populations.
    Only genuine real applications (app_eda, app_inventory, app_booking) are present in the real population.
    """
    db_path = "backend/data/reliability_platform.db"
    if not os.path.exists(db_path):
        pytest.skip(f"Live database {db_path} not found; skipping live DB test.")

    repo = SQLiteRepository(db_path=db_path)
    runs = repo.list_runs(limit=2000)

    records = []
    for r in runs:
        ev = repo.get_evidence_by_run(r.run_id)
        fa = repo.get_failures_by_run(r.run_id)
        records.append(ReliabilityFeatureExtractor.extract_record_from_run(r, ev, fa))

    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)

    real_records = PopulationSeparator.filter_records_by_population(records, PopulationType.REAL_EXECUTIONS_ONLY)
    real_vectors = PopulationSeparator.filter_vectors_by_population(vectors, PopulationType.REAL_EXECUTIONS_ONLY)

    # 1. Assert no demo shop in real records
    for r in real_records:
        assert r.application_id != "app_demo_shop", f"Demo shop record {r.run_id} leaked into REAL_EXECUTIONS_ONLY"
        assert r.target_id != "tgt_demo_shop", f"Demo shop target {r.run_id} leaked into REAL_EXECUTIONS_ONLY"
        assert r.campaign_type == "REAL_RELIABILITY", f"Non-real campaign {r.campaign_type} in REAL_EXECUTIONS_ONLY"

    # 2. Assert no demo shop in real vectors
    for v in real_vectors:
        assert v.application_id != "app_demo_shop", f"Demo shop vector {v.run_id} leaked into REAL_EXECUTIONS_ONLY"
        assert v.target_id != "tgt_demo_shop", f"Demo shop target {v.run_id} leaked into REAL_EXECUTIONS_ONLY"
        assert v.campaign_type == "REAL_RELIABILITY", f"Non-real campaign {v.campaign_type} in REAL_EXECUTIONS_ONLY"
        if v.target_campaign_type is not None:
            assert v.target_campaign_type == "REAL_RELIABILITY"

    # 3. Only the 3 genuine applications exist in REAL_EXECUTIONS_ONLY
    real_app_ids = {r.application_id for r in real_records}
    assert real_app_ids == {"app_eda", "app_inventory", "app_booking"}
    assert len(real_records) == 80  # 33 EDA + 25 Inventory + 22 Booking

