"""
Registers the VM Copy Question Generator app as an application target
in the AI Reliability Platform database.
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import init_db
from backend.app.models.enums import TargetType, TestMode
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_case import TestCase
from backend.app.repositories.sqlite_repository import SQLiteRepository

def register_question_generator():
    init_db()
    repo = SQLiteRepository()
    now_iso = datetime.now(timezone.utc).isoformat()

    target = ApplicationTarget(
        target_id="real_question_generator_local",
        application_id="app_question_generator",
        application_type="ai_eval_agent",
        name="VM Copy Question Generator",
        target_type=TargetType.WEB_APPLICATION,
        base_url="http://127.0.0.1:3000/",
        environment="local_production_dogfooding",
        version="0.1.0",
        description="Next.js 16 AI-driven adaptive mathematical question generator and curriculum assessment application.",
        created_at=now_iso,
        updated_at=now_iso,
    )
    repo.create_target(target)

    # Test Case 1: Base Question Generation & Form Validation
    tc_base = TestCase(
        test_case_id="tc_qgen_base_generate_flow",
        target_id="real_question_generator_local",
        name="Base Question Generation Form & Parameter Validation",
        test_mode=TestMode.FUNCTIONAL_QA,
        description="Inspects base-generate form inputs, standard dropdowns, model selection, and question set rendering.",
        steps=[
            {"step": "NAVIGATE", "url": "/base-generate"},
            {"step": "LOCATE", "selector": "select[name='gradeLevel'], #stateStandards"},
            {"step": "INPUT", "field": "subSkill", "value": "Multiplication with Regrouping"},
            {"step": "CLICK", "selector": "button[type='submit']"},
            {"step": "ASSERT", "check": "Question cards or validation feedback mounted"}
        ],
        assertions=[
            {"type": "DOM_EXISTS", "check": "Navigation header exists"},
            {"type": "INPUT_VALID", "check": "Model selector supports Agnes and GPT models"}
        ],
        created_at=now_iso,
    )

    # Test Case 2: Copy Question Generator & Deterministic Evaluation
    tc_copy = TestCase(
        test_case_id="tc_qgen_copy_eval_flow",
        target_id="real_question_generator_local",
        name="Copy Question Generator & Math Evaluation Verification",
        test_mode=TestMode.AI_LLM_EVALUATION,
        description="Evaluates copy question generation, 4-option constraint, exactly one Correct Answer (CA) exclusivity.",
        steps=[
            {"step": "NAVIGATE", "url": "/copy-generate"},
            {"step": "LOCATE", "selector": "textarea[name='baseQuestion']"},
            {"step": "INPUT", "field": "baseQuestion", "value": "What is 15 * 12?"},
            {"step": "CLICK", "selector": "button.generate-btn"},
            {"step": "ASSERT", "check": "Generated copies exhibit exactly one CA option"}
        ],
        assertions=[
            {"type": "CA_EXCLUSIVITY", "check": "Exactly 1 option with CA tag"},
            {"type": "OPTION_COUNT", "check": "Matches expected count"}
        ],
        created_at=now_iso,
    )

    repo.create_test_case(tc_base)
    repo.create_test_case(tc_copy)

    print(f"Registered target: {target.target_id} ({target.name})")
    print(f" - Test case 1: {tc_base.test_case_id} ({tc_base.name})")
    print(f" - Test case 2: {tc_copy.test_case_id} ({tc_copy.name})")

if __name__ == "__main__":
    register_question_generator()
