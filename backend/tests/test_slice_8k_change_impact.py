"""
Slice 8K — Change-Aware Impact Analysis & Adaptive Regression Testing Test Suite

Covers 50+ deterministic unit and integration test scenarios:
1. ChangeSet creation
2. exact Git SHA tracking
3. changed file detection
4. changed symbol detection
5. code classification
6. prompt classification
7. model classification
8. retrieval classification
9. tool classification
10. parser classification
11. API contract classification
12. UI classification
13. dependency classification
14. multi-variable classification
15. direct impact detection
16. dependency impact
17. downstream impact
18. AI behavior impact
19. contract impact
20. historical memory integration
21. reliability integration
22. workflow impact
23. deep scope generation
24. targeted scope generation
25. smoke scope generation
26. adaptive scope expansion
27. baseline/candidate run separation
28. behavioral comparison
29. deterministic contract regression
30. expected change classification
31. improvement classification
32. unknown classification
33. insufficient evidence
34. multi-variable attribution blocking
35. stale SHA invalidation
36. independent retest
37. no evidence reuse
38. governance boundary
39. live change-analysis events
40. live regression events
41. MCP ToolRegistry integration
42. API behavior
43. historical failure -> regression hypothesis
44. unknown impact handling
45. application isolation
46. Scenario A: Prompt-only change
47. Scenario B: Backend logic change
48. Scenario C: UI-only change
49. Scenario E: Prompt + model change (multi-variable)
50. Scenario G: Hidden downstream impact (runtime scope expansion)
51. Scenario H: Documentation-only change
52. Scenario D: API contract change
"""

import pytest
import uuid
from typing import Dict, Any, List

from backend.app.change_impact.models import (
    ChangeType,
    ChangeSource,
    ImpactRelationshipType,
    ComponentType,
    ImpactLevel,
    RegressionScope,
    PlanStatus,
    ComparisonClassification,
    FindingSeverity,
    ChangeSet,
    ImpactRelationship,
    AffectedComponent,
    AffectedWorkflow,
    ChangeImpact,
    RegressionPlanItem,
    RegressionScopeExpansion,
    AdaptiveRegressionPlan,
    BehavioralComparison,
    RegressionFinding,
)
from backend.app.change_impact.engine import ChangeAnalysisEngine
from backend.app.change_impact.planner import AdaptiveRegressionPlanner
from backend.app.change_impact.comparator import BehavioralComparator
from backend.app.change_impact.service import ChangeImpactService
from backend.app.dogfooding.live_events import LiveEventType
from backend.app.dogfooding.live_session_bus import live_event_bus
from backend.app.memory.repository import EngineeringMemoryRepository
from backend.app.memory.models import EngineeringMemory, MemoryType, MemoryStatus
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.control_plane.context import ToolInvocationContext


@pytest.fixture
def memory_repo(tmp_path):
    db_file = str(tmp_path / "test_memory.db")
    return EngineeringMemoryRepository(db_path=db_file)


@pytest.fixture
def engine(memory_repo):
    return ChangeAnalysisEngine(memory_repository=memory_repo)


@pytest.fixture
def planner():
    return AdaptiveRegressionPlanner()


@pytest.fixture
def comparator():
    return BehavioralComparator()


@pytest.fixture
def service(memory_repo):
    return ChangeImpactService(memory_repository=memory_repo)


# ============================================================================
# 1-4: ChangeSet & Git Tracking
# ============================================================================

def test_01_changeset_creation():
    cs = ChangeSet(
        repository="test-repo",
        base_commit="sha_base_001",
        candidate_commit="sha_cand_002",
        changed_files=["app/main.py"]
    )
    assert cs.change_set_id.startswith("cs_")
    assert cs.repository == "test-repo"
    assert cs.base_commit == "sha_base_001"
    assert cs.candidate_commit == "sha_cand_002"
    assert cs.changed_files == ["app/main.py"]


def test_02_exact_git_sha_tracking():
    cs = ChangeSet(base_commit="4b825dc642cb6eb9a060e54bf8d69288fbee4904", candidate_commit="01be85c13b28b7e452bbd3e68e7436b7bfa92305")
    assert len(cs.base_commit) == 40
    assert len(cs.candidate_commit) == 40
    assert cs.base_commit != cs.candidate_commit


