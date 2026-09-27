'use client';

import React, { useState } from 'react';
import { 
  Activity, 
  ShieldCheck, 
  GitPullRequest, 
  TrendingUp, 
  CheckCircle2, 
  Clock, 
  Layers, 
  Cpu, 
  Radio, 
  Zap, 
  Bot, 
  Database,
  Search
} from 'lucide-react';

export const ArchitectureExplorer: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'all' | 'test' | 'readiness' | 'feedback' | 'predictive'>('all');

  const pillars = [
    {
      id: 'test',
      title: 'A. Test My App',
      tagline: 'Autonomous multi-mode software & AI application tester',
      status: 'Vertical Slice 1 Active (Mock Engine) · Playwright Ready',
      statusColor: 'emerald',
      icon: Activity,
      color: 'from-cyan-500/20 to-indigo-500/10 border-cyan-500/30',
      accentColor: 'text-cyan-400',
      items: [
        { name: '1. Functional QA', desc: 'Deterministic user workflows, form inputs, button clicks & assertion validation.', active: true },
        { name: '2. Exploratory Dogfooding', desc: 'Autonomous discovery of unhandled edge cases, 404s, and dead links.', active: true },
        { name: '3. UX/UI Review', desc: 'WCAG 2.1 AA accessibility audit, responsive visual viewport validation.', active: true },
        { name: '4. AI/LLM Evaluation', desc: 'Grounding verification, hallucination detection, prompt injection defense.', active: true },
        { name: '5. Regression QA', desc: 'Continuous golden path regression benchmarks to safeguard critical flows.', active: true },
      ],
    },
    {
      id: 'readiness',
      title: 'B. Production Readiness Assessment',
      tagline: '9-dimensional production readiness audit & tool orchestration',
      status: 'Typed Domain Contracts & Tool Adapters (k6, OTel, ZAP)',
      statusColor: 'indigo',
      icon: ShieldCheck,
      color: 'from-indigo-500/20 to-purple-500/10 border-indigo-500/30',
      accentColor: 'text-indigo-400',
      items: [
        { name: '1. Reliability', desc: 'SLA uptime compliance, error budgets, and MTTR simulation.', active: true },
        { name: '2. Performance', desc: 'Latency distributions, p95/p99 TTFB, and Core Web Vitals.', active: true },
        { name: '3. Load / Capacity', desc: 'k6 load testing adapter with VU ramp-up simulation.', active: true },
        { name: '4. Failure Recovery', desc: 'Chaos engineering / Litmus fault injection & circuit breaker recovery.', active: true },
        { name: '5. Security', desc: 'OWASP ZAP baseline and active fuzzing vulnerability scans.', active: true },
        { name: '6. Resource Behavior', desc: 'Memory leak detection, CPU saturation, and heap stability.', active: true },
        { name: '7. Observability', desc: 'OpenTelemetry trace context propagation and Prometheus metrics.', active: true },
        { name: '8. AI Reliability', desc: 'Copilot hallucination rate, context window limits, and token cost curves.', active: true },
        { name: '9. Maintainability', desc: 'Codebase modularity, typed contract strictness, and cyclomatic complexity.', active: true },
      ],
    },
    {
      id: 'feedback',
      title: 'C. Engineering Feedback Loop',
      tagline: 'Automated failure diagnosis & coding agent fix packages',
      status: 'Slice 5 Active · Coding Agent (Qwen2.5-Coder) & Closed-Loop Regression QA',
      statusColor: 'emerald',
      icon: GitPullRequest,
      color: 'from-purple-500/20 to-pink-500/10 border-purple-500/30',
      accentColor: 'text-purple-400',
      items: [
        { name: '1. Detect', desc: 'Autonomous QA agent flags assertion failures, latency spikes or crashes.', active: true },
        { name: '2. Collect Evidence', desc: 'Captures DOM snapshots, network HAR, console logs, and visual frames.', active: true },
        { name: '3. Diagnose', desc: 'Root cause hypothesis engine categorizes failure and Pinpoints subsystem.', active: true },
        { name: '4. Engineering Feedback', desc: 'Formats structured diagnostic report with stack traces and log correlation.', active: true },
        { name: '5. Fix Package', desc: 'Generates structured remediation patch spec for Coding Agents (Qwen2.5-Coder).', active: true },
        { name: '6. Re-test & Verify', desc: 'Dispatches targeted re-test against patched branch to confirm resolution.', active: true },
      ],
    },
    {
      id: 'predictive',
      title: 'D. Predictive Reliability',
      tagline: 'Historical telemetry for predictive regression & failure risk ML',
      status: 'Telemetry Schema & Feature Extraction Pipeline Defined',
      statusColor: 'cyan',
      icon: TrendingUp,
      color: 'from-cyan-500/20 to-blue-500/10 border-cyan-500/30',
      accentColor: 'text-cyan-400',
      items: [
        { name: '1. Raw Telemetry', desc: 'Continuous ingestion of execution timings, DOM changes, and error signals.', active: true },
        { name: '2. Feature Engineering', desc: 'Action duration variance, failure frequency, and DOM complexity vectors.', active: true },
        { name: '3. Failure-Risk ML', desc: 'Predicts high-risk endpoints before production deployment.', active: true },
        { name: '4. Test Prioritization', desc: 'Intelligently orders test suites to run highest risk scenarios first.', active: true },
      ],
    },
  ];

  const filteredPillars = activeTab === 'all' 
    ? pillars 
    : pillars.filter(p => p.id === activeTab);

  return (
    <div className="space-y-6">
      {/* Pillar Filter Tabs */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-2">
        <button
          onClick={() => setActiveTab('all')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
            activeTab === 'all'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          All 4 Pillars (Overview)
        </button>
        <button
          onClick={() => setActiveTab('test')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
            activeTab === 'test'
              ? 'bg-cyan-600 text-white shadow-sm'
              : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          Pillar A: Test My App
        </button>
        <button
          onClick={() => setActiveTab('readiness')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
            activeTab === 'readiness'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          Pillar B: Readiness Assessment
        </button>
        <button
          onClick={() => setActiveTab('feedback')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
            activeTab === 'feedback'
              ? 'bg-purple-600 text-white shadow-sm'
              : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          Pillar C: Feedback Loop
        </button>
        <button
          onClick={() => setActiveTab('predictive')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
            activeTab === 'predictive'
              ? 'bg-cyan-600 text-white shadow-sm'
              : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          Pillar D: Predictive ML
        </button>
      </div>

      {/* Pillars Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {filteredPillars.map(pillar => {
          const Icon = pillar.icon;
          return (
            <div
              key={pillar.id}
              className={`rounded-2xl border bg-gradient-to-br ${pillar.color} bg-[#0b1120] p-6 shadow-xl space-y-4`}
            >
              {/* Header */}
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 ${pillar.accentColor}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white tracking-tight">
                      {pillar.title}
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {pillar.tagline}
                    </p>
                  </div>
                </div>
              </div>

              {/* Status Ribbon */}
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-[11px] font-mono text-slate-300">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                <span>{pillar.status}</span>
              </div>

              {/* Sub-items List */}
              <div className="space-y-2 pt-2">
                {pillar.items.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/60 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-200">
                        {item.name}
                      </span>
                      <span className="text-[10px] font-mono text-indigo-400 px-1.5 py-0.5 rounded bg-indigo-500/10">
                        READY
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                      {item.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
