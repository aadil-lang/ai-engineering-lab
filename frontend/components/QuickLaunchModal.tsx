'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  X, 
  Play, 
  Sparkles, 
  Layers, 
  Sliders, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  Loader2 
} from 'lucide-react';
import { ApplicationTarget, TestCase, TestMode, TestRunCreate, RunnerType } from '@/types';
import { api } from '@/lib/api';

interface QuickLaunchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunCreated?: (runId: string) => void;
}

const TEST_MODES: { id: TestMode; name: string; desc: string; icon: string }[] = [
  {
    id: 'FUNCTIONAL_QA',
    name: 'Functional QA',
    desc: 'Deterministic workflow execution and strict schema assertion verification.',
    icon: '⚡',
  },
  {
    id: 'EXPLORATORY_DOGFOODING',
    name: 'Exploratory Dogfooding',
    desc: 'Autonomous exploration detecting UI glitches, broken hyperlinks, and edge-cases.',
    icon: '🧭',
  },
  {
    id: 'UX_UI_REVIEW',
    name: 'UX/UI Review',
    desc: 'WCAG AA accessibility audit, responsive visual consistency, and design tokens.',
    icon: '🎨',
  },
  {
    id: 'AI_LLM_EVALUATION',
    name: 'AI/LLM Evaluation',
    desc: 'Grounding verification, hallucination detection, and prompt injection resilience.',
    icon: '🧠',
  },
  {
    id: 'REGRESSION_QA',
    name: 'Regression QA',
    desc: 'Continuous regression validation against golden baseline telemetry benchmarks.',
    icon: '🔁',
  },
];

