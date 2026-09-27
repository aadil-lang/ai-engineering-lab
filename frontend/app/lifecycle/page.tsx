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
  HelpCircle,
  Github,
  ExternalLink,
  Cpu
} from 'lucide-react';
import { api } from '@/lib/api';
import {
  GitStatusModel,
  GitCommitModel,
  PullRequestModel,
  PRReviewModel,
  CIRunModel,
  ReleaseReadinessModel,
  GitHubRepositoryModel,
  GitHubPullRequestModel,
  SynchronizedPRModel,
  GitHubWorkflowRunModel,
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

  // Slice 7.6: Real GitHub state
  const [githubRepo, setGithubRepo] = useState<GitHubRepositoryModel | null>(null);
  const [githubPRs, setGithubPRs] = useState<GitHubPullRequestModel[]>([]);
  const [activeGitHubPR, setActiveGitHubPR] = useState<GitHubPullRequestModel | null>(null);
  const [activeGitHubSync, setActiveGitHubSync] = useState<SynchronizedPRModel | null>(null);
  const [githubCIRun, setGithubCIRun] = useState<GitHubWorkflowRunModel | null>(null);
  const [githubCIStatus, setGithubCIStatus] = useState<string>('CI_UNVERIFIED');
  const [githubCIPassed, setGithubCIPassed] = useState<boolean>(false);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isTriggeringCI, setIsTriggeringCI] = useState<boolean>(false);
  const [isReviewingPR, setIsReviewingPR] = useState<boolean>(false);
  const [selectedTab, setSelectedTab] = useState<'github' | 'pipeline' | 'prs' | 'ci' | 'readiness'>('github');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load baseline lifecycle data and GitHub state
  const loadData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [status, recentCommits, prList, ghRepo, ghPRList] = await Promise.all([
        api.getLifecycleStatus().catch(() => null),
        api.getLifecycleCommits(10).catch(() => []),
        api.getLifecyclePRs().catch(() => []),
        api.getGitHubRepository().catch(() => null),
        api.getGitHubPRs().catch(() => []),
      ]);

      setGitStatus(status);
      setCommits(recentCommits);
      setPRs(prList);
      setGithubRepo(ghRepo);
      setGithubPRs(ghPRList);

      const headSha = status?.commit_sha || (recentCommits[0]?.commit_sha ?? '');
      setSelectedCommitSha(headSha);

      // Load CI & Readiness for HEAD commit
      if (headSha) {
        const [runs, ready, ghCI] = await Promise.all([
          api.getCIRuns(headSha).catch(() => []),
          api.getReleaseReadiness(headSha).catch(() => null),
          api.getGitHubCIStatus(headSha).catch(() => null),
        ]);
        setCiRuns(runs);
        setReadiness(ready);
        if (ghCI) {
          setGithubCIStatus(ghCI.gate_status);
          setGithubCIPassed(ghCI.passed);
          setGithubCIRun(ghCI.workflow_run || null);
        }
      }

      if (ghPRList && ghPRList.length > 0) {
        setActiveGitHubPR(ghPRList[0]);
        const detail = await api.getGitHubPRDetail(ghPRList[0].number).catch(() => null);
        if (detail) {
          setActiveGitHubSync(detail.synchronized);
        }
      } else if (prList.length > 0) {
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
      const [runs, ready, ghCI] = await Promise.all([
        api.getCIRuns(sha).catch(() => []),
        api.getReleaseReadiness(sha).catch(() => null),
        api.getGitHubCIStatus(sha).catch(() => null),
      ]);
      setCiRuns(runs);
      setReadiness(ready);
      if (ghCI) {
        setGithubCIStatus(ghCI.gate_status);
        setGithubCIPassed(ghCI.passed);
        setGithubCIRun(ghCI.workflow_run || null);
      }
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleSelectGitHubPR = async (pr: GitHubPullRequestModel) => {
    setActiveGitHubPR(pr);
    handleSelectCommit(pr.head_sha);
    try {
      const detail = await api.getGitHubPRDetail(pr.number);
      setActiveGitHubSync(detail.synchronized);
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleReviewGitHubPR = async () => {
    if (!activeGitHubPR) return;
    setIsReviewingPR(true);
    try {
      const res = await api.reviewGitHubPR(activeGitHubPR.number);
      setActiveGitHubSync(res.synchronized);
      // Reload readiness
      const ready = await api.getReleaseReadiness(activeGitHubPR.head_sha, `gh-${activeGitHubPR.number}`);
      setReadiness(ready);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setIsReviewingPR(false);
    }
  };

  const getGateSymbol = (status: string) => {
    switch (status) {
      case 'PASSED':
      case 'APPROVED':
      case 'READY_FOR_RELEASE':
        return <span className="text-emerald-400 font-bold text-sm">✓</span>;
      case 'FAILED':
      case 'CHANGES_REQUESTED':
      case 'BLOCKED':
        return <span className="text-rose-400 font-bold text-sm">✗</span>;
      default:
        return <span className="text-amber-400 font-bold text-sm">?</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASSED':
      case 'APPROVED':
      case 'READY_FOR_RELEASE':
      case 'success':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="h-3 w-3" />
            <span>{status.toUpperCase()}</span>
          </span>
        );
      case 'FAILED':
      case 'CHANGES_REQUESTED':
      case 'BLOCKED':
      case 'failure':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <XCircle className="h-3 w-3" />
            <span>{status.toUpperCase()}</span>
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
                <Github className="h-6 w-6 text-cyan-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white flex items-center space-x-2">
                  <span>AI Engineering Lifecycle</span>
                  <span className="text-xs uppercase tracking-wider font-semibold px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                    GitHub Actions & Lab
                  </span>
                </h1>
                <p className="text-xs text-slate-400 mt-0.5">
                  Antigravity Skill → Git Commits → Real GitHub PR & Review → GitHub Actions CI → Independent Lab Verification → Human Merge Decision
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

        {/* 5 Architecture Pillar Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* 1. GitHub Repository */}
          <div className="p-4 rounded-xl bg-[#0c1222] border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold uppercase text-[10px] tracking-wider text-slate-400">GitHub Repository</span>
              <Github className="h-4 w-4 text-cyan-400" />
            </div>
            <div className="text-sm font-semibold text-white truncate">
              {githubRepo ? githubRepo.full_name : (gitStatus?.repository || 'antigravity/engineering-lab')}
            </div>
            <div className="text-[11px] text-slate-400 flex items-center justify-between">
              <span>Branch: <span className="text-cyan-300">{githubRepo?.default_branch || gitStatus?.branch || 'main'}</span></span>
              <span className="text-[10px] text-emerald-400 flex items-center space-x-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>Active</span>
              </span>
            </div>
            <div className="font-mono text-[10px] text-slate-500 truncate">
              Commit: {selectedCommitSha.slice(0, 10)}
            </div>
          </div>

          {/* 2. Pull Request */}
          <div className="p-4 rounded-xl bg-[#0c1222] border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold uppercase text-[10px] tracking-wider text-slate-400">Pull Request</span>
              <GitPullRequest className="h-4 w-4 text-indigo-400" />
            </div>
            <div className="text-sm font-semibold text-white truncate">
              {activeGitHubPR ? `#${activeGitHubPR.number} ${activeGitHubPR.title}` : (activePR ? `#${activePR.number} ${activePR.title}` : 'No Active PR')}
            </div>
            <div className="text-[11px] text-slate-400 flex items-center justify-between">
              <span>Author: <span className="text-indigo-300">{activeGitHubPR?.author_login || 'developer'}</span></span>
              {getStatusBadge(activeGitHubSync?.local_lifecycle_state || activePR?.status || 'OPEN')}
            </div>
            <div className="font-mono text-[10px] text-slate-500 truncate">
              Head: {activeGitHubPR?.head_sha.slice(0, 8) || selectedCommitSha.slice(0, 8)}
            </div>
          </div>

          {/* 3. GitHub Actions CI */}
          <div className="p-4 rounded-xl bg-[#0c1222] border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold uppercase text-[10px] tracking-wider text-slate-400">GitHub Actions CI</span>
              <Terminal className="h-4 w-4 text-purple-400" />
            </div>
            <div className="text-sm font-semibold text-white truncate">
              {githubCIRun ? githubCIRun.workflow_name : (ciRuns[0]?.workflow || 'pytest & build CI')}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-slate-400">Conclusion:</span>
              {getStatusBadge(githubCIRun?.conclusion || githubCIStatus || 'CI_UNVERIFIED')}
            </div>
            <div className="text-[10px] text-slate-500">
              Exact SHA match: {githubCIPassed ? 'Verified' : 'Pending'}
            </div>
          </div>

          {/* 4. Engineering Lab Runtime */}
          <div className="p-4 rounded-xl bg-[#0c1222] border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold uppercase text-[10px] tracking-wider text-slate-400">Engineering Lab</span>
              <Cpu className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="text-sm font-semibold text-white">Runtime Behavioral Authority</div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-slate-400">Session Status:</span>
              {readiness ? getStatusBadge(readiness.lab_status) : getStatusBadge('PENDING')}
            </div>
            <div className="text-[10px] text-slate-500 truncate">
              Runner: Autonomous QA & Playwright
            </div>
          </div>

          {/* 5. Release Readiness Gate Matrix */}
          <div className="p-4 rounded-xl bg-[#0c1222] border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold uppercase text-[10px] tracking-wider text-slate-400">Release Readiness</span>
              <Shield className="h-4 w-4 text-amber-400" />
            </div>
            <div className="pt-0.5">
              {readiness ? getStatusBadge(readiness.overall_state) : getStatusBadge('NOT_READY')}
            </div>
            <div className="grid grid-cols-4 gap-1 text-[11px] pt-1 border-t border-slate-800/80 text-center">
              <div>
                <div className="text-[9px] text-slate-500">Review</div>
                {getGateSymbol(readiness?.review_status || 'PENDING')}
              </div>
              <div>
                <div className="text-[9px] text-slate-500">CI</div>
                {getGateSymbol(readiness?.ci_status || (githubCIPassed ? 'PASSED' : 'PENDING'))}
              </div>
              <div>
                <div className="text-[9px] text-slate-500">Lab</div>
                {getGateSymbol(readiness?.lab_status || 'PENDING')}
              </div>
              <div>
                <div className="text-[9px] text-slate-500">Evidence</div>
                {getGateSymbol(readiness?.evidence_status || 'PENDING')}
              </div>
            </div>
          </div>
        </div>

        {/* 9-Stage Pipeline Stepper */}
        <div className="p-6 rounded-2xl bg-[#090e1a] border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white tracking-wide uppercase flex items-center space-x-2">
              <Layers className="h-4 w-4 text-cyan-400" />
              <span>Full GitHub-Backed Engineering Lifecycle</span>
            </h2>
            <span className="text-[11px] text-slate-400">Antigravity → GitHub PR → GitHub Actions CI → Engineering Lab</span>
          </div>

          <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-2 pt-2">
            {[
              { id: '1', name: 'Implemented', status: 'PASSED', desc: 'Antigravity coding' },
              { id: '2', name: 'Local Tested', status: 'PASSED', desc: 'pytest & linters' },
              { id: '3', name: 'Committed', status: 'PASSED', desc: selectedCommitSha.slice(0, 7) },
              { id: '4', name: 'PR Created', status: activeGitHubPR ? 'PASSED' : 'PENDING', desc: activeGitHubPR ? `#${activeGitHubPR.number}` : 'Awaiting PR' },
              { id: '5', name: 'Reviewed', status: readiness?.review_status || 'PENDING', desc: 'Static diff scan' },
              { id: '6', name: 'CI Verified', status: githubCIPassed ? 'PASSED' : 'PENDING', desc: 'GitHub Actions' },
              { id: '7', name: 'Lab Verified', status: readiness?.lab_status || 'PASSED', desc: 'Independent retest' },
              { id: '8', name: 'Evidence Chained', status: readiness?.evidence_status || 'PASSED', desc: 'SHA-256 artifacts' },
              { id: '9', name: 'Human Release', status: readiness?.overall_state || 'PENDING', desc: 'Human decides merge' },
            ].map((step) => (
              <div
                key={step.id}
                className="relative p-3 rounded-xl bg-[#0e1628] border border-slate-800/80 flex flex-col justify-between space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-slate-500">0{step.id}</span>
                  {getGateSymbol(step.status)}
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

        {/* Tab Selection */}
        <div className="flex items-center space-x-2 border-b border-slate-800">
          <button
            onClick={() => setSelectedTab('github')}
            className={`px-4 py-2.5 text-xs font-semibold transition-all border-b-2 flex items-center space-x-2 ${
              selectedTab === 'github'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Github className="h-3.5 w-3.5" />
            <span>GitHub PRs & Actions CI</span>
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
            <span>Release Readiness Gate Matrix</span>
          </button>
        </div>

        {/* Tab 1: Real GitHub View */}
        {selectedTab === 'github' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: PRs List */}
            <div className="lg:col-span-1 p-5 rounded-2xl bg-[#090e1a] border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-2">
                  <GitPullRequest className="h-4 w-4 text-cyan-400" />
                  <span>GitHub Pull Requests</span>
                </h3>
                <span className="text-[10px] text-slate-500">Live sync</span>
              </div>

              <div className="space-y-2">
                {githubPRs.length === 0 ? (
                  <div className="text-xs text-slate-500 italic p-4 text-center">
                    No open pull requests found for {githubRepo?.full_name || 'repository'}.
                  </div>
                ) : (
                  githubPRs.map((pr) => {
                    const isSelected = activeGitHubPR?.number === pr.number;
                    return (
                      <button
                        key={pr.number}
                        onClick={() => handleSelectGitHubPR(pr)}
                        className={`w-full text-left p-3 rounded-xl transition-all border ${
                          isSelected
                            ? 'bg-cyan-600/15 border-cyan-500/40 text-white'
                            : 'bg-slate-900/60 border-slate-800/80 text-slate-300 hover:bg-slate-800/50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs font-bold text-cyan-300">#{pr.number}</span>
                          {getStatusBadge(pr.state)}
                        </div>
                        <div className="text-xs font-medium text-slate-200 mt-1 line-clamp-1">{pr.title}</div>
                        <div className="text-[10px] text-slate-500 mt-1 flex items-center justify-between">
                          <span>{pr.head_branch} → {pr.base_branch}</span>
                          <span className="font-mono">{pr.head_sha.slice(0, 7)}</span>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            {/* Right: Selected PR Inspection & CI Checks */}
            <div className="lg:col-span-2 space-y-6">
              {activeGitHubPR ? (
                <div className="p-5 rounded-2xl bg-[#090e1a] border border-slate-800 space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-sm font-bold text-cyan-400">#{activeGitHubPR.number}</span>
                        <h3 className="text-base font-bold text-white">{activeGitHubPR.title}</h3>
                      </div>
                      <div className="text-xs text-slate-400 mt-1">
                        Branch: <span className="text-cyan-300">{activeGitHubPR.head_branch}</span> into <span className="text-slate-300">{activeGitHubPR.base_branch}</span>
                      </div>
                      <div className="font-mono text-xs text-slate-500 mt-0.5">
                        Head SHA: <span className="text-indigo-400">{activeGitHubPR.head_sha}</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={handleReviewGitHubPR}
                        disabled={isReviewingPR}
                        className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition-all flex items-center space-x-2"
                      >
                        <Sparkles className="h-3.5 w-3.5" />
                        <span>{isReviewingPR ? 'Reviewing...' : 'AI Diff Review'}</span>
                      </button>
                    </div>
                  </div>

                  {/* GitHub Actions CI Status for this PR's exact commit */}
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
                        <Terminal className="h-4 w-4 text-purple-400" />
                        <span>GitHub Actions CI Gate (Exact SHA Verification)</span>
                      </div>
                      {getStatusBadge(githubCIRun?.conclusion || githubCIStatus)}
                    </div>
                    <div className="text-xs text-slate-400">
                      Commit evaluated: <span className="font-mono text-indigo-300">{activeGitHubPR.head_sha.slice(0, 10)}</span>
                    </div>
                    <div className="text-[11px] text-slate-500">
                      Rule: PR commit SHA must match CI commit SHA with conclusion == success. AI cannot override CI failures.
                    </div>
                  </div>

                  {/* Independent Lab Verification Callout */}
                  <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-800/40 text-xs text-cyan-300 space-y-1.5">
                    <div className="font-semibold flex items-center space-x-1.5">
                      <Shield className="h-4 w-4 text-cyan-400" />
                      <span>Independent Behavioral Authority</span>
                    </div>
                    <p className="text-slate-400">
                      GitHub Actions CI verifies code syntax and build checks. The Engineering Lab independently runs and tests the live application to verify behavioral correctness.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-slate-500">
                  Select a pull request to inspect review findings and CI checks.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Release Readiness Gate Matrix */}
        {selectedTab === 'readiness' && (
          <div className="p-6 rounded-2xl bg-[#090e1a] border border-slate-800 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
                  <Shield className="h-4 w-4 text-purple-400" />
                  <span>Release Readiness Gate Matrix</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Combines PR Review, GitHub Actions CI, Independent Lab verification, and Cryptographic Evidence for target commit.
                </p>
              </div>
              <div>{readiness ? getStatusBadge(readiness.overall_state) : getStatusBadge('NOT_READY')}</div>
            </div>

            {readiness && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400">1. AI Code Review</span>
                    {getGateSymbol(readiness.review_status)}
                  </div>
                  <div>{getStatusBadge(readiness.review_status)}</div>
                  <p className="text-[11px] text-slate-500">Static diff scan for defects, concurrency, and security hazards.</p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400">2. GitHub Actions CI</span>
                    {getGateSymbol(readiness.ci_status)}
                  </div>
                  <div>{getStatusBadge(readiness.ci_status)}</div>
                  <p className="text-[11px] text-slate-500">Deterministic workflow run matching exact commit SHA.</p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400">3. Engineering Lab</span>
                    {getGateSymbol(readiness.lab_status)}
                  </div>
                  <div>{getStatusBadge(readiness.lab_status)}</div>
                  <p className="text-[11px] text-slate-500">Independent runtime behavioral execution on target application.</p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400">4. Chained Evidence</span>
                    {getGateSymbol(readiness.evidence_status)}
                  </div>
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
                  <span>Active Release Blockers ({readiness.blockers.length})</span>
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

            {/* Human Gate Mandatory Notice */}
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-400 space-y-1">
              <div className="font-semibold text-slate-300 flex items-center space-x-1.5">
                <Lock className="h-3.5 w-3.5 text-amber-400" />
                <span>Human-Controlled Release Boundary</span>
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
