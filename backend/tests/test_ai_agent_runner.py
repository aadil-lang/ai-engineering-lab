import pytest
import os
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.app.models.enums import RunnerType, RunStatus, ActionStatus, TestMode, FailureCategory
from backend.app.models.test_run import TestRun, TestRunCreate
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_action import TestAction
from backend.app.agents.dom_extractor import DOMExtractor, DOMObservation, ExtractedElement
from backend.app.agents.ollama_agent import OllamaReasoner, AgentDecision
from backend.app.execution.ai_agent_runner import AIAgentTestRunner
from backend.app.execution.mock_runner import MockTestRunner
from backend.app.execution.playwright_runner import PlaywrightTestRunner
from backend.app.services.run_manager import RunManager
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.evidence.storage import LocalEvidenceBlobStorage

@pytest.fixture
def agent_test_env():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_agent.db")
    artifacts_dir = Path(temp_dir) / "artifacts"
    
    repo = SQLiteRepository(db_path=db_path)
    storage = LocalEvidenceBlobStorage(base_dir=artifacts_dir)
    
    html_file = Path(temp_dir) / "agent_target.html"
    html_file.write_text("""
    <!DOCTYPE html>
    <html>
    <head><title>Agent Target App</title></head>
    <body>
        <h1>Interactive Agent Target</h1>
        <input type="text" id="query-input" placeholder="Search..." />
        <button id="search-btn" onclick="document.getElementById('res').innerText = 'Search Completed!';">Search</button>
        <div id="res">Ready</div>
    </body>
    </html>
    """, encoding="utf-8")

    target = ApplicationTarget(
        target_id="tgt_agent_local",
        name="Local Agent Target",
        base_url=f"file:///{html_file.as_posix()}",
    )
    repo.create_target(target)

    yield repo, storage, target

def test_dom_observation_selector_lookup():
    obs = DOMObservation(
        url="http://localhost:3000",
        title="Test Page",
        elements=[
            ExtractedElement(index=1, tag="button", id="btn-login", selector="#btn-login", text="Log In"),
            ExtractedElement(index=2, tag="input", id="username", selector="#username", placeholder="Enter username"),
        ],
        text_summary="[1] <button id=\"btn-login\">Log In</button>\n[2] <input id=\"username\" />"
    )

    assert obs.get_selector(1) == "#btn-login"
    assert obs.get_selector(2) == "#username"
    assert obs.get_selector("button.custom") == "button.custom"

    with pytest.raises(ValueError):
        obs.get_selector(99)

def test_ollama_reasoner_parsing():
    reasoner = OllamaReasoner(base_url="http://localhost:11434")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "response": '{"thought": "Click the search button to test query", "action": "click", "element_index": 2}'
    }

    with patch("httpx.post", return_value=mock_resp):
        decision = reasoner.decide_next_action(
            goal="Test the search button",
            test_mode="FUNCTIONAL_QA",
            current_dom_summary="[1] <input id=\"query-input\" />\n[2] <button id=\"search-btn\">Search</button>",
            history_summary="",
            step_number=1,
            max_steps=5
        )
        assert decision.action == "click"
        assert decision.element_index == 2
        assert "search button" in decision.thought

def test_ai_agent_runner_with_mock_reasoner(agent_test_env):
    repo, storage, target = agent_test_env

    run = TestRun(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
        runner_type=RunnerType.AI_AGENT,
        natural_language_goal="Input text in search and finish",
        max_agent_steps=4
    )
    repo.create_run(run)

    class MockDeterministicReasoner:
        model = "mock-qwen"
        def __init__(self):
            self.turn = 0

        def decide_next_action(self, **kwargs) -> AgentDecision:
            self.turn += 1
            if self.turn == 1:
                return AgentDecision(
                    thought="Enter search keyword in input field",
                    action="input",
                    element_index=1,
                    value="antigravity"
                )
            elif self.turn == 2:
                return AgentDecision(
                    thought="Click the search button to submit",
                    action="click",
                    element_index=2
                )
            else:
                return AgentDecision(
                    thought="Verified search completed successfully",
                    action="finish_pass",
                    reason="Search flow verified"
                )

    runner = AIAgentTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        blob_storage=storage,
        reasoner=MockDeterministicReasoner(),
    )

    options = TestRunCreate(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
        runner_type=RunnerType.AI_AGENT,
        natural_language_goal="Input text in search and finish",
        max_agent_steps=4,
        action_delay_ms=0
    )

    executed_run = asyncio.run(runner.execute(run, target, options))

    assert executed_run.status == RunStatus.PASSED
    assert len(executed_run.actions) >= 3
    assert len(executed_run.agent_thought_trace) >= 3
    assert executed_run.agent_thought_trace[0]["action"] == "input"
    assert executed_run.agent_thought_trace[1]["action"] == "click"
    
    # Evidence verification
    evidence = repo.get_evidence_by_run(executed_run.run_id)
    assert len(evidence) >= 3

    for evi in evidence:
        if evi.artifact_path:
            assert Path(evi.artifact_path).exists()

def test_ai_agent_runner_loop_detection(agent_test_env):
    repo, storage, target = agent_test_env

    run = TestRun(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
        runner_type=RunnerType.AI_AGENT,
        max_agent_steps=6
    )
    repo.create_run(run)

    class LoopingReasoner:
        model = "mock-looping"
        def decide_next_action(self, **kwargs) -> AgentDecision:
            return AgentDecision(
                thought="Repeating same click action",
                action="click",
                element_index=1
            )

    runner = AIAgentTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        blob_storage=storage,
        reasoner=LoopingReasoner(),
    )

    options = TestRunCreate(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
        runner_type=RunnerType.AI_AGENT,
        max_agent_steps=6,
        action_delay_ms=0
    )

    executed_run = asyncio.run(runner.execute(run, target, options))

    assert executed_run.status == RunStatus.FAILED
    failures = repo.get_failures_by_run(executed_run.run_id)
    assert len(failures) == 1
    assert failures[0].category == FailureCategory.AGENT_LOOP_DETECTED

def test_run_manager_ai_agent_routing(agent_test_env):
    repo, storage, target = agent_test_env

    mock_runner = MockTestRunner(repo, repo, repo, repo)
    pw_runner = PlaywrightTestRunner(repo, repo, repo, repo, storage)
    
    class MockPassReasoner:
        model = "mock-pass"
        def decide_next_action(self, **kwargs) -> AgentDecision:
            return AgentDecision(
                thought="Pass immediately",
                action="finish_pass",
                reason="Pass immediately for testing routing"
            )

    ai_runner = AIAgentTestRunner(repo, repo, repo, repo, storage, MockPassReasoner())

    manager = RunManager(
        run_repo=repo,
        target_repo=repo,
        test_case_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        runners={
            RunnerType.MOCK: mock_runner,
            RunnerType.PLAYWRIGHT: pw_runner,
            RunnerType.AI_AGENT: ai_runner,
        }
    )

    payload = TestRunCreate(
        application_id=target.target_id,
        runner_type=RunnerType.AI_AGENT,
        natural_language_goal="Test AI agent dispatch",
        max_agent_steps=2,
        action_delay_ms=0
    )
    result = asyncio.run(manager.initiate_run(payload))

    assert result.runner_type == RunnerType.AI_AGENT
    assert result.status == RunStatus.PASSED
    assert result.natural_language_goal == "Test AI agent dispatch"