export const QuickLaunchModal: React.FC<QuickLaunchModalProps> = ({
  isOpen,
  onClose,
  onRunCreated,
}) => {
  const router = useRouter();
  const [targets, setTargets] = useState<ApplicationTarget[]>([]);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [selectedTargetId, setSelectedTargetId] = useState<string>('');
  const [selectedMode, setSelectedMode] = useState<TestMode>('FUNCTIONAL_QA');
  const [runnerType, setRunnerType] = useState<RunnerType>('AI_AGENT');
  const [targetUrlOverride, setTargetUrlOverride] = useState<string>('');
  const [naturalLanguageGoal, setNaturalLanguageGoal] = useState<string>('');
  const [maxAgentSteps, setMaxAgentSteps] = useState<number>(8);
  const [selectedTestCaseId, setSelectedTestCaseId] = useState<string>('');
  const [simulateFailure, setSimulateFailure] = useState<boolean>(false);
  const [actionDelay, setActionDelay] = useState<number>(100);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      const loadData = async () => {
        try {
          const [targetsData, casesData] = await Promise.all([
            api.getTargets(),
            api.getTestCases(),
          ]);
          setTargets(targetsData);
          if (targetsData.length > 0 && !selectedTargetId) {
            setSelectedTargetId(targetsData[0].target_id);
          }
          setTestCases(casesData);
        } catch (err: any) {
          setErrorMsg('Failed to load targets or test cases from backend');
        }
      };
      loadData();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const filteredCases = testCases.filter(
    c => c.test_mode === selectedMode
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const payload: TestRunCreate = {
        application_id: selectedTargetId || (targets[0]?.target_id ?? 'tgt_demo_shop'),
        test_mode: selectedMode,
        runner_type: runnerType,
        test_case_id: selectedTestCaseId || undefined,
        target_url_override: targetUrlOverride.trim() || undefined,
        natural_language_goal: naturalLanguageGoal.trim() || undefined,
        max_agent_steps: maxAgentSteps,
        simulate_failure: simulateFailure,
        action_delay_ms: actionDelay,
      };

      const resultRun = await api.triggerRun(payload);
      setIsSubmitting(false);
      onClose();

      if (onRunCreated) {
        onRunCreated(resultRun.run_id);
      }
      router.push(`/runs/${resultRun.run_id}`);
    } catch (err: any) {
      setIsSubmitting(false);
      setErrorMsg(err.message || 'Failed to dispatch test run');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-surface-border bg-[#0b1120] p-6 shadow-2xl space-y-6 custom-scrollbar">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
              <Play className="h-5 w-5 fill-indigo-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                Launch Autonomous Test Run
              </h2>
              <p className="text-xs text-slate-400">
                Execute AI-driven or deterministic multi-step test runs with full evidence collection
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-500/30 text-xs text-rose-300">
            {errorMsg}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* 1. Execution Engine Selector */}
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-2 font-semibold">
              1. Execution Engine
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <button
                type="button"
                onClick={() => setRunnerType('AI_AGENT')}
                className={`p-3 rounded-xl text-left border transition-all ${
                  runnerType === 'AI_AGENT'
                    ? 'border-purple-500 bg-purple-950/40 shadow-[0_0_15px_rgba(168,85,247,0.2)]'
                    : 'border-slate-800 bg-slate-900/50 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <span className="text-sm">🤖</span>
                  <div className="font-bold text-xs text-white">AI Browser Agent</div>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Local Ollama (Qwen-2.5-Coder) ReAct loop driving Playwright browser.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setRunnerType('PLAYWRIGHT')}
                className={`p-3 rounded-xl text-left border transition-all ${
                  runnerType === 'PLAYWRIGHT'
                    ? 'border-emerald-500 bg-emerald-950/30 shadow-[0_0_15px_rgba(16,185,129,0.15)]'
                    : 'border-slate-800 bg-slate-900/50 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <span className="text-sm">🌐</span>
                  <div className="font-bold text-xs text-white">Playwright Engine</div>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Deterministic headless Chromium browser execution with telemetry.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setRunnerType('MOCK')}
                className={`p-3 rounded-xl text-left border transition-all ${
                  runnerType === 'MOCK'
                    ? 'border-indigo-500 bg-indigo-950/40 shadow-sm'
                    : 'border-slate-800 bg-slate-900/50 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <span className="text-sm">⚡</span>
                  <div className="font-bold text-xs text-white">Mock Engine</div>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Deterministic simulation for offline unit tests and baseline demos.
                </p>
              </button>
            </div>
          </div>

          {/* AI Agent Goal Input (if AI_AGENT selected) */}
          {runnerType === 'AI_AGENT' && (
            <div className="p-3.5 rounded-xl border border-purple-500/30 bg-purple-950/20 space-y-2.5 animate-fade-in">
              <div className="flex items-center justify-between">
                <label className="text-xs font-mono uppercase tracking-wider text-purple-300 font-semibold flex items-center space-x-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-purple-400" />
                  <span>Natural-Language Test Goal</span>
                </label>
                <div className="flex items-center space-x-2">
                  <span className="text-[11px] text-slate-400">Step Budget:</span>
                  <select
                    value={maxAgentSteps}
                    onChange={e => setMaxAgentSteps(Number(e.target.value))}
                    className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-xs text-purple-300 font-mono focus:outline-none"
                  >
                    <option value={5}>5 Steps</option>
                    <option value={8}>8 Steps</option>
                    <option value={12}>12 Steps</option>
                    <option value={15}>15 Steps</option>
                  </select>
                </div>
              </div>
              <textarea
                rows={2}
                placeholder="e.g., Navigate through the pages, test the interactive search and navigation buttons, and ensure no errors are thrown."
                value={naturalLanguageGoal}
                onChange={e => setNaturalLanguageGoal(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900/90 border border-purple-500/30 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500 font-sans"
              />
            </div>
          )}

          {/* 2. Target Selection & Custom URL */}
          <div className="space-y-2">
            <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
              2. Application Target
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {targets.map(target => {
                const isSelected = selectedTargetId === target.target_id && !targetUrlOverride;
                return (
                  <button
                    type="button"
                    key={target.target_id}
                    onClick={() => {
                      setSelectedTargetId(target.target_id);
                      setTargetUrlOverride('');
                    }}
                    className={`p-3 rounded-xl text-left border transition-all ${
                      isSelected
                        ? 'border-indigo-500 bg-indigo-950/40 shadow-sm'
                        : 'border-slate-800 bg-slate-900/50 hover:border-slate-700'
                    }`}
                  >
                    <div className="text-xs font-bold text-white truncate">{target.name}</div>
                    <div className="text-[11px] text-slate-400 font-mono mt-0.5">{target.environment} · {target.base_url}</div>
                  </button>
                );
              })}
            </div>

            {/* Custom URL Override Input */}
            <div className="pt-1">
              <input
                type="text"
                placeholder="Or enter custom URL to test (e.g. http://127.0.0.1:8000/docs or http://localhost:3000)"
                value={targetUrlOverride}
                onChange={e => setTargetUrlOverride(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900/80 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
          </div>

          {/* 3. Test Mode Picker */}
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-2 font-semibold">
              3. Autonomous Test Mode
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {TEST_MODES.map(mode => {
                const isSelected = selectedMode === mode.id;
                return (
                  <button
                    type="button"
                    key={mode.id}
                    onClick={() => setSelectedMode(mode.id)}
                    className={`p-3 rounded-xl text-left border transition-all ${
                      isSelected
                        ? 'border-cyan-500 bg-cyan-950/30 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                        : 'border-slate-800 bg-slate-900/50 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className="text-sm">{mode.icon}</span>
                      <span className="text-xs font-bold text-white">{mode.name}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                      {mode.desc}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 4. Execution Simulation Options */}
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-200">
                  Simulate Assertion Failure
                </span>
                <p className="text-[11px] text-slate-400">
                  Tests deterministic error classification (ASSERTION_FAILED / TIMEOUT) and failure evidence capture.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSimulateFailure(!simulateFailure)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  simulateFailure ? 'bg-rose-500' : 'bg-slate-800'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    simulateFailure ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Action Footer */}
          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center space-x-2 px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-lg shadow-indigo-500/25 transition-all disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Executing 5 Actions...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-white" />
                  <span>Execute Test Run</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
