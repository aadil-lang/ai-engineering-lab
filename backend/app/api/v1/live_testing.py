from fastapi import APIRouter, HTTPException, Query, Response, Depends, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional
import json
import asyncio

from backend.app.dogfooding.live_session_models import LiveDogfoodingSession, LiveSessionStatus
from backend.app.dogfooding.live_events import LiveEvent, LiveEventType
from backend.app.dogfooding.live_session_bus import live_event_bus
from backend.app.models.test_run import TestRunCreate
from backend.app.api.deps import get_run_manager
from backend.app.services.run_manager import RunManager

router = APIRouter()

@router.get("/sessions", response_model=List[LiveDogfoodingSession])
def list_live_sessions(active_only: bool = Query(False, description="Filter for only active sessions")):
    """List all registered live dogfooding testing sessions."""
    return live_event_bus.list_sessions(active_only=active_only)

@router.get("/sessions/{session_id}", response_model=LiveDogfoodingSession)
def get_live_session(session_id: str):
    """Retrieve state and telemetry overview of a live session."""
    session = live_event_bus.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Live session '{session_id}' not found",
        )
    return session

@router.get("/sessions/by-run/{run_id}", response_model=LiveDogfoodingSession)
def get_live_session_by_run(run_id: str):
    """Retrieve live session associated with a test run."""
    session = live_event_bus.get_session_by_run_id(run_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No live session registered for run '{run_id}'",
        )
    return session

@router.get("/sessions/{session_id}/events/history", response_model=List[LiveEvent])
def get_session_event_history(
    session_id: str,
    from_sequence: int = Query(0, ge=0, description="Return events strictly after this sequence number"),
):
    """Get historical events for replay and post-run inspection."""
    session = live_event_bus.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Live session '{session_id}' not found",
        )
    return live_event_bus.get_events(session_id, from_sequence=from_sequence)

@router.get("/sessions/{session_id}/events")
async def stream_session_events(
    session_id: str,
    from_sequence: int = Query(0, ge=0, description="Replay from this sequence number"),
):
    """
    Server-Sent Events (SSE) live stream delivering real-time engineering events
    with gapless monotonic replay.
    """
    session = live_event_bus.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Live session '{session_id}' not found",
        )

    async def event_generator():
        try:
            async for event in live_event_bus.subscribe(session_id, from_sequence=from_sequence):
                data = json.dumps(event.model_dump())
                yield f"event: {event.event_type.value}\ndata: {data}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.get("/sessions/{session_id}/screenshot")
def get_live_screenshot(session_id: str):
    """Retrieve the latest captured browser viewport screenshot as PNG."""
    session = live_event_bus.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Live session '{session_id}' not found",
        )

    image_bytes = live_event_bus.get_latest_screenshot(session_id)
    if not image_bytes:
        # Return empty 1x1 transparent png if no screenshot yet
        transparent_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05"
            b"\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return Response(content=transparent_png, media_type="image/png")

    return Response(content=image_bytes, media_type="image/png")

@router.post("/sessions/{session_id}/cancel", response_model=LiveDogfoodingSession)
def cancel_live_session(session_id: str):
    """Cancel a running live test session."""
    session = live_event_bus.cancel_session(session_id, reason="User cancelled from Live Testing Console")
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Live session '{session_id}' not found",
        )
    return session

@router.post("/launch", response_model=LiveDogfoodingSession)
async def launch_live_test_run(
    payload: TestRunCreate,
    background_tasks: BackgroundTasks,
    run_manager: RunManager = Depends(get_run_manager),
):
    """
    Launch an autonomous test run with an immediately attached LiveDogfoodingSession.
    Returns the live session immediately so the frontend console can begin streaming.
    """
    import uuid
    run_id = f"run_{uuid.uuid4().hex[:8]}"

    # Pre-create the live session
    session = live_event_bus.create_session(
        run_id=run_id,
        target_id=payload.application_id,
        application_id=payload.application_id,
        test_case_id=payload.test_case_id,
        runner_type=payload.runner_type.value if hasattr(payload.runner_type, "value") else str(payload.runner_type),
        execution_source=payload.execution_source.value if hasattr(payload.execution_source, "value") else str(payload.execution_source),
        total_steps=payload.max_agent_steps or 10,
    )

    # Dispatch execution in background task
    async def _execute():
        try:
            await run_manager.initiate_run(payload)
        except Exception:
            pass

    background_tasks.add_task(_execute)

    return session


@router.get("/sessions/{session_id}/strategy")
def get_session_strategy(session_id: str):
    """Retrieve the adaptive testing strategy and current workflow priorities for a session."""
    session = live_event_bus.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Live session '{session_id}' not found",
        )
    events = live_event_bus.get_events(session_id)
    strategy_event = next(
        (e for e in reversed(events) if e.event_type in (LiveEventType.STRATEGY_PLANNED, LiveEventType.STRATEGY_ADAPTED)),
        None
    )
    if strategy_event:
        return strategy_event.payload
    return session.metadata.get("testing_strategy", {})