def test_03_changed_file_detection(engine):
    types = engine.classify_change(changed_files=["backend/app/parser.py", "frontend/styles.css"])
    assert ChangeType.PARSER in types
    assert ChangeType.UI in types
    assert ChangeType.CODE in types


def test_04_changed_symbol_detection(engine):
    diff = """
+def extract_options(payload: dict):
+    return payload.get("options")
+class QuestionResultParser:
+    pass
    """
    symbols = engine.extract_changed_symbols(diff)
    assert "extract_options" in symbols
    assert "QuestionResultParser" in symbols


# ============================================================================
# 5-14: Change Classification
# ============================================================================

def test_05_code_classification(engine):
    types = engine.classify_change(changed_files=["backend/service.py", "utils.ts"])
    assert ChangeType.CODE in types


def test_06_prompt_classification(engine):
    types = engine.classify_change(changed_files=["prompts/question_gen.prompt"], prompts_changed=["prompt_v12"])
    assert ChangeType.PROMPT in types


def test_07_model_classification(engine):
    types = engine.classify_change(models_changed=["qwen2.5-coder:7b-instruct"])
    assert ChangeType.MODEL in types


def test_08_retrieval_classification(engine):
    types = engine.classify_change(retrieval_changed=["hybrid_rag_k_5_embed_v2"])
    assert ChangeType.RETRIEVAL in types


def test_09_tool_classification(engine):
    types = engine.classify_change(tools_changed=["browser_click_action"])
    assert ChangeType.TOOL in types


def test_10_parser_classification(engine):
    types = engine.classify_change(changed_files=["backend/app/extractors/json_parser.py"])
    assert ChangeType.PARSER in types


def test_11_api_contract_classification(engine):
    types = engine.classify_change(changed_files=["backend/app/api/v1/question.py"])
    assert ChangeType.API_CONTRACT in types


def test_12_ui_classification(engine):
    types = engine.classify_change(changed_files=["frontend/components/QuestionCard.tsx", "frontend/globals.css"])
    assert ChangeType.UI in types


def test_13_dependency_classification(engine):
    types = engine.classify_change(changed_files=["requirements.txt", "package.json"])
    assert ChangeType.DEPENDENCY in types


def test_14_multi_variable_classification(engine):
    cs = ChangeSet(
        changed_files=["backend/parser.py"],
        changed_prompts=["prompt_v13"],
        changed_models=["qwen2.5-coder:7b"],
        change_types=[ChangeType.PARSER, ChangeType.PROMPT, ChangeType.MODEL]
    )
    assert cs.is_multi_variable() is True


# ============================================================================
# 15-22: Impact Graph & Integration
# ============================================================================

def test_15_direct_impact_detection(engine):
    cs = ChangeSet(
        changed_files=["backend/parser.py"],
        change_types=[ChangeType.PARSER]
    )
    impact = engine.analyze_impact(cs)
    direct_comps = [c for c in impact.affected_components if c.relationship == ImpactRelationshipType.DIRECT]
    assert len(direct_comps) > 0
    assert any("parser" in c.component_id for c in direct_comps)
    assert any("directly changed" in c.confidence_factors for c in direct_comps)


def test_16_dependency_impact(engine):
    cs = ChangeSet(
        changed_files=["backend/app/api/v1/routes.py"],
        change_types=[ChangeType.API_CONTRACT]
    )
    impact = engine.analyze_impact(cs)
    dep_comps = [c for c in impact.affected_components if c.relationship == ImpactRelationshipType.DEPENDENCY]
    assert len(dep_comps) > 0
    assert any("frontend" in c.name.lower() or "client" in c.name.lower() for c in dep_comps)


def test_17_downstream_impact(engine):
    cs = ChangeSet(
        changed_files=["backend/parser.py"],
        change_types=[ChangeType.PARSER]
    )
    impact = engine.analyze_impact(cs)
    downstream_rels = [r for r in impact.impact_relationships if r.relationship_type == ImpactRelationshipType.DOWNSTREAM]
    assert len(downstream_rels) > 0


def test_18_ai_behavior_impact(engine):
    cs = ChangeSet(
        changed_prompts=["prompt_v13"],
        change_types=[ChangeType.PROMPT]
    )
    impact = engine.analyze_impact(cs)
    assert impact.ai_behavior_affected is True
    assert any(c.component_type == ComponentType.AI_PROMPT for c in impact.affected_components)


