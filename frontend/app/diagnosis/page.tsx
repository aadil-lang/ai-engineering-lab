'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Stethoscope,
  AlertOctagon,
  Search,
  RefreshCw,
  Clock,
  Layers,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
  Bug,
  Sparkles,
  GitBranch,
  ArrowRight
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { api } from '@/lib/api';
import { EngineeringDiagnosis } from '@/types';

export default function DiagnosisOverviewPage() {
  const [loading, setLoading] = useState(true);
  const [diagnoses, setDiagnoses] = useState<EngineeringDiagnosis[]>([]);
  const [selectedDiagnosis, setSelectedDiagnosis] = useState<EngineeringDiagnosis | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchDiagnoses = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.listDiagnoses(50, 0);
      setDiagnoses(data || []);
      if (data && data.length > 0) {
        setSelectedDiagnosis(data[0]);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load failure diagnoses.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnoses();
  }, []);

  const filteredDiagnoses = diagnoses.filter((d) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      d.diagnosis_id.toLowerCase().includes(q) ||
      d.run_id.toLowerCase().includes(q) ||
      d.failure_category.toLowerCase().includes(q) ||
      (d.root_cause_summary || '').toLowerCase().includes(q)
    );
  });

  return (
    <AppShell>
      <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-slate-800/80 gap-4">
          <div>
            <div className="flex items-center space-x-3 mb-2">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-rose-500 to-amber-500 p-[1px] shadow-[0_0_20px_rgba(244,63,94,0.3)]">
                <div className="h-full w-full bg-[#090d16] rounded-[11px] flex items-center justify-center">
                  <Stethoscope className="h-5 w-5 text-rose-400" />
                </div>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white font-sans">
                AI Engineering Failure Diagnoses
              </h1>
            </div>
            <p className="text-sm text-slate-400">
              Autonomous causal inference distinguishing observed facts, AI interpretations, and remediation hypotheses.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs uppercase tracking-wider font-semibold px-2.5 py-1 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-mono">
              Epistemic Boundary Enforced
            </span>
            <button
              onClick={fetchDiagnoses}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              title="Refresh Diagnoses"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Epistemic Distinction Notice */}
        <div className="p-4 rounded-xl border border-indigo-500/30 bg-indigo-950/20 text-indigo-200 text-xs sm:text-sm flex items-start space-x-3">
          <Sparkles className="h-5 w-5 text-cyan-400 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <span className="font-semibold text-cyan-300">Epistemic Framework:</span>
            <p className="text-slate-300">
              <strong>Observed Facts</strong> (raw HTTP status codes, DOM elements, stack traces) are separated from{' '}
              <strong>AI Interpretations</strong> (causal reasoning) and <strong>Recommendations</strong>. Hypotheses are never asserted as absolute facts.
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search diagnoses by ID, run ID, or failure category..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-rose-500 font-mono"
          />
        </div>

        {/* Main 2-column Diagnosis Inspector */}
        {loading ? (
          <div className="p-16 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 text-xs flex flex-col items-center justify-center space-y-3 font-mono">
            <RefreshCw className="h-6 w-6 text-rose-400 animate-spin" />
            <span>Loading autonomous diagnoses...</span>
          </div>
        ) : diagnoses.length === 0 ? (
          <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 font-mono text-xs">
            No failure diagnoses currently recorded. Launch a test run with simulated failure or real bug reproduction to trigger autonomous diagnosis.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Diagnoses List */}
            <div className="lg:col-span-5 space-y-3">
              <h2 className="text-xs uppercase tracking-wider font-semibold text-slate-400 font-mono">
                Diagnosed Failures ({filteredDiagnoses.length})
              </h2>
              <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
                {filteredDiagnoses.map((diag) => {
                  const isSelected = selectedDiagnosis?.diagnosis_id === diag.diagnosis_id;
                  return (
                    <div
                      key={diag.diagnosis_id}
                      onClick={() => setSelectedDiagnosis(diag)}
                      className={`p-4 rounded-xl border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-slate-900 border-rose-500/60 shadow-[0_0_15px_rgba(244,63,94,0.15)]'
                          : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between font-mono text-xs mb-1.5">
                        <span className="font-bold text-rose-400">{diag.failure_category}</span>
                        <span className="text-[10px] text-slate-500">{diag.run_id}</span>
                      </div>
                      <p className="text-xs text-slate-300 line-clamp-2">{diag.root_cause_summary}</p>
                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800/80 text-[11px] font-mono text-slate-500">
                        <span>Confidence: {Math.round(diag.confidence_score * 100)}%</span>
                        <span className="text-cyan-400 flex items-center space-x-1">
                          <span>Inspect</span>
                          <ChevronRight className="h-3 w-3" />
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right Column: Detailed Diagnosis Breakdown */}
            <div className="lg:col-span-7">
              {selectedDiagnosis ? (
                <div className="p-6 rounded-xl bg-slate-900/70 border border-slate-800 space-y-6 font-mono">
                  {/* Title & Metadata */}
                  <div className="flex items-start justify-between border-b border-slate-800/80 pb-4">
                    <div>
                      <span className="text-[10px] text-rose-400 uppercase font-bold tracking-wider">
                        Diagnosis Detail
                      </span>
                      <h2 className="text-lg font-bold text-white mt-0.5">{selectedDiagnosis.title || selectedDiagnosis.failure_category}</h2>
                      <div className="text-xs text-slate-400 mt-1">
                        ID: <span className="text-cyan-400">{selectedDiagnosis.diagnosis_id}</span> · Run:{' '}
                        <Link href={`/runs/${selectedDiagnosis.run_id}`} className="text-indigo-400 hover:underline">
                          {selectedDiagnosis.run_id}
                        </Link>
                      </div>
                    </div>
                    <div className="px-3 py-1 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-bold">
                      {Math.round(selectedDiagnosis.confidence_score * 100)}% CONFIDENCE
                    </div>
                  </div>

                  {/* Section 1: Observed Facts */}
                  <div className="space-y-2">
                    <div className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center space-x-2">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>1. Observed Facts (Deterministic Telemetry)</span>
                    </div>
                    <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200">
                      <div>Suspected Component: <span className="text-cyan-300">{selectedDiagnosis.suspected_component}</span></div>
                      {selectedDiagnosis.deterministic_signals && selectedDiagnosis.deterministic_signals.length > 0 && (
                        <div className="mt-2 space-y-1">
                          <span className="text-slate-400 text-[10px] uppercase font-bold">Signals Captured:</span>
                          {selectedDiagnosis.deterministic_signals.map((sig, sIdx) => (
                            <div key={sIdx} className="text-slate-300 text-[11px]">
                              • <span className="text-indigo-300">{sig.signal_type}</span>: {sig.summary}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Section 2: AI Causal Interpretation */}
                  <div className="space-y-2">
                    <div className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center space-x-2">
                      <Sparkles className="h-4 w-4" />
                      <span>2. AI Causal Interpretation</span>
                    </div>
                    <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 leading-relaxed">
                      {selectedDiagnosis.root_cause_summary}
                    </div>
                  </div>

                  {/* Section 3: Recommended Remediation Action */}
                  <div className="space-y-2">
                    <div className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center space-x-2">
                      <AlertTriangle className="h-4 w-4" />
                      <span>3. Recommended Remediation Action</span>
                    </div>
                    <div className="p-3.5 rounded-lg bg-amber-950/20 border border-amber-500/30 text-xs text-amber-200">
                      <div className="font-semibold text-white">{selectedDiagnosis.suggested_fix}</div>
                      {selectedDiagnosis.regression_test_spec && (
                        <div className="mt-2 text-slate-400 text-[11px]">
                          Regression Test Spec: <code className="text-cyan-300">{selectedDiagnosis.regression_test_spec}</code>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Action Bar */}
                  <div className="pt-2 flex items-center justify-between border-t border-slate-800/80">
                    <Link
                      href={`/runs/${selectedDiagnosis.run_id}`}
                      className="inline-flex items-center space-x-2 text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                    >
                      <span>Open Full Run Workspace</span>
                      <ArrowRight className="h-4 w-4" />
                    </Link>

                    <Link
                      href="/governance"
                      className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs transition-all"
                    >
                      <span>Review in Governance</span>
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 text-xs font-mono">
                  Select a diagnosis to inspect observed facts and causal analysis.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
