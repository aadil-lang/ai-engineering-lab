'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { AppShell } from '@/components/AppShell';
import { MetricCards } from '@/components/MetricCards';
import { RunHistoryTable } from '@/components/RunHistoryTable';
import { QuickLaunchModal } from '@/components/QuickLaunchModal';
import { TestRun, TestMode, RunStatus } from '@/types';
import { api, governanceApi } from '@/lib/api';
import { 
  Play, 
  RefreshCw, 
  Search, 
  Filter, 
  ShieldCheck, 
  Cpu, 
  Activity,
  Layers,
  Sparkles,
  ArrowRight,
  UserCheck,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

export default function DashboardPage() {
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedModeFilter, setSelectedModeFilter] = useState<string>('');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>('');
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);

  const loadRuns = async () => {
    setIsLoading(true);
    try {
      const [data, approvalReqs] = await Promise.all([
        api.getRuns({
          test_mode: selectedModeFilter || undefined,
          status: selectedStatusFilter || undefined,
        }),
        governanceApi.getApprovalRequests('PENDING').catch(() => []),
      ]);
      setRuns(data.items || []);
      setTotalCount(data.total || 0);
      setPendingApprovalsCount(approvalReqs.length || 0);
    } catch (err) {
      console.error('Failed to load runs:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, [selectedModeFilter, selectedStatusFilter]);

  // Client-side search filtering
  const filteredRuns = runs.filter(r => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      r.run_id.toLowerCase().includes(q) ||
      r.application_id.toLowerCase().includes(q) ||
      r.test_mode.toLowerCase().includes(q)
    );
  });

  return (
    <AppShell onOpenLaunchModal={() => setIsModalOpen(true)}>
      <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Active Application Target Status Banner */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 font-mono text-xs">
          <div className="flex items-center space-x-3">
            <div className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
            <div>
              <span className="text-slate-400 uppercase text-[10px] block">Current Verification Target</span>
              <span className="text-white font-bold text-sm">Question Generator (Local Real App)</span>
            </div>
            <span className="text-slate-500 hidden sm:inline">|</span>
            <span className="text-slate-400 hidden sm:inline">Target ID: <code className="text-cyan-300">real_question_generator_local</code></span>
          </div>

          <div className="flex items-center space-x-3">
            {pendingApprovalsCount > 0 && (
              <Link
                href="/governance"
                className="px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/30 hover:bg-amber-500/20 transition-all flex items-center space-x-1.5 font-semibold"
              >
                <UserCheck className="h-3.5 w-3.5 text-amber-400" />
                <span>{pendingApprovalsCount} Pending Governance Review</span>
              </Link>
            )}
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all flex items-center space-x-1.5"
            >
              <Play className="h-3.5 w-3.5 fill-white" />
              <span>Test My App</span>
            </button>
          </div>
        </div>
        {/* Top Hero / Mission Control Banner */}
        <div className="relative overflow-hidden rounded-2xl border border-indigo-500/20 bg-gradient-to-r from-slate-950 via-[#0d162a] to-slate-950 p-6 sm:p-8 shadow-2xl">
          <div className="absolute top-0 right-0 -mt-12 -mr-12 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-1/3 -mb-12 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2 max-w-2xl">
              <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-mono">
                <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                <span>Autonomous Reliability & Diagnostic Slice v1</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight font-sans">
                AI Application Reliability & Predictive QA Platform
              </h1>
              <p className="text-sm text-slate-300 leading-relaxed font-sans">
                Autonomous test execution, structured multi-modal evidence collection, failure diagnosis, engineering remediation packages, and telemetry-driven reliability assessment.
              </p>
            </div>

            <div className="flex items-center space-x-3 flex-shrink-0">
              <button
                onClick={() => setIsModalOpen(true)}
                className="flex items-center space-x-2 px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-[0_0_25px_rgba(99,102,241,0.4)] transition-all active:scale-95"
              >
                <Play className="h-4 w-4 fill-white" />
                <span>Launch New Run</span>
              </button>
            </div>
          </div>
        </div>

        {/* Metric Cards Ribbon */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
              Execution Telemetry Overview
            </h2>
            <button
              onClick={loadRuns}
              className="flex items-center space-x-1 text-xs text-slate-400 hover:text-white transition-colors"
            >
              <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
          <MetricCards runs={runs} />
        </section>

        {/* Filter & Run History Section */}
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-2">
              <Activity className="h-4 w-4 text-indigo-400" />
              <h2 className="text-sm font-bold text-white tracking-tight uppercase font-mono">
                Autonomous Test Runs ({filteredRuns.length})
              </h2>
            </div>

            {/* Filter controls */}
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="Filter by Run ID / App..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-48 sm:w-56"
                />
              </div>

              {/* Mode filter */}
              <select
                value={selectedModeFilter}
                onChange={e => setSelectedModeFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="">All 5 Modes</option>
                <option value="FUNCTIONAL_QA">Functional QA</option>
                <option value="EXPLORATORY_DOGFOODING">Exploratory Dogfooding</option>
                <option value="UX_UI_REVIEW">UX/UI Review</option>
                <option value="AI_LLM_EVALUATION">AI/LLM Evaluation</option>
                <option value="REGRESSION_QA">Regression QA</option>
              </select>

              {/* Status filter */}
              <select
                value={selectedStatusFilter}
                onChange={e => setSelectedStatusFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Statuses</option>
                <option value="PASSED">Passed</option>
                <option value="FAILED">Failed</option>
                <option value="RUNNING">Running</option>
              </select>
            </div>
          </div>

          {/* History Table */}
          <RunHistoryTable runs={filteredRuns} isLoading={isLoading} />
        </section>
      </div>

      {/* Quick Launch Modal */}
      <QuickLaunchModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onRunCreated={() => loadRuns()}
      />
    </AppShell>
  );
}
