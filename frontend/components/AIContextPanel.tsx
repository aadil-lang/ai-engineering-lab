'use client';

import React, { useState } from 'react';
import {
  DogfoodingRunContextModel,
  ComponentVerificationModel,
  CausalClassificationModel,
  RetestResultModel,
  RetestComparisonModel,
  ProvenanceTimelineEntry,
  CausalLayer,
  RetestTransition,
  ContractStatus,
  ContextVerificationStatus,
  EpistemicStatus,
} from '@/types';
import {
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  GitCommit,
  Cpu,
  FileCode,
  Database,
  Wrench,
  Layers,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  ArrowRight,
  ArrowDown,
  ChevronDown,
  ChevronRight,
  Eye,
  EyeOff,
  Fingerprint,
  Link2,
  Activity,
  RefreshCw,
  Sparkles,
  Clock,
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════

const EPISTEMIC_COLORS: Record<EpistemicStatus, { bg: string; text: string; border: string; label: string }> = {
  OBSERVED:   { bg: 'bg-emerald-950/80', text: 'text-emerald-400', border: 'border-emerald-500/40', label: 'Observed' },
  DECLARED:   { bg: 'bg-slate-800/80',   text: 'text-slate-400',   border: 'border-slate-500/40',   label: 'Declared' },
  INFERRED:   { bg: 'bg-amber-950/80',   text: 'text-amber-400',   border: 'border-amber-500/40',   label: 'Inferred' },
  HYPOTHESIS: { bg: 'bg-purple-950/80',  text: 'text-purple-400',  border: 'border-purple-500/40',  label: 'Hypothesis' },
};

const VERIFICATION_ICONS: Record<ContextVerificationStatus, React.ReactNode> = {
  VERIFIED:    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />,
  MISMATCH:    <XCircle className="h-3.5 w-3.5 text-red-400" />,
  UNAVAILABLE: <HelpCircle className="h-3.5 w-3.5 text-slate-500" />,
};

const CAUSAL_LAYER_META: Record<CausalLayer, { icon: React.ReactNode; label: string; color: string }> = {
  PROMPT_DEFECT:     { icon: <FileCode className="h-4 w-4" />,  label: 'Prompt Defect',     color: 'text-violet-400' },
  MODEL_BEHAVIOR:    { icon: <Cpu className="h-4 w-4" />,       label: 'Model Behavior',    color: 'text-blue-400' },
  RETRIEVAL_FAILURE: { icon: <Database className="h-4 w-4" />,  label: 'Retrieval Failure', color: 'text-amber-400' },
  CONTEXT_FAILURE:   { icon: <Link2 className="h-4 w-4" />,     label: 'Context Failure',   color: 'text-orange-400' },
  TOOL_FAILURE:      { icon: <Wrench className="h-4 w-4" />,    label: 'Tool Failure',      color: 'text-cyan-400' },
  APPLICATION_LOGIC: { icon: <Layers className="h-4 w-4" />,    label: 'Application Logic', color: 'text-rose-400' },
  PARSER_FAILURE:    { icon: <FileCode className="h-4 w-4" />,  label: 'Parser Failure',    color: 'text-pink-400' },
  SCHEMA_FAILURE:    { icon: <AlertTriangle className="h-4 w-4" />, label: 'Schema Failure', color: 'text-red-400' },
  DATA_FAILURE:      { icon: <Database className="h-4 w-4" />,  label: 'Data Failure',      color: 'text-yellow-400' },
  EVALUATOR_FAILURE: { icon: <Activity className="h-4 w-4" />,  label: 'Evaluator Failure', color: 'text-teal-400' },
  UNKNOWN:           { icon: <HelpCircle className="h-4 w-4" />,label: 'Unknown',           color: 'text-slate-400' },
};

const TRANSITION_META: Record<RetestTransition, { label: string; color: string; icon: React.ReactNode }> = {
  NEW_PASS:      { label: 'New Pass',      color: 'text-emerald-400', icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> },
  NEW_FAILURE:   { label: 'New Failure',   color: 'text-red-400',     icon: <XCircle className="h-3.5 w-3.5 text-red-400" /> },
  FIXED_FAILURE: { label: 'Fixed',         color: 'text-green-400',   icon: <CheckCircle2 className="h-3.5 w-3.5 text-green-400" /> },
  REGRESSION:    { label: 'Regression',    color: 'text-red-500',     icon: <AlertTriangle className="h-3.5 w-3.5 text-red-500" /> },
  UNCHANGED:     { label: 'Unchanged',     color: 'text-slate-400',   icon: <ArrowRight className="h-3.5 w-3.5 text-slate-400" /> },
};

function EpistemicBadge({ status }: { status: EpistemicStatus }) {
  const meta = EPISTEMIC_COLORS[status];
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${meta.bg} ${meta.text} border ${meta.border}`}>
      {meta.label}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// 1. Context Binding Panel
// ═══════════════════════════════════════════════════════════════════════

interface ContextBindingPanelProps {
  context: DogfoodingRunContextModel;
}

export const ContextBindingPanel: React.FC<ContextBindingPanelProps> = ({ context }) => {
  const [expanded, setExpanded] = useState(true);
  const [showVerifications, setShowVerifications] = useState(false);

  const hasAnyMismatch = context.component_verifications.some(v => v.status === 'MISMATCH');
  const verifiedCount = context.component_verifications.filter(v => v.status === 'VERIFIED').length;
  const totalCount = context.component_verifications.length;

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/70 backdrop-blur-sm overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-800/40 transition-colors"
      >
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg ${hasAnyMismatch ? 'bg-red-950/60' : 'bg-emerald-950/60'}`}>
            {hasAnyMismatch
              ? <ShieldAlert className="h-5 w-5 text-red-400" />
              : <ShieldCheck className="h-5 w-5 text-emerald-400" />
            }
          </div>
          <div className="text-left">
            <h3 className="text-sm font-semibold text-slate-100">AI Application Context</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              {context.application_id} · {context.feature_id}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <span className={`text-xs font-mono px-2 py-1 rounded ${hasAnyMismatch ? 'bg-red-950/60 text-red-400' : 'bg-emerald-950/60 text-emerald-400'}`}>
            {verifiedCount}/{totalCount} verified
          </span>
          {expanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t border-slate-700/40">
          {/* Provenance Grid */}
          <div className="grid grid-cols-2 gap-3 pt-4">
            <ProvenanceItem
              icon={<Fingerprint className="h-4 w-4 text-slate-400" />}
              label="Context Hash"
              value={context.context_hash.slice(0, 12) + '…'}
              mono
            />
            <ProvenanceItem
              icon={<GitCommit className="h-4 w-4 text-slate-400" />}
              label="Git Commit"
              value={context.git_commit_sha?.slice(0, 10) || 'N/A'}
              mono
            />
            <ProvenanceItem
              icon={<FileCode className="h-4 w-4 text-violet-400" />}
              label="Prompt"
              value={`${context.prompt_id} v${context.prompt_version}`}
            />
            <ProvenanceItem
              icon={<Cpu className="h-4 w-4 text-blue-400" />}
              label="Model"
              value={`${context.model}${context.model_version ? ` (${context.model_version})` : ''}`}
            />
            <ProvenanceItem
              icon={<Link2 className="h-4 w-4 text-cyan-400" />}
              label="Context ID"
              value={context.evaluation_context_id}
              mono
            />
            <ProvenanceItem
              icon={<Activity className="h-4 w-4 text-amber-400" />}
              label="Contracts"
              value={`${context.behavioral_contract_ids.length} bound`}
            />
          </div>

          {/* Configuration Hashes */}
          {(context.retrieval_configuration_hash || context.tool_configuration_hash || context.parser_configuration_hash) && (
            <div className="flex flex-wrap gap-2 mt-2">
              {context.retrieval_configuration_hash && (
                <span className="inline-flex items-center space-x-1 px-2 py-1 rounded-md bg-slate-800/80 text-[11px] font-mono text-slate-400 border border-slate-700/60">
                  <Database className="h-3 w-3" />
                  <span>retrieval:{context.retrieval_configuration_hash.slice(0, 8)}</span>
                </span>
              )}
              {context.tool_configuration_hash && (
                <span className="inline-flex items-center space-x-1 px-2 py-1 rounded-md bg-slate-800/80 text-[11px] font-mono text-slate-400 border border-slate-700/60">
                  <Wrench className="h-3 w-3" />
                  <span>tools:{context.tool_configuration_hash.slice(0, 8)}</span>
                </span>
              )}
              {context.parser_configuration_hash && (
                <span className="inline-flex items-center space-x-1 px-2 py-1 rounded-md bg-slate-800/80 text-[11px] font-mono text-slate-400 border border-slate-700/60">
                  <FileCode className="h-3 w-3" />
                  <span>parser:{context.parser_configuration_hash.slice(0, 8)}</span>
                </span>
              )}
            </div>
          )}

          {/* Verification Table */}
          <div>
            <button
              onClick={() => setShowVerifications(!showVerifications)}
              className="flex items-center space-x-2 text-xs text-slate-400 hover:text-slate-300 transition-colors"
            >
              {showVerifications ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
              <span>{showVerifications ? 'Hide' : 'Show'} Component Verifications</span>
            </button>

            {showVerifications && (
              <div className="mt-3 rounded-lg border border-slate-700/60 overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-slate-800/60">
                      <th className="px-3 py-2 text-left font-semibold text-slate-300">Component</th>
                      <th className="px-3 py-2 text-left font-semibold text-slate-300">Status</th>
                      <th className="px-3 py-2 text-left font-semibold text-slate-300">Epistemic</th>
                      <th className="px-3 py-2 text-left font-semibold text-slate-300">Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {context.component_verifications.map((v, i) => (
                      <tr key={i} className="border-t border-slate-700/40 hover:bg-slate-800/30">
                        <td className="px-3 py-2 font-mono text-slate-300">{v.component}</td>
                        <td className="px-3 py-2">
                          <span className="inline-flex items-center space-x-1">
                            {VERIFICATION_ICONS[v.status]}
                            <span className={v.status === 'VERIFIED' ? 'text-emerald-400' : v.status === 'MISMATCH' ? 'text-red-400' : 'text-slate-500'}>
                              {v.status}
                            </span>
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <EpistemicBadge status={v.epistemic_status} />
                        </td>
                        <td className="px-3 py-2 text-slate-400 max-w-[200px] truncate">
                          {v.mismatch_detail || (v.declared_value ? `declared: ${v.declared_value}` : '—')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

function ProvenanceItem({ icon, label, value, mono }: { icon: React.ReactNode; label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start space-x-2.5 p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/40">
      <div className="mt-0.5">{icon}</div>
      <div>
        <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">{label}</p>
        <p className={`text-sm text-slate-200 mt-0.5 ${mono ? 'font-mono' : ''}`}>{value}</p>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════
// 2. Causal Classification View
// ═══════════════════════════════════════════════════════════════════════

interface CausalClassificationViewProps {
  classification: CausalClassificationModel;
}

export const CausalClassificationView: React.FC<CausalClassificationViewProps> = ({ classification }) => {
  const primaryMeta = CAUSAL_LAYER_META[classification.primary_layer];
  const [showRationale, setShowRationale] = useState(false);

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/70 backdrop-blur-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-700/40">
        <div className="flex items-center space-x-2">
          <Layers className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-100">Causal Classification</h3>
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Primary Layer */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/40">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg bg-slate-800/80 ${primaryMeta.color}`}>
              {primaryMeta.icon}
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Primary Layer</p>
              <p className={`text-sm font-semibold ${primaryMeta.color}`}>{primaryMeta.label}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <EpistemicBadge status={classification.primary_epistemic_status} />
            {classification.primary_evidence_refs.length > 0 && (
              <span className="text-[10px] font-mono text-slate-500">
                {classification.primary_evidence_refs.length} evidence ref(s)
              </span>
            )}
          </div>
        </div>

        {/* Secondary Layers */}
        {classification.secondary_layers.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Contributing Layers</p>
            <div className="flex flex-wrap gap-2">
              {classification.secondary_layers.map((layer, i) => {
                const meta = CAUSAL_LAYER_META[layer];
                return (
                  <span
                    key={i}
                    className={`inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/40 ${meta.color}`}
                  >
                    {meta.icon}
                    <span className="text-xs font-medium">{meta.label}</span>
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* Rationale */}
        {classification.rationale && (
          <div>
            <button
              onClick={() => setShowRationale(!showRationale)}
              className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-slate-300 transition-colors"
            >
              {showRationale ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
              <span>Analysis Rationale</span>
            </button>
            {showRationale && (
              <div className="mt-2 p-3 rounded-lg bg-slate-800/40 border border-slate-700/40">
                <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                  {classification.rationale}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════
// 3. Retest Comparison Panel
// ═══════════════════════════════════════════════════════════════════════

interface RetestComparisonPanelProps {
  result: RetestResultModel;
}

export const RetestComparisonPanel: React.FC<RetestComparisonPanelProps> = ({ result }) => {
  const [showDimensions, setShowDimensions] = useState(false);

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/70 backdrop-blur-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-700/40 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-100">Retest Comparison</h3>
        </div>
        <div className="flex items-center space-x-2">
          {result.has_regressions && (
            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-red-950/80 text-red-400 border border-red-500/40">
              <AlertTriangle className="h-3 w-3" />
              <span>REGRESSION</span>
            </span>
          )}
          {result.is_independently_verified ? (
            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-500/40">
              <ShieldCheck className="h-3 w-3" />
              <span>INDEPENDENT</span>
            </span>
          ) : (
            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-950/80 text-amber-400 border border-amber-500/40">
              <ShieldAlert className="h-3 w-3" />
              <span>NOT INDEPENDENT</span>
            </span>
          )}
          {result.is_multi_variable_change && (
            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-950/80 text-amber-400 border border-amber-500/40">
              <Sparkles className="h-3 w-3" />
              <span>MULTI-VAR</span>
            </span>
          )}
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Run References */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/40">
            <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Baseline Run</p>
            <p className="text-xs font-mono text-slate-300 mt-0.5">{result.baseline_run_id}</p>
            <p className="text-[10px] font-mono text-slate-500 mt-0.5">{result.baseline_context_id}</p>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/40">
            <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Candidate Run</p>
            <p className="text-xs font-mono text-slate-300 mt-0.5">{result.candidate_run_id}</p>
            <p className="text-[10px] font-mono text-slate-500 mt-0.5">{result.candidate_context_id}</p>
          </div>
        </div>

        {/* Transitions */}
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Check Transitions</p>
          <div className="space-y-1.5">
            {Object.entries(result.transitions).map(([check, transition]) => {
              const meta = TRANSITION_META[transition];
              return (
                <div key={check} className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                  <span className="text-xs font-mono text-slate-300">{check}</span>
                  <span className={`inline-flex items-center space-x-1.5 text-xs font-semibold ${meta.color}`}>
                    {meta.icon}
                    <span>{meta.label}</span>
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Contract Evaluations */}
        {Object.keys(result.contract_evaluations).length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Contract Status</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(result.contract_evaluations).map(([cid, status]) => (
                <span
                  key={cid}
                  className={`inline-flex items-center space-x-1 px-2 py-1 rounded-md text-[11px] font-mono border ${
                    status === 'CONTRACT_PRESERVED'
                      ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40'
                      : status === 'CONTRACT_VIOLATED'
                      ? 'bg-red-950/60 text-red-400 border-red-500/40'
                      : 'bg-slate-800/60 text-slate-400 border-slate-600/40'
                  }`}
                >
                  {status === 'CONTRACT_PRESERVED' ? <CheckCircle2 className="h-3 w-3" /> :
                   status === 'CONTRACT_VIOLATED' ? <XCircle className="h-3 w-3" /> :
                   <HelpCircle className="h-3 w-3" />}
                  <span>{cid.replace('contract_', '')}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Changed Dimensions */}
        {result.comparisons.length > 0 && (
          <div>
            <button
              onClick={() => setShowDimensions(!showDimensions)}
              className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-slate-300 transition-colors"
            >
              {showDimensions ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
              <span>Context Dimensions ({result.changed_dimensions.length} changed)</span>
            </button>
            {showDimensions && (
              <div className="mt-2 rounded-lg border border-slate-700/60 overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-slate-800/60">
                      <th className="px-3 py-2 text-left font-semibold text-slate-300">Dimension</th>
                      <th className="px-3 py-2 text-left font-semibold text-slate-300">Baseline</th>
                      <th className="px-3 py-2 text-left font-semibold text-slate-300">Candidate</th>
                      <th className="px-3 py-2 text-left font-semibold text-slate-300">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.comparisons.map((cmp, i) => (
                      <tr key={i} className="border-t border-slate-700/40 hover:bg-slate-800/30">
                        <td className="px-3 py-2 font-mono text-slate-300">{cmp.dimension}</td>
                        <td className="px-3 py-2 font-mono text-slate-400 max-w-[140px] truncate">{cmp.baseline_value || '—'}</td>
                        <td className="px-3 py-2 font-mono text-slate-400 max-w-[140px] truncate">{cmp.candidate_value || '—'}</td>
                        <td className="px-3 py-2">
                          {cmp.status === 'CHANGED' ? (
                            <span className="text-amber-400 font-semibold">CHANGED</span>
                          ) : (
                            <span className="text-slate-500">SAME</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════
// 4. Provenance Timeline
// ═══════════════════════════════════════════════════════════════════════

interface ProvenanceTimelineProps {
  entries: ProvenanceTimelineEntry[];
  title?: string;
}

export const ProvenanceTimeline: React.FC<ProvenanceTimelineProps> = ({
  entries,
  title = 'Provenance Chain',
}) => {
  const STATUS_COLORS: Record<string, string> = {
    PASS: 'bg-emerald-500',
    FAIL: 'bg-red-500',
    PENDING: 'bg-amber-500',
    INFO: 'bg-blue-500',
  };

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/70 backdrop-blur-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-700/40">
        <div className="flex items-center space-x-2">
          <Clock className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
        </div>
      </div>
      <div className="px-5 py-4">
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[7px] top-2 bottom-2 w-px bg-slate-700/60" />

          <div className="space-y-4">
            {entries.map((entry, i) => (
              <div key={i} className="relative flex items-start space-x-4 pl-0">
                {/* Dot */}
                <div className={`relative z-10 mt-1.5 h-[15px] w-[15px] rounded-full border-2 border-slate-800 ${STATUS_COLORS[entry.status] || 'bg-slate-500'}`} />

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">{entry.step}</span>
                    {entry.timestamp && (
                      <span className="text-[10px] font-mono text-slate-600">{entry.timestamp}</span>
                    )}
                  </div>
                  <p className="text-xs text-slate-200 mt-0.5">{entry.label}</p>
                  {entry.detail && (
                    <p className="text-[11px] text-slate-400 mt-0.5">{entry.detail}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
