import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.control_plane.context import ToolInvocationContext
from backend.app.models.prompt_lab_tools import (
    ListPromptsRequest,
    GetPromptRequest,
    CreatePromptVersionRequest,
    GetPromptVersionRequest,
    ListEvaluationSuitesRequest,
    GetEvaluationSuiteRequest,
    StartEvaluationRequest,
    GetEvaluationRequest,
    ComparePromptVersionsRequest,
    GetPromptRegressionsRequest,
)
from backend.app.prompt_lab.models import EvaluationCase, EvaluationCategory, SeverityLevel, EvaluationStrategy


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def control_plane():
    cp = ReliabilityControlPlane(
        db_path=":memory:",
        enable_lifecycle_tools=True,
        enable_github_tools=True,
        enable_prompt_lab_tools=True,
    )
    return cp


def test_control_plane_prompt_lab_tools(control_plane):
    """Test ToolRegistry invocation of Prompt Lab tools."""
    ctx = ToolInvocationContext(
        invocation_id="inv_test_prompt_lab",
        agent_id="agent_prompt_evaluator",
        session_id="sess_001",
    )

    # 1. Create prompt and version via prompt_service
    control_plane.prompt_service.create_prompt("prompt_calc", "Math Calculator", "Solves math questions")
    res_pv = control_plane.registry.invoke(
        "create_prompt_version",
        CreatePromptVersionRequest(
            prompt_id="prompt_calc",
            template="Calculate: {{expr}}",
            variables_schema={"required": ["expr"]},
        ),
        ctx,
    )
    assert res_pv.success is True
    assert res_pv.data.version.version == 1

    # 2. list_prompts tool
    res_list = control_plane.registry.invoke("list_prompts", ListPromptsRequest(limit=10), ctx)
    assert res_list.success is True
    assert any(p.prompt_id == "prompt_calc" for p in res_list.data.prompts)

    # 3. get_prompt tool
    res_get = control_plane.registry.invoke("get_prompt", GetPromptRequest(prompt_id="prompt_calc"), ctx)
    assert res_get.success is True
    assert res_get.data.prompt.prompt_id == "prompt_calc"

    # 4. Create evaluation suite
    control_plane.evaluation_service.create_suite("suite_calc", "Calc Suite")
    control_plane.evaluation_service.create_suite_version(
        "suite_calc",
        cases=[
            EvaluationCase(
                case_id="case_add",
                category=EvaluationCategory.NORMAL,
                severity=SeverityLevel.LOW,
                input={"expr": "2 + 2"},
                expected_behavior="Return 4",
                expected_output="Response addressing: Return 4.",
                evaluation_strategy=EvaluationStrategy.EXACT_MATCH,
            )
        ]
    )

    # 5. start_evaluation tool
    res_eval = control_plane.registry.invoke(
        "start_evaluation",
        StartEvaluationRequest(
            prompt_id="prompt_calc",
            prompt_version=1,
            suite_id="suite_calc",
            suite_version=1,
            model="mock-agent-v1",
        ),
        ctx,
    )
    assert res_eval.success is True
    assert res_eval.data.run.total_cases == 1
    assert res_eval.data.run.pass_rate == 1.0

    run_id = res_eval.data.run.evaluation_run_id

    # 6. get_evaluation tool
    res_get_eval = control_plane.registry.invoke("get_evaluation", GetEvaluationRequest(evaluation_run_id=run_id), ctx)
    assert res_get_eval.success is True
    assert res_get_eval.data.run.evaluation_run_id == run_id


def test_prompt_lab_rest_api(client):
    """Test REST API routes for Prompt Lab."""
    import uuid
    uid = uuid.uuid4().hex[:6]
    prompt_id = f"prompt_api_{uid}"
    suite_id = f"suite_api_{uid}"

    # 1. Create prompt
    r_create = client.post("/api/v1/prompt-lab/prompts", json={
        "prompt_id": prompt_id,
        "name": "API Test Prompt",
        "description": "Created via REST API",
    })
    assert r_create.status_code == 201
    assert r_create.json()["prompt_id"] == prompt_id

    # 2. List prompts
    r_list = client.get("/api/v1/prompt-lab/prompts")
    assert r_list.status_code == 200
    assert any(p["prompt_id"] == prompt_id for p in r_list.json())

    # 3. Create version
    r_ver = client.post(f"/api/v1/prompt-lab/prompts/{prompt_id}/versions", json={
        "template": "Analyze: {{text}}",
        "variables_schema": {"required": ["text"]},
    })
    assert r_ver.status_code == 201
    assert r_ver.json()["version"] == 1

    # 4. Create suite
    r_suite = client.post("/api/v1/prompt-lab/evaluation-suites", json={
        "suite_id": suite_id,
        "name": "API Suite",
        "description": "Test suite via API",
    })
    assert r_suite.status_code == 201

    # 5. Create suite version
    r_sv = client.post(f"/api/v1/prompt-lab/evaluation-suites/{suite_id}/versions", json={
        "cases": [
            {
                "case_id": "case_1",
                "input": {"text": "hello"},
                "expected_behavior": "respond with hello",
                "evaluation_strategy": "COMPOSITE",
                "severity": "LOW",
                "category": "NORMAL",
            }
        ],
        "description": "initial suite version",
    })
    assert r_sv.status_code == 201
    assert r_sv.json()["version"] == 1

    # 6. Run evaluation
    r_run = client.post("/api/v1/prompt-lab/evaluations/run", json={
        "prompt_id": prompt_id,
        "prompt_version": 1,
        "suite_id": suite_id,
        "suite_version": 1,
        "model": "mock-agent-v1",
    })
    assert r_run.status_code == 200
    data = r_run.json()
    assert data["total_cases"] == 1
    run_id = data["evaluation_run_id"]

    # 7. Get evaluation
    r_get_eval = client.get(f"/api/v1/prompt-lab/evaluations/{run_id}")
    assert r_get_eval.status_code == 200
    assert r_get_eval.json()["run"]["evaluation_run_id"] == run_id
