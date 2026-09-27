'use client';

import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  GitCommit,
  GitPullRequest,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Shield,
  Play,
  RefreshCw,
  FileCode,
  Terminal,
  Activity,
  Layers,
  Sparkles,
  Info,
  Lock,
  ChevronRight,
  HelpCircle
} from 'lucide-react';
import { api } from '@/lib/api';
import {
  GitStatusModel,
  GitCommitModel,
  PullRequestModel,
  PRReviewModel,
  CIRunModel,
  ReleaseReadinessModel,
} from '@/types';

export default function EngineeringLifecyclePage() {
  const [gitStatus, setGitStatus] = useState<GitStatusModel | null>(null);
  const [commits, setCommits] = useState<GitCommitModel[]>([]);
  const [prs, setPRs] = useState<PullRequestModel[]>([]);
  const [selectedCommitSha, setSelectedCommitSha] = useState<string>('');
  const [ciRuns, setCiRuns] = useState<CIRunModel[]>([]);
  const [readiness, setReadiness] = useState<ReleaseReadinessModel | null>(null);
  const [activePR, setActivePR] = useState<PullRequestModel | null>(null);
  const [prReviews, setPrReviews] = useState<PRReviewModel[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isTriggeringCI, setIsTriggeringCI] = useState<boolean>(false);
  const [isReviewingPR, setIsReviewingPR] = useState<boolean>(false);
  const [selectedTab, setSelectedTab] = useState<'pipeline' | 'prs' | 'ci' | 'readiness'>('pipeline');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load baseline lifecycle data
  const loadData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [status, recentCommits, prList] = await Promise.all([
        api.getLifecycleStatus(),
        api.getLifecycleCommits(10),
        api.getLifecyclePRs(),
      ]);

      setGitStatus(status);
      setCommits(recentCommits);
      setPRs(prList);

      const headSha = status.commit_sha;
      setSelectedCommitSha(headSha);

      // Load CI & Readiness for HEAD commit
      if (headSha) {
        const [runs, ready] = await Promise.all([
          api.getCIRuns(headSha).catch(() => []),
          api.getReleaseReadiness(headSha).catch(() => null),
        ]);
        setCiRuns(runs);
        setReadiness(ready);
      }

      if (prList.length > 0) {
        setActivePR(prList[0]);
        const detail = await api.getLifecyclePRDetail(prList[0].id).catch(() => null);
        if (detail) {
          setPrReviews(detail.reviews);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load engineering lifecycle data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectCommit = async (sha: string) => {
    setSelectedCommitSha(sha);
    try {
      const [runs, ready] = await Promise.all([
        api.getCIRuns(sha).catch(() => []),
        api.getReleaseReadiness(sha).catch(() => null),
      ]);
      setCiRuns(runs);
      setReadiness(ready);
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleSelectPR = async (pr: PullRequestModel) => {
    setActivePR(pr);
    try {
      const detail = await api.getLifecyclePRDetail(pr.id);
      setPrReviews(detail.reviews);
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleTriggerCI = async (workflow: string = 'pytest_unit') => {
    if (!selectedCommitSha) return;
    setIsTriggeringCI(true);
    try {
      await api.triggerCIRun(selectedCommitSha, workflow);
      const [updatedRuns, updatedReady] = await Promise.all([
        api.getCIRuns(selectedCommitSha),
        api.getReleaseReadiness(selectedCommitSha, activePR?.id),
      ]);
      setCiRuns(updatedRuns);
      setReadiness(updatedReady);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setIsTriggeringCI(false);
    }
  };

  const handleReviewPR = async () => {
    if (!activePR) return;
    setIsReviewingPR(true);
    try {
      await api.reviewLifecyclePR(activePR.id);
      const detail = await api.getLifecyclePRDetail(activePR.id);
      setPrReviews(detail.reviews);
      setActivePR(detail.pull_request);
      // Reload readiness
      if (selectedCommitSha) {
        const ready = await api.getReleaseReadiness(selectedCommitSha, activePR.id);
        setReadiness(ready);
      }
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setIsReviewingPR(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASSED':
      case 'APPROVED':
      case 'READY_FOR_RELEASE':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="h-3 w-3" />
            <span>{status}</span>
          </span>
        );
      case 'FAILED':
      case 'CHANGES_REQUESTED':
      case 'BLOCKED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <XCircle className="h-3 w-3" />
            <span>{status}</span>
          </span>
        );
      case 'ABSTAINED':
      case 'UNKNOWN':
      case 'INSUFFICIENT_DATA':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <HelpCircle className="h-3 w-3" />
            <span>{status}</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-700/40 text-slate-300 border border-slate-600/30">
            <Clock className="h-3 w-3" />
            <span>{status}</span>
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-200 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
          <div>
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-gradient-to-tr from-cyan-600/30 to-indigo-600/30 border border-cyan-500/30">
                <GitBranch className="h-6 w-6 text-cyan-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white flex items-center space-x-2">
                  <span>AI Engineering Lifecycle</span>
                  <span className="text-xs uppercase tracking-wider font-semibold px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                    Slice 7.5
                  </span>
                </h1>
                <p className="text-xs text-slate-400 mt-0.5">
                  Antigravity Skill → Git Commits → PR & AI Code Review → Deterministic CI → Independent Lab Retest → Evidence → Release Readiness
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={loadData}
              disabled={isLoading}
              className="flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/70 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-3">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Git Repository Summary Banner */}
        {gitStatus && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-[#0c1222] border border-slate-800/80">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Repository</span>
                <GitBranch className="h-4 w-4 text-cyan-400" />
              </div>
              <div className="mt-2 text-sm font-semibold text-white truncate">{gitStatus.repository}</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Active Branch: <span className="text-cyan-300">{gitStatus.branch}</span></div>
            </div>

            <div className="p-4 rounded-xl bg-[#0c1222] border border-slate-800/80">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>HEAD Commit</span>
                <GitCommit className="h-4 w-4 text-indigo-400" />
              </div>
              <div className="mt-2 font-mono text-xs font-semibold text-indigo-300 truncate">
                {gitStatus.commit_sha.slice(0, 10)}
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Parent: {gitStatus.parent_commit_sha ? gitStatus.parent_commit_sha.slice(0, 8) : 'Root'}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[#0c1222] border border-slate-800/80">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Working Tree</span>
                <Activity className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="mt-2 text-sm font-semibold flex items-center space-x-2">
                <span className={gitStatus.is_clean ? 'text-emerald-400' : 'text-amber-400'}>
                  {gitStatus.is_clean ? 'Clean (Synchronized)' : `${gitStatus.changed_files.length} Uncommitted Changes`}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">Untracked: {gitStatus.untracked_files.length} files</div>
            </div>

            <div className="p-4 rounded-xl bg-[#0c1222] border border-slate-800/80">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Release Gate</span>
                <Shield className="h-4 w-4 text-purple-400" />
              </div>
              <div className="mt-2">
                {readiness ? getStatusBadge(readiness.overall_state) : getStatusBadge('PENDING')}
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                {readiness?.blockers.length ? `${readiness.blockers.length} gate blockers` : 'No blocking issues'}
              </div>
            </div>
          </div>
        )}

        {/* 7-Stage Engineering Lifecycle Pipeline Stepper */}
        <div className="p-6 rounded-2xl bg-[#090e1a] border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white tracking-wide uppercase flex items-center space-x-2">
              <Layers className="h-4 w-4 text-cyan-400" />
              <span>Full Engineering Lifecycle Pipeline</span>
            </h2>
            <span className="text-[11px] text-slate-400">Canonical SDLC Stage Transition</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2 pt-2">
            {[
              {
                id: '1',
                name: 'Repository',
                icon: GitBranch,
                status: 'PASSED',
                desc: gitStatus?.branch || 'main',
              },
              {
                id: '2',
                name: 'Commit SHA',
                icon: GitCommit,
                status: 'PASSED',
                desc: selectedCommitSha.slice(0, 7) || 'HEAD',
              },
              {
                id: '3',
                name: 'AI Code Review',
                icon: FileCode,
                status: readiness?.review_status || 'PENDING',
                desc: 'Static diff findings',
              },
              {
                id: '4',
                name: 'Deterministic CI',
                icon: Terminal,
                status: readiness?.ci_status || 'PENDING',
                desc: 'pytest & build gates',
              },
              {
                id: '5',
                name: 'Independent Lab',
                icon: Shield,
                status: readiness?.lab_status || 'PASSED',
                desc: 'Behavioral verify',
              },
              {
                id: '6',
                name: 'Evidence SHA',
                icon: CheckCircle2,
                status: readiness?.evidence_status || 'PASSED',
                desc: 'Cryptographic log',
              },
              {
                id: '7',
                name: 'Release Readiness',
                icon: Sparkles,
                status: readiness?.overall_state || 'PENDING',
                desc: 'Human gate (no auto-deploy)',
              },
            ].map((step, idx) => (
              <div
                key={step.id}
                className="relative p-3 rounded-xl bg-[#0e1628] border border-slate-800/80 flex flex-col justify-between space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-slate-500">0{step.id}</span>
                  <step.icon className="h-3.5 w-3.5 text-slate-400" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-white">{step.name}</div>
                  <div className="text-[10px] text-slate-400 truncate">{step.desc}</div>
                </div>
                <div className="pt-1">{getStatusBadge(step.status)}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center space-x-2 border-b border-slate-800">
          <button
            onClick={() => setSelectedTab('pipeline')}
            className={`px-4 py-2.5 text-xs font-semibold transition-all border-b-2 flex items-center space-x-2 ${
              selectedTab === 'pipeline'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Activity className="h-3.5 w-3.5" />
            <span>Interactive Pipeline</span>
          </button>

          <button
            onClick={() => setSelectedTab('prs')}
            className={`px-4 py-2.5 text-xs font-semibold transition-all border-b-2 flex items-center space-x-2 ${
              selectedTab === 'prs'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <GitPullRequest className="h-3.5 w-3.5" />
            <span>Pull Requests & AI Review ({prs.length})</span>
          </button>

          <button
            onClick={() => setSelectedTab('ci')}
            className={`px-4 py-2.5 text-xs font-semibold transition-all border-b-2 flex items-center space-x-2 ${
              selectedTab === 'ci'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Terminal className="h-3.5 w-3.5" />
            <span>CI Workflow Runs ({ciRuns.length})</span>
          </button>

          <button
            onClick={() => setSelectedTab('readiness')}
            className={`px-4 py-2.5 text-xs font-semibold transition-all border-b-2 flex items-center space-x-2 ${
              selectedTab === 'readiness'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Shield className="h-3.5 w-3.5" />
            <span>Release Readiness Gate Audit</span>
          </button>
        </div>

        {/* Tab 1: Interactive Pipeline View */}
        {selectedTab === 'pipeline' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Commit History */}
            <div className="lg:col-span-1 p-5 rounded-2xl bg-[#090e1a] border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                  <GitCommit className="h-4 w-4 text-indigo-400" />
                  <span>Recent Commits</span>
                </h3>
                <span className="text-[10px] text-slate-500">Select to inspect</span>
              </div>

              <div className="space-y-2">
                {commits.map((c) => {
                  const isSelected = c.commit_sha === selectedCommitSha;
                  return (
                    <button
                      key={c.commit_sha}
                      onClick={() => handleSelectCommit(c.commit_sha)}
                      className={`w-full text-left p-3 rounded-xl transition-all border ${
                        isSelected
                          ? 'bg-indigo-600/15 border-indigo-500/40 text-white'
                          : 'bg-slate-900/60 border-slate-800/80 text-slate-300 hover:bg-slate-800/50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-semibold text-indigo-300">
                          {c.commit_sha.slice(0, 8)}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {new Date(c.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <div className="text-xs font-medium text-slate-200 mt-1 line-clamp-1">
                        {c.message}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-1 flex items-center justify-between">
                        <span>{c.author}</span>
                        <span>{c.files_changed.length} files</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Right: Selected Commit Lifecycle Details */}
            <div className="lg:col-span-2 space-y-6">
              {/* Commit Details Card */}
              <div className="p-5 rounded-2xl bg-[#090e1a] border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Commit Provenance & Gate Evaluation
                  </h3>
                  <div className="font-mono text-xs text-indigo-400">{selectedCommitSha}</div>
                </div>

                {readiness && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                      <div className="text-[11px] text-slate-400">AI Review</div>
                      <div className="mt-1">{getStatusBadge(readiness.review_status)}</div>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                      <div className="text-[11px] text-slate-400">Deterministic CI</div>
                      <div className="mt-1">{getStatusBadge(readiness.ci_status)}</div>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                      <div className="text-[11px] text-slate-400">Engineering Lab</div>
                      <div className="mt-1">{getStatusBadge(readiness.lab_status)}</div>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                      <div className="text-[11px] text-slate-400">Cryptographic Evidence</div>
                      <div className="mt-1">{getStatusBadge(readiness.evidence_status)}</div>
                    </div>
                  </div>
                )}

                {/* Gate Blockers */}
                {readiness?.blockers && readiness.blockers.length > 0 && (
                  <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 space-y-2">
                    <div className="text-xs font-semibold text-rose-300 flex items-center space-x-2">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      <span>Release Blockers Detected ({readiness.blockers.length})</span>
                    </div>
                    <ul className="text-xs text-rose-200/90 space-y-1 list-disc list-inside">
                      {readiness.blockers.map((b, i) => (
                        <li key={i}>{b}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Quick CI Trigger */}
                <div className="pt-2 flex items-center justify-between border-t border-slate-800">
                  <span className="text-xs text-slate-400">Trigger deterministic local CI on this commit:</span>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleTriggerCI('pytest_unit')}
                      disabled={isTriggeringCI}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all flex items-center space-x-1.5"
                    >
                      <Play className="h-3 w-3" />
                      <span>Run pytest Unit</span>
                    </button>
                    <button
                      onClick={() => handleTriggerCI('npm_build')}
                      disabled={isTriggeringCI}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all"
                    >
                      Run npm build
                    </button>
                  </div>
                </div>
              </div>

              {/* Invariant callout */}
              <div className="p-4 rounded-xl bg-cyan-950/30 border border-cyan-800/40 text-xs text-cyan-300 space-y-1">
                <div className="font-semibold flex items-center space-x-1.5">
                  <Info className="h-4 w-4 text-cyan-400" />
                  <span>Engineering Lab SDLC Invariant</span>
                </div>
                <p className="text-slate-400">
                  Antigravity builds the software. Git records the change. CI verifies the code. The Engineering Lab independently verifies the running application. Evidence connects the lifecycle.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Pull Requests & AI Review */}
        {selectedTab === 'prs' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 p-5 rounded-2xl bg-[#090e1a] border border-slate-800 space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-2">
                <GitPullRequest className="h-4 w-4 text-cyan-400" />
                <span>Tracked Pull Requests</span>
              </h3>

              <div className="space-y-2">
                {prs.map((pr) => {
                  const isSelected = activePR?.id === pr.id;
                  return (
                    <button
                      key={pr.id}
                      onClick={() => handleSelectPR(pr)}
                      className={`w-full text-left p-3 rounded-xl transition-all border ${
                        isSelected
                          ? 'bg-cyan-600/15 border-cyan-500/40 text-white'
                          : 'bg-slate-900/60 border-slate-800/80 text-slate-300 hover:bg-slate-800/50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-cyan-300">#{pr.number}</span>
                        {getStatusBadge(pr.status)}
                      </div>
                      <div className="text-xs font-medium text-slate-200 mt-1 line-clamp-1">{pr.title}</div>
                      <div className="text-[10px] text-slate-500 mt-1">
                        {pr.source_branch} → {pr.target_branch}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* PR Details and AI Code Review */}
            <div className="lg:col-span-2 space-y-5">
              {activePR ? (
                <div className="p-5 rounded-2xl bg-[#090e1a] border border-slate-800 space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-sm font-bold text-cyan-400">#{activePR.number}</span>
                        <h3 className="text-base font-bold text-white">{activePR.title}</h3>
                      </div>
                      <div className="text-xs text-slate-400 mt-1">
                        Branch: <span className="text-cyan-300">{activePR.source_branch}</span> into <span className="text-slate-300">{activePR.target_branch}</span>
                      </div>
                    </div>
                    <button
                      onClick={handleReviewPR}
                      disabled={isReviewingPR}
                      className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition-all flex items-center space-x-2"
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>{isReviewingPR ? 'Reviewing...' : 'Trigger AI Review'}</span>
                    </button>
                  </div>

                  {/* Reviews */}
                  <div className="space-y-4 pt-3 border-t border-slate-800">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Static AI Code Review Findings
                    </h4>

                    {prReviews.length === 0 ? (
                      <div className="text-xs text-slate-500 italic p-4 text-center">
                        No AI reviews conducted on this pull request yet. Click "Trigger AI Review" to analyze the diff.
                      </div>
                    ) : (
                      prReviews.map((rev) => (
                        <div key={rev.review_id} className="space-y-3">
                          <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900 border border-slate-800">
                            <div>
                              <div className="text-xs font-semibold text-white">{rev.summary}</div>
                              <div className="text-[10px] text-slate-500">ID: {rev.review_id}</div>
                            </div>
                            {getStatusBadge(rev.status)}
                          </div>

                          <div className="space-y-2">
                            {rev.findings.map((f, i) => (
                              <div
                                key={i}
                                className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1.5"
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center space-x-2">
                                    <span className="font-mono text-xs font-semibold text-slate-300">
                                      {f.file}:{f.line}
                                    </span>
                                    <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300">
                                      {f.category}
                                    </span>
                                    <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300">
                                      {f.epistemic_status}
                                    </span>
                                  </div>
                                  <span className={`text-[10px] font-bold ${
                                    f.severity === 'CRITICAL' || f.severity === 'HIGH' ? 'text-rose-400' : 'text-slate-400'
                                  }`}>
                                    {f.severity}
                                  </span>
                                </div>
                                <div className="text-xs font-semibold text-white">{f.title}</div>
                                <div className="text-xs text-slate-400">{f.description}</div>
                                <div className="text-[11px] font-mono bg-black/40 p-2 rounded text-slate-300">
                                  {f.evidence}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-slate-500">
                  Select a pull request to inspect review findings.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 3: CI Workflow Runs */}
        {selectedTab === 'ci' && (
          <div className="p-5 rounded-2xl bg-[#090e1a] border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-2">
                  <Terminal className="h-4 w-4 text-indigo-400" />
                  <span>Deterministic CI Pipeline Runs</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  CI gates are deterministic code-level tests (pytest, npm test, npm build). An LLM cannot override a failed check.
                </p>
              </div>

              <button
                onClick={() => handleTriggerCI('pytest_unit')}
                disabled={isTriggeringCI}
                className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center space-x-2 transition-all"
              >
                <Play className="h-3.5 w-3.5" />
                <span>{isTriggeringCI ? 'Executing...' : 'Run New CI Check'}</span>
              </button>
            </div>

            <div className="space-y-3">
              {ciRuns.length === 0 ? (
                <div className="text-xs text-slate-500 italic p-6 text-center">
                  No CI runs recorded for commit {selectedCommitSha.slice(0, 10)}. Click "Run New CI Check" to execute.
                </div>
              ) : (
                ciRuns.map((run) => (
                  <div
                    key={run.id}
                    className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-white">{run.workflow}</span>
                        <span className="font-mono text-[10px] text-slate-500">#{run.id}</span>
                      </div>
                      <div className="text-xs text-slate-400">
                        Tests: <span className="text-emerald-400 font-semibold">{run.tests_passed} passed</span> / {run.tests_total} total ({run.tests_failed} failed)
                      </div>
                      <div className="text-[10px] text-slate-500">
                        Duration: {run.duration_ms}ms · Completed: {new Date(run.started_at).toLocaleString()}
                      </div>
                    </div>
                    <div>{getStatusBadge(run.status)}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Tab 4: Release Readiness Gate Audit */}
        {selectedTab === 'readiness' && (
          <div className="p-6 rounded-2xl bg-[#090e1a] border border-slate-800 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
                  <Shield className="h-4 w-4 text-purple-400" />
                  <span>Release Readiness Gate Audit</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Full evaluation across static AI review, deterministic CI, runtime behavioral lab verification, and cryptographic evidence.
                </p>
              </div>
              <div>{readiness ? getStatusBadge(readiness.overall_state) : getStatusBadge('PENDING')}</div>
            </div>

            {readiness && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                  <div className="text-xs font-semibold text-slate-400">1. AI Code Review Gate</div>
                  <div>{getStatusBadge(readiness.review_status)}</div>
                  <p className="text-[11px] text-slate-500">Diff inspection for bugs, concurrency, security hazards.</p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                  <div className="text-xs font-semibold text-slate-400">2. Deterministic CI Gate</div>
                  <div>{getStatusBadge(readiness.ci_status)}</div>
                  <p className="text-[11px] text-slate-500">Unit test execution, build checks, zero failures allowed.</p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                  <div className="text-xs font-semibold text-slate-400">3. Independent Lab Gate</div>
                  <div>{getStatusBadge(readiness.lab_status)}</div>
                  <p className="text-[11px] text-slate-500">Autonomous runtime execution against target application.</p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                  <div className="text-xs font-semibold text-slate-400">4. Cryptographic Evidence Gate</div>
                  <div>{getStatusBadge(readiness.evidence_status)}</div>
                  <p className="text-[11px] text-slate-500">SHA-256 chained audit logs and verified run artifacts.</p>
                </div>
              </div>
            )}

            {/* Blockers list */}
            {readiness?.blockers && readiness.blockers.length > 0 && (
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 space-y-2">
                <div className="text-xs font-bold text-rose-300 flex items-center space-x-2">
                  <XCircle className="h-4 w-4" />
                  <span>Active Release Blockers</span>
                </div>
                <div className="space-y-1">
                  {readiness.blockers.map((b, i) => (
                    <div key={i} className="text-xs text-rose-200 flex items-center space-x-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
                      <span>{b}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Invariant Notice */}
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-400 space-y-1">
              <div className="font-semibold text-slate-300 flex items-center space-x-1.5">
                <Lock className="h-3.5 w-3.5 text-amber-400" />
                <span>Security & Release Boundary Notice</span>
              </div>
              <p>
                READY_FOR_RELEASE certifies that all automated and behavioral gates have passed. In accordance with platform non-negotiables, this system does NOT perform automatic production merges or deployments. Final release authorization remains human-mediated.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
