'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { AppShell } from '@/components/AppShell';
import { LiveViewport } from '@/components/LiveConsole/LiveViewport';
import { LiveEventStream } from '@/components/LiveConsole/LiveEventStream';
import { LiveTelemetryRibbon } from '@/components/LiveConsole/LiveTelemetryRibbon';
import { QuickLaunchModal } from '@/components/QuickLaunchModal';
import { liveApi, api } from '@/lib/api';
import {
  LiveDogfoodingSessionModel,
  LiveEventModel,
  TestRunCreate,
} from '@/types';
import {
  Play,
  Activity,
  Monitor,
  Terminal,
  Globe,
  RefreshCw,
  Sparkles,
  StopCircle,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Layers,
  ArrowRight,
} from 'lucide-react';

export default function LiveTestingConsolePage() {
  const [sessions, setSessions] = useState<LiveDogfoodingSessionModel[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [currentSession, setCurrentSession] = useState<LiveDogfoodingSessionModel | null>(null);
  const [events, setEvents] = useState<LiveEventModel[]>([]);
  const [latestScreenshotBase64, setLatestScreenshotBase64] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLaunchModalOpen, setIsLaunchModalOpen] = useState<boolean>(false);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);
  const [latestStrategy, setLatestStrategy] = useState<any | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);

  // 1. Load active sessions on mount
  const loadSessions = async () => {
    setIsLoading(true);
    try {
      const data = await liveApi.getSessions(false);
      setSessions(data);
      if (data.length > 0 && !selectedSessionId) {
        // Pick first active session or first recent session
        const active = data.find(s => s.status === 'RUNNING' || s.status === 'STARTING') || data[0];
        setSelectedSessionId(active.session_id);
        setCurrentSession(active);
      }
    } catch (err) {
      console.error('Failed to load live sessions:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  // 2. Connect SSE EventSource when selectedSessionId changes
  useEffect(() => {
    if (!selectedSessionId) return;

    // Fetch initial event history & session state
    const initSession = async () => {
      try {
        const [sess, history] = await Promise.all([
          liveApi.getSession(selectedSessionId).catch(() => null),
          liveApi.getEventHistory(selectedSessionId, 0).catch(() => []),
        ]);
        if (sess) setCurrentSession(sess);
        setEvents(history);

        // Check for latest screenshot in history
        const lastSc = [...history].reverse().find(e => e.event_type === 'SCREENSHOT_CAPTURED');
        if (lastSc?.payload?.screenshot_base64) {
          setLatestScreenshotBase64(lastSc.payload.screenshot_base64);
        }

        // Check for latest strategy in history
        const lastStrat = [...history].reverse().find(e => e.event_type === 'STRATEGY_PLANNED' || e.event_type === 'STRATEGY_ADAPTED');
        if (lastStrat?.payload) {
          setLatestStrategy(lastStrat.payload);
        } else {
          setLatestStrategy(null);
        }
      } catch (err) {
        console.error('Failed to initialize live session history:', err);
      }
    };
    initSession();

    // Clean up existing EventSource
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    const sseUrl = liveApi.getEventSourceUrl(selectedSessionId, 0);
    const es = new EventSource(sseUrl);
    eventSourceRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
    };

    es.onerror = () => {
      setIsConnected(false);
    };

    // Generic event handler
    es.onmessage = (eventMsg) => {
      try {
        const parsed: LiveEventModel = JSON.parse(eventMsg.data);
        setEvents(prev => {
          // Avoid duplicate sequence numbers
          if (prev.some(e => e.sequence_number === parsed.sequence_number)) return prev;
          return [...prev, parsed];
        });

        // Update live state based on incoming event
        if (parsed.event_type === 'SCREENSHOT_CAPTURED' && parsed.payload?.screenshot_base64) {
          setLatestScreenshotBase64(parsed.payload.screenshot_base64);
        }
        if (parsed.event_type === 'STRATEGY_PLANNED' || parsed.event_type === 'STRATEGY_ADAPTED') {
          setLatestStrategy(parsed.payload);
        }

        setCurrentSession(prev => {
          if (!prev) return prev;
          const updated = { ...prev, latest_event_sequence: parsed.sequence_number };
          if (parsed.event_type === 'SESSION_STARTED') {
            updated.status = 'RUNNING';
          } else if (parsed.event_type === 'SESSION_COMPLETED') {
            updated.status = 'COMPLETED';
          } else if (parsed.event_type === 'SESSION_FAILED') {
            updated.status = 'FAILED';
          } else if (parsed.event_type === 'SESSION_CANCELLED') {
            updated.status = 'CANCELLED';
          } else if (parsed.event_type === 'ACTION_STARTED') {
            updated.current_action = parsed.payload.description || parsed.payload.action_type;
            if (parsed.payload.step_index) updated.current_step = parsed.payload.step_index;
          }
          return updated;
        });
      } catch (e) {
        console.warn('Error parsing SSE event data:', e);
      }
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    };
  }, [selectedSessionId]);

  // Handle Cancel
  const handleCancelSession = async () => {
    if (!selectedSessionId) return;
    setIsCancelling(true);
    try {
      const updated = await liveApi.cancelSession(selectedSessionId);
      setCurrentSession(updated);
    } catch (err) {
      console.error('Failed to cancel session:', err);
    } finally {
      setIsCancelling(false);
    }
  };

  // Quick 1-click launch handler
  const handleQuickLaunchRealApp = async () => {
    try {
      const liveSess = await liveApi.launchLiveRun({
        application_id: 'real_question_generator_local',
        test_mode: 'EXPLORATORY_DOGFOODING' as any,
        runner_type: 'PLAYWRIGHT' as any,
        natural_language_goal: 'Autonomously explore the Question Generator app, test topic generation, and verify JSON structure.',
        max_agent_steps: 10,
        target_url_override: 'http://localhost:3000',
      });
      setSelectedSessionId(liveSess.session_id);
      setCurrentSession(liveSess);
      setSessions(prev => [liveSess, ...prev]);
    } catch (err) {
      console.error('Failed to launch live run:', err);
    }
  };

  const isSessionRunning = currentSession?.status === 'RUNNING' || currentSession?.status === 'STARTING';

  return (
    <AppShell onOpenLaunchModal={() => setIsLaunchModalOpen(true)}>
      <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Top Control Ribbon */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-2xl bg-gradient-to-r from-slate-950 via-[#0d162a] to-slate-950 border border-cyan-500/20 shadow-xl">
          <div className="space-y-1">
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-mono font-bold">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
              <span>Slice 8D — Live Observability Console</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight font-sans">
              Live Autonomous Application Testing Console
            </h1>
            <p className="text-xs text-slate-300 font-sans">
              Watch the authoritative Playwright browser session execute live actions against your application in real time.
            </p>
          </div>

          <div className="flex items-center space-x-3 flex-shrink-0">
            {/* Session Selector */}
            <select
              value={selectedSessionId || ''}
              onChange={e => {
                const sId = e.target.value;
                setSelectedSessionId(sId);
                const found = sessions.find(s => s.session_id === sId);
                if (found) setCurrentSession(found);
              }}
              className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
            >
              {sessions.length === 0 && <option value="">No Sessions Available</option>}
              {sessions.map(s => (
                <option key={s.session_id} value={s.session_id}>
                  {s.session_id} ({s.status}) - {s.application_id}
                </option>
              ))}
            </select>

            <button
              onClick={loadSessions}
              className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition"
              title="Refresh sessions list"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>

            <button
              onClick={handleQuickLaunchRealApp}
              className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-lg shadow-cyan-900/30 transition active:scale-95"
            >
              <Play className="h-3.5 w-3.5 fill-white" />
              <span>Launch Live Run</span>
            </button>
          </div>
        </div>

        {/* Active Session Ribbon */}
        {currentSession ? (
          <LiveTelemetryRibbon
            session={currentSession}
            strategy={latestStrategy}
            onCancel={handleCancelSession}
            isCancelling={isCancelling}
          />
        ) : (
          <div className="p-8 text-center rounded-2xl border border-slate-800 bg-[#0b1120] space-y-4">
            <Monitor className="h-12 w-12 text-cyan-400 mx-auto opacity-70 animate-pulse" />
            <div className="space-y-1">
              <h3 className="text-base font-bold text-white">No Live Session Active</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Launch an autonomous Playwright dogfooding test run to watch the live browser session and real-time engineering telemetry.
              </p>
            </div>
            <button
              onClick={handleQuickLaunchRealApp}
              className="px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs transition active:scale-95"
            >
              Launch Live Autonomous Test Now
            </button>
          </div>
        )}

        {/* Main Split Console Grid */}
        {currentSession && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Live Browser Viewport (7 cols) */}
            <div className="lg:col-span-7 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-2">
                  <Monitor className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Real Chromium Browser Session</span>
                </h2>
                <span className="text-[10px] font-mono text-slate-500">
                  Target: <code className="text-cyan-300">{currentSession.application_id}</code>
                </span>
              </div>

              <LiveViewport
                sessionId={currentSession.session_id}
                screenshotBase64={latestScreenshotBase64}
                currentAction={currentSession.current_action}
                targetUrl="http://localhost:3000"
                isRunning={isSessionRunning}
                latestEventSequence={currentSession.latest_event_sequence}
              />
            </div>

            {/* Right Column: Live Event Stream & Observability (5 cols) */}
            <div className="lg:col-span-5 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-2">
                  <Activity className="h-3.5 w-3.5 text-indigo-400" />
                  <span>Real-Time Runtime Observability</span>
                </h2>
                <span className="text-[10px] font-mono text-slate-500">
                  Monotonic Event Bus
                </span>
              </div>

              <LiveEventStream
                events={events}
                isConnected={isConnected}
              />
            </div>
          </div>
        )}
      </div>

      <QuickLaunchModal
        isOpen={isLaunchModalOpen}
        onClose={() => setIsLaunchModalOpen(false)}
        onRunCreated={() => loadSessions()}
      />
    </AppShell>
  );
}
