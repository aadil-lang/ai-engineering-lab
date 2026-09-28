import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from backend.app.prompt_lab.models import (
    FailureCause,
    EpistemicType,
    DiagnosticFact,
    PromptDiagnosis,
    PromptImprovementCandidate,
    CandidateStatus,
    EvaluationCase,
    EvaluatorResult,
    EvaluationStrategy,
    EvaluationStatus,
    AIExecutionRecord,
)
from backend.app.prompt_lab.application_context_models import (
    EvaluationContext,
    ContextAwarePromptCandidate,
)


class PromptDiagnosisService:
    """
    Diagnoses AI evaluation failures across multi-causal layers:
    PROMPT_DEFECT, MODEL_BEHAVIOR, RETRIEVAL_FAILURE, CONTEXT_FAILURE,
    TOOL_FAILURE, APPLICATION_LOGIC, PARSER_FAILURE, SCHEMA_FAILURE,
    DATA_FAILURE, EVALUATOR_FAILURE, UNKNOWN.

    Distinguishes OBSERVED, INFERRED, and HYPOTHESIS epistemic facts.
    Ensures prompt defects are not assumed without investigating other layers.
    """

    def diagnose_failure(
        self,
        evaluation_run_id: str,
        case: EvaluationCase,
        evaluator_results: List[EvaluatorResult],
        execution: Optional[AIExecutionRecord] = None,
        context: Optional[EvaluationContext] = None,
    ) -> PromptDiagnosis:
        facts: List[DiagnosticFact] = []
        observed_facts: List[str] = []
        inferred_facts: List[str] = []
        hypotheses: List[str] = []

        primary_cause = FailureCause.UNKNOWN
        confidence = 0.5

        # 0. Check data inputs first
        if not case.input:
            primary_cause = FailureCause.DATA_FAILURE
            observed_facts.append("Case input payload is empty or missing.")
            inferred_facts.append("Missing input data prevented valid prompt completion.")
            hypotheses.append("Ensure evaluation case inputs provide all required variables.")
            confidence = 0.95

        # 1. Inspect failed evaluators
        failed_evaluators = [r for r in evaluator_results if r.status in {EvaluationStatus.FAIL, EvaluationStatus.PARTIAL}]

        if not failed_evaluators and primary_cause == FailureCause.UNKNOWN:
            # Check for unknown / abstained
            if any(r.status == EvaluationStatus.UNKNOWN for r in evaluator_results):
                primary_cause = FailureCause.UNKNOWN
                observed_facts.append("Evaluator returned UNKNOWN due to missing ground truth or unresolvable facts.")
                inferred_facts.append("Evaluation evidence is insufficient to determine correctness.")
                hypotheses.append("Additional reference sources or clearer evaluation criteria may resolve uncertainty.")
                confidence = 0.5
            elif any(r.status == EvaluationStatus.ABSTAINED for r in evaluator_results):
                primary_cause = FailureCause.EVALUATOR_FAILURE
                observed_facts.append("Evaluator explicitly abstained from scoring.")
                inferred_facts.append("Case may fall outside evaluator operational domain.")
                hypotheses.append("Evaluator threshold or domain configuration may need adjustment.")
                confidence = 0.6
        elif primary_cause == FailureCause.UNKNOWN:
            for ev in failed_evaluators:
                # Schema failure
                if ev.strategy == EvaluationStrategy.JSON_SCHEMA:
                    observed_facts.append(f"JSON schema validation failed: {ev.rationale}")
                    if "not valid json" in ev.rationale.lower() or "expecting value" in ev.rationale.lower():
                        primary_cause = FailureCause.PARSER_FAILURE
                        inferred_facts.append("Model output could not be parsed as valid JSON.")
                        hypotheses.append("Prompt instructions may need explicit formatting constraints (e.g. ```json fences or zero commentary).")
                        confidence = 0.9
                    elif "missing required" in ev.rationale.lower():
                        primary_cause = FailureCause.PROMPT_DEFECT
                        inferred_facts.append("Output omitted required schema attributes.")
                        hypotheses.append("Prompt template may not emphasize required field definitions with sufficient clarity.")
                        confidence = 0.85
                    else:
                        primary_cause = FailureCause.SCHEMA_FAILURE
                        inferred_facts.append("Output types diverged from declared schema.")
                        hypotheses.append("Prompt examples or schema specifications may be ambiguous.")
                        confidence = 0.8

                # Rule failure
                elif ev.strategy == EvaluationStrategy.RULE_BASED:
                    observed_facts.append(f"Rule constraint violation: {ev.rationale}")
                    if "forbidden phrase" in ev.rationale.lower():
                        primary_cause = FailureCause.MODEL_BEHAVIOR
                        inferred_facts.append("Model generated phrases explicitly forbidden by evaluation constraints.")
                        hypotheses.append("Negative constraints in prompt may need reinforcement or few-shot negative examples.")
                        confidence = 0.85
                    elif "length" in ev.rationale.lower():
                        primary_cause = FailureCause.PROMPT_DEFECT
                        inferred_facts.append("Model output length exceeded configured boundary.")
                        hypotheses.append("Prompt should state concise character or token limits.")
                        confidence = 0.8
                    else:
                        primary_cause = FailureCause.PROMPT_DEFECT
                        inferred_facts.append("Explicit constraint rule was not satisfied.")
                        hypotheses.append("Prompt instruction structure could be clarified.")
                        confidence = 0.75

                # Grounding failure
                elif ev.strategy == EvaluationStrategy.GROUNDING:
                    observed_facts.append(f"Grounding failure: {ev.rationale}")
                    if not case.sources:
                        primary_cause = FailureCause.RETRIEVAL_FAILURE
                        observed_facts.append("No source context chunks were supplied to support factual claims.")
                        inferred_facts.append("Retrieval step returned zero documents or query did not match knowledge base.")
                        hypotheses.append("Retrieval configuration or index coverage should be investigated before modifying prompt.")
                        confidence = 0.95
                    else:
                        primary_cause = FailureCause.MODEL_BEHAVIOR
                        observed_facts.append(f"Retrieved {len(case.sources)} source documents, but output made unsupported claims.")
                        inferred_facts.append("The retrieval path was operational; the model hallucinated or ignored retrieved context.")
                        hypotheses.append("Prompt lacks strict grounding constraints (e.g. 'Rely only on provided sources').")
                        confidence = 0.85

                # Code / SQL execution failure
                elif ev.strategy in {EvaluationStrategy.CODE_EXECUTION, EvaluationStrategy.SQL_EXECUTION}:
                    observed_facts.append(f"Execution boundary failure: {ev.rationale}")
                    if "security violation" in ev.rationale.lower():
                        primary_cause = FailureCause.MODEL_BEHAVIOR
                        inferred_facts.append("Model attempted to call disallowed functions or imports outside the sandbox.")
                        hypotheses.append("Prompt needs explicit tool/library boundary rules.")
                        confidence = 0.95
                    else:
                        primary_cause = FailureCause.APPLICATION_LOGIC
                        inferred_facts.append("Generated code or query encountered syntax or runtime exceptions.")
                        hypotheses.append("Prompt should instruct defensive syntax checking or code templates.")
                        confidence = 0.8

                # Semantic judge failure
                elif ev.strategy in {EvaluationStrategy.SEMANTIC_JUDGE, EvaluationStrategy.LLM_AS_JUDGE}:
                    observed_facts.append(f"Semantic judge divergence: {ev.rationale}")
                    inferred_facts.append("Output diverged from expected behavior or domain task requirements.")
                    hypotheses.append("Prompt objective and examples may be misaligned with expected behavior.")
                    if primary_cause == FailureCause.UNKNOWN:
                        primary_cause = FailureCause.PROMPT_DEFECT
                        confidence = 0.75

        # 2. Check Execution Context for Tool or Application Failures
        if execution and execution.tool_usage:
            for t in execution.tool_usage:
                if t.get("error"):
                    observed_facts.append(f"Tool invocation '{t.get('tool_name')}' returned error: {t.get('error')}")
                    primary_cause = FailureCause.TOOL_FAILURE
                    inferred_facts.append("A downstream tool execution error caused or contributed to output failure.")
                    hypotheses.append("Tool service availability or tool schema mismatch should be investigated.")
                    confidence = 0.9

        # 3. Context-aware checks if context provided
        if context:
            if context.retrieval_configuration and not case.sources:
                observed_facts.append("Application context declares retrieval_configuration, but execution received empty sources.")
                if primary_cause != FailureCause.TOOL_FAILURE:
                    primary_cause = FailureCause.RETRIEVAL_FAILURE
                    inferred_facts.append("The retrieval component failed to supply required context.")
                    hypotheses.append("Check retrieval index and query pipeline before attributing failure to prompt.")
                    confidence = 0.9

        # Build structured facts
        for obs in observed_facts:
            facts.append(DiagnosticFact(epistemic_type=EpistemicType.OBSERVED, statement=obs))
        for inf in inferred_facts:
            facts.append(DiagnosticFact(epistemic_type=EpistemicType.INFERRED, statement=inf))
        for hyp in hypotheses:
            facts.append(DiagnosticFact(epistemic_type=EpistemicType.HYPOTHESIS, statement=hyp))

        diag_id = f"diag_{uuid.uuid4().hex[:12]}"
        return PromptDiagnosis(
            diagnosis_id=diag_id,
            evaluation_run_id=evaluation_run_id,
            case_id=case.case_id,
            primary_cause=primary_cause,
            confidence=round(confidence, 2),
            facts=facts,
            observed_summary="; ".join(observed_facts) if observed_facts else "No active failures observed.",
            inferred_summary="; ".join(inferred_facts) if inferred_facts else "Output satisfies operational bounds.",
            hypothesis_summary="; ".join(hypotheses) if hypotheses else "No corrective hypothesis required.",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def formulate_improvement_candidate(
        self,
        source_prompt_version: int,
        diagnoses: List[PromptDiagnosis],
        current_template: str,
    ) -> PromptImprovementCandidate:
        """
        Formulates a candidate prompt improvement based on diagnosed failures.
        Never modifies the active prompt.
        """
        candidate_id = f"cand_{uuid.uuid4().hex[:12]}"
        diagnosis_ids = [d.diagnosis_id for d in diagnoses]

        # Synthesize rationale and propose targeted modifications
        hypotheses = [d.hypothesis_summary for d in diagnoses if d.hypothesis_summary]
        primary_causes = {d.primary_cause for d in diagnoses}

        rationale_lines = [
            f"Candidate generated from {len(diagnoses)} evaluation failure diagnoses.",
            f"Primary identified causes: {', '.join(c.value for c in primary_causes)}.",
        ]
        if hypotheses:
            rationale_lines.append("Key hypotheses: " + "; ".join(hypotheses[:3]))

        proposed_template = current_template
        # Add reinforcement based on diagnoses
        additions = []
        if FailureCause.SCHEMA_FAILURE in primary_causes or FailureCause.PARSER_FAILURE in primary_causes:
            additions.append("\n\n### Formatting Constraint\nYou must respond ONLY with a valid JSON object matching the required schema. Do not include markdown preamble or commentary.")
        if FailureCause.MODEL_BEHAVIOR in primary_causes:
            additions.append("\n\n### Operational Rules\nAdhere strictly to all specified constraints and forbidden phrases. Do not exceed requested length boundaries.")
        if FailureCause.RETRIEVAL_FAILURE in primary_causes or any("grounding" in d.observed_summary.lower() for d in diagnoses):
            additions.append("\n\n### Grounding Rule\nBase all factual statements solely on the provided context sources. If a fact cannot be confirmed from the sources, state that information is unavailable.")

        if additions:
            proposed_template += "".join(additions)

        return PromptImprovementCandidate(
            candidate_id=candidate_id,
            source_prompt_version=source_prompt_version,
            proposed_template=proposed_template,
            rationale="\n".join(rationale_lines),
            evidence_ids=[],
            diagnosis_ids=diagnosis_ids,
            status=CandidateStatus.PROPOSED,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def formulate_context_aware_improvement_candidate(
        self,
        context: EvaluationContext,
        evaluation_run_id: str,
        diagnoses: List[PromptDiagnosis],
        current_template: str,
        affected_contracts: Optional[List[str]] = None,
    ) -> ContextAwarePromptCandidate:
        """
        Formulates a context-aware prompt improvement candidate explicitly bound to the
        application context from which it was derived.
        """
        candidate_id = f"cand_ctx_{uuid.uuid4().hex[:12]}"
        diagnosis_ids = [d.diagnosis_id for d in diagnoses]
        hypotheses = [d.hypothesis_summary for d in diagnoses if d.hypothesis_summary]
        primary_causes = {d.primary_cause for d in diagnoses}

        rationale_lines = [
            f"Context-aware candidate for application '{context.application_id}' (feature: '{context.feature_id}').",
            f"Derived from evaluation run '{evaluation_run_id}' under context '{context.context_id}'.",
            f"Source Git commit: {context.git_commit_sha or 'uncommitted'}, prompt v{context.prompt_version}.",
            f"Primary identified causes: {', '.join(c.value for c in primary_causes)}.",
        ]
        if hypotheses:
            rationale_lines.append("Key hypotheses: " + "; ".join(hypotheses[:3]))

        proposed_template = current_template
        additions = []
        if FailureCause.SCHEMA_FAILURE in primary_causes or FailureCause.PARSER_FAILURE in primary_causes:
            additions.append("\n\n### Formatting Constraint\nYou must respond ONLY with a valid JSON object matching the required schema. Do not include markdown preamble or commentary.")
        if FailureCause.MODEL_BEHAVIOR in primary_causes:
            additions.append("\n\n### Operational Rules\nAdhere strictly to all specified constraints and forbidden phrases. Do not exceed requested length boundaries.")
        if FailureCause.RETRIEVAL_FAILURE in primary_causes or any("grounding" in d.observed_summary.lower() for d in diagnoses):
            additions.append("\n\n### Grounding Rule\nBase all factual statements solely on the provided context sources. If a fact cannot be confirmed from the sources, state that information is unavailable.")

        if additions:
            proposed_template += "".join(additions)

        contracts = affected_contracts if affected_contracts is not None else list(context.behavioral_contract_ids)

        return ContextAwarePromptCandidate(
            candidate_id=candidate_id,
            application_id=context.application_id,
            feature_id=context.feature_id,
            source_context_id=context.context_id,
            source_git_commit_sha=context.git_commit_sha,
            source_prompt_version=context.prompt_version,
            source_evaluation_id=evaluation_run_id,
            affected_behavioral_contract_ids=contracts,
            proposed_change=proposed_template,
            rationale="\n".join(rationale_lines),
            evidence_ids=[],
            diagnosis_ids=diagnosis_ids,
            status=CandidateStatus.PROPOSED,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

