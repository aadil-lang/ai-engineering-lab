"""
Slice 8K — Change Analysis & Impact Graph Engine

Performs deterministic classification of changes (Git diffs, prompts, models,
tools, configs, dependencies, etc.) and constructs an explicit Change Impact Graph
incorporating components, workflows, behavioral contracts, 8E historical memory,
and reliability signals.
"""

from __future__ import annotations
import os
import re
from typing import Optional, Any, Dict, List, Set
from datetime import datetime, timezone
import uuid

from backend.app.change_impact.models import (
    ChangeType,
    ChangeSource,
    ImpactRelationshipType,
    ComponentType,
    ImpactLevel,
    ChangeSet,
    ImpactRelationship,
    AffectedComponent,
    AffectedWorkflow,
    ChangeImpact,
)
from backend.app.memory.models import MemoryType, MemoryStatus


class ChangeAnalysisEngine:
    """
    Analyzes proposed or committed changes to determine:
    1. Exact classification of changes across code, prompt, model, retrieval, tool, parser, UI, contracts, etc.
    2. Explicit directed component impact graph with deterministic confidence factors.
    3. Workflow impact mapping integrated with behavioral contracts and 8E Engineering Memory.
    """

    def __init__(self, memory_repository=None, app_context_service=None):
        self.memory_repo = memory_repository
        self.app_context_service = app_context_service

    def classify_change(
        self,
        changed_files: Optional[List[str]] = None,
        prompts_changed: Optional[List[str]] = None,
        models_changed: Optional[List[str]] = None,
        retrieval_changed: Optional[List[str]] = None,
        tools_changed: Optional[List[str]] = None,
        config_changed: Optional[Dict[str, Any]] = None,
        diff_text: Optional[str] = None,
    ) -> List[ChangeType]:
        """
        Deterministically classifies changes into explicit types.
        A single change can yield multiple types (never reduced to just CODE).
        """
        types: Set[ChangeType] = set()
        changed_files = changed_files or []

        # 1. Direct explicit inputs
        if prompts_changed:
            types.add(ChangeType.PROMPT)
        if models_changed:
            types.add(ChangeType.MODEL)
            if any("temp" in m.lower() or "param" in m.lower() or "config" in m.lower() for m in models_changed):
                types.add(ChangeType.MODEL_CONFIGURATION)
        if retrieval_changed:
            types.add(ChangeType.RETRIEVAL)
        if tools_changed:
            types.add(ChangeType.TOOL)
        if config_changed:
            types.add(ChangeType.CONFIGURATION)
            if any("model" in k.lower() or "temperature" in k.lower() for k in config_changed):
                types.add(ChangeType.MODEL_CONFIGURATION)
            if any("retriev" in k.lower() or "embed" in k.lower() for k in config_changed):
                types.add(ChangeType.RETRIEVAL)

        # 2. File-based classification
        for f in changed_files:
            lower_f = f.lower().replace("\\", "/")
            
            # Documentation
            if lower_f.endswith((".md", ".txt", ".rst")) and not any(p in lower_f for p in ["prompt", "contract"]):
                types.add(ChangeType.DOCUMENTATION)
                continue

            # Prompts
            if "prompt" in lower_f or lower_f.endswith((".prompt", ".jinja", ".jinja2")):
                types.add(ChangeType.PROMPT)

            # Parsers
            if "parser" in lower_f or "extractor" in lower_f or "parse_" in lower_f:
                types.add(ChangeType.PARSER)

            # Behavioral Contracts
            if "contract" in lower_f:
                types.add(ChangeType.BEHAVIORAL_CONTRACT)

            # API Contracts / Endpoints
            if "/api/" in lower_f or "routes" in lower_f or "endpoint" in lower_f or "openapi" in lower_f:
                types.add(ChangeType.API_CONTRACT)

            # UI / Frontend
            if (
                lower_f.endswith((".css", ".scss", ".sass", ".less"))
                or "/components/" in lower_f
                or "/frontend/" in lower_f
                or lower_f.endswith((".tsx", ".jsx", ".vue", ".svelte", ".html"))
            ):
                types.add(ChangeType.UI)

            # Dependencies
            if any(lower_f.endswith(dep) for dep in [
                "requirements.txt", "pyproject.toml", "package.json", "package-lock.json", "poetry.lock", "setup.py"
            ]):
                types.add(ChangeType.DEPENDENCY)

            # Database Schema
            if "migration" in lower_f or "schema" in lower_f or lower_f.endswith((".sql",)):
                types.add(ChangeType.DATABASE_SCHEMA)

            # Deployment / CI
            if (
                "docker" in lower_f
                or ".github/workflows" in lower_f
                or lower_f.endswith((".k8s.yaml", ".k8s.yml"))
            ):
                types.add(ChangeType.DEPLOYMENT)

            # Configuration
            if lower_f.endswith((".env", ".ini", ".yaml", ".yml", ".toml", "config.py", "settings.py")):
                types.add(ChangeType.CONFIGURATION)

            # General Code
            if lower_f.endswith((".py", ".ts", ".js", ".go", ".rs", ".java", ".c", ".cpp")):
                types.add(ChangeType.CODE)

        # 3. Diff inspection for fine-grained changes
        if diff_text:
            lower_diff = diff_text.lower()
            if "def parse_" in lower_diff or "class " in lower_diff and "parser" in lower_diff:
                types.add(ChangeType.PARSER)
            if "temperature" in lower_diff or "top_p" in lower_diff or "max_tokens" in lower_diff:
                types.add(ChangeType.MODEL_CONFIGURATION)
            if "embedding" in lower_diff or "vector" in lower_diff or "rag" in lower_diff:
                types.add(ChangeType.RETRIEVAL)
            if "def test_" in lower_diff:
                types.add(ChangeType.CODE)

        if not types:
            types.add(ChangeType.UNKNOWN)

        return sorted(list(types), key=lambda x: x.value)

    def extract_changed_symbols(self, diff_text: Optional[str] = None) -> List[str]:
        """Extracts function, class, or method symbol names touched in a git diff."""
        if not diff_text:
            return []
        symbols = set()
        # Python definitions
        py_matches = re.findall(r"^[+-]\s*(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)", diff_text, re.MULTILINE)
        py_classes = re.findall(r"^[+-]\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)", diff_text, re.MULTILINE)
        # JS/TS functions & classes
        ts_matches = re.findall(r"^[+-]\s*(?:export\s+)?(?:function|const)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=", diff_text, re.MULTILINE)
        ts_classes = re.findall(r"^[+-]\s*(?:export\s+)?class\s+([a-zA-Z_][a-zA-Z0-9_]*)", diff_text, re.MULTILINE)

        for s in py_matches + py_classes + ts_matches + ts_classes:
            if not s.startswith("__"):
                symbols.add(s)
        return sorted(list(symbols))

    def analyze_impact(
        self,
        change_set: ChangeSet,
        application_id: Optional[str] = None,
        app_context: Optional[Any] = None,
    ) -> ChangeImpact:
        """
        Builds the complete ChangeImpact artifact:
        - Maps changed files/symbols to affected components
        - Traverses dependencies and downstream consumers
        - Identifies affected workflows and behavioral contracts
        - Correlates with 8E Engineering Memory for historical failure patterns
        """
        relationships: List[ImpactRelationship] = []
        affected_components_map: Dict[str, AffectedComponent] = {}
        affected_workflows_map: Dict[str, AffectedWorkflow] = {}
        affected_contracts: Set[str] = set(change_set.changed_contracts)
        ai_behavior_affected = False
        unknown_impact = False

        app_id = application_id or change_set.repository or "default_app"

        # Check for unknown / unclassifiable changes
        if not change_set.changed_files and not change_set.changed_prompts and not change_set.changed_models and not change_set.changed_configuration:
            return ChangeImpact(
                change_set_id=change_set.change_set_id,
                unknown_impact=True,
                summary="Empty or unidentifiable change set provided; impact unknown."
            )

        # Check documentation-only changes
        if change_set.change_types == [ChangeType.DOCUMENTATION]:
            return ChangeImpact(
                change_set_id=change_set.change_set_id,
                unknown_impact=False,
                summary="Documentation-only change detected; no application behavioral impact."
            )

        # 1. Process Prompts
        if ChangeType.PROMPT in change_set.change_types or change_set.changed_prompts:
            ai_behavior_affected = True
            comp_id = "comp_ai_prompt"
            affected_components_map[comp_id] = AffectedComponent(
                component_id=comp_id,
                name="AI Prompt Specification",
                component_type=ComponentType.AI_PROMPT,
                impact_level=ImpactLevel.HIGH,
                relationship=ImpactRelationshipType.DIRECT,
                reason="Prompt template or version changed",
                confidence_factors=["directly changed", "ai_behavior_source", "governs LLM generation output"]
            )
            # Downstream: AI generation component & output parser
            parser_comp_id = "comp_output_parser"
            affected_components_map[parser_comp_id] = AffectedComponent(
                component_id=parser_comp_id,
                name="Output Parser & Schema Extractor",
                component_type=ComponentType.PARSER,
                impact_level=ImpactLevel.HIGH,
                relationship=ImpactRelationshipType.DOWNSTREAM,
                reason="Consumes AI model generation guided by changed prompt",
                confidence_factors=["consumes AI output", "downstream parser validation", "schema contract dependency"]
            )
            relationships.append(ImpactRelationship(
                source_id=comp_id,
                target_id=parser_comp_id,
                relationship_type=ImpactRelationshipType.DOWNSTREAM,
                description="Prompt changes affect structure and content consumed by output parser",
                confidence_factors=["ai_pipeline_flow"]
            ))

        # 2. Process Model / Model Configuration
        if any(t in change_set.change_types for t in [ChangeType.MODEL, ChangeType.MODEL_CONFIGURATION]) or change_set.changed_models:
            ai_behavior_affected = True
            comp_id = "comp_ai_model"
            affected_components_map[comp_id] = AffectedComponent(
                component_id=comp_id,
                name="AI Model Runtime & Parameters",
                component_type=ComponentType.AI_MODEL,
                impact_level=ImpactLevel.HIGH,
                relationship=ImpactRelationshipType.DIRECT,
                reason="Model architecture, checkpoint, or generation parameters modified",
                confidence_factors=["directly changed", "generation parameter delta", "non-deterministic output boundary"]
            )
            relationships.append(ImpactRelationship(
                source_id=comp_id,
                target_id="comp_output_parser",
                relationship_type=ImpactRelationshipType.AI_BEHAVIOR,
                description="Model changes affect generative reasoning and structured formatting",
                confidence_factors=["model_inference_variance"]
            ))

        # 3. Process Retrieval
        if ChangeType.RETRIEVAL in change_set.change_types or change_set.changed_retrieval:
            ai_behavior_affected = True
            comp_id = "comp_retrieval_rag"
            affected_components_map[comp_id] = AffectedComponent(
                component_id=comp_id,
                name="Retrieval & Vector Search Subsystem",
                component_type=ComponentType.RETRIEVAL,
                impact_level=ImpactLevel.HIGH,
                relationship=ImpactRelationshipType.DIRECT,
                reason="Vector index, embedding model, top-k, or chunking strategy changed",
                confidence_factors=["directly changed", "retrieval context formulation"]
            )

        # 4. Process Tools
        if ChangeType.TOOL in change_set.change_types or change_set.changed_tools:
            comp_id = "comp_tool_registry"
            affected_components_map[comp_id] = AffectedComponent(
                component_id=comp_id,
                name="Tool Execution & Dispatcher",
                component_type=ComponentType.TOOL,
                impact_level=ImpactLevel.HIGH,
                relationship=ImpactRelationshipType.DIRECT,
                reason="Tool definition, schema, or implementation changed",
                confidence_factors=["directly changed", "tool invocation contract"]
            )

        # 5. Process Parsers & Extractors
        if ChangeType.PARSER in change_set.change_types:
            comp_id = "comp_parser"
            affected_components_map[comp_id] = AffectedComponent(
                component_id=comp_id,
                name="Payload Parser",
                component_type=ComponentType.PARSER,
                impact_level=ImpactLevel.HIGH,
                relationship=ImpactRelationshipType.DIRECT,
                reason="Direct modification of parser logic, regex, or deserializer",
                confidence_factors=["directly changed", "data transformation critical path"]
            )
            # Downstream UI component
            ui_comp_id = "comp_ui_display"
            affected_components_map[ui_comp_id] = AffectedComponent(
                component_id=ui_comp_id,
                name="Question & Answer Result View",
                component_type=ComponentType.FRONTEND_UI,
                impact_level=ImpactLevel.MEDIUM,
                relationship=ImpactRelationshipType.DOWNSTREAM,
                reason="Consumes structured parsed payload to render interactive elements",
                confidence_factors=["downstream rendering", "DOM element generation"]
            )
            relationships.append(ImpactRelationship(
                source_id=comp_id,
                target_id=ui_comp_id,
                relationship_type=ImpactRelationshipType.DOWNSTREAM,
                description="Parser output feeds directly into result display UI",
                confidence_factors=["data_flow_dependency"]
            ))

        # 6. Process API Contracts
        if ChangeType.API_CONTRACT in change_set.change_types:
            comp_id = "comp_api_endpoint"
            affected_components_map[comp_id] = AffectedComponent(
                component_id=comp_id,
                name="HTTP REST Endpoint",
                component_type=ComponentType.API_ENDPOINT,
                impact_level=ImpactLevel.HIGH,
                relationship=ImpactRelationshipType.DIRECT,
                reason="API route, request/response schema, or status codes modified",
                confidence_factors=["directly changed", "network boundary contract"]
            )
            # Frontend consumer is dependent
            frontend_comp_id = "comp_frontend_client"
            affected_components_map[frontend_comp_id] = AffectedComponent(
                component_id=frontend_comp_id,
                name="Frontend API Client",
                component_type=ComponentType.FRONTEND_UI,
                impact_level=ImpactLevel.HIGH,
                relationship=ImpactRelationshipType.DEPENDENCY,
                reason="Consumes HTTP REST endpoint payload",
                confidence_factors=["imports changed endpoint", "client-server contract"]
            )
            relationships.append(ImpactRelationship(
                source_id=comp_id,
                target_id=frontend_comp_id,
                relationship_type=ImpactRelationshipType.DEPENDENCY,
                description="Frontend client depends on API endpoint contract",
                confidence_factors=["api_consumption"]
            ))

        # 7. Process UI
        if ChangeType.UI in change_set.change_types:
            comp_id = "comp_frontend_ui"
            if comp_id not in affected_components_map:
                affected_components_map[comp_id] = AffectedComponent(
                    component_id=comp_id,
                    name="Frontend Interface & Layout",
                    component_type=ComponentType.FRONTEND_UI,
                    impact_level=ImpactLevel.HIGH,
                    relationship=ImpactRelationshipType.DIRECT,
                    reason="Stylesheet, component markup, or interactive DOM handler modified",
                    confidence_factors=["directly changed", "visual presentation & event listeners"]
                )

        # 8. Process General Code files
        for f in change_set.changed_files:
            file_comp_id = f"comp_{os.path.basename(f).replace('.', '_')}"
            if file_comp_id not in affected_components_map:
                affected_components_map[file_comp_id] = AffectedComponent(
                    component_id=file_comp_id,
                    name=os.path.basename(f),
                    component_type=ComponentType.BACKEND if f.endswith(".py") else ComponentType.FRONTEND_UI,
                    impact_level=ImpactLevel.MEDIUM,
                    relationship=ImpactRelationshipType.DIRECT,
                    reason=f"Direct file edit in {f}",
                    confidence_factors=["directly changed"]
                )

        # 9. Map Components to Workflows
        # E.g. For question generator: question_generation, result_validation, answer_submission, app_navigation
        has_ai = ai_behavior_affected or any(c.component_type in [ComponentType.AI_PROMPT, ComponentType.AI_MODEL, ComponentType.PARSER] for c in affected_components_map.values())
        has_ui = any(c.component_type == ComponentType.FRONTEND_UI for c in affected_components_map.values())
        has_api = any(c.component_type == ComponentType.API_ENDPOINT for c in affected_components_map.values())

        if has_ai or any(ChangeType.PARSER in change_set.change_types for _ in [1]):
            wf_gen_id = "wf_question_generation"
            affected_workflows_map[wf_gen_id] = AffectedWorkflow(
                workflow_id=wf_gen_id,
                name="Question Generation Workflow",
                impact_level=ImpactLevel.HIGH,
                reason="Workflow depends on AI prompt, model inference, and output parser",
                associated_contracts=["contract_4_options_present", "contract_correct_answer_indicated"]
            )
            affected_contracts.add("contract_4_options_present")
            affected_contracts.add("contract_correct_answer_indicated")

            wf_val_id = "wf_result_validation"
            affected_workflows_map[wf_val_id] = AffectedWorkflow(
                workflow_id=wf_val_id,
                name="Result Validation Workflow",
                impact_level=ImpactLevel.MEDIUM,
                reason="Verifies generated options, distractor uniqueness, and correct indicator",
                associated_contracts=["contract_unique_distractors"]
            )
            affected_contracts.add("contract_unique_distractors")

        has_backend = any(c.component_type == ComponentType.BACKEND for c in affected_components_map.values())
        if has_backend and not has_ai:
            wf_backend_id = "wf_backend_service_execution"
            affected_workflows_map[wf_backend_id] = AffectedWorkflow(
                workflow_id=wf_backend_id,
                name="Backend Service & Logic Execution",
                impact_level=ImpactLevel.MEDIUM,
                reason="Direct logic modification in backend service",
                associated_contracts=[]
            )

        if has_ui:
            wf_render_id = "wf_result_rendering"
            affected_workflows_map[wf_render_id] = AffectedWorkflow(
                workflow_id=wf_render_id,
                name="Result Rendering & Interaction Workflow",
                impact_level=ImpactLevel.HIGH if change_set.change_types == [ChangeType.UI] else ImpactLevel.MEDIUM,
                reason="Renders options, radio buttons, and feedback states in DOM",
                associated_contracts=["contract_interactive_radio_group"]
            )
            affected_contracts.add("contract_interactive_radio_group")

        if has_api:
            wf_api_id = "wf_api_dispatch"
            affected_workflows_map[wf_api_id] = AffectedWorkflow(
                workflow_id=wf_api_id,
                name="API Dispatch & Response Handling",
                impact_level=ImpactLevel.HIGH,
                reason="Handles HTTP transport, status codes, and JSON serialization",
                associated_contracts=["contract_http_status_200", "contract_json_response"]
            )

        # Baseline Smoke Workflow (always relevant to broad application integrity)
        wf_smoke_id = "wf_app_navigation_smoke"
        affected_workflows_map[wf_smoke_id] = AffectedWorkflow(
            workflow_id=wf_smoke_id,
            name="Application Initialization & Navigation Smoke",
            impact_level=ImpactLevel.LOW,
            reason="Ensures root application loads, routes mount cleanly, and navigation is functional",
            associated_contracts=[]
        )

        # 10. Integrate 8E Historical Engineering Memory
        if self.memory_repo:
            try:
                # Query historical failures and reliability patterns
                memories = self.memory_repo.list_memories(application_id=app_id)
                for mem in memories:
                    if mem.status in [MemoryStatus.OBSERVED, MemoryStatus.HISTORICAL]:
                        # Correlate memory to affected components/workflows
                        if mem.memory_type in [MemoryType.FAILURE_HISTORY, MemoryType.REGRESSION_HISTORY]:
                            for wf_id, wf in affected_workflows_map.items():
                                if mem.workflow_id == wf_id or mem.component_id in affected_components_map:
                                    wf.historical_failures.append(mem.content)
                                    # Add historical relationship
                                    relationships.append(ImpactRelationship(
                                        source_id=mem.memory_id,
                                        target_id=wf_id,
                                        relationship_type=ImpactRelationshipType.HISTORICAL,
                                        description=f"Historical failure recorded in memory: {mem.content}",
                                        confidence_factors=["source_memory_evidence", "historical_precedent"]
                                    ))
                        elif mem.memory_type == MemoryType.RELIABILITY_PATTERN:
                            for wf_id, wf in affected_workflows_map.items():
                                if mem.workflow_id == wf_id:
                                    wf.reliability_history["pattern"] = mem.content
            except Exception as e:
                # Fallback gracefully per Failure Isolation principle
                pass

        summary_parts = []
        if change_set.is_multi_variable():
            summary_parts.append("MULTI_VARIABLE_CHANGE detected.")
        summary_parts.append(f"{len(affected_components_map)} components affected.")
        summary_parts.append(f"{len(affected_workflows_map)} workflows affected.")
        summary_parts.append(f"{len(affected_contracts)} behavioral contracts identified.")

        return ChangeImpact(
            change_set_id=change_set.change_set_id,
            impact_relationships=relationships,
            affected_components=list(affected_components_map.values()),
            affected_workflows=list(affected_workflows_map.values()),
            affected_contracts=sorted(list(affected_contracts)),
            ai_behavior_affected=ai_behavior_affected,
            unknown_impact=False,
            summary=" ".join(summary_parts)
        )
