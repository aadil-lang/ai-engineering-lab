"""
Registers the 3 distinct application targets and their 6 test cases
into SQLite database for Slice 6.8 multi-application real reliability campaigns.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from backend.app.core.database import init_db
from backend.app.models.enums import TargetType, TestMode
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_case import TestCase
from backend.app.repositories.sqlite_repository import SQLiteRepository

def register():
    init_db()
    repo = SQLiteRepository()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Target 1: Engineering Design Automation (EDA)
    target_eda = ApplicationTarget(
        target_id="real_eda_local",
        application_id="app_eda",
        application_type="engineering_workflow",
        name="Engineering Design Automation",
        target_type=TargetType.WEB_APPLICATION,
        base_url="http://127.0.0.1:8088/docs",
        environment="local_engineering_cluster",
        version="1.0.0",
        description="FastAPI-driven Engineering Design Automation and structural calculations platform.",
        created_at=now_iso,
        updated_at=now_iso,
    )
    repo.create_target(target_eda)

    tc_eda_1 = TestCase(
        test_case_id="tc_eda_health_smoke",
        target_id="real_eda_local",
        name="EDA Swagger UI Health & Smoke Probe",
        test_mode=TestMode.FUNCTIONAL_QA,
        description="Verifies Swagger UI documentation rendering and API schema availability.",
        steps=[{"step": "NAVIGATE"}, {"step": "LOCATE"}, {"step": "INPUT"}, {"step": "CLICK"}, {"step": "ASSERT"}],
        assertions=[{"type": "DOM_EXISTS", "check": "Swagger UI mounted"}, {"type": "PAGE_TITLE", "check": "Title matches Engineering Intelligence"}],
        created_at=now_iso,
    )
    tc_eda_2 = TestCase(
        test_case_id="tc_eda_calculation_workflow",
        target_id="real_eda_local",
        name="Engineering Structural Calculation Workflow",
        test_mode=TestMode.FUNCTIONAL_QA,
        description="Executes structural stress/strain calculation with material load limits.",
        steps=[{"step": "NAVIGATE"}, {"step": "LOCATE_SWAGGER"}, {"step": "INPUT_PARAMS"}, {"step": "EXECUTE_CALC"}, {"step": "ASSERT_SAFETY"}],
        assertions=[{"type": "STATUS_CHECK", "check": "Status is SAFE"}, {"type": "STRESS_CHECK", "check": "Stress matches 60.0 MPa"}],
        created_at=now_iso,
    )
    repo.create_test_case(tc_eda_1)
    repo.create_test_case(tc_eda_2)

    # Target 2: Inventory & Asset Management (CRUD Business)
    target_inv = ApplicationTarget(
        target_id="real_inventory_local",
        application_id="app_inventory",
        application_type="crud_business",
        name="Enterprise Inventory & Asset Management",
        target_type=TargetType.WEB_APPLICATION,
        base_url="http://127.0.0.1:8089/",
        environment="local_warehouse_cluster",
        version="1.0.0",
        description="CRUD and asset catalogue web application with client-side modals and validation.",
        created_at=now_iso,
        updated_at=now_iso,
    )
    repo.create_target(target_inv)

    tc_inv_1 = TestCase(
        test_case_id="tc_inventory_create_edit",
        target_id="real_inventory_local",
        name="Inventory Asset Create & Edit Lifecycle",
        test_mode=TestMode.FUNCTIONAL_QA,
        description="Opens modal, adds new SKU item, verifies in table, and edits stock quantity.",
        steps=[{"step": "NAVIGATE"}, {"step": "OPEN_MODAL"}, {"step": "INPUT_ITEM_FIELDS"}, {"step": "SAVE_ITEM"}, {"step": "EDIT_QUANTITY"}, {"step": "ASSERT_UPDATED"}],
        assertions=[{"type": "DOM_EXISTS", "check": "Row exists in DOM"}, {"type": "VALUE_CHECK", "check": "Updated quantity is 45"}],
        created_at=now_iso,
    )
    tc_inv_2 = TestCase(
        test_case_id="tc_inventory_validation_flow",
        target_id="real_inventory_local",
        name="Inventory Validation Guardrails & Search Filter",
        test_mode=TestMode.FUNCTIONAL_QA,
        description="Tests form validation rejection for empty fields and negative quantities, then verifies search.",
        steps=[{"step": "NAVIGATE"}, {"step": "TRIGGER_EMPTY_VALIDATION"}, {"step": "TRIGGER_NEGATIVE_QTY"}, {"step": "SUBMIT_CORRECT"}, {"step": "SEARCH_FILTER"}],
        assertions=[{"type": "ALERT_VISIBLE", "check": "Validation errors visible"}, {"type": "TOAST_VISIBLE", "check": "Notification toast appears"}, {"type": "FILTER_CHECK", "check": "Search filters correctly"}],
        created_at=now_iso,
    )
    repo.create_test_case(tc_inv_1)
    repo.create_test_case(tc_inv_2)

    # Target 3: QA Certification & Testing Dispatch Wizard (Stateful Workflow)
    target_book = ApplicationTarget(
        target_id="real_booking_local",
        application_id="app_booking",
        application_type="stateful_workflow",
        name="QA Certification & Testing Dispatch Wizard",
        target_type=TargetType.WEB_APPLICATION,
        base_url="http://127.0.0.1:8090/",
        environment="local_dispatch_cluster",
        version="1.0.0",
        description="Multi-step stateful wizard application for scheduling autonomous QA test certification flights.",
        created_at=now_iso,
        updated_at=now_iso,
    )
    repo.create_target(target_book)

    tc_book_1 = TestCase(
        test_case_id="tc_booking_complete_wizard",
        target_id="real_booking_local",
        name="Multi-Step QA Dispatch Booking Flow",
        test_mode=TestMode.FUNCTIONAL_QA,
        description="Walks through 4-step wizard: tier selection, scheduling details, add-on configuration, and submission.",
        steps=[{"step": "NAVIGATE"}, {"step": "SELECT_TIER"}, {"step": "SCHEDULE_DETAILS"}, {"step": "CONFIGURE_ADDONS"}, {"step": "ASSERT_CONFIRMATION"}],
        assertions=[{"type": "REF_CODE", "check": "Reference code starts with BK-"}, {"type": "CONFIRM_BADGE", "check": "Confirmation badge visible"}],
        created_at=now_iso,
    )
    tc_book_2 = TestCase(
        test_case_id="tc_booking_edge_validation_flow",
        target_id="real_booking_local",
        name="Booking Wizard Edge Validation & State Preservation",
        test_mode=TestMode.FUNCTIONAL_QA,
        description="Tests tier guardrails, invalid email formats, and step-back state persistence.",
        steps=[{"step": "NAVIGATE"}, {"step": "STEP1_GUARD"}, {"step": "SELECT_TIER"}, {"step": "EMAIL_GUARD"}, {"step": "CORRECT_EMAIL"}, {"step": "BACK_STEP_VERIFY"}, {"step": "SUBMIT"}],
        assertions=[{"type": "STEP1_ALERT", "check": "Step 1 error visible"}, {"type": "STEP2_ALERT", "check": "Step 2 error visible"}, {"type": "STATE_PERSIST", "check": "State preserved after step-back"}, {"type": "CODE_GEN", "check": "Confirmation code generated"}],
        created_at=now_iso,
    )
    repo.create_test_case(tc_book_1)
    repo.create_test_case(tc_book_2)

    print("Successfully registered 3 application targets and 6 test cases:")
    for t in repo.list_targets():
        if t.target_id in ("real_eda_local", "real_inventory_local", "real_booking_local"):
            print(f" - Target: {t.target_id} | App: {t.application_id} | Type: {t.application_type} | URL: {t.base_url}")
            for tc in repo.list_test_cases(target_id=t.target_id):
                print(f"    * Test Case: {tc.test_case_id} - {tc.name}")

if __name__ == "__main__":
    register()
