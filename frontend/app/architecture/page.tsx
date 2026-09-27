'use client';

import React, { useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { ArchitectureExplorer } from '@/components/ArchitectureExplorer';
import { QuickLaunchModal } from '@/components/QuickLaunchModal';
import { 
  Layers, 
  ShieldCheck, 
  Cpu, 
  Database, 
  GitBranch, 
  Play, 
  CheckCircle2, 
  Sparkles 
} from 'lucide-react';

export default function ArchitecturePage() {
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  return (
    <div className="flex-1 flex flex-col">
      <Navbar onOpenLaunchModal={() => setIsModalOpen(true)} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Header */}
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-mono">
            <Layers className="h-3.5 w-3.5 text-cyan-400" />
            <span>High-Level Product Architecture</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight font-sans">
            The 4 Platform Capabilities & Roadmap
          </h1>
          <p className="text-sm text-slate-300 max-w-3xl leading-relaxed font-sans">
            Built following modular, typed vertical slice engineering. Day-1 delivers a complete, local-first vertical slice (Frontend → FastAPI → Run Manager → Mock Test Runner → Structured Evidence & Telemetry → SQLite Persistence → Visual Results UI).
          </p>
        </div>

        {/* 4 Pillars Interactive Explorer */}
        <ArchitectureExplorer />

        {/* Integration Interfaces & Adapters Grid */}
        <section className="rounded-2xl border border-surface-border bg-[#0b1120] p-6 space-y-5 shadow-xl">
          <div className="flex items-center space-x-2">
            <Cpu className="h-5 w-5 text-indigo-400" />
            <h2 className="text-base font-bold text-white tracking-tight">
              Future Tool Adapters & Reasoning Contracts
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
              <div className="font-bold text-cyan-400 font-mono flex items-center space-x-1.5">
                <CheckCircle2 className="h-4 w-4" />
                <span>k6 Load & Capacity Adapter</span>
              </div>
              <p className="text-slate-400 leading-relaxed font-sans">
                Interface defined in <code>backend/app/assessment/base_assessor.py</code> for programmatic scenario execution, virtual user ramp-up, and latency profiling.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
              <div className="font-bold text-emerald-400 font-mono flex items-center space-x-1.5">
                <CheckCircle2 className="h-4 w-4" />
                <span>OpenTelemetry & Prometheus</span>
              </div>
              <p className="text-slate-400 leading-relaxed font-sans">
                Interface defined in <code>backend/app/telemetry/telemetry_collector.py</code> for span ingestion, W3C trace-context tracking, and Prometheus metric aggregations.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
              <div className="font-bold text-purple-400 font-mono flex items-center space-x-1.5">
                <CheckCircle2 className="h-4 w-4" />
                <span>Qwen2.5-Coder via Ollama</span>
              </div>
              <p className="text-slate-400 leading-relaxed font-sans">
                Interface defined in <code>backend/app/agents/base_agent.py</code>. LLM acts as a modular reasoning engine for diagnostic synthesis and fix packages.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Quick Launch Modal */}
      <QuickLaunchModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
