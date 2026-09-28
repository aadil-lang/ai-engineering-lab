"""
Slice 8K — Change-Aware Impact Analysis & Adaptive Regression Testing Domain Models

Provides canonical structured models for:
- ChangeSets and deterministic change classification (Code, Prompt, Model, Parser, UI, Contract, etc.)
- Component and Workflow Impact Graphs
- Adaptive Regression Plans (DEEP, TARGETED, SMOKE scopes)
- Runtime Scope Expansions
- Behavioral Comparisons and Multi-Variable Attribution Blocking
- Regression Findings and Governance Boundaries

Core Principle:
- A change determines where the Lab starts testing; evidence determines where it must continue.
- Historical memory informs what deserves attention; deterministic systems remain authoritative.
- Never reduce multi-variable changes to a single cause without controlled evidence.
- No automated release/merge/deploy without human governance authorization.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Any, Dict, List, Set, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid


class ChangeType(str, Enum):
    """Explicit deterministic classification of changes."""
    CODE = "CODE"
    PROMPT = "PROMPT"
    MODEL = "MODEL"
    MODEL_CONFIGURATION = "MODEL_CONFIGURATION"
    RETRIEVAL = "RETRIEVAL"
    TOOL = "TOOL"
    PARSER = "PARSER"
    BEHAVIORAL_CONTRACT = "BEHAVIORAL_CONTRACT"
    UI = "UI"
    API_CONTRACT = "API_CONTRACT"
    CONFIGURATION = "CONFIGURATION"
    DEPENDENCY = "DEPENDENCY"
    DATABASE_SCHEMA = "DATABASE_SCHEMA"
    DEPLOYMENT = "DEPLOYMENT"
    DOCUMENTATION = "DOCUMENTATION"
    UNKNOWN = "UNKNOWN"


class ChangeSource(str, Enum):
    """Origin or trigger of the change."""
    GIT = "GIT"
    PROMPT_LAB = "PROMPT_LAB"
    RUNTIME_CONFIG = "RUNTIME_CONFIG"
    MODEL_REGISTRY = "MODEL_REGISTRY"
    MANUAL = "MANUAL"
    UNKNOWN = "UNKNOWN"


class ImpactRelationshipType(str, Enum):
    """Relationship between changed element and affected component/workflow."""
    DIRECT = "DIRECT"
    DEPENDENCY = "DEPENDENCY"
    DOWNSTREAM = "DOWNSTREAM"
    AI_BEHAVIOR = "AI_BEHAVIOR"
    CONTRACT = "CONTRACT"
    HISTORICAL = "HISTORICAL"
    RISK_RELATED = "RISK_RELATED"
    UNKNOWN = "UNKNOWN"


class ComponentType(str, Enum):
    """Architectural classification of an application component."""
    BACKEND = "BACKEND"
    FRONTEND_UI = "FRONTEND_UI"
    AI_PROMPT = "AI_PROMPT"
    AI_MODEL = "AI_MODEL"
    PARSER = "PARSER"
    API_ENDPOINT = "API_ENDPOINT"
    DATABASE = "DATABASE"
    CONFIG = "CONFIG"
    TOOL = "TOOL"
    RETRIEVAL = "RETRIEVAL"
    CONTRACT = "CONTRACT"
    UNKNOWN = "UNKNOWN"


class ImpactLevel(str, Enum):
    """Categorical severity of impact."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class RegressionScope(str, Enum):
    """Testing depth scope for adaptive regression planning."""
    DEEP = "DEEP"          # Directly affected, high risk: full workflow, edge cases, malformed outputs
    TARGETED = "TARGETED"  # Direct dependencies, historical failure hypotheses, downstream consumers
    SMOKE = "SMOKE"        # Critical path health, primary navigation, baseline integrity


class PlanStatus(str, Enum):
    """Lifecycle status of an adaptive regression plan."""
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    EXPANDED = "EXPANDED"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


