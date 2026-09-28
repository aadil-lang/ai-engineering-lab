'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  FileSearch,
  ShieldCheck,
  ShieldAlert,
  Search,
  RefreshCw,
  Hash,
  Clock,
  Layers,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
  Database,
  ArrowRight
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { governanceApi, api } from '@/lib/api';
import { EvidencePackageModel, TestRun } from '@/types';

export default function EvidenceExplorerPage() {
  const [loading, setLoading] = useState(true);
  const [selectedPackageId, setSelectedPackageId] = useState<string>('pkg_sample_01');
  const [evidencePackage, setEvidencePackage] = useState<EvidencePackageModel | null>(null);
  const [isValid, setIsValid] = useState<boolean | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [recentRuns, setRecentRuns] = useState<TestRun[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchEvidence = async (pkgId: string) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await governanceApi.getEvidence(pkgId);
      setEvidencePackage(res.evidence_package);
      setIsValid(res.is_valid);
    } catch (err: any) {
      setErrorMsg(err.message || `Evidence package '${pkgId}' not found.`);
      setEvidencePackage(null);
      setIsValid(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial load: attempt to load sample or inspect recent runs
    const init = async () => {
      try {
        const runsData = await api.getRuns({ limit: 10 });
        setRecentRuns(runsData.items || []);
      } catch (e) {
        console.warn('Could not load runs for evidence reference:', e);
      }
      fetchEvidence('pkg_sample_01');
    };
    init();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setSelectedPackageId(searchQuery.trim());
      fetchEvidence(searchQuery.trim());
    }
  };

  return (
    <AppShell>
      <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-slate-800/80 gap-4">
          <div>
            <div className="flex items-center space-x-3 mb-2">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 p-[1px] shadow-[0_0_20px_rgba(6,182,212,0.3)]">
                <div className="h-full w-full bg-[#090d16] rounded-[11px] flex items-center justify-center">
                  <FileSearch className="h-5 w-5 text-cyan-400" />
                </div>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white font-sans">
                Evidence Explorer & Integrity Validator
              </h1>
            </div>
            <p className="text-sm text-slate-400">
              Multi-modal evidence packages cryptographically bound to test runs, observed failures, and change authorizations.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs uppercase tracking-wider font-semibold px-2.5 py-1 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono">
              SHA-256 Tamper Protection
            </span>
          </div>
        </div>

        {/* Search bar */}
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search Evidence Package ID (e.g. pkg_sample_01)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>
          <button
            type="submit"
            className="px-5 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs font-mono transition-all"
          >
            Inspect Package
          </button>
        </form>

        {/* Evidence Content Area */}
        {loading ? (
          <div className="p-16 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 text-xs flex flex-col items-center justify-center space-y-3 font-mono">
            <RefreshCw className="h-6 w-6 text-cyan-400 animate-spin" />
            <span>Verifying evidence package cryptographic hashes...</span>
          </div>
        ) : errorMsg ? (
          <div className="p-8 rounded-xl bg-rose-950/20 border border-rose-500/30 text-rose-300 space-y-3 font-mono text-xs">
            <div className="flex items-center space-x-2 font-bold text-sm">
              <ShieldAlert className="h-5 w-5 text-rose-400" />
              <span>Evidence Query Returned No Record</span>
            </div>
            <p className="text-slate-400">{errorMsg}</p>
            <div className="pt-2 text-slate-400">
              Try querying default packages: <code className="text-cyan-300">pkg_sample_01</code>, or run a test scenario to generate new structured packages.
            </div>
          </div>
        ) : evidencePackage ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Metadata & Integrity Verification */}
            <div className="lg:col-span-4 space-y-4 font-mono">
              <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-400 uppercase font-semibold">Integrity Status</span>
                  {isValid ? (
                    <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>INTACT (VALID)</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 text-xs font-semibold">
                      <ShieldAlert className="h-3.5 w-3.5" />
                      <span>TAMPERED / INVALID</span>
                    </span>
                  )}
                </div>

                <div className="space-y-3 text-xs border-t border-slate-800/80 pt-3">
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Package ID</span>
                    <span className="text-white font-semibold">{evidencePackage.package_id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Subject ID</span>
                    <span className="text-cyan-400">{evidencePackage.subject_id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Target Version</span>
                    <span className="text-slate-300">v{evidencePackage.prompt_version || '1.0.0'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Git Commit SHA</span>
                    <span className="text-slate-400">{evidencePackage.git_commit_sha || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">SHA-256 Digest</span>
                    <div className="text-[11px] text-slate-300 break-all p-2 rounded bg-slate-950 border border-slate-800 font-mono mt-1">
                      {evidencePackage.content_hash}
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800/80">
                  <Link
                    href={`/governance`}
                    className="flex items-center justify-between text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                  >
                    <span>View in Governance Control Center</span>
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </div>
              </div>
            </div>

            {/* Right Column: Observations, Failures & Verification Results */}
            <div className="lg:col-span-8 space-y-6">
              {/* Observations Panel */}
              <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center space-x-2">
                  <Layers className="h-4 w-4 text-cyan-400" />
                  <span>Collected Observations ({evidencePackage.observations?.length || 0})</span>
                </h3>
                <div className="space-y-2">
                  {evidencePackage.observations && evidencePackage.observations.length > 0 ? (
                    evidencePackage.observations.map((obs, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 font-mono"
                      >
                        {obs}
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-500 font-mono p-4">No observations recorded.</div>
                  )}
                </div>
              </div>

              {/* Failures & Regressions Panel */}
              <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center space-x-2">
                  <AlertTriangle className="h-4 w-4 text-amber-400" />
                  <span>Detected Failures & Regressions</span>
                </h3>
                <div className="space-y-2">
                  {evidencePackage.failures && evidencePackage.failures.length > 0 ? (
                    evidencePackage.failures.map((fail, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-rose-950/20 border border-rose-500/30 text-xs text-rose-300 font-mono"
                      >
                        {fail}
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-emerald-400 font-mono p-3 bg-emerald-950/10 border border-emerald-500/20 rounded-lg">
                      Zero unmitigated failures recorded in this package.
                    </div>
                  )}
                </div>
              </div>

              {/* Verification Results Key-Value Map */}
              <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3 font-mono">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <span>Independent Verification Results</span>
                </h3>
                <pre className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 overflow-x-auto">
                  {JSON.stringify(evidencePackage.verification_results || {}, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
