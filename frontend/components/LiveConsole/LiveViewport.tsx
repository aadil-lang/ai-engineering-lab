'use client';

import React, { useState, useEffect } from 'react';
import {
  Monitor,
  Maximize2,
  Minimize2,
  RefreshCw,
  Globe,
  Wifi,
  WifiOff,
  Crosshair,
  ExternalLink,
  Layers,
  Sparkles,
} from 'lucide-react';

interface LiveViewportProps {
  sessionId: string;
  screenshotBase64?: string | null;
  currentAction?: string | null;
  targetUrl?: string | null;
  isRunning?: boolean;
  latestEventSequence?: number;
}

export const LiveViewport: React.FC<LiveViewportProps> = ({
  sessionId,
  screenshotBase64,
  currentAction,
  targetUrl,
  isRunning = false,
  latestEventSequence = 0,
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [fallbackTimestamp, setFallbackTimestamp] = useState(Date.now());
  const [imageError, setImageError] = useState(false);

  // Poll screenshot every 2 seconds as backup if no direct base64 event
  useEffect(() => {
    if (!isRunning) return;
    const interval = setInterval(() => {
      setFallbackTimestamp(Date.now());
    }, 2000);
    return () => clearInterval(interval);
  }, [isRunning]);

  const screenshotSrc = screenshotBase64
    ? `data:image/png;base64,${screenshotBase64}`
    : `/api/v1/live/sessions/${encodeURIComponent(sessionId)}/screenshot?t=${fallbackTimestamp}`;

  return (
    <div
      className={`relative flex flex-col rounded-2xl border border-slate-800 bg-[#090d16] overflow-hidden shadow-2xl transition-all ${
        isFullscreen ? 'fixed inset-4 z-50 shadow-[0_0_50px_rgba(0,0,0,0.9)]' : 'h-[520px] lg:h-[620px]'
      }`}
    >
      {/* Top Browser Chrome Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950 border-b border-slate-800/90 text-xs font-mono select-none">
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1.5 mr-2">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
          </div>

          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300 max-w-md truncate">
            <Globe className="h-3 w-3 text-cyan-400 flex-shrink-0" />
            <span className="truncate text-[11px]">{targetUrl || 'http://localhost:3000'}</span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {isRunning ? (
            <div className="flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] font-bold">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
              <span>LIVE BROWSER (PLAYWRIGHT)</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-slate-800/60 border border-slate-700/40 text-slate-400 text-[10px]">
              <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
              <span>OFFLINE / COMPLETED</span>
            </div>
          )}

          <div className="hidden sm:flex items-center text-slate-500 text-[11px]">
            <span>1920 × 1080</span>
          </div>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white transition"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Main Canvas Viewport */}
      <div className="relative flex-1 bg-black flex items-center justify-center overflow-hidden">
        {screenshotSrc && !imageError ? (
          <img
            src={screenshotSrc}
            alt="Live Application Browser Session"
            className="w-full h-full object-contain select-none"
            onError={() => setImageError(true)}
            onLoad={() => setImageError(false)}
          />
        ) : (
          <div className="flex flex-col items-center justify-center p-8 text-center space-y-3">
            <Monitor className="h-12 w-12 text-slate-700 animate-pulse" />
            <div className="space-y-1">
              <p className="text-sm font-semibold text-slate-300">
                {isRunning ? 'Waiting for initial viewport snapshot...' : 'No live screenshot available'}
              </p>
              <p className="text-xs text-slate-500 max-w-sm">
                The authoritative Chromium instance automatically streams viewport captures upon navigation and interactions.
              </p>
            </div>
          </div>
        )}

        {/* Live Action Overlay Banner */}
        {currentAction && isRunning && (
          <div className="absolute top-4 left-4 right-4 z-10 flex items-center justify-between p-3 rounded-xl bg-slate-950/85 backdrop-blur-md border border-cyan-500/40 text-xs shadow-xl animate-in fade-in slide-in-from-top-2">
            <div className="flex items-center space-x-2.5">
              <Crosshair className="h-4 w-4 text-cyan-400 animate-spin" />
              <div>
                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider block">
                  Agent Executing Action
                </span>
                <span className="text-white font-mono font-medium truncate">{currentAction}</span>
              </div>
            </div>

            <div className="flex items-center space-x-2 font-mono text-[10px] text-slate-400">
              <span>Seq #{latestEventSequence}</span>
            </div>
          </div>
        )}
      </div>

      {/* Footer Info Strip */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-950/90 border-t border-slate-800/80 text-[11px] font-mono text-slate-400">
        <div className="flex items-center space-x-3">
          <span className="flex items-center space-x-1">
            <span className="text-slate-500">Session:</span>
            <span className="text-slate-300 font-bold">{sessionId}</span>
          </span>
          <span className="text-slate-700">|</span>
          <span className="text-slate-500">Viewport: Headless Chromium (Hardware-Accelerated)</span>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-slate-500">Authoritative Runner:</span>
          <span className="text-indigo-400 font-bold">Playwright Engine</span>
        </div>
      </div>
    </div>
  );
};
