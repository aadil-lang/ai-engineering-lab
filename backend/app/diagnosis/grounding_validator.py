import re
import logging
import uuid
from typing import Any

from backend.app.models.enums import ClaimType, GroundingStatus, FailureCategory
from backend.app.models.diagnosis import (
    EngineeringDiagnosis,
    EvidenceBundle,
    DeterministicSignal,
    DiagnosisClaim,
    GroundingSummary,
)

logger = logging.getLogger("ai_qa_platform.diagnosis_grounding_validator")

class DiagnosisGroundingValidator:
    """
    Independent validator that verifies whether AI-generated diagnosis claims
    are supported by, unsupported by, or contradicted by deterministic evidence.
    
    Ensures that downstream systems (such as the CodingAgent) consume grounded engineering
    facts rather than unverified LLM hallucinations.
    """

    def validate(
        self,
        raw_diagnosis: EngineeringDiagnosis,
        bundle: EvidenceBundle,
    ) -> EngineeringDiagnosis:
        """
        Validates raw diagnosis claims against the deterministic EvidenceBundle.
        Returns a validated EngineeringDiagnosis with populated claims, grounding score,
        and evidence-grounded root cause / component fields.
        """
        claims = self._extract_claims(raw_diagnosis, bundle)
        validated_claims: list[DiagnosisClaim] = []
        validation_notes: list[str] = []

        supported_count = 0
        partially_supported_count = 0
        unsupported_count = 0
        contradicted_count = 0

        for claim in claims:
            status, refs, explanation = self._evaluate_claim(claim, bundle)
            claim.grounding_status = status
            claim.evidence_refs = refs
            claim.explanation = explanation
            validated_claims.append(claim)

            if status == GroundingStatus.SUPPORTED:
                supported_count += 1
            elif status == GroundingStatus.PARTIALLY_SUPPORTED:
                partially_supported_count += 1
            elif status == GroundingStatus.UNSUPPORTED:
                unsupported_count += 1
                validation_notes.append(f"Unsupported claim [{claim.claim_type.value}]: '{claim.text[:80]}' - no corroborating telemetry found.")
            elif status == GroundingStatus.CONTRADICTED:
                contradicted_count += 1
                validation_notes.append(f"Contradiction detected [{claim.claim_type.value}]: '{claim.text[:80]}' conflicts with deterministic evidence. ({explanation})")

        total = len(validated_claims)
        if total > 0:
            raw_score = (supported_count * 1.0 + partially_supported_count * 0.7) / total
            penalty = contradicted_count * 0.5
            grounding_score = max(0.0, min(1.0, round(raw_score - penalty, 2)))
        else:
            grounding_score = 1.0

        # Grounded if no contradictions and root cause is supported
        rc_supported = any(c.claim_type == ClaimType.ROOT_CAUSE and c.grounding_status == GroundingStatus.SUPPORTED for c in validated_claims)
        is_grounded = contradicted_count == 0 and (grounding_score >= 0.6 or rc_supported)

        # Derive grounded root cause and suspected component
        grounded_root_cause, grounded_component = self._derive_grounded_fields(
            raw_diagnosis, bundle, validated_claims, contradicted_count > 0
        )

        grounded_confidence = round(raw_diagnosis.confidence_score * max(0.2, grounding_score), 2)

        # Clone and enrich diagnosis with validation results
        validated_diagnosis = raw_diagnosis.model_copy(
            update={
                "claims": validated_claims,
                "grounding_score": grounding_score,
                "is_grounded": is_grounded,
                "grounded_root_cause": grounded_root_cause,
                "grounded_suspected_component": grounded_component,
                "grounded_confidence_score": grounded_confidence,
                "validation_notes": validation_notes,
            }
        )

        return validated_diagnosis

    def _extract_claims(
        self,
        raw_diagnosis: EngineeringDiagnosis,
        bundle: EvidenceBundle,
    ) -> list[DiagnosisClaim]:
        """Decomposes the raw diagnosis into discrete verifiable claims."""
        if raw_diagnosis.claims:
            return raw_diagnosis.claims

        claims: list[DiagnosisClaim] = []

        # 1. Observed Facts from title & signals
        claims.append(
            DiagnosisClaim(
                text=raw_diagnosis.title,
                claim_type=ClaimType.OBSERVED_FACT,
                confidence=1.0,
            )
        )

        # 2. Root Cause Hypothesis
        claims.append(
            DiagnosisClaim(
                text=raw_diagnosis.root_cause_summary,
                claim_type=ClaimType.ROOT_CAUSE,
                confidence=raw_diagnosis.confidence_score,
            )
        )

        # 3. Suspected Component
        claims.append(
            DiagnosisClaim(
                text=raw_diagnosis.suspected_component,
                claim_type=ClaimType.COMPONENT,
                confidence=raw_diagnosis.confidence_score,
            )
        )

        # 4. Recommendation / Suggested Fix
        claims.append(
            DiagnosisClaim(
                text=raw_diagnosis.suggested_fix,
                claim_type=ClaimType.RECOMMENDATION,
                confidence=0.9,
            )
        )

        return claims

    def _evaluate_claim(
        self,
        claim: DiagnosisClaim,
        bundle: EvidenceBundle,
    ) -> tuple[GroundingStatus, list[str], str]:
        """
        Evaluates a single claim against deterministic telemetry signals and facts in the EvidenceBundle.
        """
        claim_text_lower = claim.text.lower()
        
        # Check for explicit contradictions first
        is_contradicted, contradiction_reason = self._check_contradiction(claim, bundle)
        if is_contradicted:
            return GroundingStatus.CONTRADICTED, [], contradiction_reason

        # Gather matching evidence references
        matching_refs: list[str] = []

        # 1. Check deterministic signals
        for idx, sig in enumerate(bundle.deterministic_signals):
            ref_id = f"signal:{sig.signal_type}:{idx}"
            summary_lower = sig.summary.lower()
            
            # Check for strong keyword / token overlaps
            if self._has_evidence_match(claim.text, sig.summary, sig.details):
                matching_refs.append(ref_id)

        # 2. Check failed network calls
        for idx, net in enumerate(bundle.failed_network_calls):
            url = net.get("url", "")
            status = str(net.get("status", ""))
            if status in claim_text_lower or (url and any(part in claim_text_lower for part in url.split("/") if len(part) > 3)):
                matching_refs.append(f"network:http_{status}_{idx}")

        # 3. Check browser console errors
        for idx, ce in enumerate(bundle.console_errors):
            if any(word in claim_text_lower for word in ce.lower().split() if len(word) > 4):
                matching_refs.append(f"console:error_{idx}")

        # 4. Check error message & target context
        if bundle.error_message:
            if self._has_evidence_match(claim.text, bundle.error_message, {}):
                matching_refs.append("error_message:primary")

        # 5. Check target ID or action history for component matches
        if claim.claim_type == ClaimType.COMPONENT:
            if bundle.target_id.lower() in claim_text_lower or claim_text_lower in bundle.target_id.lower():
                matching_refs.append(f"target:{bundle.target_id}")
            elif any(self._has_evidence_match(claim.text, act.get("description", ""), {}) for act in bundle.action_history):
                matching_refs.append("action_history:step")

        # Determine status based on matched evidence
        if len(matching_refs) >= 1:
            status = GroundingStatus.SUPPORTED
            explanation = f"Directly corroborated by {len(matching_refs)} deterministic evidence reference(s)."
        else:
            if claim.claim_type == ClaimType.RECOMMENDATION:
                status = GroundingStatus.PARTIALLY_SUPPORTED
                explanation = "Actionable engineering suggestion derived from failure context."
            else:
                status = GroundingStatus.UNSUPPORTED
                explanation = "No matching deterministic telemetry signals, network errors, or console logs substantiate this claim."

        return status, matching_refs, explanation

    def _check_contradiction(
        self,
        claim: DiagnosisClaim,
        bundle: EvidenceBundle,
    ) -> tuple[bool, str]:
        """
        Detects factual contradictions between a claim and the known execution environment / evidence.
        """
        text = claim.text.lower()

        # Case 1: Backend Unit Test / In-Process failure vs Frontend / Network / API mismatch hallucination
        is_unit_test = (
            (bundle.test_mode == "FUNCTIONAL_QA" or "test_" in (bundle.natural_language_goal or "").lower() or (bundle.error_message and ".py" in bundle.error_message))
            and len(bundle.failed_network_calls) == 0
            and len(bundle.console_errors) == 0
            and not bundle.dom_error_snippet
        )

        frontend_keywords = ["frontend", "ui component", "network request", "api mismatch", "client-side", "browser request", "http request failed", "rest endpoint mismatch"]
        if is_unit_test:
            for kw in frontend_keywords:
                if kw in text and claim.claim_type in (ClaimType.ROOT_CAUSE, ClaimType.COMPONENT):
                    return True, f"Claim asserts '{kw}', but the execution was an isolated backend test with zero HTTP/network requests and no browser interaction."

        # Case 2: Claim asserts HTTP 500 / Network Error when no network errors were recorded
        if ("http 500" in text or "network failure" in text or "endpoint returned 500" in text or "500 internal server error" in text) and len(bundle.failed_network_calls) == 0:
            has_http_signal = any(s.signal_type == "HTTP_ERROR" for s in bundle.deterministic_signals)
            if not has_http_signal:
                return True, "Claim asserts an HTTP 500/network error, but all network telemetry indicates no failed HTTP requests were recorded."

        # Case 3: Claim asserts missing DOM element when test had no DOM context or all DOM checks passed
        if ("dom element" in text or "selector not found" in text or "element locator" in text) and not any(s.signal_type == "DOM_MISSING" for s in bundle.deterministic_signals) and is_unit_test:
            return True, "Claim asserts a DOM locator failure, but the test execution has no DOM context."

        # Case 4: Assertion mismatch contradiction (e.g. expected vs observed inverted)
        for sig in bundle.deterministic_signals:
            if sig.signal_type == "ASSERTION_ERROR":
                err = sig.details.get("error", "")
                if "expected" in err.lower() and "observed" in err.lower():
                    # If claim says test passed or observed the expected value
                    if "test succeeded" in text or "expected behavior occurred" in text:
                        return True, "Claim asserts test succeeded, directly contradicting the failed assertion signal."

        return False, ""

    def _tokenize(self, text: str) -> set[str]:
        """Tokenize text into lowercased alphanumeric words, camelCase splits, and snake_case subwords."""
        # Find all words
        raw_words = set(re.findall(r'[a-zA-Z_0-9.]{3,}', text))
        words = set()
        for w in raw_words:
            words.add(w.lower())
            # Split camelCase
            camel_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+', w)
            for cp in camel_parts:
                if len(cp) >= 3:
                    words.add(cp.lower())
            # Split on underscores and dots
            sub = re.split(r'[_.\s]+', w)
            for s in sub:
                if len(s) >= 3:
                    words.add(s.lower())
        return words

    def _has_evidence_match(self, claim_text: str, evidence_text: str, details: dict) -> bool:
        """Helper to test for meaningful semantic/keyword overlap between claim and evidence."""
        claim_words = self._tokenize(claim_text)
        evidence_words = self._tokenize(evidence_text)
        
        # Include detail values
        for k, v in details.items():
            if isinstance(v, str):
                evidence_words.update(self._tokenize(v.lower()))

        # Check significant matches (e.g., status enums, class names, function names, error terms)
        common = claim_words.intersection(evidence_words)
        stop_words = {"the", "and", "for", "that", "this", "with", "from", "test", "during", "execution", "failed", "failure", "error"}
        significant_common = common - stop_words

        if len(significant_common) >= 1:
            return True

        # Check substring containment for words >= 4 chars
        for cw in claim_words - stop_words:
            if len(cw) >= 4 and any(cw in ew for ew in evidence_words):
                return True

        return False

    def _derive_grounded_fields(
        self,
        raw_diagnosis: EngineeringDiagnosis,
        bundle: EvidenceBundle,
        validated_claims: list[DiagnosisClaim],
        has_contradictions: bool,
    ) -> tuple[str, str]:
        """
        Derives an accurate, evidence-grounded root cause and suspected component,
        replacing hallucinated or contradicted statements with deterministic facts.
        """
        # Find root cause claim
        rc_claim = next((c for c in validated_claims if c.claim_type == ClaimType.ROOT_CAUSE), None)
        comp_claim = next((c for c in validated_claims if c.claim_type == ClaimType.COMPONENT), None)

        grounded_rc = raw_diagnosis.root_cause_summary
        grounded_comp = raw_diagnosis.suspected_component

        # If root cause is contradicted or unsupported, synthesize from deterministic signals
        if rc_claim and rc_claim.grounding_status in (GroundingStatus.CONTRADICTED, GroundingStatus.UNSUPPORTED):
            assertion_sig = next((s for s in bundle.deterministic_signals if s.signal_type == "ASSERTION_ERROR"), None)
            http_sig = next((s for s in bundle.deterministic_signals if s.signal_type == "HTTP_ERROR"), None)
            dom_sig = next((s for s in bundle.deterministic_signals if s.signal_type == "DOM_MISSING"), None)
            console_sig = next((s for s in bundle.deterministic_signals if s.signal_type == "CONSOLE_ERROR"), None)

            if assertion_sig:
                grounded_rc = f"Deterministic Assertion Failure: {assertion_sig.summary}. Deterministic evidence confirms direct value mismatch."
            elif http_sig:
                grounded_rc = f"Deterministic Server HTTP Error: {http_sig.summary}."
            elif dom_sig:
                grounded_rc = f"Deterministic DOM Missing Element: {dom_sig.summary}."
            elif console_sig:
                grounded_rc = f"Deterministic Uncaught Runtime Exception: {console_sig.summary}."
            elif bundle.error_message:
                grounded_rc = f"Execution Failure: {bundle.error_message[:150]}"

        # If suspected component is contradicted or unsupported, ground component from error / target
        if comp_claim and comp_claim.grounding_status in (GroundingStatus.CONTRADICTED, GroundingStatus.UNSUPPORTED):
            if bundle.error_message and "/" in bundle.error_message:
                # Extract filepath if present (e.g. backend/app/analysis/planner.py)
                matches = re.findall(r'[\w/\\]+\.py', bundle.error_message)
                if matches:
                    grounded_comp = f"Backend Module ({matches[0]})"
                else:
                    grounded_comp = f"Target Application ({bundle.target_id})"
            elif any(s.signal_type == "ASSERTION_ERROR" for s in bundle.deterministic_signals):
                grounded_comp = f"Core Business Logic ({bundle.target_id})"
            else:
                grounded_comp = bundle.target_id

        return grounded_rc, grounded_comp
