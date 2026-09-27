import asyncio
from datetime import datetime, timezone
from typing import Any
import uuid

from backend.app.models.enums import (
    CampaignStatus,
    CampaignType,
    RunnerType,
    ExecutionSource,
    RunStatus,
    TestMode,
    PopulationType,
)
from backend.app.models.campaign import (
    Campaign,
    CampaignConfiguration,
    CampaignSummaryReport,
    CampaignCreate,
)
from backend.app.models.test_run import TestRunCreate
from backend.app.repositories.base import (
    CampaignRepositoryInterface,
    TargetRepositoryInterface,
    TestCaseRepositoryInterface,
)
from backend.app.services.run_manager import RunManager
from backend.app.core.exceptions import NotFoundException
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.prediction.walk_forward_evaluator import PopulationSeparator


class CampaignService:
    """
    Orchestrates repeatable real-world QA telemetry campaigns across targets,
    test cases, and runner types (Playwright & AI Agent) using RunManager.
    """

    def __init__(
        self,
        campaign_repo: CampaignRepositoryInterface,
        run_manager: RunManager,
        target_repo: TargetRepositoryInterface,
        test_case_repo: TestCaseRepositoryInterface,
    ):
        self.campaign_repo = campaign_repo
        self.run_manager = run_manager
        self.target_repo = target_repo
        self.test_case_repo = test_case_repo

    def create_campaign(self, payload: CampaignCreate) -> Campaign:
        target = self.target_repo.get_target(payload.target_id)
        if not target:
            raise NotFoundException(f"Target '{payload.target_id}' not found")

        # Resolve test cases
        test_case_ids = payload.test_case_ids
        if not test_case_ids:
            # Fall back to all test cases registered for this target, or a single None exploratory run
            target_tcs = self.test_case_repo.list_test_cases(target_id=payload.target_id)
            if target_tcs:
                test_case_ids = [tc.test_case_id for tc in target_tcs]
            else:
                test_case_ids = [None]

        runner_types = payload.runner_types or [RunnerType.PLAYWRIGHT]
        iterations = max(1, payload.iterations_per_test_case)
        total_requested = len(test_case_ids) * len(runner_types) * iterations

        # Determine explicit execution sources
        execution_sources = payload.execution_sources
        if not execution_sources:
            execution_sources = []
            for rt in runner_types:
                if rt == RunnerType.PLAYWRIGHT:
                    execution_sources.append(ExecutionSource.REAL_PLAYWRIGHT)
                elif rt == RunnerType.AI_AGENT:
                    execution_sources.append(ExecutionSource.REAL_AI_AGENT)
                elif rt == RunnerType.MOCK:
                    execution_sources.append(ExecutionSource.SYNTHETIC_MOCK)
                else:
                    execution_sources.append(ExecutionSource.UNKNOWN)

        camp_type = payload.campaign_type
        if not camp_type:
            if payload.parameters.get("simulate_failure"):
                camp_type = CampaignType.CONTROLLED_EXPERIMENT
            elif runner_types == [RunnerType.MOCK]:
                camp_type = CampaignType.SYNTHETIC
            else:
                camp_type = CampaignType.REAL_RELIABILITY
        elif camp_type == CampaignType.REAL_RELIABILITY and payload.parameters.get("simulate_failure"):
            camp_type = CampaignType.CONTROLLED_EXPERIMENT

        config = CampaignConfiguration(
            target_id=payload.target_id,
            campaign_type=camp_type,
            test_case_ids=[t for t in test_case_ids if t is not None],
            runner_types=runner_types,
            execution_sources=execution_sources,
            iterations_per_test_case=iterations,
            target_url_override=payload.target_url_override or target.base_url,
            natural_language_goal=payload.natural_language_goal,
            max_agent_steps=payload.max_agent_steps,
            delay_between_runs_ms=payload.delay_between_runs_ms,
            stop_on_first_failure=payload.stop_on_first_failure,
            stop_on_consecutive_failures=payload.stop_on_consecutive_failures,
            environment_id=payload.environment_id or target.environment,
            description=payload.description,
            parameters=payload.parameters,
        )

        campaign = Campaign(
            campaign_id=f"camp_{uuid.uuid4().hex[:8]}",
            name=payload.name,
            description=payload.description,
            target_id=target.target_id,
            campaign_type=camp_type,
            environment_id=config.environment_id,
            status=CampaignStatus.CREATED,
            created_at=datetime.now(timezone.utc).isoformat(),
            requested_runs=total_requested,
            completed_runs=0,
            passed_runs=0,
            failed_runs=0,
            cancelled_runs=0,
            execution_sources=execution_sources,
            configuration=config,
            run_ids=[],
            summary_report={},
            created_by=payload.created_by,
        )

        return self.campaign_repo.create_campaign(campaign)

    async def execute_campaign(self, campaign_id: str) -> Campaign:
        campaign = self.campaign_repo.get_campaign(campaign_id)
        if not campaign:
            raise NotFoundException(f"Campaign '{campaign_id}' not found")

        target = self.target_repo.get_target(campaign.target_id)
        if not target:
            raise NotFoundException(f"Target '{campaign.target_id}' not found")

        campaign.status = CampaignStatus.RUNNING
        campaign.started_at = datetime.now(timezone.utc).isoformat()
        self.campaign_repo.update_campaign(campaign)

        config = campaign.configuration
        test_case_ids = config.test_case_ids if config.test_case_ids else [None]
        runner_types = config.runner_types or [RunnerType.PLAYWRIGHT]
        iterations = max(1, config.iterations_per_test_case)

        consecutive_failures = 0
        early_stop_triggered = False
        early_stop_reason = ""
        total_duration_ms = 0
        executed_runs = []

        try:
            for iteration_idx in range(1, iterations + 1):
                if early_stop_triggered:
                    break

                for tc_id in test_case_ids:
                    if early_stop_triggered:
                        break

                    for runner_idx, runner_type in enumerate(runner_types):
                        if early_stop_triggered:
                            break

                        # Determine execution source for this runner
                        if config.execution_sources and runner_idx < len(config.execution_sources):
                            exec_source = config.execution_sources[runner_idx]
                        elif runner_type == RunnerType.PLAYWRIGHT:
                            exec_source = ExecutionSource.REAL_PLAYWRIGHT
                        elif runner_type == RunnerType.AI_AGENT:
                            exec_source = ExecutionSource.REAL_AI_AGENT
                        elif runner_type == RunnerType.MOCK:
                            exec_source = ExecutionSource.SYNTHETIC_MOCK
                        else:
                            exec_source = ExecutionSource.UNKNOWN

                        # Mode
                        if runner_type == RunnerType.AI_AGENT:
                            mode = TestMode.EXPLORATORY_DOGFOODING
                        else:
                            mode = TestMode.FUNCTIONAL_QA

                        # Principle 3: No fault injection in the REAL_RELIABILITY population
                        sim_fail = False if campaign.campaign_type == CampaignType.REAL_RELIABILITY else config.parameters.get("simulate_failure", False)


                        run_req = TestRunCreate(
                            application_id=campaign.target_id,
                            application_version=target.version,
                            test_mode=mode,
                            runner_type=runner_type,
                            execution_source=exec_source,
                            test_case_id=tc_id,
                            environment_id=campaign.environment_id,
                            target_url_override=config.target_url_override,
                            natural_language_goal=config.natural_language_goal,
                            max_agent_steps=config.max_agent_steps,
                            campaign_id=campaign.campaign_id,
                            campaign_type=campaign.campaign_type,
                            simulate_failure=sim_fail,
                            action_delay_ms=config.parameters.get("action_delay_ms", 50),
                        )

                        try:
                            executed_run = await self.run_manager.initiate_run(run_req)
                            campaign.run_ids.append(executed_run.run_id)
                            campaign.completed_runs += 1
                            total_duration_ms += executed_run.duration_ms
                            executed_runs.append(executed_run)

                            is_passed = executed_run.status == RunStatus.PASSED
                            if is_passed:
                                campaign.passed_runs += 1
                                consecutive_failures = 0
                            else:
                                campaign.failed_runs += 1
                                consecutive_failures += 1

                            # Failure policies
                            if not is_passed and config.stop_on_first_failure:
                                early_stop_triggered = True
                                early_stop_reason = f"Stopped early: First failure encountered on run {executed_run.run_id}"
                            elif (
                                config.stop_on_consecutive_failures
                                and consecutive_failures >= config.stop_on_consecutive_failures
                            ):
                                early_stop_triggered = True
                                early_stop_reason = f"Stopped early: {consecutive_failures} consecutive failures encountered"

                        except Exception as ex:
                            campaign.completed_runs += 1
                            campaign.failed_runs += 1
                            consecutive_failures += 1
                            if config.stop_on_first_failure:
                                early_stop_triggered = True
                                early_stop_reason = f"Stopped early on runner exception: {str(ex)}"

                        # Update checkpoint
                        self.campaign_repo.update_campaign(campaign)

                        # Delay between runs
                        if config.delay_between_runs_ms > 0 and not early_stop_triggered:
                            await asyncio.sleep(config.delay_between_runs_ms / 1000.0)

        finally:
            campaign.finished_at = datetime.now(timezone.utc).isoformat()
            remaining = campaign.requested_runs - campaign.completed_runs
            if remaining > 0:
                campaign.cancelled_runs = remaining

            if early_stop_triggered or campaign.cancelled_runs > 0:
                campaign.status = CampaignStatus.PARTIAL
            elif campaign.failed_runs == campaign.completed_runs and campaign.completed_runs > 0:
                campaign.status = CampaignStatus.FAILED
            else:
                campaign.status = CampaignStatus.COMPLETED

            # Build summary report
            pass_rate = (
                campaign.passed_runs / campaign.completed_runs
                if campaign.completed_runs > 0
                else 0.0
            )
            avg_duration = (
                total_duration_ms / campaign.completed_runs
                if campaign.completed_runs > 0
                else 0.0
            )

            # Sources and runners breakdown
            sources_breakdown: dict[str, int] = {}
            runners_breakdown: dict[str, int] = {}
            for r in executed_runs:
                s_key = r.execution_source.value if hasattr(r.execution_source, "value") else str(r.execution_source)
                r_key = r.runner_type.value if hasattr(r.runner_type, "value") else str(r.runner_type)
                sources_breakdown[s_key] = sources_breakdown.get(s_key, 0) + 1
                runners_breakdown[r_key] = runners_breakdown.get(r_key, 0) + 1

            # Population impact audit
            population_impact: dict[str, Any] = {}
            try:
                all_runs_count = self.run_manager.run_repo.count_runs()
                all_runs = self.run_manager.run_repo.list_runs(limit=all_runs_count)
                records = []
                for r in all_runs:
                    evi = self.run_manager.evidence_repo.get_evidence_by_run(r.run_id)
                    fails = self.run_manager.failure_repo.get_failures_by_run(r.run_id)
                    records.append(ReliabilityFeatureExtractor.extract_record_from_run(r, evi, fails))
                vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)

                for pop in [
                    PopulationType.ALL_HISTORICAL,
                    PopulationType.REAL_EXECUTIONS_ONLY,
                    PopulationType.REAL_PLAYWRIGHT_ONLY,
                    PopulationType.REAL_AI_AGENT_ONLY,
                    PopulationType.CONTROLLED_AND_DEMO,
                ]:
                    audit = PopulationSeparator.audit_population(pop, records, vectors)
                    population_impact[pop.value] = {
                        "population_name": audit.population_name,
                        "total_runs": audit.total_runs,
                        "total_transitions": audit.total_transitions,
                        "passes": audit.passes_count,
                        "failures": audit.failures_count,
                        "failure_rate": round(audit.failure_rate, 4),
                        "status": audit.status.value,
                        "status_reason": audit.status_reason,
                    }
            except Exception as pop_err:
                population_impact["error"] = str(pop_err)

            campaign.summary_report = {
                "campaign_id": campaign.campaign_id,
                "name": campaign.name,
                "target_id": campaign.target_id,
                "status": campaign.status.value,
                "total_requested": campaign.requested_runs,
                "total_completed": campaign.completed_runs,
                "passed_count": campaign.passed_runs,
                "failed_count": campaign.failed_runs,
                "cancelled_count": campaign.cancelled_runs,
                "pass_rate": round(pass_rate, 4),
                "total_duration_ms": total_duration_ms,
                "average_duration_ms": round(avg_duration, 1),
                "sources_breakdown": sources_breakdown,
                "runners_breakdown": runners_breakdown,
                "early_stop_reason": early_stop_reason,
                "population_impact": population_impact,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            self.campaign_repo.update_campaign(campaign)

        return campaign

    def get_campaign(self, campaign_id: str) -> Campaign:
        campaign = self.campaign_repo.get_campaign(campaign_id)
        if not campaign:
            raise NotFoundException(f"Campaign '{campaign_id}' not found")
        return campaign

    def list_campaigns(
        self, limit: int = 50, offset: int = 0, target_id: str | None = None
    ) -> list[Campaign]:
        return self.campaign_repo.list_campaigns(limit=limit, offset=offset, target_id=target_id)

    def get_campaign_runs(self, campaign_id: str) -> list[Any]:
        self.get_campaign(campaign_id) # Verify exists
        return self.campaign_repo.get_runs_by_campaign(campaign_id)