def test_19_contract_impact(engine):
    cs = ChangeSet(
        changed_prompts=["prompt_v13"],
        change_types=[ChangeType.PROMPT]
    )
    impact = engine.analyze_impact(cs)
    assert "contract_4_options_present" in impact.affected_contracts


def test_20_historical_memory_integration(memory_repo, engine):
    # Add historical failure memory
    mem = EngineeringMemory(
        target_id="target_qgen",
        application_id="app_qgen",
        workflow_id="wf_question_generation",
        memory_type=MemoryType.FAILURE_HISTORY,
        status=MemoryStatus.OBSERVED,
        content="Failure observed when model emitted duplicate distractor items",
        source_run_id="run_prev_999",
        source_evidence_ids=["evi_01"]
    )
    memory_repo.save_memory(mem)

    cs = ChangeSet(
        repository="app_qgen",
        changed_files=["backend/parser.py"],
        change_types=[ChangeType.PARSER]
    )
    impact = engine.analyze_impact(cs, application_id="app_qgen")
    gen_wf = next((wf for wf in impact.affected_workflows if wf.workflow_id == "wf_question_generation"), None)
    assert gen_wf is not None
    assert len(gen_wf.historical_failures) > 0
    assert "duplicate distractor items" in gen_wf.historical_failures[0]


def test_21_reliability_integration(memory_repo, engine):
    mem = EngineeringMemory(
        target_id="target_qgen",
        application_id="app_qgen",
        workflow_id="wf_question_generation",
        memory_type=MemoryType.RELIABILITY_PATTERN,
        status=MemoryStatus.OBSERVED,
        content="P95 latency elevated to 8.2s during concurrent prompts",
        source_run_id="run_prev_888",
        source_evidence_ids=["evi_02"]
    )
    memory_repo.save_memory(mem)

    cs = ChangeSet(repository="app_qgen", changed_prompts=["prompt_v13"], change_types=[ChangeType.PROMPT])
    impact = engine.analyze_impact(cs, application_id="app_qgen")
    gen_wf = next((wf for wf in impact.affected_workflows if wf.workflow_id == "wf_question_generation"), None)
    assert gen_wf is not None
    assert "pattern" in gen_wf.reliability_history


def test_22_workflow_impact(engine):
    cs = ChangeSet(changed_files=["backend/parser.py"], change_types=[ChangeType.PARSER])
    impact = engine.analyze_impact(cs)
    workflow_ids = [wf.workflow_id for wf in impact.affected_workflows]
    assert "wf_question_generation" in workflow_ids
    assert "wf_result_validation" in workflow_ids


# ============================================================================
# 23-26: Adaptive Regression Plan Scopes & Expansion
# ============================================================================

def test_23_deep_scope_generation(planner, engine):
    cs = ChangeSet(changed_prompts=["prompt_v13"], change_types=[ChangeType.PROMPT])
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_qgen")
    deep_items = [it for it in plan.items if it.scope == RegressionScope.DEEP]
    assert len(deep_items) > 0
    assert all(it.priority >= 0.8 for it in deep_items)


def test_24_targeted_scope_generation(planner, engine):
    cs = ChangeSet(changed_files=["backend/parser.py"], change_types=[ChangeType.PARSER])
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_qgen")
    targeted_items = [it for it in plan.items if it.scope == RegressionScope.TARGETED]
    assert len(targeted_items) > 0


def test_25_smoke_scope_generation(planner, engine):
    cs = ChangeSet(changed_files=["backend/parser.py"], change_types=[ChangeType.PARSER])
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_qgen")
    smoke_items = [it for it in plan.items if it.scope == RegressionScope.SMOKE]
    assert len(smoke_items) > 0
    assert any("smoke" in it.workflow_id for it in smoke_items)


