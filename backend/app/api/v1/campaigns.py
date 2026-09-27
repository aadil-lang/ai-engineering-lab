from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from typing import Any

from backend.app.models.campaign import Campaign, CampaignCreate
from backend.app.models.test_run import TestRun
from backend.app.services.campaign_service import CampaignService
from backend.app.api.deps import get_campaign_service

router = APIRouter()


@router.post("/", response_model=Campaign, status_code=status.HTTP_201_CREATED)
async def create_and_launch_campaign(
    payload: CampaignCreate,
    execute_async: bool = Query(
        False,
        description="If True, runs the campaign in the background and returns immediately with status CREATED/RUNNING. If False, executes synchronously to completion.",
    ),
    background_tasks: BackgroundTasks = None,
    service: CampaignService = Depends(get_campaign_service),
) -> Campaign:
    """Create a new QA campaign and launch multi-iteration longitudinal execution."""
    campaign = service.create_campaign(payload)
    if execute_async and background_tasks is not None:
        background_tasks.add_task(service.execute_campaign, campaign.campaign_id)
        return campaign
    else:
        executed_campaign = await service.execute_campaign(campaign.campaign_id)
        return executed_campaign


@router.get("/", response_model=list[Campaign])
def list_campaigns(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    target_id: str | None = None,
    service: CampaignService = Depends(get_campaign_service),
) -> list[Campaign]:
    """List historical QA campaigns with optional target filtering."""
    return service.list_campaigns(limit=limit, offset=offset, target_id=target_id)


@router.get("/{campaign_id}", response_model=Campaign)
def get_campaign(
    campaign_id: str,
    service: CampaignService = Depends(get_campaign_service),
) -> Campaign:
    """Retrieve detailed state of a QA campaign."""
    return service.get_campaign(campaign_id)


@router.get("/{campaign_id}/runs", response_model=list[TestRun])
def get_campaign_runs(
    campaign_id: str,
    service: CampaignService = Depends(get_campaign_service),
) -> list[TestRun]:
    """Retrieve all test runs generated within a specific QA campaign."""
    return service.get_campaign_runs(campaign_id)


@router.get("/{campaign_id}/report", response_model=dict[str, Any])
def get_campaign_report(
    campaign_id: str,
    service: CampaignService = Depends(get_campaign_service),
) -> dict[str, Any]:
    """Retrieve the summary report and longitudinal metrics for a campaign."""
    campaign = service.get_campaign(campaign_id)
    return campaign.summary_report
