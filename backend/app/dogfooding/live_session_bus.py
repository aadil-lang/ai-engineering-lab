import asyncio
import logging
from typing import Dict, List, Optional, AsyncGenerator, Set
from datetime import datetime, timezone
import base64

from backend.app.dogfooding.live_session_models import LiveDogfoodingSession, LiveSessionStatus
from backend.app.dogfooding.live_events import LiveEvent, LiveEventType

logger = logging.getLogger("ai_qa_platform.live_session_bus")

class LiveSessionEventBus:
    """
    Central event bus and state registry for Live Autonomous Application Testing.
    Enforces monotonic sequence numbering, subscriber broadcasting, gapless replay,
    and live screenshot caching.
    """

    def __init__(self):
        self._sessions: Dict[str, LiveDogfoodingSession] = {}
        self._run_to_session: Dict[str, str] = {}
        self._events: Dict[str, List[LiveEvent]] = {}
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._latest_screenshots: Dict[str, bytes] = {}
        self._lock = asyncio.Lock()

    def create_session(
        self,
        run_id: str,
        target_id: str,
        application_id: str,
        test_case_id: Optional[str] = None,
        runner_type: str = "PLAYWRIGHT",
        execution_source: str = "REAL_PLAYWRIGHT",
        total_steps: int = 10,
    ) -> LiveDogfoodingSession:
        session = LiveDogfoodingSession(
            run_id=run_id,
            target_id=target_id,
            application_id=application_id,
            test_case_id=test_case_id,
            runner_type=runner_type,
            execution_source=execution_source,
            status=LiveSessionStatus.CREATED,
            total_steps=total_steps,
        )
        self._sessions[session.session_id] = session
        self._run_to_session[run_id] = session.session_id
        self._events[session.session_id] = []
        self._subscribers[session.session_id] = set()

        # Emit initial SESSION_CREATED event
        self.publish(
            session_id=session.session_id,
            event_type=LiveEventType.SESSION_CREATED,
            payload={
                "session_id": session.session_id,
                "run_id": run_id,
                "target_id": target_id,
                "application_id": application_id,
                "total_steps": total_steps,
            },
        )
        return session

    def get_session(self, session_id: str) -> Optional[LiveDogfoodingSession]:
        return self._sessions.get(session_id)

    def get_session_by_run_id(self, run_id: str) -> Optional[LiveDogfoodingSession]:
        session_id = self._run_to_session.get(run_id)
        if session_id:
            return self._sessions.get(session_id)
        return None

    def list_sessions(self, active_only: bool = False) -> List[LiveDogfoodingSession]:
        sessions = list(self._sessions.values())
        if active_only:
            return [s for s in sessions if s.status in (LiveSessionStatus.CREATED, LiveSessionStatus.STARTING, LiveSessionStatus.RUNNING)]
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    def publish(
        self,
        session_id: str,
        event_type: LiveEventType,
        payload: Optional[Dict] = None,
    ) -> LiveEvent:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Live session {session_id} not found")

        payload = payload or {}
        # Monotonically increment sequence
        session.latest_event_sequence += 1
        sequence_num = session.latest_event_sequence

        event = LiveEvent(
            session_id=session_id,
            run_id=session.run_id,
            sequence_number=sequence_num,
            event_type=event_type,
            payload=payload,
        )

        # Update session state based on event
        self._update_session_state(session, event)

        # Append to event history
        if session_id not in self._events:
            self._events[session_id] = []
        self._events[session_id].append(event)

        # Dispatch to active subscribers
        subs = self._subscribers.get(session_id, set())
        for q in list(subs):
            try:
                q.put_nowait(event)
            except Exception as e:
                logger.warning(f"Failed to put event into subscriber queue: {e}")

        return event

    def _update_session_state(self, session: LiveDogfoodingSession, event: LiveEvent):
        etype = event.event_type
        payload = event.payload

        if etype == LiveEventType.SESSION_STARTED:
            session.status = LiveSessionStatus.RUNNING
            session.started_at = event.timestamp
        elif etype in (LiveEventType.NAVIGATION_STARTED, LiveEventType.NAVIGATION_COMPLETED):
            session.current_action = f"Navigate to {payload.get('url', '')}"
        elif etype == LiveEventType.ACTION_STARTED:
            session.current_action = payload.get("action_type") or payload.get("description")
            if "step_index" in payload:
                session.current_step = payload["step_index"]
        elif etype == LiveEventType.SCREENSHOT_CAPTURED:
            if "screenshot_id" in payload:
                session.latest_screenshot_id = payload["screenshot_id"]
            if "screenshot_base64" in payload:
                try:
                    self._latest_screenshots[session.session_id] = base64.b64decode(payload["screenshot_base64"])
                except Exception:
                    pass
        elif etype == LiveEventType.SESSION_COMPLETED:
            session.status = LiveSessionStatus.COMPLETED
            session.finished_at = event.timestamp
        elif etype == LiveEventType.SESSION_FAILED:
            session.status = LiveSessionStatus.FAILED
            session.finished_at = event.timestamp
        elif etype == LiveEventType.SESSION_CANCELLED:
            session.status = LiveSessionStatus.CANCELLED
            session.finished_at = event.timestamp

    def store_latest_screenshot(self, session_id: str, image_bytes: bytes, screenshot_id: Optional[str] = None):
        self._latest_screenshots[session_id] = image_bytes
        session = self._sessions.get(session_id)
        if session and screenshot_id:
            session.latest_screenshot_id = screenshot_id

    def get_latest_screenshot(self, session_id: str) -> Optional[bytes]:
        return self._latest_screenshots.get(session_id)

    def get_events(self, session_id: str, from_sequence: int = 0) -> List[LiveEvent]:
        events = self._events.get(session_id, [])
        if from_sequence <= 0:
            return list(events)
        return [e for e in events if e.sequence_number > from_sequence]

    async def subscribe(
        self,
        session_id: str,
        from_sequence: int = 0,
    ) -> AsyncGenerator[LiveEvent, None]:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Live session {session_id} not found")

        queue: asyncio.Queue = asyncio.Queue()
        if session_id not in self._subscribers:
            self._subscribers[session_id] = set()

        self._subscribers[session_id].add(queue)
        session.subscriber_count = len(self._subscribers[session_id])

        try:
            # 1. Replay historical events
            replay_events = self.get_events(session_id, from_sequence=from_sequence)
            for event in replay_events:
                yield event

            # 2. Stream real-time events
            while True:
                event = await queue.get()
                yield event
                if event.event_type in (
                    LiveEventType.SESSION_COMPLETED,
                    LiveEventType.SESSION_FAILED,
                    LiveEventType.SESSION_CANCELLED,
                ):
                    break
        finally:
            if session_id in self._subscribers:
                self._subscribers[session_id].discard(queue)
                session.subscriber_count = len(self._subscribers[session_id])

    def cancel_session(self, session_id: str, reason: str = "User requested cancellation") -> Optional[LiveDogfoodingSession]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        if session.status in (LiveSessionStatus.RUNNING, LiveSessionStatus.STARTING, LiveSessionStatus.CREATED):
            self.publish(
                session_id=session_id,
                event_type=LiveEventType.SESSION_CANCELLED,
                payload={"reason": reason},
            )
        return session

# Global singleton event bus
live_event_bus = LiveSessionEventBus()
