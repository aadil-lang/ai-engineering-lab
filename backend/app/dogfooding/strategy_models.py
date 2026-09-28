"""
Slice 8D.1 — Application-Adaptive Autonomous Testing Strategy Domain Models

Provides structured planning artifacts that enable the autonomous QA agent
to derive and dynamically adapt its testing strategy based on application context,
capabilities, workflows, behavioral contracts, historical reliability data,
and real-time runtime observations.

Core Principle:
- The strategy is a planning artifact, not authoritative evidence.
- Observed runtime behavior always takes precedence over declared assumptions.
- Application A -> Strategy A; Application B -> Strategy B; Application C -> Strategy C.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid


class ApplicationArchetype(str, Enum):
    """Identified application paradigm or domain structure."""
    AI_APPLICATION = "AI_APPLICATION"              # LLM generator, prompt lab, chat assistant, question generator
    DATA_DASHBOARD = "DATA_DASHBOARD"              # Metrics, charts, data grids, telemetry filters, analytics
    FORM_WORKFLOW = "FORM_WORKFLOW"                # Multi-step forms, registration wizards, questionnaires
    E_COMMERCE = "E_COMMERCE"                      # Product catalog, cart, checkout, inventory
    CONTENT_MANAGEMENT = "CONTENT_MANAGEMENT"      # Article/blog editors, media uploaders, document tools
    GENERIC_WEB = "GENERIC_WEB"                    # Default fallback for arbitrary web applications


class StrategyMode(str, Enum):
    """High-level testing posture or objective."""
    EXPLORATORY_DISCOVERY = "EXPLORATORY_DISCOVERY"          # Broad surface discovery and interaction mapping
    CONTRACT_VERIFICATION = "CONTRACT_VERIFICATION"          # Targeted verification of declared behavioral contracts
    CRITICAL_PATH_WALKTHROUGH = "CRITICAL_PATH_WALKTHROUGH"  # Primary user conversion/workflow walkthrough
    REGRESSION_PROBING = "REGRESSION_PROBING"                # Deep probe on historically flaky or failing features
    ADAPTIVE_STRESS = "ADAPTIVE_STRESS"                      # Boundary value testing and rapid state transitions


class WorkflowPriorityStatus(str, Enum):
    """Current execution status of an individual prioritized workflow."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"
    ABANDONED = "ABANDONED"