class ComparisonClassification(str, Enum):
    """Behavioral outcome classification between baseline and candidate."""
    NO_REGRESSION = "NO_REGRESSION"
    EXPECTED_CHANGE = "EXPECTED_CHANGE"
    REGRESSION = "REGRESSION"
    IMPROVEMENT = "IMPROVEMENT"
    NEW_BEHAVIOR = "NEW_BEHAVIOR"
    UNRELATED_CHANGE = "UNRELATED_CHANGE"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class FindingSeverity(str, Enum):
    """Severity rating for detected regressions."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


# ============================================================================
# 1. ChangeSet & Metadata
# ============================================================================

class ChangeSet(BaseModel):
    """
    Canonical representation of a proposed or detected change.
    Preserves exact identity (base SHA and candidate SHA) for Git-backed changes.
    """
    change_set_id: str = Field(default_factory=lambda: f"cs_{uuid.uuid4().hex[:10]}")
    change_source: ChangeSource = ChangeSource.GIT
    change_types: List[ChangeType] = Field(default_factory=list)
    repository: Optional[str] = None
    base_commit: str = ""
    candidate_commit: str = ""
    changed_files: List[str] = Field(default_factory=list)
    changed_symbols: List[str] = Field(default_factory=list, description="Class, function, or symbol names")
    changed_components: List[str] = Field(default_factory=list)
    changed_workflows: List[str] = Field(default_factory=list)
    changed_contracts: List[str] = Field(default_factory=list)
    changed_prompts: List[str] = Field(default_factory=list)
    changed_models: List[str] = Field(default_factory=list)
    changed_retrieval: List[str] = Field(default_factory=list)
    changed_tools: List[str] = Field(default_factory=list)
    changed_configuration: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: Dict[str, Any] = Field(default_factory=dict)

    def is_multi_variable(self) -> bool:
        """Determines if multiple architectural variables changed simultaneously."""
        independent_vars = 0
        if any(t in self.change_types for t in [ChangeType.CODE, ChangeType.PARSER, ChangeType.UI]):
            independent_vars += 1
        if ChangeType.PROMPT in self.change_types or bool(self.changed_prompts):
            independent_vars += 1
        if any(t in self.change_types for t in [ChangeType.MODEL, ChangeType.MODEL_CONFIGURATION]) or bool(self.changed_models):
            independent_vars += 1
        if ChangeType.RETRIEVAL in self.change_types or bool(self.changed_retrieval):
            independent_vars += 1
        if ChangeType.TOOL in self.change_types or bool(self.changed_tools):
            independent_vars += 1
        return independent_vars > 1


# ============================================================================
# 2. Component & Workflow Impact Models
# ============================================================================

class ImpactRelationship(BaseModel):
    """Directed edge in the Change Impact Graph."""
    source_id: str
    target_id: str
    relationship_type: ImpactRelationshipType
    description: str = ""
    confidence_factors: List[str] = Field(default_factory=list)


class AffectedComponent(BaseModel):
    """Application component identified as impacted by the ChangeSet."""
    component_id: str
    name: str
    component_type: ComponentType = ComponentType.UNKNOWN
    impact_level: ImpactLevel = ImpactLevel.MEDIUM
    relationship: ImpactRelationshipType = ImpactRelationshipType.DIRECT
    reason: str = ""
    evidence_ids: List[str] = Field(default_factory=list)
    memory_ids: List[str] = Field(default_factory=list)
    confidence_factors: List[str] = Field(
        default_factory=list,
        description="Deterministic factors: directly changed, imports changed module, workflow depends, etc."
    )


class AffectedWorkflow(BaseModel):
    """Workflow identified as impacted by the ChangeSet."""
    workflow_id: str
    name: str
    impact_level: ImpactLevel = ImpactLevel.MEDIUM
    reason: str = ""
    historical_failures: List[str] = Field(default_factory=list)
    reliability_history: Dict[str, Any] = Field(default_factory=dict)
    associated_contracts: List[str] = Field(default_factory=list)


class ChangeImpact(BaseModel):
    """Complete impact analysis artifact linking ChangeSet to components, workflows, and contracts."""
    change_set_id: str
    impact_relationships: List[ImpactRelationship] = Field(default_factory=list)
    affected_components: List[AffectedComponent] = Field(default_factory=list)
    affected_workflows: List[AffectedWorkflow] = Field(default_factory=list)
    affected_contracts: List[str] = Field(default_factory=list)
    ai_behavior_affected: bool = False
    unknown_impact: bool = False
    summary: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================================
# 3. Adaptive Regression Plan Models
# ============================================================================

class RegressionPlanItem(BaseModel):
    """Individual test item selected in the regression plan."""
    item_id: str = Field(default_factory=lambda: f"item_{uuid.uuid4().hex[:8]}")
    workflow_id: str
    name: str
    test_case_id: Optional[str] = None
    scope: RegressionScope
    reasons: List[str] = Field(
        default_factory=list,
        description="Structured deterministic reasons for inclusion (no opaque AI decisions)"
    )
    target_component_ids: List[str] = Field(default_factory=list)
    relevant_memory_ids: List[str] = Field(default_factory=list)
    relevant_contracts: List[str] = Field(default_factory=list)
    priority: float = Field(default=0.5, ge=0.0, le=1.0)


class RegressionScopeExpansion(BaseModel):
    """Record of dynamic mid-execution scope expansion triggered by runtime evidence."""
    expansion_id: str = Field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:8]}")
    plan_id: str
    trigger: str
    evidence_ids: List[str] = Field(default_factory=list)
    previous_scope: Dict[str, int] = Field(default_factory=dict)
    new_scope: Dict[str, int] = Field(default_factory=dict)
    added_items: List[RegressionPlanItem] = Field(default_factory=list)
    reason: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdaptiveRegressionPlan(BaseModel):
    """Root plan directing change-aware regression testing."""
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:10]}")
    change_set_id: str
    target_id: str
    application_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    base_commit: str = ""
    candidate_commit: str = ""
    scope_summary: Dict[str, int] = Field(default_factory=lambda: {"DEEP": 0, "TARGETED": 0, "SMOKE": 0})
    plan_status: PlanStatus = PlanStatus.PLANNED
    reasoning_summary: str = ""
    impact_summary: str = ""
    memory_summary: str = ""
    reliability_summary: str = ""
    items: List[RegressionPlanItem] = Field(default_factory=list)
    expansions: List[RegressionScopeExpansion] = Field(default_factory=list)
    budget: Dict[str, Any] = Field(default_factory=dict)
    stale: bool = False


# ============================================================================
# 4. Behavioral Comparison & Regression Findings
# ============================================================================

class BehavioralComparison(BaseModel):
    """
    Evidence-grounded comparison between baseline and candidate run executions.
    Strictly forbids reusing baseline evidence as candidate evidence.
    """
    comparison_id: str = Field(default_factory=lambda: f"comp_{uuid.uuid4().hex[:10]}")
    plan_id: str
    change_set_id: str
    baseline_run_id: str
    candidate_run_id: str
    classification: ComparisonClassification
    is_multi_variable_change: bool = False
    can_attribute_cause: bool = True
    attribution_note: str = ""
    contract_violations: List[str] = Field(default_factory=list)
    broken_assertions: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    summary: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RegressionFinding(BaseModel):
    """Specific regression finding requiring human governance evaluation."""
    finding_id: str = Field(default_factory=lambda: f"find_{uuid.uuid4().hex[:10]}")
    plan_id: str
    comparison_id: str
    severity: FindingSeverity
    title: str
    description: str
    affected_workflows: List[str] = Field(default_factory=list)
    affected_contracts: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    recommended_action: str = ""
    requires_human_governance: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChangeCoverageSummary(BaseModel):
    """Summary of planned vs executed vs expanded regression coverage."""
    plan_id: str
    change_set_id: str
    total_planned: int = 0
    deep_count: int = 0
    targeted_count: int = 0
    smoke_count: int = 0
    expanded_count: int = 0
    passed_items: int = 0
    failed_items: int = 0
    findings_count: int = 0
    overall_classification: ComparisonClassification = ComparisonClassification.UNKNOWN