def test_26_adaptive_scope_expansion(planner, engine):
    cs = ChangeSet(changed_files=["backend/parser.py"], change_types=[ChangeType.PARSER])
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_qgen")
    initial_deep = plan.scope_summary["DEEP"]

    new_item = RegressionPlanItem(
        workflow_id="wf_result_rendering",
        name="Result Rendering Workflow",
        scope=RegressionScope.DEEP,
        reasons=["runtime_dom_exception"],
        priority=0.9
    )
    expansion = planner.expand_scope(
        plan=plan,
        trigger="DOM_CONTRACT_VIOLATION",
        evidence_ids=["evi_dom_err_10"],
        new_items=[new_item],
        reason="Radio button elements failed to mount after parser returned malformed payload"
    )
    assert plan.plan_status == PlanStatus.EXPANDED
    assert plan.scope_summary["DEEP"] >= initial_deep
    assert expansion.trigger == "DOM_CONTRACT_VIOLATION"
    assert len(plan.expansions) == 1


# ============================================================================
# 27-37: Behavioral Comparison & Multi-Variable Rules
# ============================================================================

def test_27_baseline_candidate_run_separation(comparator, planner, engine):
    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2")
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")

    with pytest.raises(ValueError, match="Independent execution violation"):
        comparator.compare_runs(
            plan=plan,
            change_set=cs,
            baseline_run_id="run_same_100",
            candidate_run_id="run_same_100",
            baseline_results={},
            candidate_results={}
        )


def test_28_behavioral_comparison_no_regression(comparator, planner, engine):
    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2", change_types=[ChangeType.CODE])
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")

    comp = comparator.compare_runs(
        plan=plan,
        change_set=cs,
        baseline_run_id="run_base_1",
        candidate_run_id="run_cand_2",
        baseline_results={"passed": True, "errors": []},
        candidate_results={"passed": True, "errors": []},
        contract_evaluations={"contract_4_options_present": True}
    )
    assert comp.classification == ComparisonClassification.NO_REGRESSION
    assert comp.is_multi_variable_change is False


def test_29_deterministic_contract_regression(comparator, planner, engine):
    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2", change_types=[ChangeType.CODE])
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")

    comp = comparator.compare_runs(
        plan=plan,
        change_set=cs,
        baseline_run_id="run_base_1",
        candidate_run_id="run_cand_2",
        baseline_results={"passed": True, "errors": []},
        candidate_results={"passed": True, "errors": []},
        contract_evaluations={"contract_4_options_present": False}
    )
    assert comp.classification == ComparisonClassification.REGRESSION
    assert "contract_4_options_present" in comp.contract_violations

    findings = comparator.generate_findings(comp, plan)
    assert len(findings) > 0
    assert findings[0].severity == FindingSeverity.CRITICAL


def test_30_expected_change_classification(comparator, planner, engine):
    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2", change_types=[ChangeType.PROMPT])
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")

    comp = comparator.compare_runs(
        plan=plan,
        change_set=cs,
        baseline_run_id="run_base_1",
        candidate_run_id="run_cand_2",
        baseline_results={"passed": True, "errors": [], "output_differs": True},
        candidate_results={"passed": True, "errors": []},
        contract_evaluations={"contract_4_options_present": True}
    )
    assert comp.classification == ComparisonClassification.EXPECTED_CHANGE


def test_31_improvement_classification(comparator, planner, engine):
    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2", change_types=[ChangeType.CODE])
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")

    comp = comparator.compare_runs(
        plan=plan,
        change_set=cs,
        baseline_run_id="run_base_1",
        candidate_run_id="run_cand_2",
        baseline_results={"passed": False, "errors": ["Null pointer on distractor"]},
        candidate_results={"passed": True, "errors": []},
        contract_evaluations={"contract_4_options_present": True}
    )
    assert comp.classification == ComparisonClassification.IMPROVEMENT


def test_32_unknown_classification(comparator, planner, engine):
    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2")
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")

    comp = comparator.compare_runs(
        plan=plan,
        change_set=cs,
        baseline_run_id="run_base_1",
        candidate_run_id="run_cand_2",
        baseline_results={"passed": False, "errors": ["Network dropped"]},
        candidate_results={"passed": False, "errors": ["Network dropped"]},
        contract_evaluations={}
    )
    assert comp.classification in [ComparisonClassification.UNKNOWN, ComparisonClassification.INSUFFICIENT_EVIDENCE]


def test_33_insufficient_evidence(comparator, planner, engine):
    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2")
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")

    comp = comparator.compare_runs(
        plan=plan,
        change_set=cs,
        baseline_run_id="run_base_1",
        candidate_run_id="run_cand_2",
        baseline_results={},
        candidate_results={}
    )
    assert comp.classification == ComparisonClassification.INSUFFICIENT_EVIDENCE


