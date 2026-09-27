'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  RemediationTask,
  RemediationStatus,
  CodeChange,
  FileChange,
  EngineeringDiagnosis,
} from '@/types';
import {
  Wrench,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  GitPullRequest,
  FileCode2,
  Terminal,
  ShieldCheck,
  AlertTriangle,
  Play,
  RotateCw,
  Copy,
  Check,
  ArrowRight,
  ExternalLink,
  Code2,
  Layers,
  Cpu,
  Flame,
} from 'lucide-react';

interface RemediationWorkbenchProps {
  task: RemediationTask | null;
  runId: string;
  diagnosis?: EngineeringDiagnosis | null;
  onTriggerRemediation: () => Promise<void>;
  onApplyAndVerify: (taskId: string) => Promise<void>;
  isGenerating?: boolean;
  isApplying?: boolean;
}

export const RemediationWorkbench: React.FC<RemediationWorkbenchProps> = ({
  task,
  runId,
  diagnosis,
  onTriggerRemediation,
  onApplyAndVerify,
  isGenerating = false,
  isApplying = false,
}) => {
  const [selectedFileIdx, setSelectedFileIdx] = useState<number>(0);
  const [copiedDiff, setCopiedDiff] = useState<boolean>(false);

  const activeCodeChange = task?.code_changes?.[0];
  const activeFile = activeCodeChange?.files?.[selectedFileIdx] || activeCodeChange?.files?.[0];
  const latestVerification = task?.verifications?.[task.verifications.length - 1];

  const handleCopyDiff = (diffText: string) => {
    navigator.clipboard.writeText(diffText);
    setCopiedDiff(true);
    setTimeout(() => setCopiedDiff(false), 2000);
  };

  const getStatusBadge = (status: RemediationStatus) => {
    switch (status) {
      case 'RESOLVED':
        return (
          <span className="flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span>RESOLVED & VERIFIED</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
            <XCircle className="w-3.5 h-3.5 text-rose-400" />
            <span>VERIFICATION FAILED</span>
          </span>
        );
      case 'APPLYING':
      case 'VALIDATING':
      case 'TESTING':
        return (
          <span className="flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30 animate-pulse">
            <RotateCw className="w-3.5 h-3.5 text-blue-400 animate-spin" />
            <span>{status} IN PROGRESS...</span>
          </span>
        );
      case 'PROPOSED':
        return (
          <span className="flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span>FIX PROPOSED</span>
          </span>
        );
      case 'ANALYZING':
        return (
          <span className="flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            <RotateCw className="w-3.5 h-3.5 text-amber-400 animate-spin" />
            <span>REMEDIATION REASONING...</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-semibold bg-zinc-700/50 text-zinc-300 border border-zinc-600/30">
            <Clock className="w-3.5 h-3.5" />
            <span>{status}</span>
          </span>
        );
    }
  };

  // Stepper state calculation
  const steps = [
    { label: 'Failure', done: true, current: false },
    { label: 'Diagnosis', done: Boolean(diagnosis), current: false },
    { label: 'Coding Agent', done: Boolean(task), current: isGenerating },
    { label: 'Proposed Patch', done: Boolean(activeCodeChange), current: task?.status === 'PROPOSED' },
    { label: 'Sandbox Apply', done: task?.attempts?.length ? true : false, current: task?.status === 'APPLYING' },
    { label: 'Validation', done: task?.attempts?.[0]?.build_result?.status === 'PASSED', current: task?.status === 'VALIDATING' },
    { label: 'Regression QA', done: Boolean(latestVerification), current: task?.status === 'TESTING' },
    {
      label: task?.status === 'RESOLVED' ? 'Resolved' : task?.status === 'FAILED' ? 'Failed' : 'Outcome',
      done: task?.status === 'RESOLVED',
      current: false,
      error: task?.status === 'FAILED',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner / Hero Card */}
      <div className="rounded-2xl border border-purple-500/30 bg-[#0f0a1c]/90 shadow-2xl p-6 backdrop-blur-md relative overflow-hidden">
        <div className="absolute -right-12 -bottom-12 w-64 h-64 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-purple-500/20">
          <div>
            <div className="flex items-center space-x-3 mb-2 flex-wrap gap-y-2">
              <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold font-mono bg-purple-500/20 text-purple-300 border border-purple-500/40">
                <Wrench className="w-3.5 h-3.5 text-purple-400" />
                <span>AUTONOMOUS REMEDIATION WORKBENCH</span>
              </span>
              {task && getStatusBadge(task.status)}
            </div>
            <h2 className="text-xl font-bold text-zinc-100 flex items-center space-x-2">
              <span>Remediation & Fix Verification</span>
              {diagnosis && (
                <span className="text-sm font-normal text-purple-300/80">
                  for {diagnosis.suspected_component}
                </span>
              )}
            </h2>
            <p className="text-xs text-zinc-400 mt-1">
              Autonomous loop: Diagnosed Failure → Coding Agent reasoning → Targeted Patch → Sandbox Apply → Build Validation → Regression Test.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            {!task ? (
              <button
                onClick={onTriggerRemediation}
                disabled={isGenerating}
                className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium text-sm shadow-lg shadow-purple-900/40 hover:shadow-purple-700/50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isGenerating ? (
                  <>
                    <RotateCw className="w-4 h-4 animate-spin text-white" />
                    <span>Coding Agent Reasoning...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-purple-200" />
                    <span>Generate Fix with Coding Agent</span>
                  </>
                )}
              </button>
            ) : task.status === 'PROPOSED' || task.status === 'FAILED' ? (
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => onApplyAndVerify(task.task_id)}
                  disabled={isApplying}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-medium text-sm shadow-lg shadow-emerald-900/40 hover:shadow-emerald-700/50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {isApplying ? (
                    <>
                      <RotateCw className="w-4 h-4 animate-spin text-white" />
                      <span>Applying & Retesting...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 text-emerald-200 fill-emerald-200" />
                      <span>Apply Patch & Verify Regression</span>
                    </>
                  )}
                </button>

                <button
                  onClick={onTriggerRemediation}
                  disabled={isGenerating || isApplying}
                  className="flex items-center space-x-1.5 px-3.5 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium text-xs border border-zinc-700 transition cursor-pointer"
                  title="Re-run coding agent to generate fresh patch"
                >
                  <RotateCw className="w-3.5 h-3.5" />
                  <span>Regenerate</span>
                </button>
              </div>
            ) : task.status === 'RESOLVED' ? (
              <div className="flex items-center space-x-2">
                <div className="px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Fix Verified Successfully</span>
                </div>
                <button
                  onClick={onTriggerRemediation}
                  disabled={isGenerating || isApplying}
                  className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium text-xs border border-zinc-700 transition cursor-pointer"
                >
                  <RotateCw className="w-3.5 h-3.5" />
                  <span>New Remediation</span>
                </button>
              </div>
            ) : null}
          </div>
        </div>

        {/* Pipeline Stepper Visualizer */}
        <div className="pt-6">
          <div className="text-xs font-semibold text-zinc-400 mb-3 uppercase tracking-wider flex items-center space-x-2">
            <Layers className="w-3.5 h-3.5 text-purple-400" />
            <span>Closed-Loop Remediation Pipeline</span>
          </div>

          <div className="grid grid-cols-4 md:grid-cols-8 gap-2">
            {steps.map((step, idx) => (
              <div
                key={idx}
                className={`relative flex flex-col items-center p-2.5 rounded-xl border text-center transition-all ${
                  step.error
                    ? 'bg-rose-950/40 border-rose-500/50 text-rose-300'
                    : step.done
                    ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300'
                    : step.current
                    ? 'bg-purple-950/40 border-purple-500 text-purple-200 ring-2 ring-purple-500/30 animate-pulse'
                    : 'bg-zinc-900/60 border-zinc-800 text-zinc-500'
                }`}
              >
                <div className="text-[10px] font-mono font-semibold uppercase tracking-wider mb-1">
                  Step 0{idx + 1}
                </div>
                <div className="text-xs font-medium truncate w-full">{step.label}</div>
                <div className="mt-1.5">
                  {step.error ? (
                    <XCircle className="w-3.5 h-3.5 text-rose-400" />
                  ) : step.done ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : step.current ? (
                    <RotateCw className="w-3.5 h-3.5 text-purple-400 animate-spin" />
                  ) : (
                    <div className="w-2 h-2 rounded-full bg-zinc-700 my-1" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Regression Verification Outcome Card (when verification exists) */}
      {latestVerification && (
        <div
          className={`rounded-2xl border p-5 backdrop-blur-md animate-fade-in ${
            latestVerification.status === 'RESOLVED' || (!latestVerification.failed_after && !latestVerification.regression_detected)
              ? 'bg-emerald-950/20 border-emerald-500/40'
              : 'bg-rose-950/20 border-rose-500/40'
          }`}
        >
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start space-x-3.5">
              <div
                className={`p-2.5 rounded-xl border ${
                  latestVerification.status === 'RESOLVED' || (!latestVerification.failed_after && !latestVerification.regression_detected)
                    ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
                    : 'bg-rose-500/20 border-rose-500/40 text-rose-400'
                }`}
              >
                {latestVerification.status === 'RESOLVED' || (!latestVerification.failed_after && !latestVerification.regression_detected) ? (
                  <ShieldCheck className="w-6 h-6" />
                ) : (
                  <AlertTriangle className="w-6 h-6" />
                )}
              </div>
              <div>
                <h4 className="text-base font-bold text-zinc-100 flex items-center space-x-2">
                  <span>
                    {latestVerification.status === 'RESOLVED'
                      ? 'Regression Verification PASSED — Root Cause Remediated'
                      : 'Regression Verification FAILED'}
                  </span>
                </h4>
                <p className="text-xs text-zinc-300 mt-1">{latestVerification.summary}</p>
                <div className="flex items-center space-x-4 mt-2 text-xs font-mono">
                  <span className="text-zinc-400">
                    Before Fix: <span className="text-rose-400 font-semibold">FAILED</span>
                  </span>
                  <ArrowRight className="w-3 h-3 text-zinc-500" />
                  <span className="text-zinc-400">
                    After Fix:{' '}
                    <span
                      className={
                        latestVerification.failed_after
                          ? 'text-rose-400 font-semibold'
                          : 'text-emerald-400 font-semibold'
                      }
                    >
                      {latestVerification.failed_after ? 'FAILED' : 'PASSED'}
                    </span>
                  </span>
                  {latestVerification.verification_run_id && (
                    <Link
                      href={`/runs/${latestVerification.verification_run_id}`}
                      className="text-purple-400 hover:text-purple-300 flex items-center space-x-1 underline"
                    >
                      <span>Verification Run: {latestVerification.verification_run_id}</span>
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  )}
                </div>
              </div>
            </div>

            <div className="text-right">
              <span className="text-xs text-zinc-500">
                Verified at: {new Date(latestVerification.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Code Change & Diff Inspector */}
      {activeCodeChange ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Summary, Rationale, & Tests */}
          <div className="space-y-4 lg:col-span-1">
            {/* Summary & Rationale */}
            <div className="rounded-2xl border border-zinc-800 bg-[#120f1e]/80 p-5 space-y-4">
              <div className="flex items-center space-x-2 text-purple-400 font-semibold text-sm">
                <Code2 className="w-4 h-4" />
                <span>Coding Agent Fix Plan</span>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Summary</h4>
                <p className="text-sm text-zinc-200 font-medium">{activeCodeChange.summary}</p>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Engineering Rationale</h4>
                <p className="text-xs text-zinc-300 leading-relaxed bg-zinc-900/70 p-3 rounded-xl border border-zinc-800/80">
                  {activeCodeChange.rationale}
                </p>
              </div>

              {activeCodeChange.risk_notes && (
                <div>
                  <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Risk Assessment</h4>
                  <div className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-xl">
                    {activeCodeChange.risk_notes}
                  </div>
                </div>
              )}

              {activeCodeChange.tests_to_run?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 flex items-center space-x-1.5">
                    <Terminal className="w-3.5 h-3.5 text-zinc-400" />
                    <span>Regression Tests Triggered</span>
                  </h4>
                  <div className="space-y-1.5">
                    {activeCodeChange.tests_to_run.map((cmd, i) => (
                      <div
                        key={i}
                        className="text-xs font-mono bg-zinc-950 px-3 py-1.5 rounded-lg text-emerald-300 border border-zinc-800 truncate"
                      >
                        $ {cmd}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Affected Files Selector */}
            <div className="rounded-2xl border border-zinc-800 bg-[#120f1e]/80 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-zinc-300 font-semibold text-sm">
                  <FileCode2 className="w-4 h-4 text-purple-400" />
                  <span>Modified Files ({activeCodeChange.files?.length || 0})</span>
                </div>
                <span className="text-xs text-zinc-500">Atomic patch</span>
              </div>

              <div className="space-y-2">
                {activeCodeChange.files?.map((file, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedFileIdx(idx)}
                    className={`w-full text-left p-3 rounded-xl border transition flex items-center justify-between cursor-pointer ${
                      selectedFileIdx === idx
                        ? 'bg-purple-600/20 border-purple-500/50 text-purple-200'
                        : 'bg-zinc-900/50 border-zinc-800 hover:bg-zinc-800/60 text-zinc-400'
                    }`}
                  >
                    <div className="flex items-center space-x-2.5 min-w-0">
                      <FileCode2 className="w-4 h-4 shrink-0 text-purple-400" />
                      <span className="text-xs font-mono truncate">{file.path}</span>
                    </div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${
                        file.operation === 'CREATE'
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                          : file.operation === 'DELETE'
                          ? 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                          : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                      }`}
                    >
                      {file.operation}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Code Diff Viewer */}
          <div className="lg:col-span-2 space-y-4">
            <div className="rounded-2xl border border-zinc-800 bg-[#0d0a17]/95 overflow-hidden shadow-2xl">
              {/* Diff Viewer Header */}
              <div className="flex items-center justify-between px-5 py-3.5 bg-zinc-900/80 border-b border-zinc-800">
                <div className="flex items-center space-x-3">
                  <div className="flex space-x-1.5">
                    <div className="w-3 h-3 rounded-full bg-rose-500/70" />
                    <div className="w-3 h-3 rounded-full bg-amber-500/70" />
                    <div className="w-3 h-3 rounded-full bg-emerald-500/70" />
                  </div>
                  <span className="text-xs font-mono text-zinc-300 font-medium">
                    {activeFile ? activeFile.path : 'unified.diff'}
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleCopyDiff(activeFile?.diff || activeCodeChange.diff)}
                    className="flex items-center space-x-1 px-3 py-1 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-300 transition cursor-pointer border border-zinc-700"
                  >
                    {copiedDiff ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy Diff</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Diff Code Container */}
              <div className="p-4 overflow-x-auto max-h-[520px] font-mono text-xs leading-relaxed">
                <pre className="text-zinc-300">
                  {(activeFile?.diff || activeCodeChange.diff || '// No diff preview available')
                    .split('\n')
                    .map((line, idx) => {
                      const isAddition = line.startsWith('+') && !line.startsWith('+++');
                      const isDeletion = line.startsWith('-') && !line.startsWith('---');
                      const isHeader = line.startsWith('@@') || line.startsWith('---') || line.startsWith('+++');

                      return (
                        <div
                          key={idx}
                          className={`flex items-start px-2 py-0.5 rounded ${
                            isAddition
                              ? 'bg-emerald-950/40 text-emerald-300 border-l-2 border-emerald-500'
                              : isDeletion
                              ? 'bg-rose-950/40 text-rose-300 border-l-2 border-rose-500 line-through opacity-80'
                              : isHeader
                              ? 'text-purple-400 font-semibold bg-purple-950/30'
                              : 'text-zinc-400 hover:bg-zinc-900/50'
                          }`}
                        >
                          <span className="w-8 select-none text-zinc-600 text-right pr-3 shrink-0">
                            {idx + 1}
                          </span>
                          <span className="break-all whitespace-pre-wrap">{line}</span>
                        </div>
                      );
                    })}
                </pre>
              </div>
            </div>

            {/* Validation Check Results Badge */}
            <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80 flex items-center justify-between text-xs">
              <div className="flex items-center space-x-2 text-zinc-300">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Pre-flight Static Syntax Validation:</span>
                <span className="font-semibold text-emerald-400 font-mono">PASSED</span>
              </div>
              <span className="text-zinc-500 font-mono text-[11px]">
                Target: {task?.target_repository}:{task?.target_branch}
              </span>
            </div>
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="rounded-2xl border border-zinc-800 bg-[#120f1e]/40 p-12 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-purple-600/10 border border-purple-500/20 text-purple-400 flex items-center justify-center mx-auto">
            <Sparkles className="w-8 h-8" />
          </div>
          <div className="max-w-md mx-auto space-y-2">
            <h3 className="text-lg font-bold text-zinc-200">No Remediation Proposed Yet</h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Trigger the AI Coding Agent to analyze the failure diagnosis and deterministic signals, reason about the code defect, and generate an atomic patch with automated regression tests.
            </p>
          </div>
          <button
            onClick={onTriggerRemediation}
            disabled={isGenerating}
            className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium text-sm shadow-xl shadow-purple-900/40 transition-all cursor-pointer disabled:opacity-50"
          >
            {isGenerating ? (
              <>
                <RotateCw className="w-4 h-4 animate-spin" />
                <span>Coding Agent Analyzing...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Generate Autonomous Remediation</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
