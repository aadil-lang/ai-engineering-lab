'use client';

import React from 'react';
import Link from 'next/link';
import {
  LiveDogfoodingSessionModel,
  LiveSessionStatus,
} from '@/types';
import {
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  StopCircle,
  Terminal,
  Globe,
  ExternalLink,
  ShieldCheck,
  Cpu,
  Layers,
  Sparkles,
} from 'lucide-react';

interface LiveTelemetryRibbonProps {
  session: LiveDogfoodingSessionModel;
  strategy?: any | null;
  onCancel?: () => void;
  isCancelling?: boolean;
}

const STATUS_CONFIG: Record<
  LiveSessionStatus,
  { label: string; bg: string; text: string; border: string; icon: React.ReactNode }
> = {
  CREATED: {
    label: 'QUEUED',
    bg: 'bg-indigo-950/60',
    text: 'text-indigo-400',
    border: 'border-indigo-500/30',
    icon: <Play className="h-3 w-3" />,
  },
  STARTING: {
    label: 'STARTING BROWSER',
    bg: 'bg-cyan-950/60',
    text: 'text-cyan-400',
    border: 'border-cyan-500/30',
    icon: <Activity className="h-3 w-3 animate-spin" />,
  },
  RUNNING: {
    label: 'ACTIVE TESTING',
    bg: 'bg-emerald-950/70',
    text: 'text-emerald-400',
    border: 'border-emerald-500/50',
    icon: <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />,
  },
  COMPLETED: {
    label: 'PASSED',
    bg: 'bg-emerald-950/80',
    text: 'text-emerald-300',
    border: 'border-emerald-500/40',
    icon: <CheckCircle2 className="h-3 w-3" />,
  },
  FAILED: {
    label: 'FAILED',
    bg: 'bg-rose-950/80',
    text: 'text-rose-400',
    border: 'border-rose-500/40',
    icon: <XCircle className="h-3 w-3" />,
  },
  CANCELLED: {
    label: 'CANCELLED',
    bg: 'bg-amber-950/80',
    text: 'text-amber-400',
    border: 'border-amber-500/40',
    icon: <AlertTriangle className="h-3 w-3" />,
  },
};

export const LiveTelemetryRibbon: React.FC<LiveTelemetryRibbonProps> = ({
  session,
  strategy,
  onCancel,
  isCancelling = false,
}) => {
  const statusCfg = STATUS_CONFIG[session.status] || STATUS_CONFIG.RUNNING;
  const isRunning = session.status === 'RUNNING' || session.status === 'STARTING' || session.status === 'CREATED';

  const progressPercent = session.total_steps > 0
    ? Math.min(Math.round((session.current_step / session.total_steps) * 100), 100)
    : 0;

  return (
    <div className="rounded-2xl border border-slate-800 bg-[#0b1120] p-4 sm:p-5 shadow-xl space-y-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 font-mono text-xs">
        {/* Left: Session metadata & status badge */}
        <div className="space-y-1.5">
          <div className="flex items-center space-x-3 flex-wrap gap-y-1">
            <span className="text-white font-bold text-sm tracking-tight">{session.session_id}</span>

            <span
              className={`inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full border text-[10px] font-bold ${statusCfg.bg} ${statusCfg.text} ${statusCfg.border}`}
            >
              {statusCfg.icon}
              <span>{statusCfg.label}</span>
            </span>

            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-indigo-300">
              {session.runner_type}
            </span>

            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-cyan-300">
              {session.application_id}
            </span>

            {strategy && (
              <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded bg-blue-950/70 border border-blue-500/40 text-[10px] text-blue-300 font-medium">
                <Sparkles className="h-3 w-3 text-blue-400" />
                <span>Strategy: {strategy.application_archetype || strategy.archetype}</span>
                {strategy.active_workflow && (
                  <span className="text-slate-400 font-normal">→ {strategy.active_workflow.name}</span>
                )}
              </span>
            )}
          </div>

          <div className="flex items-center space-x-3 text-slate-400 text-[11px]">
            <span>
              Run:{' '}
              <Link
                href={`/runs/${session.run_id}`}
                className="text-cyan-400 hover:underline inline-flex items-center space-x-0.5 font-bold"
              >
                <span>{session.run_id}</span>
                <ExternalLink className="h-2.5 w-2.5" />
              </Link>
            </span>
            <span className="text-slate-600">|</span>
            <span>Live Subscribers: <strong className="text-white">{session.subscriber_count}</strong></span>
            <span className="text-slate-600">|</span>
            <span>Total Events: <strong className="text-white">{session.latest_event_sequence}</strong></span>
          </div>
        </div>

        {/* Right: Step Counter & Cancel Action */}
        <div className="flex items-center space-x-4 flex-shrink-0">
          <div className="text-right">
            <div className="text-[10px] uppercase text-slate-500">Autonomous Budget</div>
            <div className="text-sm font-bold text-white">
              Step <span className="text-cyan-400">{session.current_step}</span> / {session.total_steps}
            </div>
          </div>

          {isRunning && onCancel && (
            <button
              onClick={onCancel}
              disabled={isCancelling}
              className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 text-xs font-semibold transition active:scale-95 disabled:opacity-50"
            >
              <StopCircle className="h-4 w-4 text-rose-400" />
              <span>{isCancelling ? 'Cancelling...' : 'Cancel Test'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1">
        <div className="w-full h-1.5 rounded-full bg-slate-900 overflow-hidden border border-slate-800">
          <div
            className={`h-full transition-all duration-500 ${
              session.status === 'FAILED'
                ? 'bg-rose-500'
                : session.status === 'COMPLETED'
                ? 'bg-emerald-400'
                : 'bg-gradient-to-r from-cyan-500 to-indigo-500'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex justify-between text-[10px] font-mono text-slate-500">
          <span>Action: {session.current_action || 'Initializing...'}</span>
          <span>{progressPercent}% Complete</span>
        </div>
      </div>
    </div>
  );
};