def test_34_multi_variable_attribution_blocking(comparator, planner, engine):
    cs = ChangeSet(
        base_commit="sha1",
        candidate_commit="sha2",
        changed_prompts=["prompt_v13"],
        changed_models=["qwen2.5-coder:7b"],
        change_types=[ChangeType.PROMPT, ChangeType.MODEL]
    )
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")

    comp = comparator.compare_runs(
        plan=plan,
        change_set=cs,
        baseline_run_id="run_base_1",
        candidate_run_id="run_cand_2",
        baseline_results={"passed": True, "errors": []},
        candidate_results={"passed": False, "errors": ["Missing correct indicator"]},
        contract_evaluations={"contract_correct_answer_indicated": False}
    )
    assert comp.is_multi_variable_change is True
    assert comp.can_attribute_cause is False
    assert "Multiple architectural variables" in comp.attribution_note


def test_35_stale_sha_invalidation(planner, engine):
    cs = ChangeSet(base_commit="sha_base", candidate_commit="sha_cand_v1", change_types=[ChangeType.CODE])
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")

    # Drift in candidate SHA
    is_fresh = planner.validate_plan_freshness(plan, current_candidate_sha="sha_cand_v2_drifted")
    assert is_fresh is False
    assert plan.stale is True
    assert plan.plan_status == PlanStatus.STALE


def test_36_independent_retest(comparator, planner, engine):
    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2", change_types=[ChangeType.CODE])
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")

    # Retest after candidate fix
    retest_comp = comparator.compare_runs(
        plan=plan,
        change_set=cs,
        baseline_run_id="run_base_original",
        candidate_run_id="run_candidate_retest_fresh",
        baseline_results={"passed": True},
        candidate_results={"passed": True},
        contract_evaluations={"contract_4_options_present": True}
    )
    assert retest_comp.classification == ComparisonClassification.NO_REGRESSION


def test_37_no_evidence_reuse(comparator, planner, engine):
    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2")
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")

    # Baseline and candidate cannot share the same run ID
    with pytest.raises(ValueError):
        comparator.compare_runs(
            plan=plan,
            change_set=cs,
            baseline_run_id="run_reuse_test",
            candidate_run_id="run_reuse_test",
            baseline_results={},
            candidate_results={}
        )


# ============================================================================
# 38-45: Governance, Events & Platform Integration
# ============================================================================

def test_38_governance_boundary(comparator, planner, engine):
    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2", change_types=[ChangeType.CODE])
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")

    comp = comparator.compare_runs(
        plan=plan,
        change_set=cs,
        baseline_run_id="run_b",
        candidate_run_id="run_c",
        baseline_results={"passed": True},
        candidate_results={"passed": False, "errors": ["Contract violated"]},
        contract_evaluations={"contract_4_options_present": False}
    )
    findings = comparator.generate_findings(comp, plan)
    assert len(findings) > 0
    # Mandatory invariant: Finding requires human governance authorization
    assert findings[0].requires_human_governance is True


def test_39_live_change_analysis_events(service):
    session = live_event_bus.create_session("run_live_39", "target_live", "app_live")
    session_id = session.session_id

    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2", changed_files=["backend/parser.py"], change_types=[ChangeType.PARSER])
    service.analyze_change(cs, session_id=session_id)

    events = live_event_bus.get_events(session_id)
    event_types = [e.event_type for e in events]
    assert LiveEventType.CHANGE_ANALYSIS_STARTED in event_types
    assert LiveEventType.IMPACT_GRAPH_BUILT in event_types
    assert LiveEventType.CHANGE_ANALYSIS_COMPLETED in event_types


def test_40_live_regression_events(service):
    session = live_event_bus.create_session("run_live_40", "target_live", "app_live")
    session_id = session.session_id

    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2", changed_files=["backend/parser.py"], change_types=[ChangeType.PARSER])
    service.register_change_set(cs)
    plan = service.create_regression_plan(cs.change_set_id, "target_live", session_id=session_id)

    service.execute_regression_plan(plan.plan_id, session_id=session_id)

    events = live_event_bus.get_events(session_id)
    event_types = [e.event_type for e in events]
    assert LiveEventType.REGRESSION_PLAN_CREATED in event_types
    assert LiveEventType.REGRESSION_EXECUTION_STARTED in event_types
    assert LiveEventType.REGRESSION_EXECUTION_COMPLETED in event_types


