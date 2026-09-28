'use client';

import React, { useState, useEffect } from 'react';
import { AppShell } from '@/components/AppShell';
import { provenanceApi } from '@/lib/api';
import {
  EngineeringLifecycleEventModel,
  ProvenanceChainVerificationResultModel,
  ProvenanceTraceModel,
} from '@/types';
import {
  ShieldCheck,
  ShieldAlert,
  GitCommit,
  GitPullRequest,
  CheckCircle2,
  Clock,
  Layers,
  ArrowRight,
  User,
  Bot,
  Terminal,
  Activity,
  Search,
  RefreshCw,
  Hash,
  FileCheck,
  Stethoscope,
  Wrench,
  UserCheck,
  Key,
} from 'lucide-react';

export default function ProvenancePage() {
  const [correlationId, setCorrelationId] = useState('corr_feat_question_gen_884');
  const [trace, setTrace] = useState<ProvenanceTraceModel | null>(null);
  const [verification, setVerification] = useState<ProvenanceChainVerificationResultModel | null>(null);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<EngineeringLifecycleEventModel | null>(null);

  const fetchTraceAndVerify = async (corrId: string) => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch trace
      const traceRes = await provenanceApi.getTrace(corrId);
      setTrace(traceRes);
      if (traceRes.events.length > 0) {
        setSelectedEvent(traceRes.events[traceRes.events.length - 1]);
      }

      // 2. Verify cryptographic chain
      const verifyRes = await provenanceApi.verifyChain(corrId);
      setVerification(verifyRes);
    } catch (err: any) {
      setError(err?.message || 'Failed to load provenance trace.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyChain = async () => {
    setVerifying(true);
    try {
      const verifyRes = await provenanceApi.verifyChain(correlationId);
      setVerification(verifyRes);
    } catch (err: any) {
      setError(err?.message || 'Verification audit failed.');
    } finally {
      setVerifying(false);
    }
  };

  useEffect(() => {
    fetchTraceAndVerify(correlationId);
  }, []);

  const getActorIcon = (actorType: string) => {
    switch (actorType) {
      case 'HUMAN':
        return <User className="w-3.5 h-3.5 text-blue-400" />;
      case 'AI_AGENT':
        return <Bot className="w-3.5 h-3.5 text-purple-400" />;
      case 'CI':
        return <Activity className="w-3.5 h-3.5 text-amber-400" />;
      default:
        return <Terminal className="w-3.5 h-3.5 text-gray-400" />;
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded">
                Slice 8L
              </span>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Unified Engineering Provenance & Change Trace
              </h1>
            </div>
            <p className="text-sm text-gray-400 mt-1">
              Append-only, cryptographically hashed timeline tracking changes from inception to post-change reliability.
            </p>
          </div>

          {/* Search Correlation & Action Buttons */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                value={correlationId}
                onChange={(e) => setCorrelationId(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchTraceAndVerify(correlationId)}
                placeholder="Search correlation ID..."
                className="pl-9 pr-3 py-1.5 bg-gray-900 border border-gray-800 rounded-lg text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 w-64"
              />
            </div>
            <button
              onClick={() => fetchTraceAndVerify(correlationId)}
              disabled={loading}
              className="p-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors disabled:opacity-50"
              title="Refresh Trace"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={handleVerifyChain}
              disabled={verifying}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition-colors shadow-sm disabled:opacity-50"
            >
              <ShieldCheck className={`w-4 h-4 ${verifying ? 'animate-spin' : ''}`} />
              Verify Chain
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-950/40 border border-red-800/60 rounded-lg text-red-300 text-sm">
            {error}
          </div>
        )}

        {/* Verification Status Banner */}
        {verification && (
          <div className={`p-4 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
            verification.is_valid
              ? 'bg-emerald-950/20 border-emerald-900/40 text-emerald-300'
              : 'bg-red-950/30 border-red-900/50 text-red-300'
          }`}>
            <div className="flex items-center gap-3">
              {verification.is_valid ? (
                <ShieldCheck className="w-6 h-6 text-emerald-400 flex-shrink-0" />
              ) : (
                <ShieldAlert className="w-6 h-6 text-red-400 flex-shrink-0" />
              )}
              <div>
                <div className="font-bold text-sm text-white">
                  {verification.is_valid
                    ? 'Cryptographic Chain Verified'
                    : 'Cryptographic Chain Integrity Violation Detected'}
                </div>
                <div className="text-xs text-gray-400 mt-0.5">{verification.details}</div>
              </div>
            </div>

            <div className="flex items-center gap-6 text-xs font-mono">
              <div>
                <span className="text-gray-500">AUDITED EVENTS: </span>
                <span className="font-bold text-white">{verification.verified_events}</span> / {verification.total_events}
              </div>
              <div>
                <span className="text-gray-500">TAMPER STATUS: </span>
                <span className={`font-bold ${verification.is_valid ? 'text-emerald-400' : 'text-red-400'}`}>
                  {verification.violation_type || 'NONE'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Trace Summary & Split View */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Column 1 & 2: Timeline */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between border-b border-gray-800 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-sm font-semibold text-white">Chronological Lifecycle Timeline</h3>
                </div>
                {trace && (
                  <span className="text-xs font-mono text-gray-400">
                    {trace.total_events} Events Recorded
                  </span>
                )}
              </div>

              {(!trace || trace.events.length === 0) ? (
                <div className="py-12 text-center text-gray-500 text-sm">
                  No lifecycle events recorded for correlation ID '{correlationId}'.
                </div>
              ) : (
                <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-800">
                  {trace.events.map((evt) => {
                    const isSelected = selectedEvent?.event_id === evt.event_id;
                    return (
                      <div
                        key={evt.event_id}
                        onClick={() => setSelectedEvent(evt)}
                        className={`relative cursor-pointer p-3.5 rounded-lg border transition-all ${
                          isSelected
                            ? 'bg-indigo-950/40 border-indigo-700/60 shadow-sm'
                            : 'bg-gray-950 border-gray-800 hover:border-gray-700 hover:bg-gray-900/60'
                        }`}
                      >
                        {/* Sequence Node Dot */}
                        <div className={`absolute -left-[27px] top-4 w-3.5 h-3.5 rounded-full border-2 bg-gray-950 ${
                          isSelected ? 'border-indigo-400 bg-indigo-500' : 'border-gray-600'
                        }`} />

                        <div className="flex items-center justify-between gap-2 mb-1.5">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-gray-500">#{evt.sequence_number}</span>
                            <span className="text-xs font-bold text-white tracking-wide">
                              {evt.event_type}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-500 font-mono">
                              {new Date(evt.timestamp).toLocaleTimeString()}
                            </span>
                            <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-gray-850 border border-gray-800 text-gray-300">
                              {getActorIcon(evt.actor_type)}
                              {evt.actor_id}
                            </span>
                          </div>
                        </div>

                        {/* Hash Chaining Pill */}
                        <div className="flex items-center gap-2 text-[11px] font-mono text-gray-500 mt-2">
                          <Hash className="w-3 h-3 text-gray-600" />
                          <span className="truncate max-w-[120px]" title={evt.previous_event_hash}>
                            {evt.previous_event_hash ? evt.previous_event_hash.slice(0, 10) + '...' : 'GENESIS'}
                          </span>
                          <ArrowRight className="w-3 h-3 text-gray-600 flex-shrink-0" />
                          <span className="text-indigo-400 font-semibold truncate max-w-[120px]" title={evt.event_hash}>
                            {evt.event_hash.slice(0, 10)}...
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Column 3: Event Details & Cryptographic Inspector */}
          <div className="space-y-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-1.5">
                  <Key className="w-4 h-4 text-emerald-400" />
                  Event Provenance Inspector
                </h3>
              </div>

              {!selectedEvent ? (
                <div className="py-8 text-center text-gray-500 text-xs">
                  Select an event in the timeline to inspect its cryptographic payload and domain references.
                </div>
              ) : (
                <div className="space-y-3 text-xs">
                  <div>
                    <div className="text-gray-500 font-mono">EVENT ID</div>
                    <div className="font-mono text-gray-200 mt-0.5">{selectedEvent.event_id}</div>
                  </div>

                  <div>
                    <div className="text-gray-500 font-mono">TYPE & ACTOR</div>
                    <div className="text-gray-200 mt-0.5 font-semibold">
                      {selectedEvent.event_type} ({selectedEvent.actor_type} - {selectedEvent.actor_id})
                    </div>
                  </div>

                  <div>
                    <div className="text-gray-500 font-mono">TIMESTAMP</div>
                    <div className="text-gray-300 font-mono mt-0.5">{selectedEvent.timestamp}</div>
                  </div>

                  {/* Entity References */}
                  <div className="pt-2 border-t border-gray-800 space-y-1.5">
                    <div className="text-gray-400 font-semibold mb-1">Referenced Subsystem Entities:</div>
                    {selectedEvent.git_commit && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">Git Commit:</span>
                        <span className="font-mono text-gray-300">{selectedEvent.git_commit.slice(0, 8)}</span>
                      </div>
                    )}
                    {selectedEvent.pull_request_id && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">Pull Request:</span>
                        <span className="font-mono text-gray-300">{selectedEvent.pull_request_id}</span>
                      </div>
                    )}
                    {selectedEvent.run_id && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">Run ID:</span>
                        <span className="font-mono text-indigo-400">{selectedEvent.run_id}</span>
                      </div>
                    )}
                    {selectedEvent.change_set_id && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">ChangeSet:</span>
                        <span className="font-mono text-gray-300">{selectedEvent.change_set_id}</span>
                      </div>
                    )}
                    {selectedEvent.plan_id && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">Plan ID:</span>
                        <span className="font-mono text-gray-300">{selectedEvent.plan_id}</span>
                      </div>
                    )}
                    {selectedEvent.evidence_id && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">Evidence ID:</span>
                        <span className="font-mono text-gray-300">{selectedEvent.evidence_id}</span>
                      </div>
                    )}
                    {selectedEvent.diagnosis_id && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">Diagnosis ID:</span>
                        <span className="font-mono text-gray-300">{selectedEvent.diagnosis_id}</span>
                      </div>
                    )}
                    {selectedEvent.governance_id && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">Governance ID:</span>
                        <span className="font-mono text-amber-400">{selectedEvent.governance_id}</span>
                      </div>
                    )}
                  </div>

                  {/* Cryptographic Hashes */}
                  <div className="pt-2 border-t border-gray-800 space-y-1.5">
                    <div className="text-gray-400 font-semibold mb-1">Cryptographic Proofs:</div>
                    <div>
                      <div className="text-gray-500 font-mono text-[11px]">PREVIOUS HASH</div>
                      <div className="font-mono text-[10px] text-gray-400 break-all bg-gray-950 p-1.5 rounded border border-gray-800">
                        {selectedEvent.previous_event_hash || 'GENESIS'}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-500 font-mono text-[11px]">EVENT HASH (SHA-256)</div>
                      <div className="font-mono text-[10px] text-emerald-400 break-all bg-gray-950 p-1.5 rounded border border-emerald-900/40">
                        {selectedEvent.event_hash}
                      </div>
                    </div>
                  </div>

                  {/* Metadata Payload */}
                  {selectedEvent.metadata && Object.keys(selectedEvent.metadata).length > 0 && (
                    <div className="pt-2 border-t border-gray-800">
                      <div className="text-gray-400 font-semibold mb-1">Structured Metadata:</div>
                      <pre className="p-2 bg-gray-950 rounded text-[11px] font-mono text-gray-300 overflow-x-auto border border-gray-800">
                        {JSON.stringify(selectedEvent.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
