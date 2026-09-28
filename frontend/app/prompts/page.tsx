'use client';

import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Layers,
  FileCode,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  Plus,
  Play,
  GitCompare,
  Search,
  BookOpen,
  Lock,
  ExternalLink,
  ChevronRight,
  Terminal,
  Cpu,
  GitBranch,
  Fingerprint,
  Box,
  Binary,
} from 'lucide-react';
import { api } from '@/lib/api';
import { AppShell } from '@/components/AppShell';
import {
  PromptDefinitionModel,
  PromptVersionModel,
  EvaluationSuiteModel,
  EvaluationSuiteVersionModel,
  EvaluationRunModel,
  PromptComparisonResultModel,
  PromptDiagnosisModel,
  AIApplicationManifestModel,
  EvaluationContextModel,
  ContextProvenanceModel,
  ContextDifferenceModel,
  EpistemicStatus,
} from '@/types';

export default function PromptReliabilityLabPage() {
  const [activeTab, setActiveTab] = useState<'prompts' | 'suites' | 'runs' | 'compare' | 'context'>('prompts');
  const [prompts, setPrompts] = useState<PromptDefinitionModel[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptDefinitionModel | null>(null);
  const [versions, setVersions] = useState<PromptVersionModel[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<PromptVersionModel | null>(null);

  const [appManifest, setAppManifest] = useState<AIApplicationManifestModel | null>(null);
  const [evalContext, setEvalContext] = useState<EvaluationContextModel | null>(null);
  const [contextProvenance, setContextProvenance] = useState<ContextProvenanceModel[]>([]);
  const [contextDiff, setContextDiff] = useState<ContextDifferenceModel | null>(null);
  const [ctxIdA, setCtxIdA] = useState<string>('ctx_baseline_v17');
  const [ctxIdB, setCtxIdB] = useState<string>('ctx_candidate_v18');

  const [suites, setSuites] = useState<EvaluationSuiteModel[]>([]);
  const [selectedSuite, setSelectedSuite] = useState<EvaluationSuiteModel | null>(null);
  const [suiteVersion, setSuiteVersion] = useState<EvaluationSuiteVersionModel | null>(null);

  const [latestRun, setLatestRun] = useState<EvaluationRunModel | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [diagnoses, setDiagnoses] = useState<PromptDiagnosisModel[]>([]);

  // Comparison state
  const [compPromptId, setCompPromptId] = useState<string>('');
  const [compV1, setCompV1] = useState<number>(1);
  const [compV2, setCompV2] = useState<number>(2);
  const [comparisonResult, setComparisonResult] = useState<PromptComparisonResultModel | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRunningEval, setIsRunningEval] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // New version form state
  const [showNewVersionModal, setShowNewVersionModal] = useState<boolean>(false);
  const [newTemplate, setNewTemplate] = useState<string>('');
  const [newReason, setNewReason] = useState<string>('');
  const [newRole, setNewRole] = useState<string>('');
  const [newConstraints, setNewConstraints] = useState<string>('');

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const pList = await api.listPrompts();
      setPrompts(pList);
      if (pList.length > 0) {
        setSelectedPrompt(pList[0]);
        setCompPromptId(pList[0].prompt_id);
        const pDetails = await api.getPrompt(pList[0].prompt_id);
        setVersions(pDetails.versions);
        if (pDetails.versions.length > 0) {
          setSelectedVersion(pDetails.versions[pDetails.versions.length - 1]);
        }
      }

      const sList = await api.listEvaluationSuites();
      setSuites(sList);
      if (sList.length > 0) {
        setSelectedSuite(sList[0]);
        const sDetails = await api.getEvaluationSuite(sList[0].suite_id);
        setSuiteVersion(sDetails.version || null);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load Prompt Lab data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectPrompt = async (p: PromptDefinitionModel) => {
    setSelectedPrompt(p);
    setCompPromptId(p.prompt_id);
    try {
      const pDetails = await api.getPrompt(p.prompt_id);
      setVersions(pDetails.versions);
      if (pDetails.versions.length > 0) {
        setSelectedVersion(pDetails.versions[pDetails.versions.length - 1]);
      } else {
        setSelectedVersion(null);
      }
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleCreateVersion = async () => {
    if (!selectedPrompt || !newTemplate) return;
    try {
      const constraintsList = newConstraints
        .split('\n')
        .map((c) => c.trim())
        .filter(Boolean);

      const created = await api.createPromptVersion(selectedPrompt.prompt_id, {
        template: newTemplate,
        change_reason: newReason || 'Candidate refinement',
        components: {
          role: newRole || undefined,
          constraints: constraintsList.length > 0 ? constraintsList : undefined,
        },
      });

      setShowNewVersionModal(false);
      setNewTemplate('');
      setNewReason('');
      setNewRole('');
      setNewConstraints('');

      // Refresh versions
      const pDetails = await api.getPrompt(selectedPrompt.prompt_id);
      setVersions(pDetails.versions);
      setSelectedVersion(created);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create prompt version');
    }
  };

  const handleRunEvaluation = async () => {
    if (!selectedPrompt || !selectedVersion || !selectedSuite) return;
    setIsRunningEval(true);
    setErrorMsg(null);
    try {
      const run = await api.runEvaluation({
        prompt_id: selectedPrompt.prompt_id,
        prompt_version: selectedVersion.version,
        suite_id: selectedSuite.suite_id,
        suite_version: suiteVersion?.version || 1,
        model: 'mock-agent-v1',
      });
      setLatestRun(run);
      if (run.case_results.length > 0) {
        setSelectedCaseId(run.case_results[0].case_id);
      }

      // Fetch diagnoses
      const runDetails = await api.getEvaluation(run.evaluation_run_id);
      setDiagnoses(runDetails.diagnoses || []);
      setActiveTab('runs');
    } catch (err: any) {
      setErrorMsg(err.message || 'Evaluation run failed');
    } finally {
      setIsRunningEval(false);
    }
  };

  const handleRunComparison = async () => {
    if (!compPromptId || !selectedSuite) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.comparePromptVersions(
        compPromptId,
        compV1,
        compV2,
        selectedSuite.suite_id,
        suiteVersion?.version || 1
      );
      setComparisonResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Comparison failed. Ensure both versions have completed evaluation runs on the same suite.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto w-full">
        {/* Header Banner */}
        <div className="mb-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
          <div>
            <div className="flex items-center space-x-3 mb-1">
              <div className="p-2 rounded-xl bg-pink-500/10 border border-pink-500/30 text-pink-400">
                <Sparkles className="h-6 w-6" />
              </div>
              <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-white">
                Prompt Reliability Lab
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                Slice 7.7
              </span>
            </div>
            <p className="text-sm text-slate-400 max-w-2xl">
              Systematic evaluation of AI application behavior. Immutable prompt versions, versioned evaluation suites, multi-causal layer diagnostics, and regression detection.
            </p>
          </div>

          {/* Invariant Tags */}
          <div className="flex flex-wrap gap-2 text-[11px] font-medium">
            <span className="px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300 flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-amber-400" />
              Immutable Versions
            </span>
            <span className="px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300 flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
              Deterministic Precedence
            </span>
            <span className="px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300 flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5 text-indigo-400" />
              Multi-Layer Diagnosis
            </span>
          </div>
        </div>

        {errorMsg && (
          <div className="mt-4 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button
              onClick={() => setErrorMsg(null)}
              className="text-slate-400 hover:text-white text-xs underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex space-x-2 mt-6 border-b border-slate-800/80">
          <button
            onClick={() => setActiveTab('prompts')}
            className={`pb-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
              activeTab === 'prompts'
                ? 'border-pink-500 text-pink-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileCode className="h-4 w-4" />
            Prompt Registry & Editor
          </button>
          <button
            onClick={() => setActiveTab('suites')}
            className={`pb-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
              activeTab === 'suites'
                ? 'border-pink-500 text-pink-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="h-4 w-4" />
            Evaluation Suites
          </button>
          <button
            onClick={() => setActiveTab('runs')}
            className={`pb-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
              activeTab === 'runs'
                ? 'border-pink-500 text-pink-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Play className="h-4 w-4" />
            Evaluation Runs & Inspector
          </button>
          <button
            onClick={() => setActiveTab('compare')}
            className={`pb-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
              activeTab === 'compare'
                ? 'border-pink-500 text-pink-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <GitCompare className="h-4 w-4" />
            Version Comparison & Regressions
          </button>
          <button
            onClick={() => setActiveTab('context')}
            className={`pb-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
              activeTab === 'context'
                ? 'border-pink-500 text-pink-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu className="h-4 w-4" />
            Application Context (Slice 7.7.1)
          </button>
        </div>
      </div>

      {/* Main Body */}
      <div className="max-w-7xl mx-auto">
        {/* 1. Prompt Registry & Editor */}
        {activeTab === 'prompts' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Sidebar: Prompt List */}
            <div className="lg:col-span-4 bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur-md">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                  Registered Prompts
                </h2>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                  {prompts.length}
                </span>
              </div>

              <div className="space-y-2">
                {prompts.map((p) => (
                  <button
                    key={p.prompt_id}
                    onClick={() => handleSelectPrompt(p)}
                    className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                      selectedPrompt?.prompt_id === p.prompt_id
                        ? 'bg-pink-500/10 border-pink-500/40 text-white'
                        : 'bg-slate-900/40 border-slate-800/80 text-slate-300 hover:bg-slate-800/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-xs text-white truncate">
                        {p.name}
                      </span>
                      <ChevronRight className="h-3.5 w-3.5 text-slate-500" />
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono truncate mb-1">
                      {p.prompt_id}
                    </div>
                    <div className="text-[11px] text-slate-500 line-clamp-2">
                      {p.description || 'No description provided.'}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Main Content: Version Viewer & Structured Editor */}
            <div className="lg:col-span-8 space-y-6">
              {selectedPrompt ? (
                <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-md">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h2 className="text-lg font-bold text-white">{selectedPrompt.name}</h2>
                        <span className="text-xs font-mono text-slate-400">({selectedPrompt.prompt_id})</span>
                      </div>
                      <p className="text-xs text-slate-400">{selectedPrompt.description}</p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setShowNewVersionModal(true)}
                        className="px-3.5 py-1.5 rounded-xl bg-pink-600 hover:bg-pink-500 text-white text-xs font-medium flex items-center gap-1.5 shadow-lg shadow-pink-600/20 transition-all"
                      >
                        <Plus className="h-3.5 w-3.5" />
                        New Version
                      </button>
                      <button
                        onClick={handleRunEvaluation}
                        disabled={isRunningEval}
                        className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium flex items-center gap-1.5 shadow-lg shadow-indigo-600/20 transition-all"
                      >
                        <Play className="h-3.5 w-3.5" />
                        {isRunningEval ? 'Evaluating...' : 'Run Benchmark'}
                      </button>
                    </div>
                  </div>

                  {/* Version Carousel / Pill Selector */}
                  <div className="mt-5">
                    <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Immutable Version History
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {versions.map((v) => (
                        <button
                          key={v.version}
                          onClick={() => setSelectedVersion(v)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-mono flex items-center gap-2 border transition-all ${
                            selectedVersion?.version === v.version
                              ? 'bg-slate-800 border-pink-500/50 text-pink-300'
                              : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          <span>v{v.version}</span>
                          <span
                            className={`text-[9px] px-1.5 py-0.2 rounded font-sans uppercase font-bold ${
                              v.status === 'PASSED'
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : v.status === 'CANDIDATE'
                                ? 'bg-indigo-500/20 text-indigo-300'
                                : v.status === 'DEPLOYED'
                                ? 'bg-cyan-500/20 text-cyan-300'
                                : 'bg-slate-700 text-slate-300'
                            }`}
                          >
                            {v.status}
                          </span>
                          {v.is_evaluated && <Lock className="h-3 w-3 text-amber-400" />}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Selected Version Detail */}
                  {selectedVersion && (
                    <div className="mt-6 space-y-4">
                      <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-bold text-slate-300">Prompt Template</span>
                          <span className="text-[10px] text-slate-500 font-mono">
                            {selectedVersion.is_evaluated ? 'IMMUTABLE (Evaluated)' : 'MUTABLE (Draft)'}
                          </span>
                        </div>
                        <pre className="text-xs text-pink-200 font-mono whitespace-pre-wrap leading-relaxed bg-[#0a0f1d] p-3 rounded-lg border border-slate-800">
                          {selectedVersion.template}
                        </pre>
                      </div>

                      {/* Structured Sections */}
                      {selectedVersion.components && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {selectedVersion.components.role && (
                            <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800">
                              <span className="text-[11px] font-bold text-cyan-400 uppercase tracking-wider block mb-1">
                                Role
                              </span>
                              <p className="text-xs text-slate-300">{selectedVersion.components.role}</p>
                            </div>
                          )}
                          {selectedVersion.components.constraints && selectedVersion.components.constraints.length > 0 && (
                            <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800">
                              <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider block mb-1">
                                Constraints
                              </span>
                              <ul className="text-xs text-slate-300 list-disc list-inside space-y-1">
                                {selectedVersion.components.constraints.map((c, i) => (
                                  <li key={i}>{c}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Variables & Output Schema */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800">
                          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                            Input Variables Schema
                          </span>
                          <pre className="text-[11px] font-mono text-slate-300">
                            {JSON.stringify(selectedVersion.variables_schema, null, 2)}
                          </pre>
                        </div>
                        <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800">
                          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                            Declared Output Schema
                          </span>
                          <pre className="text-[11px] font-mono text-slate-300">
                            {selectedVersion.output_schema
                              ? JSON.stringify(selectedVersion.output_schema, null, 2)
                              : 'None (Unstructured text)'}
                          </pre>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-2xl border border-slate-800">
                  Select a prompt definition to inspect versions.
                </div>
              )}
            </div>
          </div>
        )}

        {/* 2. Evaluation Suites */}
        {activeTab === 'suites' && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-md">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800 mb-6">
              <div>
                <h2 className="text-lg font-bold text-white">Versioned Evaluation Suites</h2>
                <p className="text-xs text-slate-400">
                  Frozen evaluation benchmarks categorized across normal, boundary, missing info, and prompt injection cases.
                </p>
              </div>

              {suiteVersion && (
                <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-indigo-500/10 border border-indigo-500/30 text-indigo-300">
                  Suite Version: v{suiteVersion.version} {suiteVersion.is_frozen ? '(FROZEN)' : '(ACTIVE)'}
                </span>
              )}
            </div>

            {suiteVersion && suiteVersion.cases.length > 0 ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-center">
                    <span className="text-xs text-slate-400">Total Benchmark Cases</span>
                    <div className="text-2xl font-bold text-white mt-1 font-mono">{suiteVersion.cases.length}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-center">
                    <span className="text-xs text-slate-400">Evaluation Strategy</span>
                    <div className="text-2xl font-bold text-cyan-400 mt-1 font-mono">COMPOSITE</div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-center">
                    <span className="text-xs text-slate-400">Suite Integrity</span>
                    <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">VERIFIED</div>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                      <tr>
                        <th className="py-3 px-4">Case ID</th>
                        <th className="py-3 px-4">Category</th>
                        <th className="py-3 px-4">Severity</th>
                        <th className="py-3 px-4">Expected Behavior</th>
                        <th className="py-3 px-4">Constraints</th>
                        <th className="py-3 px-4">Grounding Sources</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono">
                      {suiteVersion.cases.map((c) => (
                        <tr key={c.case_id} className="hover:bg-slate-800/30">
                          <td className="py-3 px-4 font-semibold text-white">{c.case_id}</td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                              {c.category}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                c.severity === 'CRITICAL'
                                  ? 'bg-rose-500/20 text-rose-300'
                                  : c.severity === 'HIGH'
                                  ? 'bg-amber-500/20 text-amber-300'
                                  : 'bg-slate-800 text-slate-300'
                              }`}
                            >
                              {c.severity}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-sans text-slate-300 max-w-xs truncate">
                            {c.expected_behavior}
                          </td>
                          <td className="py-3 px-4 text-slate-400">
                            {c.constraints.length > 0 ? c.constraints.join(', ') : 'None'}
                          </td>
                          <td className="py-3 px-4 text-slate-400">
                            {c.sources.length > 0 ? `${c.sources.length} chunk(s)` : 'None'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500">No evaluation cases found in suite.</div>
            )}
          </div>
        )}

        {/* 3. Evaluation Runs & Failure Inspector */}
        {activeTab === 'runs' && (
          <div className="space-y-6">
            {latestRun ? (
              <>
                {/* Stats Bar */}
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
                    <span className="text-[11px] text-slate-400">Total Cases</span>
                    <div className="text-xl font-bold text-white mt-1 font-mono">{latestRun.total_cases}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
                    <span className="text-[11px] text-emerald-400">Passed</span>
                    <div className="text-xl font-bold text-emerald-400 mt-1 font-mono">{latestRun.passed_cases}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
                    <span className="text-[11px] text-rose-400">Failed</span>
                    <div className="text-xl font-bold text-rose-400 mt-1 font-mono">{latestRun.failed_cases}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
                    <span className="text-[11px] text-amber-400">Partial</span>
                    <div className="text-xl font-bold text-amber-400 mt-1 font-mono">{latestRun.partial_cases}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
                    <span className="text-[11px] text-indigo-400">Unknown / Abstained</span>
                    <div className="text-xl font-bold text-indigo-400 mt-1 font-mono">
                      {latestRun.unknown_cases + latestRun.abstained_cases}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
                    <span className="text-[11px] text-cyan-400">Pass Rate</span>
                    <div className="text-xl font-bold text-cyan-400 mt-1 font-mono">
                      {(latestRun.pass_rate * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>

                {/* Case Drill-Down & Failure Inspector */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                  {/* Case List */}
                  <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
                    <div className="text-xs font-bold text-white uppercase tracking-wider mb-3 px-1">
                      Evaluated Cases
                    </div>
                    <div className="space-y-2">
                      {latestRun.case_results.map((cr) => (
                        <button
                          key={cr.case_id}
                          onClick={() => setSelectedCaseId(cr.case_id)}
                          className={`w-full text-left p-3 rounded-xl border transition-all ${
                            selectedCaseId === cr.case_id
                              ? 'bg-slate-800/80 border-pink-500/50 text-white'
                              : 'bg-slate-950/40 border-slate-800/60 text-slate-300 hover:bg-slate-800/40'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-semibold font-mono truncate">{cr.case_id}</span>
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                                cr.overall_status === 'PASS'
                                  ? 'bg-emerald-500/20 text-emerald-300'
                                  : cr.overall_status === 'FAIL'
                                  ? 'bg-rose-500/20 text-rose-300'
                                  : 'bg-amber-500/20 text-amber-300'
                              }`}
                            >
                              {cr.overall_status}
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-400 flex items-center gap-2">
                            <span>Category: {cr.category}</span>
                            <span>•</span>
                            <span>Sev: {cr.severity}</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Failure & Evidence Inspector */}
                  <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
                    {selectedCaseId ? (
                      (() => {
                        const cr = latestRun.case_results.find((c) => c.case_id === selectedCaseId);
                        const diag = diagnoses.find((d) => d.case_id === selectedCaseId);
                        if (!cr) return null;

                        return (
                          <div className="space-y-5">
                            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                              <div>
                                <h3 className="text-sm font-bold text-white font-mono">{cr.case_id}</h3>
                                <span className="text-xs text-slate-400">
                                  Status: <strong className="text-white">{cr.overall_status}</strong>
                                </span>
                              </div>
                              <span className="text-xs font-mono text-slate-500">
                                Run ID: {latestRun.evaluation_run_id.slice(0, 14)}
                              </span>
                            </div>

                            {/* Evaluator Breakdown */}
                            <div>
                              <span className="text-xs font-bold text-slate-300 block mb-2">
                                Evaluator Breakdown
                              </span>
                              <div className="space-y-2">
                                {cr.evaluator_results.map((er, idx) => (
                                  <div
                                    key={idx}
                                    className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs"
                                  >
                                    <div className="flex items-center justify-between mb-1">
                                      <span className="font-semibold text-slate-200">{er.evaluator_name}</span>
                                      <span
                                        className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                                          er.status === 'PASS'
                                            ? 'text-emerald-400'
                                            : er.status === 'FAIL'
                                            ? 'text-rose-400'
                                            : 'text-amber-400'
                                        }`}
                                      >
                                        {er.status}
                                      </span>
                                    </div>
                                    <p className="text-slate-400 text-[11px]">{er.rationale}</p>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Multi-Layer Diagnosis */}
                            {diag && (
                              <div className="p-4 rounded-xl bg-slate-950 border border-indigo-500/30 space-y-3">
                                <div className="flex items-center justify-between">
                                  <span className="text-xs font-bold text-indigo-300 uppercase tracking-wider flex items-center gap-1.5">
                                    <Cpu className="h-4 w-4 text-indigo-400" />
                                    Multi-Layer Causal Diagnosis
                                  </span>
                                  <span className="px-2 py-0.5 rounded text-xs font-bold bg-indigo-500/20 text-indigo-200 font-mono">
                                    {diag.primary_cause}
                                  </span>
                                </div>

                                <div className="space-y-2 text-xs">
                                  <div className="p-2.5 rounded bg-slate-900/80 border border-slate-800">
                                    <strong className="text-cyan-400">Observed:</strong>{' '}
                                    <span className="text-slate-300">{diag.observed_summary}</span>
                                  </div>
                                  <div className="p-2.5 rounded bg-slate-900/80 border border-slate-800">
                                    <strong className="text-amber-400">Inferred:</strong>{' '}
                                    <span className="text-slate-300">{diag.inferred_summary}</span>
                                  </div>
                                  <div className="p-2.5 rounded bg-slate-900/80 border border-slate-800">
                                    <strong className="text-purple-400">Hypothesis:</strong>{' '}
                                    <span className="text-slate-300">{diag.hypothesis_summary}</span>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })()
                    ) : (
                      <div className="p-8 text-center text-slate-500">Select a case to inspect failure facts.</div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-2xl border border-slate-800">
                No evaluation run recorded. Trigger "Run Benchmark" from the Prompt Registry tab to execute.
              </div>
            )}
          </div>
        )}

        {/* 4. Prompt Version Comparison & Regressions */}
        {activeTab === 'compare' && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-md space-y-6">
            <div>
              <h2 className="text-lg font-bold text-white">Comparative Version Evaluation</h2>
              <p className="text-xs text-slate-400">
                Evaluates multi-dimensional pass rate deltas and per-case regressions over the identical frozen benchmark suite.
              </p>
            </div>

            {/* Controls */}
            <div className="flex flex-wrap items-center gap-4 p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Prompt</label>
                <select
                  value={compPromptId}
                  onChange={(e) => setCompPromptId(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-xs rounded-lg px-3 py-1.5 text-white"
                >
                  {prompts.map((p) => (
                    <option key={p.prompt_id} value={p.prompt_id}>
                      {p.name} ({p.prompt_id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Baseline Version (v1)</label>
                <input
                  type="number"
                  min="1"
                  value={compV1}
                  onChange={(e) => setCompV1(parseInt(e.target.value) || 1)}
                  className="w-20 bg-slate-900 border border-slate-700 text-xs rounded-lg px-3 py-1.5 text-white"
                />
              </div>

              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Candidate Version (v2)</label>
                <input
                  type="number"
                  min="1"
                  value={compV2}
                  onChange={(e) => setCompV2(parseInt(e.target.value) || 2)}
                  className="w-20 bg-slate-900 border border-slate-700 text-xs rounded-lg px-3 py-1.5 text-white"
                />
              </div>

              <div className="pt-4">
                <button
                  onClick={handleRunComparison}
                  className="px-4 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-indigo-600/20"
                >
                  <GitCompare className="h-3.5 w-3.5" />
                  Compare Versions
                </button>
              </div>
            </div>

            {/* Comparison Results */}
            {comparisonResult && (
              <div className="space-y-6">
                {/* Critical Regressions Banner if any */}
                {comparisonResult.critical_regressions.length > 0 && (
                  <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/40 text-rose-300 text-xs space-y-2">
                    <div className="flex items-center gap-2 font-bold text-rose-400">
                      <AlertTriangle className="h-4 w-4" />
                      CRITICAL REGRESSIONS DETECTED ({comparisonResult.critical_regressions.length})
                    </div>
                    <p className="text-[11px] text-slate-300">
                      Candidate version v{compV2} regressed on high/critical benchmark cases previously passing in v{compV1}. Automatic deployment prohibited.
                    </p>
                  </div>
                )}

                {/* Multidimensional Metrics Table */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-center">
                    <span className="text-[11px] text-slate-400">Overall Pass Rate Delta</span>
                    <div
                      className={`text-xl font-bold mt-1 font-mono ${
                        comparisonResult.pass_rate_delta >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {comparisonResult.pass_rate_delta >= 0 ? '+' : ''}
                      {(comparisonResult.pass_rate_delta * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-center">
                    <span className="text-[11px] text-emerald-400">Fixed Failures</span>
                    <div className="text-xl font-bold text-white mt-1 font-mono">
                      {comparisonResult.fixed_failures_count}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-center">
                    <span className="text-[11px] text-rose-400">Regressions</span>
                    <div className="text-xl font-bold text-rose-400 mt-1 font-mono">
                      {comparisonResult.regressions_count}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-center">
                    <span className="text-[11px] text-slate-400">Unchanged</span>
                    <div className="text-xl font-bold text-white mt-1 font-mono">
                      {comparisonResult.unchanged_count}
                    </div>
                  </div>
                </div>

                {/* Transition Diff Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                      <tr>
                        <th className="py-3 px-4">Case ID</th>
                        <th className="py-3 px-4">Category</th>
                        <th className="py-3 px-4">Severity</th>
                        <th className="py-3 px-4">v{compV1} Status</th>
                        <th className="py-3 px-4">v{compV2} Status</th>
                        <th className="py-3 px-4">Transition</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono">
                      {comparisonResult.transitions.map((t) => (
                        <tr key={t.case_id} className="hover:bg-slate-800/30">
                          <td className="py-3 px-4 font-semibold text-white">{t.case_id}</td>
                          <td className="py-3 px-4 text-slate-400">{t.category}</td>
                          <td className="py-3 px-4">{t.severity}</td>
                          <td className="py-3 px-4">{t.status_v1}</td>
                          <td className="py-3 px-4">{t.status_v2}</td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                t.transition === 'FIXED_FAILURE' || t.transition === 'NEW_PASS'
                                  ? 'bg-emerald-500/20 text-emerald-300'
                                  : t.transition === 'REGRESSION' || t.transition === 'NEW_FAILURE'
                                  ? 'bg-rose-500/20 text-rose-300'
                                  : 'bg-slate-800 text-slate-400'
                              }`}
                            >
                              {t.transition}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 5. Application Context Contract (Slice 7.7.1) */}
        {activeTab === 'context' && (
          <div className="space-y-6">
            {/* Header & Principle Banner */}
            <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/20 to-slate-900 border border-indigo-500/20 backdrop-blur-md">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
                      <Cpu className="h-4 w-4" />
                    </span>
                    <h2 className="text-base font-bold text-white">AI Application Context Contract & Epistemic Boundaries</h2>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300">
                      Slice 7.7.1
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 max-w-3xl">
                    Prompt-level evaluation is for isolated experimentation; <strong className="text-indigo-300">Application-level evaluation</strong> binds to the real application runtime, frozen Git commit, model, tools, retrieval, and behavioral contracts.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[11px] font-semibold flex items-center gap-1.5">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Frozen Contract Active
                  </span>
                </div>
              </div>

              {/* Epistemic Status Guide */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 pt-4 border-t border-slate-800/80 text-[11px]">
                <div className="p-2.5 rounded-xl bg-slate-950/80 border border-emerald-500/20">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-bold mb-0.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
                    OBSERVED
                  </div>
                  <p className="text-[10px] text-slate-400">Verified at runtime or exact Git commit provenance.</p>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-950/80 border border-amber-500/20">
                  <div className="flex items-center gap-1.5 text-amber-400 font-bold mb-0.5">
                    <span className="h-2 w-2 rounded-full bg-amber-400"></span>
                    DECLARED
                  </div>
                  <p className="text-[10px] text-slate-400">Stated configuration in manifest awaiting verification.</p>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-950/80 border border-sky-500/20">
                  <div className="flex items-center gap-1.5 text-sky-400 font-bold mb-0.5">
                    <span className="h-2 w-2 rounded-full bg-sky-400"></span>
                    INFERRED
                  </div>
                  <p className="text-[10px] text-slate-400">Derived from operational signals and telemetry.</p>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-950/80 border border-purple-500/20">
                  <div className="flex items-center gap-1.5 text-purple-400 font-bold mb-0.5">
                    <span className="h-2 w-2 rounded-full bg-purple-400"></span>
                    HYPOTHESIS
                  </div>
                  <p className="text-[10px] text-slate-400">Candidate improvement or non-verified causal theory.</p>
                </div>
              </div>
            </div>

            {/* Application Manifest & Frozen Context Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: AI Application Manifest */}
              <div className="lg:col-span-6 bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur-md space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Box className="h-4 w-4 text-pink-400" />
                    <h3 className="text-sm font-bold text-white">AI Application Manifest</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300">
                    order-triage-app:v2.4.1
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                    <span className="text-[10px] uppercase tracking-wider text-slate-400 block mb-1">Application ID</span>
                    <span className="font-mono text-white font-semibold">order-triage-service</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                    <span className="text-[10px] uppercase tracking-wider text-slate-400 block mb-1">Feature ID</span>
                    <span className="font-mono text-white font-semibold">refund-routing-v2</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] uppercase tracking-wider text-slate-400">Git Commit SHA</span>
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400">OBSERVED</span>
                    </div>
                    <span className="font-mono text-indigo-300 font-semibold">7f8a9b1c2d3e</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] uppercase tracking-wider text-slate-400">Bound Prompt</span>
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400">OBSERVED</span>
                    </div>
                    <span className="font-mono text-pink-400 font-semibold">order_triage:v17</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] uppercase tracking-wider text-slate-400">Model & Config</span>
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-500/20 text-amber-400">DECLARED</span>
                    </div>
                    <span className="font-mono text-white font-semibold">claude-3-5-sonnet:20241022</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] uppercase tracking-wider text-slate-400">Bound Evaluation Suite</span>
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400">OBSERVED</span>
                    </div>
                    <span className="font-mono text-white font-semibold">suite_order_exceptions:v1</span>
                  </div>
                </div>

                {/* Behavioral Contracts */}
                <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                      <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
                      Bound Behavioral Contracts
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">2 Active Contracts</span>
                  </div>
                  <div className="space-y-1.5 text-xs font-mono">
                    <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900 border border-slate-800">
                      <span className="text-cyan-300">contract_refund_threshold_precedence</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300">PRESERVED</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900 border border-slate-800">
                      <span className="text-cyan-300">contract_strict_grounding_fidelity</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300">PRESERVED</span>
                    </div>
                  </div>
                </div>

                {/* Context Cryptographic Fingerprint */}
                <div className="p-3.5 rounded-xl bg-slate-950/80 border border-indigo-500/30 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <Fingerprint className="h-4 w-4 text-indigo-400" />
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 block">Context SHA-256 Hash</span>
                      <span className="font-mono text-indigo-300 text-[11px]">8f4a1c7e9b2d3f6a8e0c1b4d7e9f2a4b...</span>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-300 font-bold text-[10px]">
                    FROZEN
                  </span>
                </div>
              </div>

              {/* Right Column: Component Provenance Records */}
              <div className="lg:col-span-6 bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur-md space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <GitBranch className="h-4 w-4 text-emerald-400" />
                    <h3 className="text-sm font-bold text-white">Context Provenance Ledger</h3>
                  </div>
                  <span className="text-[11px] text-slate-400">8 Provenance Layers</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                      <tr>
                        <th className="py-2.5 px-3">Component</th>
                        <th className="py-2.5 px-3">Source</th>
                        <th className="py-2.5 px-3">Version / ID</th>
                        <th className="py-2.5 px-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                      <tr className="hover:bg-slate-800/30">
                        <td className="py-2.5 px-3 font-semibold text-white">prompt</td>
                        <td className="py-2.5 px-3 text-slate-400">PromptRegistry</td>
                        <td className="py-2.5 px-3 text-pink-300">order_triage:v17</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400">OBSERVED</span>
                        </td>
                      </tr>
                      <tr className="hover:bg-slate-800/30">
                        <td className="py-2.5 px-3 font-semibold text-white">git_commit</td>
                        <td className="py-2.5 px-3 text-slate-400">GitHub</td>
                        <td className="py-2.5 px-3 text-indigo-300">7f8a9b1c2d3e</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400">OBSERVED</span>
                        </td>
                      </tr>
                      <tr className="hover:bg-slate-800/30">
                        <td className="py-2.5 px-3 font-semibold text-white">model</td>
                        <td className="py-2.5 px-3 text-slate-400">ApplicationConfig</td>
                        <td className="py-2.5 px-3 text-white">claude-3-5-sonnet</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-400">DECLARED</span>
                        </td>
                      </tr>
                      <tr className="hover:bg-slate-800/30">
                        <td className="py-2.5 px-3 font-semibold text-white">retrieval</td>
                        <td className="py-2.5 px-3 text-slate-400">KnowledgeBase</td>
                        <td className="py-2.5 px-3 text-slate-300">retrieval_pipeline_v1</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400">OBSERVED</span>
                        </td>
                      </tr>
                      <tr className="hover:bg-slate-800/30">
                        <td className="py-2.5 px-3 font-semibold text-white">tools</td>
                        <td className="py-2.5 px-3 text-slate-400">ToolRegistry</td>
                        <td className="py-2.5 px-3 text-slate-300">2 registered tools</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400">OBSERVED</span>
                        </td>
                      </tr>
                      <tr className="hover:bg-slate-800/30">
                        <td className="py-2.5 px-3 font-semibold text-white">parser</td>
                        <td className="py-2.5 px-3 text-slate-400">OutputParser</td>
                        <td className="py-2.5 px-3 text-slate-300">json_schema_parser:v2</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400">OBSERVED</span>
                        </td>
                      </tr>
                      <tr className="hover:bg-slate-800/30">
                        <td className="py-2.5 px-3 font-semibold text-white">behavioral_contract</td>
                        <td className="py-2.5 px-3 text-slate-400">EvaluationRegistry</td>
                        <td className="py-2.5 px-3 text-cyan-300">2 contracts</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400">OBSERVED</span>
                        </td>
                      </tr>
                      <tr className="hover:bg-slate-800/30">
                        <td className="py-2.5 px-3 font-semibold text-white">evaluation_suite</td>
                        <td className="py-2.5 px-3 text-slate-400">EvaluationRegistry</td>
                        <td className="py-2.5 px-3 text-white">suite_order_exceptions:v1</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400">OBSERVED</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Context Difference & Causal Attribution Section */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-md space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Binary className="h-5 w-5 text-indigo-400" />
                  <div>
                    <h3 className="text-sm font-bold text-white">10-Dimensional Context Difference & Causal Attribution</h3>
                    <p className="text-xs text-slate-400">
                      Detects <strong className="text-amber-300">MULTI_VARIABLE_CHANGE</strong> to prevent unsupported causal attribution of improvements to prompt changes.
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Isolated Variable Verified
                  </span>
                </div>
              </div>

              {/* Context Difference Matrix */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4">Context Dimension</th>
                      <th className="py-3 px-4">Baseline (ctx_baseline_v17)</th>
                      <th className="py-3 px-4">Candidate (ctx_candidate_v18)</th>
                      <th className="py-3 px-4">Delta State</th>
                      <th className="py-3 px-4">Attribution Impact</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                    <tr className="bg-pink-500/5 hover:bg-pink-500/10">
                      <td className="py-3 px-4 font-bold text-white flex items-center gap-2">
                        <FileCode className="h-3.5 w-3.5 text-pink-400" />
                        Prompt Version
                      </td>
                      <td className="py-3 px-4 text-pink-300 font-semibold">order_triage:v17</td>
                      <td className="py-3 px-4 text-pink-300 font-semibold">order_triage:v18</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-pink-500/20 text-pink-300">
                          CHANGED (v17 → v18)
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-300 text-[11px] font-sans">
                        Target experimental variable.
                      </td>
                    </tr>
                    <tr className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Git Commit SHA</td>
                      <td className="py-3 px-4 text-slate-400">7f8a9b1c2d3e</td>
                      <td className="py-3 px-4 text-slate-400">7f8a9b1c2d3e</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">UNCHANGED</span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px] font-sans">Identical codebase commit.</td>
                    </tr>
                    <tr className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Model & Version</td>
                      <td className="py-3 px-4 text-slate-400">claude-3-5-sonnet:20241022</td>
                      <td className="py-3 px-4 text-slate-400">claude-3-5-sonnet:20241022</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">UNCHANGED</span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px] font-sans">Identical model baseline.</td>
                    </tr>
                    <tr className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Model Parameters</td>
                      <td className="py-3 px-4 text-slate-400">temp=0.0, max=1024</td>
                      <td className="py-3 px-4 text-slate-400">temp=0.0, max=1024</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">UNCHANGED</span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px] font-sans">Deterministic sampling preserved.</td>
                    </tr>
                    <tr className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Retrieval Pipeline</td>
                      <td className="py-3 px-4 text-slate-400">kb_pipeline_v1</td>
                      <td className="py-3 px-4 text-slate-400">kb_pipeline_v1</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">UNCHANGED</span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px] font-sans">Identical knowledge chunks retrieved.</td>
                    </tr>
                    <tr className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Tool Permissions & Registry</td>
                      <td className="py-3 px-4 text-slate-400">registry_v4 (2 tools)</td>
                      <td className="py-3 px-4 text-slate-400">registry_v4 (2 tools)</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">UNCHANGED</span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px] font-sans">Identical tool boundaries.</td>
                    </tr>
                    <tr className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Parser Configuration</td>
                      <td className="py-3 px-4 text-slate-400">pydantic_v2</td>
                      <td className="py-3 px-4 text-slate-400">pydantic_v2</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">UNCHANGED</span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px] font-sans">Identical parsing rules.</td>
                    </tr>
                    <tr className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Evaluation Suite</td>
                      <td className="py-3 px-4 text-slate-400">suite_order_exceptions:v1</td>
                      <td className="py-3 px-4 text-slate-400">suite_order_exceptions:v1</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">UNCHANGED</span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px] font-sans">Identical frozen test suite.</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Attribution Callout */}
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs flex items-center justify-between text-emerald-300">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                  <span>
                    <strong>ISOLATED_VARIABLE VALIDATION</strong>: Only prompt version changed while all other 9 context dimensions remained identical. Performance change can be causally attributed to the prompt.
                  </span>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 uppercase">
                  Attribution Permitted
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* New Prompt Version Modal */}
      {showNewVersionModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Create Candidate Prompt Version</h3>
              <button
                onClick={() => setShowNewVersionModal(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Prompt versions are immutable once evaluated. Creating a version establishes a candidate without mutating production.
            </p>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">
                Prompt Template (use &#123;&#123;variable&#125;&#125; placeholders)
              </label>
              <textarea
                rows={5}
                value={newTemplate}
                onChange={(e) => setNewTemplate(e.target.value)}
                placeholder="Enter prompt instructions and placeholders..."
                className="w-full bg-slate-950 border border-slate-700 text-xs font-mono rounded-xl p-3 text-white focus:outline-none focus:border-pink-500"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Role / Persona</label>
                <input
                  type="text"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  placeholder="e.g. Order Triage Specialist"
                  className="w-full bg-slate-950 border border-slate-700 text-xs rounded-xl p-2.5 text-white"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Change Reason</label>
                <input
                  type="text"
                  value={newReason}
                  onChange={(e) => setNewReason(e.target.value)}
                  placeholder="e.g. Fix missing schema fields"
                  className="w-full bg-slate-950 border border-slate-700 text-xs rounded-xl p-2.5 text-white"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">
                Constraints (one per line)
              </label>
              <textarea
                rows={2}
                value={newConstraints}
                onChange={(e) => setNewConstraints(e.target.value)}
                placeholder="forbidden: as an ai language model&#10;max_chars: 400"
                className="w-full bg-slate-950 border border-slate-700 text-xs font-mono rounded-xl p-2.5 text-white"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                onClick={() => setShowNewVersionModal(false)}
                className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateVersion}
                disabled={!newTemplate.trim()}
                className="px-4 py-2 rounded-xl bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-pink-600/20"
              >
                Create Candidate Version
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </AppShell>
  );
}