def test_41_mcp_tool_registry_integration(memory_repo):
    control_plane = ReliabilityControlPlane(
        db_path=memory_repo.db_path,
        enable_change_impact_tools=True
    )
    tools = control_plane.registry.list_tools()
    tool_names = [t.name for t in tools]
    assert "analyze_change_impact" in tool_names
    assert "get_change_impact" in tool_names
    assert "create_regression_plan" in tool_names
    assert "get_regression_plan" in tool_names
    assert "execute_regression_plan" in tool_names
    assert "get_regression_findings" in tool_names
    assert "compare_change_behavior" in tool_names


def test_42_api_behavior(service):
    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2", changed_prompts=["prompt_v13"])
    impact = service.analyze_change(cs)
    assert impact.change_set_id == cs.change_set_id
    retrieved_impact = service.get_impact(cs.change_set_id)
    assert retrieved_impact is not None


def test_43_historical_failure_to_regression_hypothesis(memory_repo, engine, planner):
    mem = EngineeringMemory(
        target_id="target_app",
        application_id="app_test",
        workflow_id="wf_result_validation",
        memory_type=MemoryType.FAILURE_HISTORY,
        status=MemoryStatus.OBSERVED,
        content="Distractor options were blank",
        source_run_id="run_old_10",
        source_evidence_ids=["evi_old_1"]
    )
    memory_repo.save_memory(mem)

    cs = ChangeSet(repository="app_test", changed_files=["backend/parser.py"], change_types=[ChangeType.PARSER])
    impact = engine.analyze_impact(cs, application_id="app_test")
    plan = planner.create_plan(cs, impact, target_id="target_app")

    val_item = next((it for it in plan.items if it.workflow_id == "wf_result_validation"), None)
    assert val_item is not None
    assert any("historical_failure_hypothesis" in r for r in val_item.reasons)


def test_44_unknown_impact_handling(engine):
    cs = ChangeSet(base_commit="sha1", candidate_commit="sha2")
    impact = engine.analyze_impact(cs)
    assert impact.unknown_impact is True
    assert "impact unknown" in impact.summary.lower()


def test_45_application_isolation(service):
    cs_a = ChangeSet(repository="app_alpha", changed_files=["alpha.py"], change_types=[ChangeType.CODE])
    cs_b = ChangeSet(repository="app_beta", changed_files=["beta.py"], change_types=[ChangeType.CODE])
    impact_a = service.analyze_change(cs_a, application_id="app_alpha")
    impact_b = service.analyze_change(cs_b, application_id="app_beta")

    assert impact_a.change_set_id != impact_b.change_set_id
    assert service.get_impact(cs_a.change_set_id) is not None
    assert service.get_impact(cs_b.change_set_id) is not None


# ============================================================================
# 46-52: Controlled Scenarios A through H
# ============================================================================

def test_46_scenario_a_prompt_only_change(engine, planner):
    """Scenario A: Prompt-only change (v12 -> v13) triggers AI behavior & output contract tests."""
    cs = ChangeSet(
        changed_prompts=["prompt_question_gen_v13"],
        change_types=[ChangeType.PROMPT]
    )
    impact = engine.analyze_impact(cs)
    assert impact.ai_behavior_affected is True
    assert "contract_4_options_present" in impact.affected_contracts

    plan = planner.create_plan(cs, impact, target_id="target_1")
    assert plan.scope_summary["DEEP"] >= 1
    deep_item = [it for it in plan.items if it.scope == RegressionScope.DEEP][0]
    assert "wf_question_generation" in deep_item.workflow_id


def test_47_scenario_b_backend_logic_change(engine, planner):
    """Scenario B: Backend logic change triggers generation workflow + validation + downstream handling."""
    cs = ChangeSet(
        changed_files=["backend/app/question_generator/service.py"],
        change_types=[ChangeType.CODE]
    )
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")
    assert plan.scope_summary["TARGETED"] >= 1 or plan.scope_summary["DEEP"] >= 1


