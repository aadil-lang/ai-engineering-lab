'use client';

import React, { useState } from 'react';
import { 
  EngineeringDiagnosis, 
  DeterministicSignal, 
  ReproductionStep,
  DiagnosisClaim,
  GroundingStatus,
} from '@/types';
import { 
  AlertTriangle, 
  Cpu, 
  Bug, 
  CheckCircle2, 
  Copy, 
  Check, 
  Terminal, 
  RefreshCw, 
  Layers, 
  Sparkles, 
  ArrowRight, 
  FileCode,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Sliders,
  CheckCircle,
  XCircle,
  HelpCircle,
  Info,
  ExternalLink,
} from 'lucide-react';

interface EngineeringDiagnosisCardProps {
  diagnosis: EngineeringDiagnosis;
  onReDiagnose?: () => void;
  isReDiagnosing?: boolean;
}

export const EngineeringDiagnosisCard: React.FC<EngineeringDiagnosisCardProps> = ({
  diagnosis,
  onReDiagnose,
  isReDiagnosing = false,
}) => {
  const [copiedSpec, setCopiedSpec] = useState<boolean>(false);
  const [copiedFix, setCopiedFix] = useState<boolean>(false);

  const handleCopySpec = () => {
    navigator.clipboard.writeText(diagnosis.regression_test_spec);
    setCopiedSpec(true);
    setTimeout(() => setCopiedSpec(false), 2000);
  };

  const handleCopyFix = () => {
    navigator.clipboard.writeText(diagnosis.suggested_fix);
    setCopiedFix(true);
    setTimeout(() => setCopiedFix(false), 2000);
  };

  const confidencePct = Math.round((diagnosis.confidence_score || 0.9) * 100);
  const groundingPct = Math.round((diagnosis.grounding_score ?? 1.0) * 100);
  const isGrounded = diagnosis.is_grounded ?? true;
  const hasGroundedCorrection = !!diagnosis.grounded_root_cause && diagnosis.grounded_root_cause !== diagnosis.root_cause_summary;
  const effectiveComponent = diagnosis.grounded_suspected_component || diagnosis.suspected_component;
  const effectiveRootCause = diagnosis.grounded_root_cause || diagnosis.root_cause_summary;

  const getStatusBadge = (status: GroundingStatus) => {
    switch (status) {
      case 'SUPPORTED':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-500/40">
            <CheckCircle2 className="h-3 w-3 text-emerald-400" />
            <span>SUPPORTED</span>
          </span>
        );
      case 'PARTIALLY_SUPPORTED':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-950/80 text-amber-400 border border-amber-500/40">
            <AlertTriangle className="h-3 w-3 text-amber-400" />
            <span>PARTIALLY SUPPORTED</span>
          </span>
        );
      case 'CONTRADICTED':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-rose-950/80 text-rose-400 border border-rose-500/50 animate-pulse">
            <ShieldX className="h-3 w-3 text-rose-400" />
            <span>CONTRADICTED</span>
          </span>
        );
      case 'UNSUPPORTED':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-slate-900 text-slate-400 border border-slate-700">
            <HelpCircle className="h-3 w-3 text-slate-400" />
            <span>UNSUPPORTED</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-slate-900 text-slate-400 border border-slate-700">
            <Info className="h-3 w-3 text-slate-400" />
            <span>{status}</span>
          </span>
        );
    }
  };

  return (
    <div className="rounded-2xl border border-rose-500/30 bg-[#120a14]/90 shadow-2xl p-6 space-y-6 animate-fade-in backdrop-blur-md">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-rose-500/20">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center space-x-3 flex-wrap gap-y-2">
            <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold font-mono bg-rose-500/20 text-rose-300 border border-rose-500/40">
              <Bug className="h-3.5 w-3.5 text-rose-400" />
              <span>AI ROOT-CAUSE DIAGNOSIS</span>
            </span>

            <span className="px-2.5 py-0.5 rounded-md text-xs font-mono uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold">
              {diagnosis.failure_category}
            </span>

            <span className="px-2.5 py-0.5 rounded-md text-xs font-mono uppercase bg-amber-500/10 text-amber-300 border border-amber-500/30 font-semibold">
              SEVERITY: {diagnosis.severity}
            </span>

            {/* Evidence Grounding Badge */}
            {isGrounded ? (
              <span className="flex items-center space-x-1 px-2.5 py-0.5 rounded-md text-xs font-mono font-bold uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                <span>EVIDENCE GROUNDED</span>
              </span>
            ) : (
              <span className="flex items-center space-x-1 px-2.5 py-0.5 rounded-md text-xs font-mono font-bold uppercase bg-rose-500/20 text-rose-300 border border-rose-500/50">
                <ShieldAlert className="h-3.5 w-3.5 text-rose-400" />
                <span>GROUNDING CORRECTION APPLIED</span>
              </span>
            )}
          </div>

          <h2 className="text-lg font-bold text-white tracking-tight mt-1 font-sans">
            {diagnosis.title}
          </h2>

          <div className="flex items-center space-x-2 text-xs font-mono text-slate-400 pt-0.5">
            <span>Suspected Component:</span>
            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-300 font-bold">
              {effectiveComponent}
            </span>
            {diagnosis.grounded_suspected_component && diagnosis.grounded_suspected_component !== diagnosis.suspected_component && (
              <span className="text-[11px] text-amber-400 italic">
                (grounded from {diagnosis.suspected_component})
              </span>
            )}
          </div>
        </div>

        {/* Confidence & Grounding Gauge & Re-diagnose action */}
        <div className="flex items-center space-x-3 flex-shrink-0">
          {/* Grounding Score Gauge */}
          <div className="text-right bg-slate-950/80 px-3.5 py-2 rounded-xl border border-slate-800/80">
            <div className="flex items-center justify-end space-x-1 text-[11px] font-mono text-slate-400 uppercase">
              <ShieldCheck className="h-3 w-3 text-cyan-400" />
              <span>Grounding</span>
            </div>
            <div className={`text-lg font-bold font-mono ${groundingPct >= 80 ? 'text-emerald-400' : groundingPct >= 50 ? 'text-amber-400' : 'text-rose-400'}`}>
              {groundingPct}%
            </div>
          </div>

          {/* AI Confidence Gauge */}
          <div className="text-right bg-slate-950/80 px-3.5 py-2 rounded-xl border border-slate-800/80">
            <div className="flex items-center justify-end space-x-1 text-[11px] font-mono text-slate-400 uppercase">
              <Sparkles className="h-3 w-3 text-purple-400" />
              <span>Confidence</span>
            </div>
            <div className="text-lg font-bold font-mono text-purple-300">
              {confidencePct}%
            </div>
          </div>

          {onReDiagnose && (
            <button
              onClick={onReDiagnose}
              disabled={isReDiagnosing}
              className="flex items-center space-x-2 px-3.5 py-2.5 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/40 text-xs font-mono font-semibold transition-all disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isReDiagnosing ? 'animate-spin' : ''}`} />
              <span>{isReDiagnosing ? 'Diagnosing...' : 'Re-Diagnose'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Grounding Correction Alert Box if Contradiction occurred */}
      {hasGroundedCorrection && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/40 space-y-2">
          <div className="flex items-center space-x-2 text-rose-300 font-bold text-xs font-mono uppercase">
            <ShieldAlert className="h-4 w-4 text-rose-400" />
            <span>Diagnosis Grounding Validator: Contradiction Detected & Corrected</span>
          </div>
          <p className="text-xs text-slate-300 font-sans leading-relaxed">
            The raw AI diagnosis formulated a hypothesis contradicted by deterministic runtime facts. The platform automatically corrected the root cause to match verified hardware/runtime telemetry.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1 text-xs">
            <div className="p-2.5 rounded bg-slate-950/80 border border-rose-900/50">
              <span className="text-[10px] font-mono font-bold text-rose-400 uppercase block mb-1">
                ⚠️ Raw AI Hypothesis (Contradicted):
              </span>
              <p className="text-slate-400 italic line-through font-mono text-[11px]">
                {diagnosis.root_cause_summary}
              </p>
            </div>
            <div className="p-2.5 rounded bg-slate-950/80 border border-emerald-900/50">
              <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase block mb-1">
                ✅ Evidence-Grounded Root Cause (Verified):
              </span>
              <p className="text-emerald-300 font-mono text-[11px]">
                {diagnosis.grounded_root_cause}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Root Cause Summary */}
      <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1.5">
        <span className="text-xs font-mono uppercase tracking-wider text-purple-300 font-bold flex items-center space-x-1.5">
          <Cpu className="h-4 w-4 text-purple-400" />
          <span>Root Cause Explanation (Telemetry Ground Truth + Validated Reasoning)</span>
        </span>
        <p className="text-sm text-slate-200 leading-relaxed font-sans">
          {effectiveRootCause}
        </p>
      </div>

      {/* Diagnosis Claims & Evidence Consistency Validation Section */}
      {diagnosis.claims && diagnosis.claims.length > 0 && (
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-mono uppercase tracking-wider text-cyan-300 font-bold flex items-center space-x-1.5">
              <ShieldCheck className="h-4 w-4 text-cyan-400" />
              <span>Diagnosis Claims Grounding Validation ({diagnosis.claims.length} Assessed)</span>
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              Score: <strong className="text-cyan-300">{groundingPct}%</strong>
            </span>
          </div>

          <div className="space-y-2.5 overflow-x-auto">
            {diagnosis.claims.map(claim => (
              <div
                key={claim.claim_id}
                className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-1.5"
              >
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-slate-800 text-slate-300">
                      {claim.claim_type}
                    </span>
                    {getStatusBadge(claim.grounding_status)}
                  </div>
                  {claim.evidence_refs && claim.evidence_refs.length > 0 && (
                    <div className="flex items-center space-x-1 text-[10px] font-mono text-cyan-400">
                      <span>Evidence Refs:</span>
                      {claim.evidence_refs.map((ref, rIdx) => (
                        <span key={rIdx} className="px-1.5 py-0.2 rounded bg-cyan-950/80 border border-cyan-800 text-cyan-300">
                          {ref}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <p className="text-xs font-mono text-slate-200">
                  {claim.text}
                </p>

                {claim.explanation && (
                  <p className="text-[11px] font-sans text-slate-400 italic">
                    {claim.explanation}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grid: Deterministic Signals (Facts) vs Reproduction Steps */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* 1. Deterministic Telemetry Signals */}
        <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/90 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-mono uppercase tracking-wider text-cyan-300 font-bold flex items-center space-x-1.5">
              <ShieldAlert className="h-4 w-4 text-cyan-400" />
              <span>Deterministic Signals ({diagnosis.deterministic_signals?.length || 0} Facts)</span>
            </span>
            <span className="text-[10px] font-mono text-slate-500">Hardware & Runtime Truth</span>
          </div>

          <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
            {diagnosis.deterministic_signals && diagnosis.deterministic_signals.length > 0 ? (
              diagnosis.deterministic_signals.map((sig, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs space-y-1"
                >
                  <div className="flex items-center space-x-2">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                      {sig.signal_type}
                    </span>
                  </div>
                  <p className="text-xs font-mono text-slate-300 break-words">
                    {sig.summary}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 italic">No specific anomaly signals recorded.</p>
            )}
          </div>
        </div>

        {/* 2. Step-by-Step Reproduction */}
        <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/90 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-mono uppercase tracking-wider text-amber-300 font-bold flex items-center space-x-1.5">
              <Terminal className="h-4 w-4 text-amber-400" />
              <span>Reproduction Sequence</span>
            </span>
            <span className="text-[10px] font-mono text-slate-500">Deterministic Steps</span>
          </div>

          <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
            {diagnosis.reproduction_steps && diagnosis.reproduction_steps.length > 0 ? (
              diagnosis.reproduction_steps.map(step => (
                <div
                  key={step.step_number}
                  className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs space-y-1"
                >
                  <div className="flex items-center space-x-2">
                    <span className="flex items-center justify-center h-4 w-4 rounded-full bg-amber-500/20 text-[10px] font-mono font-bold text-amber-300">
                      {step.step_number}
                    </span>
                    <span className="font-bold text-slate-200">{step.action}</span>
                  </div>
                  {step.target && (
                    <div className="text-[11px] font-mono text-slate-400 pl-6">
                      Target: <span className="text-cyan-300">{step.target}</span>
                    </div>
                  )}
                  {step.observed && (
                    <div className="text-[11px] font-mono text-rose-300 pl-6">
                      Observed: {step.observed}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 italic">No reproduction steps generated.</p>
            )}
          </div>
        </div>
      </div>

      {/* Suggested Engineering Fix & Code Diff */}
      <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono uppercase tracking-wider text-emerald-300 font-bold flex items-center space-x-1.5">
            <FileCode className="h-4 w-4 text-emerald-400" />
            <span>Suggested Engineering Remediation</span>
          </span>
          <button
            onClick={handleCopyFix}
            className="flex items-center space-x-1 text-[11px] font-mono text-slate-400 hover:text-white transition-colors"
          >
            {copiedFix ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
            <span>{copiedFix ? 'Copied' : 'Copy Fix'}</span>
          </button>
        </div>

        <p className="text-xs text-slate-300 font-sans leading-relaxed">
          {diagnosis.suggested_fix}
        </p>

        {diagnosis.code_diff_suggestion && (
          <div className="mt-2 rounded-lg bg-[#070b14] border border-slate-900 p-3 overflow-x-auto">
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block mb-1">
              Proposed Code Diff:
            </span>
            <pre className="text-xs font-mono text-emerald-300/90 whitespace-pre leading-relaxed">
              {diagnosis.code_diff_suggestion}
            </pre>
          </div>
        )}
      </div>

      {/* Automated Regression Test Specification */}
      {diagnosis.regression_test_spec && (
        <div className="p-4 rounded-xl bg-[#090e1c] border border-indigo-500/30 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-indigo-300 font-bold flex items-center space-x-1.5">
              <Terminal className="h-4 w-4 text-indigo-400" />
              <span>Recommended Regression Test (Playwright / pytest)</span>
            </span>
            <button
              onClick={handleCopySpec}
              className="flex items-center space-x-1 px-2.5 py-1 rounded-md bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 text-xs font-mono font-semibold transition-colors"
            >
              {copiedSpec ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              <span>{copiedSpec ? 'Copied Test Script' : 'Copy Test Script'}</span>
            </button>
          </div>

          <pre className="p-3.5 rounded-lg bg-[#050811] text-xs font-mono text-cyan-300/90 border border-slate-900 overflow-x-auto max-h-72 leading-relaxed">
            {diagnosis.regression_test_spec}
          </pre>
        </div>
      )}
    </div>
  );
};