class PrioritizedWorkflow(BaseModel):
    """A prioritized workflow slice or user journey targeted during testing."""
    workflow_id: str = Field(default_factory=lambda: f"wf_{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    archetype_affinity: ApplicationArchetype = ApplicationArchetype.GENERIC_WEB
    priority: float = Field(default=0.5, ge=0.0, le=1.0, description="Higher value = executed earlier")
    target_selectors: List[str] = Field(default_factory=list, description="Relevant CSS selectors or keyword hints")
    expected_state_change: str = ""
    associated_contract_ids: List[str] = Field(default_factory=list, description="Bound Slice 8C behavioral contracts")
    status: WorkflowPriorityStatus = WorkflowPriorityStatus.PENDING
    attempts: int = 0
    verification_notes: Optional[str] = None


class ExplorationPolicy(BaseModel):
    """Fine-grained exploration heuristics guiding agent action choices."""
    depth_first_bias: float = Field(default=0.5, ge=0.0, le=1.0)
    input_variety_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    error_tolerance: int = Field(default=2, ge=1, le=5, description="Max consecutive errors before branch adaptation")
    assertion_density: str = Field(default="BALANCED", description="LIGHT | BALANCED | INTENSIVE")
    prefer_semantic_elements: bool = True
    defensive_wait_ms: int = 500


class StrategyAdaptationTrigger(str, Enum):
    """Runtime events that trigger dynamic strategy updates."""
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"                  # Page error, 500 status, or action exception
    WORKFLOW_BLOCKED = "WORKFLOW_BLOCKED"                  # Precondition not met (disabled button, missing input)
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"              # Observed state directly violated a declared contract
    EARLY_COMPLETION = "EARLY_COMPLETION"                  # Active workflow verified ahead of step budget
    BUDGET_PRESSURE = "BUDGET_PRESSURE"                    # Remaining step budget low (< 25%), must prune/wrap up
    NEW_CAPABILITY_DISCOVERED = "NEW_CAPABILITY_DISCOVERED"# Unanticipated interactive surface or modal exposed


class StrategyAdaptationEvent(BaseModel):
    """Record of a mid-execution strategy mutation."""
    adaptation_id: str = Field(default_factory=lambda: f"adapt_{uuid.uuid4().hex[:8]}")
    step_number: int
    trigger: StrategyAdaptationTrigger
    adaptation_type: str  # REPRIORITIZE | BRANCH_RECOVERY | SKIP_BLOCKED | PRUNE_BUDGET | ELEVATE_DISCOVERY
    reason: str
    previous_active_workflow: Optional[str] = None
    new_active_workflow: Optional[str] = None
    changes: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TestingStrategy(BaseModel):
    """
    Root planning artifact constructed for a dogfooding session.
    
    Contains initial prioritized workflows, active workflow pointer, risk areas,
    exploration policies, and a complete history of dynamic adaptations.
    """
    strategy_id: str = Field(default_factory=lambda: f"strat_{uuid.uuid4().hex[:8]}")
    run_id: str
    target_id: str
    application_id: Optional[str] = None
    application_archetype: ApplicationArchetype = ApplicationArchetype.GENERIC_WEB
    strategy_mode: StrategyMode = StrategyMode.EXPLORATORY_DISCOVERY
    goal: str = ""

    # Slice 8C context references
    declared_context_hash: Optional[str] = None
    behavioral_contract_ids: List[str] = Field(default_factory=list)

    # Prioritized target workflows
    prioritized_workflows: List[PrioritizedWorkflow] = Field(default_factory=list)
    active_workflow_id: Optional[str] = None

    # Heuristics & Historical context
    exploration_policy: ExplorationPolicy = Field(default_factory=ExplorationPolicy)
    risk_areas: List[str] = Field(default_factory=list)
    historical_failure_count: int = 0

    # Slice 8E Engineering Memory references
    retrieved_memory_count: int = 0
    retrieved_memory_summaries: List[str] = Field(default_factory=list)

    # Adaptation audit trail
    adaptation_history: List[StrategyAdaptationEvent] = Field(default_factory=list)

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def get_active_workflow(self) -> Optional[PrioritizedWorkflow]:
        """Returns the currently active workflow if defined."""
        if not self.active_workflow_id:
            return None
        for wf in self.prioritized_workflows:
            if wf.workflow_id == self.active_workflow_id:
                return wf
        return None

    def get_next_pending_workflow(self) -> Optional[PrioritizedWorkflow]:
        """Finds the highest priority pending workflow."""
        pending = [wf for wf in self.prioritized_workflows if wf.status == WorkflowPriorityStatus.PENDING]
        if not pending:
            return None
        return max(pending, key=lambda w: w.priority)

    def advance_to_next_workflow(self, reason: str = "Advancing to next pending workflow") -> Optional[PrioritizedWorkflow]:
        """Marks current workflow finished and sets active workflow to highest pending."""
        current = self.get_active_workflow()
        if current and current.status == WorkflowPriorityStatus.IN_PROGRESS:
            current.status = WorkflowPriorityStatus.VERIFIED
        
        next_wf = self.get_next_pending_workflow()
        if next_wf:
            next_wf.status = WorkflowPriorityStatus.IN_PROGRESS
            self.active_workflow_id = next_wf.workflow_id
        else:
            self.active_workflow_id = None
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return next_wf

    def to_summary_dict(self) -> Dict[str, Any]:
        """Summary dictionary without private CoT, suitable for live streaming and API."""
        active = self.get_active_workflow()
        return {
            "strategy_id": self.strategy_id,
            "run_id": self.run_id,
            "target_id": self.target_id,
            "application_archetype": self.application_archetype.value,
            "strategy_mode": self.strategy_mode.value,
            "goal": self.goal,
            "behavioral_contract_count": len(self.behavioral_contract_ids),
            "total_workflows": len(self.prioritized_workflows),
            "active_workflow": {
                "workflow_id": active.workflow_id,
                "name": active.name,
                "status": active.status.value,
                "priority": active.priority,
            } if active else None,
            "risk_areas": self.risk_areas,
            "adaptations_count": len(self.adaptation_history),
            "updated_at": self.updated_at,
        }