def test_48_scenario_c_ui_only_change(engine, planner):
    """Scenario C: UI-only change triggers UI regression + smoke, not deep backend."""
    cs = ChangeSet(
        changed_files=["frontend/components/QuestionCard.css"],
        change_types=[ChangeType.UI]
    )
    impact = engine.analyze_impact(cs)
    plan = planner.create_plan(cs, impact, target_id="target_1")
    # Should not have deep backend question generation
    gen_deep = [it for it in plan.items if it.scope == RegressionScope.DEEP and it.workflow_id == "wf_question_generation"]
    assert len(gen_deep) == 0


def test_49_scenario_e_prompt_plus_model_change(comparator, planner, engine):
    """Scenario E: Prompt + Model change triggers MULTI_VARIABLE_CHANGE and blocks causal attribution."""
    cs = ChangeSet(
        base_commit="sha1",
        candidate_commit="sha2",
        changed_prompts=["prompt_v13"],
        changed_models=["qwen2.5-coder:14b"],
        change_types=[ChangeType.PROMPT, ChangeType.MODEL]
    )
    assert cs.is_multi_variable() is True
    impact = engine.analyze_impact(cs)
    assert "MULTI_VARIABLE_CHANGE" in impact.summary

    plan = planner.create_plan(cs, impact, target_id="target_1")
    comp = comparator.compare_runs(
        plan=plan,
        change_set=cs,
        baseline_run_id="run_base",
        candidate_run_id="run_cand",
        baseline_results={"passed": True},
        candidate_results={"passed": False, "errors": ["Latency spike"]},
        contract_evaluations={}
    )
    assert comp.is_multi_variable_change is True
    assert comp.can_attribute_cause is False


def test_50_scenario_g_hidden_downstream_impact_expansion(service):
    """Scenario G: Parser change -> runtime discovers rendering failure -> REGRESSION_SCOPE_EXPANDED."""
    session = live_event_bus.create_session("run_live_50", "target_qgen", "app_qgen")
    session_id = session.session_id

    cs = ChangeSet(
        base_commit="sha_base",
        candidate_commit="sha_cand",
        changed_files=["backend/app/parser.py"],
        change_types=[ChangeType.PARSER]
    )
    service.register_change_set(cs)
    plan = service.create_regression_plan(cs.change_set_id, "target_qgen", session_id=session_id)

    # Runtime discovers DOM rendering failure
    expansion = service.expand_plan_scope(
        plan_id=plan.plan_id,
        trigger="DOM_RENDERING_FAILURE",
        evidence_ids=["evi_dom_error_42"],
        new_items=[
            RegressionPlanItem(
                workflow_id="wf_result_rendering",
                name="Result Rendering & Interaction Workflow",
                scope=RegressionScope.DEEP,
                reasons=["runtime_rendering_failure_observed"],
                priority=0.95
            )
        ],
        reason="Parser returned malformed options payload that broke frontend radio button rendering",
        session_id=session_id
    )

    assert expansion.trigger == "DOM_RENDERING_FAILURE"
    assert plan.plan_status == PlanStatus.EXPANDED
    events = live_event_bus.get_events(session_id)
    assert any(e.event_type == LiveEventType.REGRESSION_SCOPE_EXPANDED for e in events)


def test_51_scenario_h_documentation_only_change(engine, planner):
    """Scenario H: Documentation-only change results in smoke sanity check without deep tests."""
    cs = ChangeSet(
        changed_files=["README.md", "docs/architecture.md"],
        change_types=[ChangeType.DOCUMENTATION]
    )
    impact = engine.analyze_impact(cs)
    assert "documentation-only" in impact.summary.lower()
    plan = planner.create_plan(cs, impact, target_id="target_1")
    assert plan.scope_summary["DEEP"] == 0
    assert plan.scope_summary["TARGETED"] == 0
    assert plan.scope_summary["SMOKE"] == 1


def test_52_scenario_d_api_contract_change(engine, planner):
    """Scenario D: API contract change triggers endpoint, parser, frontend client, and behavioral contract."""
    cs = ChangeSet(
        changed_files=["backend/app/api/v1/question.py"],
        change_types=[ChangeType.API_CONTRACT]
    )
    impact = engine.analyze_impact(cs)
    assert any(c.component_type == ComponentType.API_ENDPOINT for c in impact.affected_components)
    assert any(c.relationship == ImpactRelationshipType.DEPENDENCY for c in impact.affected_components)
    assert any(wf.workflow_id == "wf_api_dispatch" for wf in impact.affected_workflows)
