'use client';

import React, { useState, useEffect } from 'react';
import {
  Scale,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Layers,
  Activity,
  ShieldAlert,
  Sliders,
  BarChart2,
  Cpu,
  ArrowRight,
  RefreshCw,
  GitCommit,
  FlaskConical,
  Eye,
  Info,
  ShieldCheck,
  Check,
  Ban
} from 'lucide-react';
import { api } from '@/lib/api';
import {
  UncertaintyExperiment,
  PredictionUncertainty,
  RiskCoveragePoint,
  DecisionPolicy,
  UncertaintyBucketSummary,
  SelectivePredictionResult,
  ApplicationShiftUncertainty,
  HypothesisVerdict
} from '@/types';

export default function UncertaintyPage() {
  const [experiment, setExperiment] = useState<UncertaintyExperiment | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedApp, setSelectedApp] = useState<string>('app_inventory');
  const [selectedK, setSelectedK] = useState<number | 'all'>('all');
  const [activeTab, setActiveTab] = useState<'summary' | 'risk_coverage' | 'abstention' | 'buckets' | 'shift' | 'failures'>('summary');

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getUncertaintyExperiment();
      setExperiment(data);
    } catch (err: any) {
      console.error('Failed to load uncertainty experiment:', err);
      setError(err?.message || 'Could not load uncertainty experiment data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#070b14] text-slate-200 flex flex-col items-center justify-center space-y-4">
        <RefreshCw className="h-8 w-8 text-amber-400 animate-spin" />
        <p className="text-sm text-slate-400 font-mono tracking-wide">
          Loading Slice 7.1 Uncertainty-Aware Decision Utility Experiment...
        </p>
      </div>
    );
  }

  if (error || !experiment) {
    return (
      <div className="min-h-screen bg-[#070b14] text-slate-200 p-8 flex flex-col items-center justify-center space-y-4">
        <AlertTriangle className="h-10 w-10 text-rose-400" />
        <h2 className="text-xl font-bold text-white">Uncertainty Evaluation Unavailable</h2>
        <p className="text-sm text-slate-400 max-w-md text-center">{error || 'No experiment data found.'}</p>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-amber-600 hover:bg-amber-500 rounded-lg text-xs font-semibold text-white transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Filter cold start results by app and K
  const filteredColdStart = experiment.cold_start_results.filter((res) => {
    const matchesApp = !selectedApp || res.application_id === selectedApp;
    const matchesK = selectedK === 'all' || res.budget_k === selectedK;
    return matchesApp && matchesK;
  });

  // Filter predictions
  const filteredPredictions = experiment.predictions.filter((p) => {
    const matchesApp = !selectedApp || p.application_id === selectedApp;
    const matchesK = selectedK === 'all' || p.budget_k === selectedK;
    return matchesApp && matchesK;
  });

  const failurePredictions = experiment.predictions.filter(
    (p) => p.observed_label === 1 && (!selectedApp || p.application_id === selectedApp)
  );

  const appShift = experiment.shift_uncertainty_analysis.find(
    (s) => s.application_id === selectedApp
  );

  const appPolicies = experiment.selective_results.filter(
    (r) => r.test_application_id === selectedApp
  );

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-200 pb-20">
      {/* Header Banner */}
      <div className="border-b border-surface-border/80 bg-[#090d16]/80 backdrop-blur-md px-6 py-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3 mb-1">
              <span className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
                <Scale className="h-5 w-5" />
              </span>
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                Slice 7.1 — Uncertainty-Aware Reliability & Decision Utility
              </h1>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                {experiment.protocol_version}
              </span>
            </div>
            <p className="text-xs text-slate-400 max-w-3xl">
              Connecting predictive uncertainty bounds to operational decision thresholds and selective prediction. 
              Enforcing zero test-set leakage: decision policies and bucket cutoffs are derived strictly from training applications.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={loadData}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 space-y-6">
        {/* Scientific Audit & Parent Invariant Banner */}
        <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4">
          <div className="flex items-start space-x-3">
            <ShieldCheck className="h-5 w-5 text-indigo-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <span className="font-bold text-indigo-300 uppercase tracking-wide">
                Rigorous Invariant & Parent Snapshot Preservation
              </span>
              <p className="text-slate-300 leading-relaxed">
                Snapshot <code className="text-indigo-200">{experiment.snapshot_id}</code> is strictly verified against parent snapshot <code className="text-indigo-200">{experiment.parent_snapshot_id}</code> (Slice 7.0 Frozen). 
                All epistemic covariance bounds are computed via Fisher Information and Empirical Bayes logit shrinkage. 
                Decision thresholds were frozen before testing unseen applications (zero test-set leakage).
              </p>
            </div>
          </div>
        </div>

        {/* Hypotheses Deterministic Verdicts */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {experiment.hypotheses_verdicts.map((hyp) => {
            const isSupported = hyp.verdict === 'SUPPORTED';
            const isPartial = hyp.verdict === 'PARTIALLY_SUPPORTED';
            return (
              <div key={hyp.hypothesis_id} className="rounded-xl border border-slate-800 bg-[#0b101d] p-3.5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px] font-bold text-slate-400">{hyp.hypothesis_id}</span>
                    <span
                      className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded border ${
                        isSupported
                          ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                          : isPartial
                          ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                          : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                      }`}
                    >
                      {hyp.verdict}
                    </span>
                  </div>
                  <div className="text-xs font-semibold text-white mb-1">{hyp.title}</div>
                </div>
                <div className="text-[10px] text-slate-400 leading-tight">{hyp.threshold_criterion}</div>
              </div>
            );
          })}
        </div>

        {/* Application & Budget Filter Controls */}
        <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-slate-800 bg-[#0b101d]">
          <div className="flex items-center space-x-3">
            <span className="text-xs font-medium text-slate-400">Held-Out App:</span>
            <div className="flex space-x-1">
              {['app_inventory', 'app_eda', 'app_booking'].map((appId) => (
                <button
                  key={appId}
                  onClick={() => setSelectedApp(appId)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    selectedApp === appId
                      ? 'bg-amber-600 text-white shadow-lg shadow-amber-600/30'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {appId === 'app_inventory' ? 'Inventory' : appId === 'app_eda' ? 'EDA' : 'Booking'}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <span className="text-xs font-medium text-slate-400">Local Budget K:</span>
            <div className="flex space-x-1">
              {['all', 0, 1, 3, 5, 10].map((kVal) => (
                <button
                  key={String(kVal)}
                  onClick={() => setSelectedK(kVal as any)}
                  className={`px-2.5 py-1 rounded text-xs font-mono font-semibold transition-all ${
                    selectedK === kVal
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {kVal === 'all' ? 'All K' : `K=${kVal}`}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 space-x-6">
          {[
            { id: 'summary', label: 'Uncertainty Overview', icon: Scale },
            { id: 'risk_coverage', label: 'Risk-Coverage Trade-off', icon: BarChart2 },
            { id: 'abstention', label: 'Selective Abstention Policy', icon: Ban },
            { id: 'buckets', label: 'Calibration Buckets (LOW/MED/HIGH)', icon: Layers },
            { id: 'shift', label: 'Covariate Shift & Uncertainty', icon: Activity },
            { id: 'failures', label: 'Natural Failure Inspection', icon: ShieldAlert }
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 py-3 border-b-2 text-xs font-semibold transition-colors ${
                  isActive
                    ? 'border-amber-500 text-amber-300'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab: Summary & Cold-Start Curve */}
        {activeTab === 'summary' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0b101d] overflow-hidden">
              <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                    Cold-Start Predictive Uncertainty Across Local Budget K
                  </h4>
                  <p className="text-[11px] text-slate-400">
                    Evaluating posterior probability intervals, effective evidence counts, and selective prediction utility across K = 0, 1, 3, 5, 10.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/60 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
                    <tr>
                      <th className="px-4 py-3">Held-Out App</th>
                      <th className="px-3 py-3">Budget K</th>
                      <th className="px-3 py-3">Eval N</th>
                      <th className="px-3 py-3">Failures</th>
                      <th className="px-3 py-3">Mean P(Fail)</th>
                      <th className="px-3 py-3">Mean Uncertainty</th>
                      <th className="px-3 py-3">Median Uncertainty</th>
                      <th className="px-3 py-3">Brier Score</th>
                      <th className="px-3 py-3">Selective Brier (τ75)</th>
                      <th className="px-3 py-3">Abstention %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 font-mono text-[11px]">
                    {filteredColdStart.map((res, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                        <td className="px-4 py-3 font-sans font-semibold text-white">
                          {res.application_id}
                        </td>
                        <td className="px-3 py-3 font-bold text-amber-400">K={res.budget_k}</td>
                        <td className="px-3 py-3 text-slate-300">{res.prediction_count}</td>
                        <td className="px-3 py-3">
                          <span className={res.observed_failures > 0 ? 'text-rose-400 font-bold' : 'text-slate-500'}>
                            {res.observed_failures}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-slate-300">{res.mean_predicted_prob.toFixed(4)}</td>
                        <td className="px-3 py-3 font-bold text-amber-300">{res.mean_uncertainty.toFixed(4)}</td>
                        <td className="px-3 py-3 text-slate-400">{res.median_uncertainty.toFixed(4)}</td>
                        <td className="px-3 py-3 text-slate-300">{res.brier_score.toFixed(4)}</td>
                        <td className="px-3 py-3 font-semibold text-emerald-400">
                          {res.selective_brier_default_policy.toFixed(4)}
                        </td>
                        <td className="px-3 py-3 text-slate-400">
                          {(res.abstention_rate_default_policy * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Risk-Coverage */}
        {activeTab === 'risk_coverage' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0b101d] p-5">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-2">
                Risk-Coverage Trade-Off Curve (Selective Prediction)
              </h4>
              <p className="text-xs text-slate-400 mb-4">
                Evaluating prediction error (selective Brier score) as coverage is progressively restricted to lowest-uncertainty predictions. 
                Testing whether predictive uncertainty successfully identifies and isolates unreliable predictions.
              </p>

              <div className="overflow-x-auto border border-slate-800 rounded-lg">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-900/80 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                    <tr>
                      <th className="px-3 py-2.5">Coverage Level</th>
                      <th className="px-3 py-2.5">Accepted Samples</th>
                      <th className="px-3 py-2.5">Tau Threshold</th>
                      <th className="px-3 py-2.5">Selective Brier</th>
                      <th className="px-3 py-2.5">Random Baseline Brier</th>
                      <th className="px-3 py-2.5">Selective MAE</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-[11px]">
                    {experiment.risk_coverage_curve.map((rc, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/40">
                        <td className="px-3 py-2 font-bold text-indigo-400">{(rc.coverage * 100).toFixed(1)}%</td>
                        <td className="px-3 py-2 text-slate-300">{rc.accepted_count}</td>
                        <td className="px-3 py-2 text-amber-300">{rc.threshold_tau.toFixed(4)}</td>
                        <td className="px-3 py-2 font-semibold text-emerald-400">{rc.selective_brier.toFixed(4)}</td>
                        <td className="px-3 py-2 text-slate-500">{rc.baseline_random_brier.toFixed(4)}</td>
                        <td className="px-3 py-2 text-slate-300">{rc.selective_mae.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Abstention Policies */}
        {activeTab === 'abstention' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0b101d] p-5">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-2">
                Frozen Decision Policies Evaluated on {selectedApp}
              </h4>
              <p className="text-xs text-slate-400 mb-4">
                Decision policies are fitted exclusively on training applications and frozen before evaluation on {selectedApp}. 
                Validating whether selective abstention reduces operational prediction risk.
              </p>

              <div className="overflow-x-auto border border-slate-800 rounded-lg">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-900/80 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                    <tr>
                      <th className="px-3 py-2.5">Policy ID</th>
                      <th className="px-3 py-2.5">Threshold (τ)</th>
                      <th className="px-3 py-2.5">Test Coverage</th>
                      <th className="px-3 py-2.5">Abstention Rate</th>
                      <th className="px-3 py-2.5">Accepted Fails</th>
                      <th className="px-3 py-2.5">Accepted Brier</th>
                      <th className="px-3 py-2.5">Overall Brier</th>
                      <th className="px-3 py-2.5">Δ Brier (Improvement)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-[11px]">
                    {appPolicies.map((pol) => {
                      const impr = pol.selective_brier_improvement;
                      const isGood = impr > 0.0001;
                      return (
                        <tr key={pol.policy_id} className="hover:bg-slate-900/40">
                          <td className="px-3 py-2 font-sans font-semibold text-white">{pol.policy_id}</td>
                          <td className="px-3 py-2 text-amber-300 font-bold">{pol.threshold_tau.toFixed(3)}</td>
                          <td className="px-3 py-2 text-indigo-400">{(pol.test_coverage * 100).toFixed(1)}%</td>
                          <td className="px-3 py-2 text-slate-400">{(pol.test_abstention_rate * 100).toFixed(1)}%</td>
                          <td className="px-3 py-2 text-rose-400 font-bold">{pol.accepted_failures_count}</td>
                          <td className="px-3 py-2 text-slate-200 font-semibold">{pol.accepted_brier_score.toFixed(4)}</td>
                          <td className="px-3 py-2 text-slate-400">{pol.overall_brier_score.toFixed(4)}</td>
                          <td className="px-3 py-2">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                isGood
                                  ? 'bg-emerald-500/20 text-emerald-400'
                                  : impr < -0.0001
                                  ? 'bg-rose-500/20 text-rose-400'
                                  : 'bg-slate-800 text-slate-400'
                              }`}
                            >
                              {impr > 0 ? `+${impr.toFixed(4)}` : impr.toFixed(4)}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Buckets */}
        {activeTab === 'buckets' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0b101d] p-5">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-2">
                Uncertainty-Stratified Calibration Buckets (Testing H2)
              </h4>
              <p className="text-xs text-slate-400 mb-4">
                Predictions stratified across LOW, MEDIUM, and HIGH uncertainty buckets using frozen training quantile thresholds. 
                Testing whether higher predictive uncertainty reliably identifies worse probability calibration.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                {experiment.uncertainty_buckets.map((b) => (
                  <div key={b.bucket_level} className="p-4 rounded-xl border border-slate-700 bg-slate-900/60 space-y-2 font-mono text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">{b.bucket_level} Uncertainty</span>
                      <span className="text-[10px] text-slate-400">[{b.lower_bound.toFixed(3)}, {b.upper_bound.toFixed(3)}]</span>
                    </div>
                    <div className="space-y-1 text-slate-300">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Sample Count:</span>
                        <span className="font-bold text-white">{b.sample_count}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Failures:</span>
                        <span className="font-bold text-rose-400">{b.failure_count}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Brier Score:</span>
                        <span className="font-bold text-amber-300">{b.brier_score.toFixed(4)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">MAE:</span>
                        <span className="font-bold text-slate-200">{b.mean_absolute_error.toFixed(4)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab: Shift */}
        {activeTab === 'shift' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0b101d] p-5">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-2">
                Covariate Distribution Shift vs Predictive Uncertainty (Testing H5)
              </h4>
              <p className="text-xs text-slate-400 mb-4">
                Evaluating whether applications with larger feature distribution shift manifest greater initial predictive uncertainty (Fisher information projection distance).
              </p>

              <div className="overflow-x-auto border border-slate-800 rounded-lg">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-900/80 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                    <tr>
                      <th className="px-3 py-2.5">Application</th>
                      <th className="px-3 py-2.5">Standardized Shift</th>
                      <th className="px-3 py-2.5">Raw Features Shift</th>
                      <th className="px-3 py-2.5">Relative Features Shift</th>
                      <th className="px-3 py-2.5">Mean Uncertainty (K=0)</th>
                      <th className="px-3 py-2.5">Mean Uncertainty (K=5)</th>
                      <th className="px-3 py-2.5">Uncertainty Reduction</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-[11px]">
                    {experiment.shift_uncertainty_analysis.map((sh) => (
                      <tr key={sh.application_id} className="hover:bg-slate-900/40">
                        <td className="px-3 py-2 font-sans font-semibold text-white">{sh.application_id}</td>
                        <td className="px-3 py-2 text-amber-300 font-bold">{sh.standardized_shift_mean.toFixed(2)}σ</td>
                        <td className="px-3 py-2 text-rose-400">{sh.raw_shift_mean.toFixed(2)}σ</td>
                        <td className="px-3 py-2 text-emerald-400">{sh.relative_shift_mean.toFixed(2)}σ</td>
                        <td className="px-3 py-2 text-slate-200">{sh.mean_uncertainty_k0.toFixed(4)}</td>
                        <td className="px-3 py-2 text-slate-200">{sh.mean_uncertainty_k5.toFixed(4)}</td>
                        <td className="px-3 py-2 font-bold text-indigo-400">
                          {sh.uncertainty_reduction_k0_to_k5 > 0 ? `-${sh.uncertainty_reduction_k0_to_k5.toFixed(4)}` : '0.0000'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Failures */}
        {activeTab === 'failures' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0b101d] p-5">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-2">
                Naturally Occurring Failures & Uncertainty Bounds
              </h4>
              <p className="text-xs text-slate-400 mb-4">
                Inspection of individual natural failures, their predicted mean failure probability, and posterior uncertainty intervals.
              </p>

              {failurePredictions.length === 0 ? (
                <div className="p-6 rounded-lg border border-slate-800 bg-slate-900/30 text-center text-slate-400 text-xs">
                  Zero natural evaluation failures observed for {selectedApp}.
                </div>
              ) : (
                <div className="overflow-x-auto border border-slate-800 rounded-lg">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-900/80 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                      <tr>
                        <th className="px-3 py-2.5">Prediction ID</th>
                        <th className="px-3 py-2.5">Budget K</th>
                        <th className="px-3 py-2.5">Mean P(Fail)</th>
                        <th className="px-3 py-2.5">Posterior Interval [Lower, Upper]</th>
                        <th className="px-3 py-2.5">Uncertainty Width</th>
                        <th className="px-3 py-2.5">Effective Evidence</th>
                        <th className="px-3 py-2.5">Bucket</th>
                        <th className="px-3 py-2.5">Decision (τ75)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-[11px]">
                      {failurePredictions.map((fp) => (
                        <tr key={fp.prediction_id} className="hover:bg-slate-900/40">
                          <td className="px-3 py-2 text-slate-300 truncate max-w-[120px]">{fp.prediction_id}</td>
                          <td className="px-3 py-2 text-amber-400 font-bold">K={fp.budget_k}</td>
                          <td className="px-3 py-2 text-white font-bold">{fp.p_mean.toFixed(4)}</td>
                          <td className="px-3 py-2 text-slate-300">[{fp.p_lower.toFixed(3)}, {fp.p_upper.toFixed(3)}]</td>
                          <td className="px-3 py-2 text-amber-300 font-bold">{fp.uncertainty_width.toFixed(4)}</td>
                          <td className="px-3 py-2 text-indigo-400">{fp.effective_evidence.toFixed(1)}</td>
                          <td className="px-3 py-2">
                            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                              {fp.uncertainty_bucket}
                            </span>
                          </td>
                          <td className="px-3 py-2">
                            {fp.decision === 'ACCEPT' ? (
                              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-[10px] font-bold">
                                ACCEPT
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400 text-[10px] font-bold">
                                ABSTAIN
                              </span>
                            )}
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
    </div>
  );
}
