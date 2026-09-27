from backend.app.models.test_case import TestCase, TestCaseCreate
from backend.app.models.enums import TestMode
from backend.app.repositories.base import TestCaseRepositoryInterface
from backend.app.core.exceptions import NotFoundException
import uuid

class TestCaseService:
    def __init__(self, test_case_repo: TestCaseRepositoryInterface):
        self.test_case_repo = test_case_repo

    def create_test_case(self, payload: TestCaseCreate) -> TestCase:
        tc = TestCase(
            test_case_id=f"tc_{uuid.uuid4().hex[:8]}",
            target_id=payload.target_id,
            name=payload.name,
            test_mode=payload.test_mode,
            description=payload.description,
            steps=payload.steps,
            assertions=payload.assertions,
            tags=payload.tags,
        )
        return self.test_case_repo.create_test_case(tc)

    def get_test_case(self, test_case_id: str) -> TestCase:
        tc = self.test_case_repo.get_test_case(test_case_id)
        if not tc:
            raise NotFoundException(f"Test case with ID '{test_case_id}' not found")
        return tc

    def list_test_cases(self, target_id: str | None = None, test_mode: str | None = None) -> list[TestCase]:
        cases = self.test_case_repo.list_test_cases(target_id=target_id, test_mode=test_mode)
        if not cases:
            # Seed default test cases across all 5 modes
            defaults = [
                TestCase(
                    test_case_id="tc_func_checkout",
                    target_id="tgt_demo_shop",
                    name="End-to-End Checkout & Promo Redemption",
                    test_mode=TestMode.FUNCTIONAL_QA,
                    description="Autonomous verification of cart calculation, discount application, and payment authorization.",
                    steps=[
                        {"action": "NAVIGATE", "url": "/checkout"},
                        {"action": "LOCATE", "selector": "#checkout-form input[name='promo_code']"},
                        {"action": "INPUT", "selector": "#checkout-form input[name='promo_code']", "value": "RELIABILITY_PASS_2026"},
                        {"action": "CLICK", "selector": "#btn-submit-order"},
                        {"action": "SUBMIT", "expected": "ORDER_CONFIRMATION"},
                    ],
                    assertions=[{"field": "status", "expected": 200}, {"field": "order_id", "regex": "^ORD-[0-9]{5}-[A-Z]$"}],
                    tags=["checkout", "p0", "functional"],
                ),
                TestCase(
                    test_case_id="tc_exploratory_dogfood",
                    target_id="tgt_demo_shop",
                    name="Autonomous Exploratory User Journey",
                    test_mode=TestMode.EXPLORATORY_DOGFOODING,
                    description="Randomized user navigation path detecting unexpected 404s, broken hyperlinks, and unhandled client exceptions.",
                    steps=[
                        {"action": "NAVIGATE", "url": "/"},
                        {"action": "LOCATE", "selector": "nav.categories a"},
                        {"action": "CLICK", "selector": "nav.categories a:nth-child(2)"},
                        {"action": "INPUT", "selector": "input#search-catalog", "value": "wireless noise cancelling headphones"},
                        {"action": "SUBMIT", "expected": "SEARCH_RESULTS_LOADED"},
                    ],
                    tags=["dogfooding", "unbounded", "resilience"],
                ),
                TestCase(
                    test_case_id="tc_ux_ui_accessibility",
                    target_id="tgt_demo_shop",
                    name="WCAG 2.1 AA & Responsive UX Audit",
                    test_mode=TestMode.UX_UI_REVIEW,
                    description="Audits color contrast, touch target sizes, ARIA labels, and viewport layout stability.",
                    steps=[
                        {"action": "NAVIGATE", "url": "/product/detail/401"},
                        {"action": "LOCATE", "selector": ".product-actions"},
                        {"action": "CLICK", "selector": "#btn-view-specifications"},
                        {"action": "INPUT", "selector": "#review-filter", "value": "verified"},
                        {"action": "SUBMIT", "expected": "UX_METRICS_LOGGED"},
                    ],
                    tags=["accessibility", "wcag", "ui_ux"],
                ),
                TestCase(
                    test_case_id="tc_llm_hallucination_guard",
                    target_id="tgt_demo_shop",
                    name="AI Copilot Grounding & Hallucination Guardrail",
                    test_mode=TestMode.AI_LLM_EVALUATION,
                    description="Tests shopping assistant agent responses against real inventory database to detect hallucinations and toxic outputs.",
                    steps=[
                        {"action": "NAVIGATE", "url": "/assistant"},
                        {"action": "LOCATE", "selector": "textarea#copilot-prompt"},
                        {"action": "INPUT", "selector": "textarea#copilot-prompt", "value": "Is the Sony WH-1000XM5 in stock with overnight shipping?"},
                        {"action": "CLICK", "selector": "#btn-send-prompt"},
                        {"action": "SUBMIT", "expected": "GROUNDED_CITATION_VERIFIED"},
                    ],
                    tags=["ai_eval", "hallucination", "rag_validation"],
                ),
                TestCase(
                    test_case_id="tc_regression_core_flows",
                    target_id="tgt_demo_shop",
                    name="Core Tier-1 Regression Verification Suite",
                    test_mode=TestMode.REGRESSION_QA,
                    description="Validates that recent code patches have not degraded existing checkout or authentication contracts.",
                    steps=[
                        {"action": "NAVIGATE", "url": "/auth/session"},
                        {"action": "LOCATE", "selector": "#session-status"},
                        {"action": "INPUT", "selector": "#token-auth-input", "value": "test_jwt_session_2026"},
                        {"action": "CLICK", "selector": "#btn-verify-session"},
                        {"action": "SUBMIT", "expected": "SESSION_AUTHENTICATED"},
                    ],
                    tags=["regression", "tier1", "ci_cd"],
                ),
            ]
            for d in defaults:
                self.test_case_repo.create_test_case(d)
            return defaults
        return cases
