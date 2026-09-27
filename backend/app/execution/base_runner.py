from abc import ABC, abstractmethod
from backend.app.models.test_run import TestRun, TestRunCreate
from backend.app.models.target import ApplicationTarget

class BaseTestRunner(ABC):
    """
    Abstract base test runner.
    Future implementations will include PlaywrightBrowserRunner, LLMAgentRunner, APIEndpointRunner.
    """
    @abstractmethod
    async def execute(self, run: TestRun, target: ApplicationTarget, options: TestRunCreate) -> TestRun:
        """Executes the test run end-to-end and populates actions, evidence, failures, and metrics."""
        pass
