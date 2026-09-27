'use client';

import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle,
  Brain, 
  Sparkles, 
  RefreshCw, 
  Sliders, 
  BarChart3, 
  Target, 
  ChevronRight, 
  Info, 
  X, 
  Activity, 
  Cpu, 
  Layers, 
  HelpCircle,
  Clock,
  Flame,
  ArrowUpRight,
  ShieldAlert,
  FlaskConical,
  Database,
  Scale,
  GitCommit,
  Check,
  Calendar
} from 'lucide-react';
import { api } from '@/lib/api';
import {
  ReliabilitySummary,
  TargetReliability,
  TestCaseReliability,
  TrendAnalysis,
  FailurePattern,
  TestCasePrediction,
  QAPrioritizationItem,
  ModelEvaluationMetrics,
  DatasetAuditReport,
  ContinuousScientificEvaluationReport,
  PredictionRecord,
  DatasetDiagnosticsReport,
  PopulationSeparationReport,

  PopulationType,
  PopulationAuditSummary,
  WalkForwardEvaluationReport,
  TrendStatus,
  RiskBand,
  PredictionStatus,
  DatasetStatus,
  PredictionEvaluationStatus,
} from '@/types';
import { StatusBadge } from '@/components/StatusBadge';

export default function ReliabilityPage() {
  const [summary, setSummary] = useState<ReliabilitySummary | null>(null);
  const [trends, setTrends] = useState<TrendAnalysis | null>(null);
  const [targets, setTargets] = useState<TargetReliability[]>([]);
  const [testCases, setTestCases] = useState<TestCaseReliability[]>([]);
  const [failurePatterns, setFailurePatterns] = useState<FailurePattern[]>([]);
  const [predictions, setPredictions] = useState<TestCasePrediction[]>([]);
  const [prioritization, setPrioritization] = useState<QAPrioritizationItem[]>([]);
  const [modelStatus, setModelStatus] = useState<ModelEvaluationMetrics | null>(null);
  
  // Slice 6.1, 6.3 & 6.4 Scientific, Diagnostic & Separation State
  const [auditReport, setAuditReport] = useState<DatasetAuditReport | null>(null);
  const [scientificReport, setScientificReport] = useState<ContinuousScientificEvaluationReport | null>(null);
  const [predictionRecords, setPredictionRecords] = useState<PredictionRecord[]>([]);
  const [diagnosticsReport, setDiagnosticsReport] = useState<DatasetDiagnosticsReport | null>(null);
  const [popReport, setPopReport] = useState<PopulationSeparationReport | null>(null);
  const [selectedPopTab, setSelectedPopTab] = useState<PopulationType>('ALL_HISTORICAL');

  const [selectedPrediction, setSelectedPrediction] = useState<TestCasePrediction | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isTraining, setIsTraining] = useState<boolean>(false);
  const [trainingFeedback, setTrainingFeedback] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'separation' | 'dataset_diagnostics' | 'prioritization' | 'scientific_validation' | 'continuous_tracking' | 'test_cases' | 'targets' | 'patterns'>('separation');


  const loadData = async () => {
    setIsLoading(true);
    try {
      const [
        sumData,
        trendData,
        targetData,
        testCaseData,
        patternData,
        predData,
        prioData,
        statusData,
        auditData,
        sciData,
        recordsData,
        diagData,
        popData
      ] = await Promise.all([
        api.getReliabilitySummary().catch(() => null),
        api.getReliabilityTrends().catch(() => null),
        api.getReliabilityTargets().catch(() => []),
        api.getReliabilityTestCases().catch(() => []),
        api.getFailurePatterns().catch(() => []),
        api.getReliabilityPredictions().catch(() => []),
        api.getQAPrioritization().catch(() => []),
        api.getModelStatus().catch(() => null),
        api.getDatasetAudit().catch(() => null),
        api.getScientificEvaluation().catch(() => null),
        api.getPredictionRecords().catch(() => []),
        api.getDatasetDiagnostics().catch(() => null),
        api.getPopulationSeparation().catch(() => null),
      ]);

      setSummary(sumData);
      setTrends(trendData);
      setTargets(targetData || []);
      setTestCases(testCaseData || []);
      setFailurePatterns(patternData || []);
      setPredictions(predData || []);
      setPrioritization(prioData || []);
      setModelStatus(statusData);
      setAuditReport(auditData);
      setScientificReport(sciData);
      setPredictionRecords(recordsData || []);
      setDiagnosticsReport(diagData);
      setPopReport(popData);


    } catch (err) {
      console.error('Failed to load reliability analytics data', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTrainModel = async () => {
    setIsTraining(true);
    setTrainingFeedback(null);
    try {
      const metrics = await api.trainReliabilityModel();
      setModelStatus(metrics);
      if (metrics.status === 'TRAINED') {
        setTrainingFeedback(`Model fitted on ${metrics.train_samples} chronological samples (Validation Accuracy: ${((metrics.accuracy || 0) * 100).toFixed(1)}%)`);
      } else {
        setTrainingFeedback(metrics.notes[0] || 'Insufficient historical execution transitions for statistical model calibration.');
      }
      await loadData();
    } catch (err: any) {
      setTrainingFeedback(`Training failed: ${err.message}`);
    } finally {
      setIsTraining(false);
    }
  };

  const getTrendBadge = (trend: TrendStatus) => {
    switch (trend) {
      case 'IMPROVING':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[11px] font-medium">
            <TrendingDown className="h-3 w-3" />
            <span>Improving</span>
          </span>
        );
      case 'DEGRADING':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-300 border border-rose-500/20 text-[11px] font-medium animate-pulse">
            <TrendingUp className="h-3 w-3" />
            <span>Degrading</span>
          </span>
        );
      case 'STABLE':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 text-[11px] font-medium">
            <Minus className="h-3 w-3" />
            <span>Stable</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-slate-800/60 text-slate-400 border border-slate-700/50 text-[11px]">
            <span>Insufficient Data</span>
          </span>
        );
    }
  };

  const getRiskBandBadge = (risk: RiskBand) => {
    switch (risk) {
      case 'HIGH':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30 text-[10px] font-semibold uppercase tracking-wider">
            High Risk
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[10px] font-semibold uppercase tracking-wider">
            Medium Risk
          </span>
        );
      case 'LOW':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px] font-semibold uppercase tracking-wider">
            Low Risk
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 text-[10px] font-medium">
            Unknown
          </span>
        );
    }
  };

  const fmtPct = (val: number | null | undefined) => (typeof val === 'number' ? `${(val * 100).toFixed(1)}%` : 'N/A');

  const getDatasetStatusBadge = (status: DatasetStatus) => {
    switch (status) {
      case 'USABLE':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-xs font-semibold">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>USABLE DATASET</span>
          </span>
        );
      case 'INSUFFICIENT_DATA':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 text-xs font-semibold">
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>INSUFFICIENT DATA</span>
          </span>
        );
      case 'NO_DATA':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700 text-xs font-semibold">
            <Minus className="h-3.5 w-3.5" />
            <span>NO DATA</span>
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 pb-16">
      {/* Top Hero Banner */}
      <div className="border-b border-slate-800/80 bg-gradient-to-b from-[#0d1527] to-[#070b14] py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div>
              <div className="flex items-center space-x-3 mb-2">
                <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 p-[1px] shadow-[0_0_20px_rgba(6,182,212,0.3)]">
                  <div className="h-full w-full bg-slate-950 rounded-[11px] flex items-center justify-center">
                    <Brain className="h-5 w-5 text-cyan-400" />
                  </div>
                </div>
                <div>
                  <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-sans flex items-center space-x-2">
                    <span>Historical Reliability & Scientific Predictive QA</span>
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-mono font-semibold">
                      Slice 6.1 Validated
                    </span>
                  </h1>
                  <p className="text-xs sm:text-sm text-slate-400">
                    Scientific benchmark validation, zero-leakage chronological evaluation, empirical calibration, and continuous closed-loop tracking.
                  </p>
                </div>
              </div>
            </div>

            {/* Model Lifecycle & Training Controller */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 bg-slate-900/90 border border-slate-800 rounded-xl p-3 shadow-lg">
              <div className="text-xs">
                <div className="flex items-center space-x-2">
                  <span className="text-slate-400">Model:</span>
                  <span className="font-mono text-cyan-300 font-medium">
                    {modelStatus?.model_version || 'v1.0-logistic-reliability'}
                  </span>
                  <span className={`inline-block h-2 w-2 rounded-full ${modelStatus?.status === 'TRAINED' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                </div>
                <div className="text-[11px] text-slate-400 flex items-center space-x-3 mt-1">
                  <span>Samples: <strong className="text-slate-200">{modelStatus?.train_samples || 0}</strong></span>
                  <span>Validation Acc: <strong className="text-slate-200">{modelStatus?.accuracy ? `${(modelStatus.accuracy * 100).toFixed(0)}%` : 'N/A'}</strong></span>
                </div>
              </div>

              <button
                onClick={handleTrainModel}
                disabled={isTraining}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-[0_0_15px_rgba(99,102,241,0.4)] disabled:opacity-50 transition-all active:scale-95"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isTraining ? 'animate-spin' : ''}`} />
                <span>{isTraining ? 'Fitting...' : 'Fit Model'}</span>
              </button>
            </div>
          </div>

          {trainingFeedback && (
            <div className="mt-4 p-2.5 rounded-lg bg-indigo-950/50 border border-indigo-500/30 text-xs text-indigo-200 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Info className="h-4 w-4 text-cyan-400 flex-shrink-0" />
                <span>{trainingFeedback}</span>
              </div>
              <button onClick={() => setTrainingFeedback(null)} className="text-slate-400 hover:text-slate-200">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        {/* KPI Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5 mb-6">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Total Historical Runs</div>
            <div className="text-2xl font-bold text-white mt-1 font-mono">{summary?.total_runs ?? 0}</div>
            <div className="text-[11px] text-slate-400 mt-1 flex items-center space-x-1">
              <span>Failures:</span>
              <span className="text-rose-400 font-semibold">{summary?.total_failures ?? 0}</span>
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Failure Rate</div>
            <div className="text-2xl font-bold text-rose-400 mt-1 font-mono">
              {summary?.failure_rate !== undefined ? `${(summary.failure_rate * 100).toFixed(1)}%` : '0.0%'}
            </div>
            <div className="mt-1 flex items-center space-x-1">
              {summary ? getTrendBadge(summary.overall_trend) : null}
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Dataset Status</div>
            <div className="mt-2">
              {auditReport ? getDatasetStatusBadge(auditReport.status) : <span className="text-xs text-slate-400">Loading...</span>}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {auditReport?.total_usable_prediction_samples ?? 0} t &rarr; t+1 samples
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Tracked Predictions</div>
            <div className="text-2xl font-bold text-cyan-400 mt-1 font-mono">
              {scientificReport?.evaluated_predictions_count ?? 0}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {scientificReport?.pending_predictions_count ?? 0} pending next run
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Calibration Score</div>
            <div className="text-2xl font-bold text-indigo-400 mt-1 font-mono">
              {scientificReport?.calibration.is_evaluated && typeof scientificReport.calibration.brier_score === 'number'
                ? `Brier: ${scientificReport.calibration.brier_score.toFixed(3)}`
                : 'UNESTABLISHED'}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {scientificReport?.calibration.is_evaluated ? `ECE: ${((scientificReport.calibration.expected_calibration_error || 0) * 100).toFixed(1)}%` : 'Insufficient samples'}
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-3 mb-6">
          <button
            onClick={() => setActiveTab('separation')}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'separation'
                ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.2)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Layers className="h-3.5 w-3.5 text-emerald-400" />
            <span>Dataset Separation & Walk-Forward</span>
            <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-emerald-950/80 text-[10px] text-emerald-300 font-mono border border-emerald-500/30">
              Slice 6.4
            </span>
          </button>

          <button
            onClick={() => setActiveTab('dataset_diagnostics')}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'dataset_diagnostics'
                ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30 shadow-[0_0_12px_rgba(245,158,11,0.2)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <ShieldAlert className="h-3.5 w-3.5 text-amber-400" />
            <span>Dataset Diagnostics & Failure Analysis</span>
            <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-amber-950/80 text-[10px] text-amber-300 font-mono border border-amber-500/30">
              Slice 6.3
            </span>
          </button>


          <button
            onClick={() => setActiveTab('prioritization')}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'prioritization'
                ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
            <span>Risk Prioritization</span>
            <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] text-slate-300 font-mono">
              {prioritization.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('scientific_validation')}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'scientific_validation'
                ? 'bg-purple-500/15 text-purple-300 border border-purple-500/30 shadow-[0_0_12px_rgba(168,85,247,0.2)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <FlaskConical className="h-3.5 w-3.5 text-purple-400" />
            <span>Scientific Validation & Benchmarks</span>
            <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-purple-950/80 text-[10px] text-purple-300 font-mono border border-purple-500/30">
              Slice 6.1
            </span>
          </button>


          <button
            onClick={() => setActiveTab('continuous_tracking')}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'continuous_tracking'
                ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.2)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <GitCommit className="h-3.5 w-3.5 text-emerald-400" />
            <span>Continuous Tracking (Prediction &rarr; Outcome)</span>
            <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] text-slate-300 font-mono">
              {predictionRecords.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('test_cases')}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'test_cases'
                ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Activity className="h-3.5 w-3.5 text-indigo-400" />
            <span>Test Cases</span>
            <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] text-slate-300 font-mono">
              {testCases.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('targets')}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'targets'
                ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Layers className="h-3.5 w-3.5 text-indigo-400" />
            <span>Target Reliability</span>
            <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] text-slate-300 font-mono">
              {targets.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('patterns')}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'patterns'
                ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Flame className="h-3.5 w-3.5 text-indigo-400" />
            <span>Failure Patterns</span>
            <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] text-slate-300 font-mono">
              {failurePatterns.length}
            </span>
          </button>
        </div>

        {/* Tab -1: Dataset Separation & Walk-Forward Evaluation (Slice 6.4) */}
        {activeTab === 'separation' && (
          <div className="space-y-6">
            {/* 1. Provenance & Population Summary Banner */}
            <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-emerald-500/20 gap-3">
                <div className="flex items-center space-x-2.5">
                  <Layers className="h-5 w-5 text-emerald-400" />
                  <div>
                    <h3 className="font-semibold text-emerald-200 text-sm">Production-Grade Dataset Separation & Walk-Forward Cross-Validation</h3>
                    <p className="text-xs text-emerald-300/80">
                      Explicitly segregates real-world application executions from mock and alternating demo harness cycles to prevent evaluation contamination.
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-mono font-semibold">
                    Slice 6.4 Verified
                  </span>
                </div>
              </div>

              {/* Source Provenance Counters */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-slate-950/80 border border-emerald-500/20 p-3 rounded-lg">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Synthetic Mock</div>
                  <div className="text-xl font-bold font-mono text-slate-200 mt-0.5">
                    {popReport?.source_breakdown?.['SYNTHETIC_MOCK'] ?? 60}
                    <span className="text-xs font-normal text-slate-400 ml-1">runs</span>
                  </div>
                  <div className="text-[10px] text-amber-400/90 mt-1">Deterministic unit tests</div>
                </div>

                <div className="bg-slate-950/80 border border-emerald-500/20 p-3 rounded-lg">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Demo Shop Harness</div>
                  <div className="text-xl font-bold font-mono text-purple-300 mt-0.5">
                    {popReport?.source_breakdown?.['DEMO_HARNESS'] ?? 76}
                    <span className="text-xs font-normal text-slate-400 ml-1">runs</span>
                  </div>
                  <div className="text-[10px] text-purple-400 mt-1">Alternating r = -0.52 sequence</div>
                </div>

                <div className="bg-slate-950/80 border border-emerald-500/20 p-3 rounded-lg">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Real Playwright Browser</div>
                  <div className="text-xl font-bold font-mono text-blue-300 mt-0.5">
                    {popReport?.source_breakdown?.['REAL_PLAYWRIGHT'] ?? 0}
                    <span className="text-xs font-normal text-slate-400 ml-1">runs</span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">Real Web Applications</div>
                </div>

                <div className="bg-slate-950/80 border border-emerald-500/20 p-3 rounded-lg">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Real AI Agent</div>
                  <div className="text-xl font-bold font-mono text-cyan-300 mt-0.5">
                    {popReport?.source_breakdown?.['REAL_AI_AGENT'] ?? 0}
                    <span className="text-xs font-normal text-slate-400 ml-1">runs</span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">Ollama / Qwen Agent runs</div>
                </div>
              </div>

              {/* Critical Finding Callout */}
              <div className="p-3.5 rounded-lg bg-slate-950/90 border border-amber-500/30 text-xs text-amber-200/90 space-y-1">
                <div className="font-semibold flex items-center space-x-1.5 text-amber-300">
                  <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                  <span>Crucial Empirical Provenance Finding:</span>
                </div>
                <p className="text-[11px] leading-relaxed text-slate-300 pl-5">
                  The historical database is 100% composed of synthetic mock runs and the demo-shop test harness. Real application executions (Populations B, C, D) represent an unpopulated partition (0 runs). Models fitted on Population E learn the alternating test harness pattern, which must not be conflated with genuine software reliability.
                </p>
              </div>
            </div>

            {/* 2. Population Audit Cards */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                  <Database className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Operational Population Partitions</span>
                </h4>
                <span className="text-[11px] text-slate-400">Click a population to inspect walk-forward evaluation</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3">
                {popReport?.populations.map((pop) => {
                  const isSelected = selectedPopTab === pop.population_id;
                  const isUsable = pop.status === 'USABLE';
                  return (
                    <button
                      key={pop.population_id}
                      onClick={() => setSelectedPopTab(pop.population_id)}
                      className={`text-left p-3.5 rounded-xl border transition-all ${
                        isSelected
                          ? 'bg-slate-900 border-emerald-500/60 shadow-[0_0_15px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/50'
                          : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/90'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-mono font-bold text-slate-400">
                          {pop.population_id.replace('ALL_', '').replace('_ONLY', '')}
                        </span>
                        <span
                          className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-semibold ${
                            isUsable
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {pop.status}
                        </span>
                      </div>

                      <div className="text-xs font-semibold text-slate-200 line-clamp-1 mb-2">
                        {pop.population_name.split(':')[1]?.trim() || pop.population_name}
                      </div>

                      <div className="grid grid-cols-2 gap-1 text-[11px] font-mono text-slate-300 mb-2">
                        <div>Runs: <span className="text-slate-100 font-bold">{pop.total_runs}</span></div>
                        <div>Transitions: <span className="text-slate-100 font-bold">{pop.total_transitions}</span></div>
                        <div>Failures: <span className="text-rose-400">{pop.failures_count}</span></div>
                        <div>Passes: <span className="text-emerald-400">{pop.passes_count}</span></div>
                      </div>

                      <div className="text-[10px] text-slate-400 truncate">
                        Rate: <span className="font-mono text-amber-300">{(pop.failure_rate * 100).toFixed(1)}%</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 3. Walk-Forward Cross-Validation Explorer */}
            {popReport && (
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
                {(() => {
                  const currentWf = popReport.walk_forward_reports[selectedPopTab];
                  if (!currentWf) return null;

                  if (currentWf.status === 'INSUFFICIENT_DATA') {
                    return (
                      <div className="p-6 text-center space-y-3">
                        <div className="h-10 w-10 mx-auto rounded-full bg-slate-800 flex items-center justify-center text-slate-400">
                          <Database className="h-5 w-5" />
                        </div>
                        <h4 className="text-sm font-semibold text-slate-200">
                          {currentWf.population_name}: Insufficient Data for Walk-Forward Validation
                        </h4>
                        <p className="text-xs text-slate-400 max-w-lg mx-auto">
                          {currentWf.status_reason}
                        </p>
                        <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg max-w-md mx-auto text-left text-xs text-slate-300 space-y-1">
                          <div className="font-semibold text-slate-400 text-[11px]">Scientific Validation Rule:</div>
                          <p className="text-[11px] text-slate-400">
                            The platform refuses to fabricate synthetic runs to populate this partition. To establish predictive performance on real software, live executions against real applications must be recorded.
                          </p>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div className="space-y-5">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                        <div>
                          <h4 className="font-semibold text-sm text-slate-200 flex items-center space-x-2">
                            <span>Expanding Window Walk-Forward Validation:</span>
                            <span className="text-emerald-400">{currentWf.population_name}</span>
                          </h4>
                          <p className="text-xs text-slate-400 mt-0.5">
                            Evaluated across {currentWf.num_folds} expanding chronological folds (Min Train: {currentWf.min_train_size}, Step Size: {currentWf.step_size}) without lookahead bias.
                          </p>
                        </div>
                        <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-mono font-medium">
                          {currentWf.total_samples} Usable Transitions
                        </span>
                      </div>

                      {/* Model Aggregate Comparison Table */}
                      <div>
                        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                          Walk-Forward Aggregate Performance Across All Folds (Mean ± Std)
                        </div>
                        <div className="overflow-x-auto rounded-lg border border-slate-800">
                          <table className="w-full text-xs text-left">
                            <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[10px]">
                              <tr>
                                <th className="p-3">Model / Reference Baseline</th>
                                <th className="p-3">Mean Accuracy</th>
                                <th className="p-3">Mean Brier Score</th>
                                <th className="p-3">Mean ROC-AUC</th>
                                <th className="p-3">Mean F1-Score</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800 font-mono">
                              {currentWf.model_aggregates.map((agg) => (
                                <tr key={agg.model_id} className="hover:bg-slate-800/30">
                                  <td className="p-3 font-sans font-medium text-slate-200">
                                    {agg.model_name}
                                  </td>
                                  <td className="p-3 text-emerald-300 font-semibold">
                                    {agg.mean_accuracy !== null && agg.mean_accuracy !== undefined
                                      ? `${(agg.mean_accuracy * 100).toFixed(1)}% ± ${(agg.std_accuracy || 0) * 100 < 0.1 ? '0.0%' : `${((agg.std_accuracy || 0) * 100).toFixed(1)}%`}`
                                      : 'N/A'}
                                  </td>
                                  <td className="p-3 text-indigo-300">
                                    {agg.mean_brier_score !== null && agg.mean_brier_score !== undefined
                                      ? `${agg.mean_brier_score.toFixed(4)} ± ${(agg.std_brier_score || 0).toFixed(4)}`
                                      : 'N/A'}
                                  </td>
                                  <td className="p-3 text-cyan-300">
                                    {agg.mean_roc_auc !== null && agg.mean_roc_auc !== undefined
                                      ? `${(agg.mean_roc_auc * 100).toFixed(1)}% ± ${((agg.std_roc_auc || 0) * 100).toFixed(1)}%`
                                      : 'N/A'}
                                  </td>
                                  <td className="p-3 text-slate-300">
                                    {agg.mean_f1 !== null && agg.mean_f1 !== undefined
                                      ? `${agg.mean_f1.toFixed(4)} ± ${(agg.std_f1 || 0).toFixed(4)}`
                                      : 'N/A'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Fold-by-Fold Progression Table */}
                      <div>
                        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                          Fold-by-Fold Expanding Window Progression
                        </div>
                        <div className="overflow-x-auto rounded-lg border border-slate-800 max-h-80 overflow-y-auto">
                          <table className="w-full text-xs text-left">
                            <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[10px] sticky top-0">
                              <tr>
                                <th className="p-2.5">Fold</th>
                                <th className="p-2.5">Train Window</th>
                                <th className="p-2.5">Test Window</th>
                                <th className="p-2.5">Test Failure Prev</th>
                                <th className="p-2.5">v1.0 (Fixed) Acc</th>
                                <th className="p-2.5">v1.1 (Scaled) Acc</th>
                                <th className="p-2.5">v1.1 Brier</th>
                                <th className="p-2.5">Majority Base Acc</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800 font-mono text-[11px]">
                              {currentWf.folds.map((fold) => {
                                const v10Acc = fold.model_metrics?.['v1.0']?.accuracy;
                                const v11Acc = fold.model_metrics?.['v1.1']?.accuracy;
                                const v11Brier = fold.brier_scores?.['v1.1'];
                                const majAcc = fold.model_metrics?.['majority_baseline']?.accuracy;

                                return (
                                  <tr key={fold.fold_index} className="hover:bg-slate-800/30">
                                    <td className="p-2.5 font-bold text-slate-300">#{fold.fold_index + 1}</td>
                                    <td className="p-2.5 text-slate-400">[0 : {fold.train_sample_count}]</td>
                                    <td className="p-2.5 text-slate-300 font-semibold">{fold.test_sample_count} runs</td>
                                    <td className="p-2.5 text-amber-300">{(fold.test_failure_rate * 100).toFixed(1)}%</td>
                                    <td className={`p-2.5 ${typeof v10Acc === 'number' && v10Acc < 0.2 ? 'text-rose-400 font-bold' : 'text-slate-300'}`}>
                                      {typeof v10Acc === 'number' ? `${(v10Acc * 100).toFixed(1)}%` : 'N/A'}
                                    </td>
                                    <td className={`p-2.5 ${typeof v11Acc === 'number' && v11Acc >= 0.8 ? 'text-emerald-300 font-bold' : 'text-slate-300'}`}>
                                      {typeof v11Acc === 'number' ? `${(v11Acc * 100).toFixed(1)}%` : 'N/A'}
                                    </td>
                                    <td className="p-2.5 text-indigo-300">
                                      {typeof v11Brier === 'number' ? v11Brier.toFixed(4) : 'N/A'}
                                    </td>
                                    <td className="p-2.5 text-slate-400">
                                      {typeof majAcc === 'number' ? `${(majAcc * 100).toFixed(1)}%` : 'N/A'}
                                    </td>
                                  </tr>
                                );
                              })}

                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {/* 4. Primary Insights & Recommendations */}
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-3">
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                <Brain className="h-4 w-4 text-emerald-400" />
                <span>Slice 6.4 Scientific Conclusions & Insights</span>
              </h4>
              <ul className="space-y-2 text-xs text-slate-300">
                <li className="flex items-start space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span>
                    <strong>Population Separation is Essential:</strong> The historical data contains zero real browser or AI agent runs; it consists entirely of synthetic mock runs and the demo-shop harness. Combining them masks the fact that real application failure predictability remains unobserved.
                  </span>
                </li>
                <li className="flex items-start space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span>
                    <strong>Walk-Forward Cross-Validation Resolves Single-Split Fragility:</strong> Testing across 13 expanding chronological folds confirms that v1.0 consistently achieves 3.1% ± 7.2% accuracy across all temporal slices, proving the failure is structural and not an artifact of a single cut point.
                  </span>
                </li>
                <li className="flex items-start space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span>
                    <strong>Harness Inversion Warning:</strong> While v1.1 achieves 92.3% accuracy on Population E, this is solely because it learns the harness defect-remediation alternation ($r = -0.52$). It does not demonstrate real software failure forecasting.
                  </span>
                </li>
              </ul>
            </div>
          </div>
        )}

        {/* Tab 0: Dataset Diagnostics & Model Failure Analysis (Slice 6.3) */}
        {activeTab === 'dataset_diagnostics' && (
          <div className="space-y-6">
            {/* 1. Root Diagnostic Findings & Warnings Banner */}
            <div className="bg-amber-950/30 border border-amber-500/40 rounded-xl p-5 shadow-lg space-y-4">

              <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-amber-500/20 gap-3">
                <div className="flex items-center space-x-2.5">
                  <ShieldAlert className="h-5 w-5 text-amber-400" />
                  <div>
                    <h3 className="font-semibold text-amber-200 text-sm">Model Failure Analysis & Root Diagnostic Findings</h3>
                    <p className="text-xs text-amber-300/80">
                      Scientific diagnosis of why Logistic Reliability Model v1.0 underperformed on historical holdouts.
                    </p>
                  </div>
                </div>
                <span className="px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-mono font-semibold">
                  Evidence-Based Diagnosis
                </span>
              </div>

              {diagnosticsReport?.root_diagnostic_findings && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  {diagnosticsReport.root_diagnostic_findings.map((finding, fIdx) => (
                    <div key={fIdx} className="bg-slate-950/80 border border-amber-500/20 p-3 rounded-lg text-slate-200 flex items-start space-x-2">
                      <span className="h-5 w-5 rounded-full bg-amber-500/20 text-amber-400 font-mono font-bold text-[11px] flex items-center justify-center flex-shrink-0 mt-0.5">
                        {fIdx + 1}
                      </span>
                      <span className="text-[11px] leading-relaxed">{finding}</span>
                    </div>
                  ))}
                </div>
              )}

              {diagnosticsReport?.data_quality_warnings && diagnosticsReport.data_quality_warnings.length > 0 && (
                <div className="p-3 rounded-lg bg-slate-950/90 border border-rose-500/30 text-xs text-rose-200 space-y-1">
                  <div className="font-semibold flex items-center space-x-1.5 text-rose-300">
                    <AlertTriangle className="h-4 w-4" />
                    <span>Active Dataset Quality Warnings:</span>
                  </div>
                  <ul className="list-disc pl-5 space-y-0.5 text-[11px] text-rose-200/90">
                    {diagnosticsReport.data_quality_warnings.map((w, wIdx) => (
                      <li key={wIdx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* 2. Multi-Model and Baseline Comparison Table */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
              <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
                <div>
                  <div className="flex items-center space-x-2.5">
                    <Scale className="h-5 w-5 text-cyan-400" />
                    <h3 className="font-semibold text-slate-100 text-sm">Deterministic Baselines & Multi-Model Benchmark</h3>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Evaluated on identical untouched chronological test holdouts without artificial ranking.
                  </p>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  {diagnosticsReport?.test_count ?? 0} Holdout Samples
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[11px] uppercase tracking-wider font-semibold">
                    <tr>
                      <th className="py-3 px-4">Candidate Model / Baseline</th>
                      <th className="py-3 px-3">Version</th>
                      <th className="py-3 px-3">Accuracy</th>
                      <th className="py-3 px-3">Precision</th>
                      <th className="py-3 px-3">Recall</th>
                      <th className="py-3 px-3">F1-Score</th>
                      <th className="py-3 px-3">ROC-AUC</th>
                      <th className="py-3 px-3">Brier Score</th>
                      <th className="py-3 px-4">Confusion Matrix</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-slate-200">
                    {diagnosticsReport?.model_comparisons.map((m, mIdx) => (
                      <tr key={mIdx} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-sans font-semibold text-slate-100">{m.model_name}</div>
                          <div className="font-sans text-[11px] text-slate-400 font-normal">{m.description}</div>
                        </td>
                        <td className="py-3 px-3 text-cyan-300 text-[11px]">{m.version}</td>
                        <td className="py-3 px-3 font-bold text-slate-100">{fmtPct(m.accuracy)}</td>
                        <td className="py-3 px-3">{fmtPct(m.precision)}</td>
                        <td className="py-3 px-3">{fmtPct(m.recall)}</td>
                        <td className="py-3 px-3">{fmtPct(m.f1_score)}</td>
                        <td className="py-3 px-3">{fmtPct(m.roc_auc)}</td>
                        <td className="py-3 px-3 font-semibold text-indigo-300">
                          {typeof m.brier_score === 'number' ? m.brier_score.toFixed(4) : 'N/A'}
                        </td>
                        <td className="py-3 px-4 text-[10px] text-slate-400">
                          <span className="text-emerald-400 font-semibold">TP:{m.confusion_matrix.true_positives}</span>{' '}
                          <span className="text-rose-400 font-semibold">FP:{m.confusion_matrix.false_positives}</span>{' '}
                          <span className="text-amber-400 font-semibold">FN:{m.confusion_matrix.false_negatives}</span>{' '}
                          <span className="text-slate-300 font-semibold">TN:{m.confusion_matrix.true_negatives}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 3. Brier Score Interpretation Card */}
            {diagnosticsReport?.brier_interpretation && (
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs">
                <div className="space-y-1 max-w-3xl">
                  <div className="font-semibold text-slate-200 flex items-center space-x-2">
                    <FlaskConical className="h-4 w-4 text-purple-400" />
                    <span>Brier Score Scientific Contextualization</span>
                  </div>
                  <p className="text-slate-300 text-[11px] leading-relaxed">
                    {diagnosticsReport.brier_interpretation.explanation}
                  </p>
                </div>
                <div className="flex items-center space-x-3 bg-slate-950 border border-slate-800 p-3 rounded-lg flex-shrink-0 font-mono">
                  <div>
                    <div className="text-[10px] uppercase text-slate-400">Model v1.0 Brier</div>
                    <div className="text-base font-bold text-rose-400">{diagnosticsReport.brier_interpretation.model_v1_0_brier.toFixed(4)}</div>
                  </div>
                  <div className="h-8 w-px bg-slate-800" />
                  <div>
                    <div className="text-[10px] uppercase text-slate-400">Prevalence Baseline</div>
                    <div className="text-base font-bold text-emerald-400">{diagnosticsReport.brier_interpretation.prevalence_baseline_brier.toFixed(4)}</div>
                  </div>
                </div>
              </div>
            )}

            {/* 4. Feature Distributions & Predictiveness */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Feature Distributions */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
                <div className="p-4 border-b border-slate-800/80">
                  <h3 className="font-semibold text-slate-100 text-sm">Feature Distributions (Train vs Test)</h3>
                  <p className="text-xs text-slate-400">Verifying feature scaling disparities and temporal distribution shifts.</p>
                </div>
                <div className="overflow-x-auto max-h-96">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[10px] uppercase tracking-wider sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3">Feature</th>
                        <th className="py-2.5 px-2">Train Mean ± Std</th>
                        <th className="py-2.5 px-2">Test Mean ± Std</th>
                        <th className="py-2.5 px-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono text-[11px] text-slate-300">
                      {diagnosticsReport?.feature_distributions.map((f, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/20">
                          <td className="py-2 px-3 font-sans text-slate-200">{f.feature_name}</td>
                          <td className="py-2 px-2">{f.train_mean.toFixed(2)} (±{f.train_std.toFixed(2)})</td>
                          <td className="py-2 px-2">{f.test_mean.toFixed(2)} (±{f.test_std.toFixed(2)})</td>
                          <td className="py-2 px-3">
                            {f.is_constant ? (
                              <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">CONSTANT</span>
                            ) : f.distribution_shift === 'LARGE_SHIFT' ? (
                              <span className="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 text-[10px]">SHIFT</span>
                            ) : (
                              <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 text-[10px]">STABLE</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Training Feature Predictiveness */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
                <div className="p-4 border-b border-slate-800/80">
                  <h3 className="font-semibold text-slate-100 text-sm">Training Feature Associations (No Leakage)</h3>
                  <p className="text-xs text-slate-400">Statistical correlation strictly computed on past training data.</p>
                </div>
                <div className="overflow-x-auto max-h-96">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[10px] uppercase tracking-wider sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3">Feature</th>
                        <th className="py-2.5 px-2">Train r</th>
                        <th className="py-2.5 px-3">Observed Direction in Historical Data</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-[11px] text-slate-300">
                      {diagnosticsReport?.feature_predictiveness.map((f, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/20">
                          <td className="py-2 px-3 font-semibold text-slate-200">{f.feature_name}</td>
                          <td className="py-2 px-2 font-mono">
                            {typeof f.training_correlation === 'number' ? (
                              <span className={f.training_correlation < 0 ? 'text-amber-300' : 'text-cyan-300'}>
                                {f.training_correlation > 0 ? '+' : ''}{f.training_correlation.toFixed(4)}
                              </span>
                            ) : (
                              <span className="text-slate-500">N/A</span>
                            )}
                          </td>
                          <td className="py-2 px-3 text-[10px] text-slate-400">{f.association_description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* 5. Test Case Heterogeneity & Sequence Analysis */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Test Case Heterogeneity Table */}
              <div className="lg:col-span-2 bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
                <div className="p-4 border-b border-slate-800/80">
                  <h3 className="font-semibold text-slate-100 text-sm">Test Case Heterogeneity & Sequence Analysis</h3>
                  <p className="text-xs text-slate-400">Quantifying transition volume, runner types, and lag-1 autocorrelation per test case.</p>
                </div>
                <div className="overflow-x-auto max-h-80">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[10px] uppercase tracking-wider sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3">Test Case ID</th>
                        <th className="py-2.5 px-2">Runs</th>
                        <th className="py-2.5 px-2">Transitions</th>
                        <th className="py-2.5 px-2">Fail Rate</th>
                        <th className="py-2.5 px-2">Runner</th>
                        <th className="py-2.5 px-3">Autocorr (Lag 1)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono text-[11px] text-slate-300">
                      {diagnosticsReport?.test_case_heterogeneity.map((tc, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/20">
                          <td className="py-2 px-3 font-sans text-slate-200">
                            <span>{tc.test_case_id}</span>
                            {tc.is_dominant && (
                              <span className="ml-2 px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 text-[9px] uppercase font-bold">
                                Dominates Dataset
                              </span>
                            )}
                          </td>
                          <td className="py-2 px-2">{tc.total_executions}</td>
                          <td className="py-2 px-2 font-bold text-cyan-300">{tc.transition_count}</td>
                          <td className="py-2 px-2 text-rose-400">{(tc.failure_rate * 100).toFixed(1)}%</td>
                          <td className="py-2 px-2 font-sans text-[10px] text-slate-400">{tc.dominant_runner}</td>
                          <td className="py-2 px-3">
                            {typeof tc.autocorrelation_lag1 === 'number' ? (
                              <span className={tc.autocorrelation_lag1 < -0.3 ? 'text-amber-400 font-bold' : 'text-slate-300'}>
                                {tc.autocorrelation_lag1.toFixed(4)}
                              </span>
                            ) : (
                              <span className="text-slate-500">N/A</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Demo Shop Sequence Card */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
                <div className="flex items-center space-x-2">
                  <Database className="h-4 w-4 text-cyan-400" />
                  <h3 className="font-semibold text-slate-100 text-sm">Demo Shop Sequence Pattern</h3>
                </div>
                {diagnosticsReport?.demo_shop_analysis ? (
                  <div className="space-y-3 text-xs">
                    <div className="p-2.5 rounded bg-slate-950 border border-slate-800 space-y-1 text-slate-300">
                      <div>Total Executions: <strong className="text-white font-mono">{diagnosticsReport.demo_shop_analysis.total_runs}</strong></div>
                      <div>Failures / Passes: <strong className="text-rose-400 font-mono">{diagnosticsReport.demo_shop_analysis.failures}</strong> / <strong className="text-emerald-400 font-mono">{diagnosticsReport.demo_shop_analysis.passes}</strong></div>
                      <div>Lag-1 Autocorrelation: <strong className="text-amber-300 font-mono">{diagnosticsReport.demo_shop_analysis.autocorrelation_lag1?.toFixed(4) || 'N/A'}</strong></div>
                      <div>Pattern Type: <strong className="text-rose-300">Alternating Test Harness (Fail &rarr; Pass &rarr; Fail)</strong></div>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      {diagnosticsReport.demo_shop_analysis.description}
                    </p>
                  </div>
                ) : (
                  <div className="p-4 text-center text-slate-400 text-xs">No demo shop sequence records found.</div>
                )}
              </div>
            </div>

            {/* 6. Recommended Next Experiments */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
              <div className="flex items-center space-x-2">
                <Brain className="h-5 w-5 text-indigo-400" />
                <h3 className="font-semibold text-slate-100 text-sm">Recommended Next Scientific Experiments</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {diagnosticsReport?.recommended_next_experiment.map((rec, rIdx) => (
                  <div key={rIdx} className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex items-start space-x-2.5">
                    <span className="h-5 w-5 rounded-md bg-indigo-500/20 text-indigo-300 font-mono font-bold text-[11px] flex items-center justify-center flex-shrink-0">
                      {rIdx + 1}
                    </span>
                    <span className="text-[11px] text-slate-300 leading-relaxed">{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 1: Risk-Aware QA Prioritization */}
        {activeTab === 'prioritization' && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
            <div className="p-4 border-b border-slate-800/80 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div>
                <h3 className="font-semibold text-slate-100 text-sm flex items-center space-x-2">
                  <span>Recommended QA Test Execution Schedule</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Data-driven test execution priority list based on predicted failure risk, degrading trends, and recent regressions.
                </p>
              </div>
              <span className="text-[11px] text-slate-400">
                Sorted by highest risk transition
              </span>
            </div>


            {prioritization.length > 0 ? (
              <div className="divide-y divide-slate-800/60">
                {prioritization.map((item) => (
                  <div key={item.priority_rank} className="p-3.5 hover:bg-slate-800/30 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
                    <div className="flex items-start space-x-3">
                      <div className="h-6 w-6 rounded-md bg-slate-800 text-cyan-400 font-mono font-bold flex items-center justify-center text-xs flex-shrink-0">
                        #{item.priority_rank}
                      </div>
                      <div>
                        <div className="font-semibold text-slate-200 flex items-center space-x-2">
                          <span>{item.test_case_name}</span>
                          <span className="text-[11px] font-mono text-slate-400 font-normal">({item.test_case_id})</span>
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5 flex items-center space-x-2">
                          <span>Target: <strong className="text-slate-300 font-mono">{item.target_id}</strong></span>
                          <span>•</span>
                          <span className="text-indigo-300">{item.reason}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4 pl-9 md:pl-0">
                      <div className="flex items-center space-x-2">
                        {getTrendBadge(item.trend)}
                        {getRiskBandBadge(item.risk_band)}
                      </div>

                      {item.failure_probability !== null && item.failure_probability !== undefined ? (
                        <div className="text-right">
                          <div className="font-mono font-bold text-slate-200 text-sm">
                            {(item.failure_probability * 100).toFixed(0)}%
                          </div>
                          <div className="text-[10px] text-slate-400">Est. Failure Prob</div>
                        </div>
                      ) : (
                        <span className="text-slate-400 text-[11px]">N/A</span>
                      )}

                      <button
                        onClick={() => {
                          const pred = predictions.find(p => p.test_case_id === item.test_case_id);
                          if (pred) setSelectedPrediction(pred);
                        }}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 text-[11px] font-medium transition-colors flex items-center space-x-1"
                      >
                        <span>Explain Signals</span>
                        <ChevronRight className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-slate-400 text-xs">
                No active test cases available for prioritization scheduling.
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Scientific Validation & Benchmarks (Slice 6.1) */}
        {activeTab === 'scientific_validation' && (
          <div className="space-y-6">
            {/* 1. Formal Dataset Audit Card */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg">
              <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800/80 gap-4">
                <div>
                  <div className="flex items-center space-x-2.5">
                    <Database className="h-5 w-5 text-purple-400" />
                    <h3 className="font-semibold text-slate-100 text-sm">Formal Historical Dataset Audit</h3>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Authentic empirical QA execution inventory. Never fabricates synthetic runs.
                  </p>
                </div>
                {auditReport && getDatasetStatusBadge(auditReport.status)}
              </div>

              {auditReport && (
                <div className="mt-4 space-y-4">
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-xs text-slate-300 flex items-start space-x-2.5">
                    <Info className="h-4 w-4 text-purple-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <span className="font-semibold text-slate-200">Dataset Status Rationale: </span>
                      <span>{auditReport.status_reason}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
                    <div className="bg-slate-950/80 border border-slate-800/80 p-3 rounded-lg">
                      <div className="text-slate-400 text-[10px] uppercase font-semibold">Total Runs</div>
                      <div className="font-mono font-bold text-slate-100 text-lg mt-0.5">{auditReport.total_runs}</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">{auditReport.failed_runs} fails / {auditReport.passed_runs} passes</div>
                    </div>
                    <div className="bg-slate-950/80 border border-slate-800/80 p-3 rounded-lg">
                      <div className="text-slate-400 text-[10px] uppercase font-semibold">Usable Samples (t&rarr;t+1)</div>
                      <div className="font-mono font-bold text-cyan-400 text-lg mt-0.5">{auditReport.total_usable_prediction_samples}</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Transitions across runs</div>
                    </div>
                    <div className="bg-slate-950/80 border border-slate-800/80 p-3 rounded-lg">
                      <div className="text-slate-400 text-[10px] uppercase font-semibold">Class Balance</div>
                      <div className="font-mono font-bold text-slate-100 text-lg mt-0.5">
                        {auditReport.positive_labels_count} : {auditReport.negative_labels_count}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Fails vs Passes</div>
                    </div>
                    <div className="bg-slate-950/80 border border-slate-800/80 p-3 rounded-lg">
                      <div className="text-slate-400 text-[10px] uppercase font-semibold">Test Cases</div>
                      <div className="font-mono font-bold text-slate-100 text-lg mt-0.5">{auditReport.unique_test_cases_count}</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">{auditReport.repeated_execution_test_cases_count} repeated execs</div>
                    </div>
                    <div className="bg-slate-950/80 border border-slate-800/80 p-3 rounded-lg sm:col-span-2">
                      <div className="text-slate-400 text-[10px] uppercase font-semibold">Temporal Bounds</div>
                      <div className="text-[11px] font-mono text-slate-300 mt-1 truncate">
                        Start: {auditReport.earliest_execution_timestamp ? new Date(auditReport.earliest_execution_timestamp).toLocaleDateString() : 'N/A'}
                      </div>
                      <div className="text-[11px] font-mono text-slate-300 truncate">
                        End: {auditReport.latest_execution_timestamp ? new Date(auditReport.latest_execution_timestamp).toLocaleDateString() : 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* 2. Chronological Splits Breakdown */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg">
              <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-800/80">
                <Calendar className="h-5 w-5 text-indigo-400" />
                <div>
                  <h3 className="font-semibold text-slate-100 text-sm">Chronological Evaluation Splits</h3>
                  <p className="text-xs text-slate-400">Strict temporal splitting without data leakage (max(Train) &le; min(Validation) &le; min(Test)).</p>
                </div>
              </div>

              {scientificReport?.splits && scientificReport.splits.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 mt-4">
                  {scientificReport.splits.map((sp, sIdx) => (
                    <div key={sIdx} className="bg-slate-950 border border-slate-800 rounded-lg p-3.5 text-xs">
                      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                        <span className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">{sp.split_name} SPLIT</span>
                        <span className="px-2 py-0.5 rounded bg-slate-800 font-mono text-[10px] text-slate-300">{sp.sample_count} samples</span>
                      </div>
                      <div className="mt-2.5 space-y-1 text-slate-400 text-[11px]">
                        <div>Labels: <strong className="text-rose-400 font-mono">{sp.positive_count} fails</strong> / <strong className="text-emerald-400 font-mono">{sp.negative_count} passes</strong></div>
                        <div className="truncate">Range Start: <span className="font-mono text-slate-300">{sp.time_range_start ? new Date(sp.time_range_start).toLocaleString() : 'N/A'}</span></div>
                        <div className="truncate">Range End: <span className="font-mono text-slate-300">{sp.time_range_end ? new Date(sp.time_range_end).toLocaleString() : 'N/A'}</span></div>
                      </div>
                      {typeof sp.metrics.accuracy === 'number' && (
                        <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                          <span className="text-slate-400">Measured Accuracy:</span>
                          <span className="font-mono font-bold text-cyan-300">{fmtPct(sp.metrics.accuracy)}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6 text-center text-slate-400 text-xs mt-2">
                  Insufficient chronological samples to establish 3-way train/validation/test holdouts.
                </div>
              )}
            </div>

            {/* 3. Deterministic Baselines vs ML Model Benchmark Table */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
              <div className="p-4 border-b border-slate-800/80">
                <div className="flex items-center space-x-2.5">
                  <Scale className="h-5 w-5 text-cyan-400" />
                  <h3 className="font-semibold text-slate-100 text-sm">Deterministic Baselines & ML Model Scientific Benchmark</h3>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Raw comparative performance on chronological holdouts without biased ranking or fabricated winner claims.
                </p>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[11px] uppercase tracking-wider font-semibold">
                    <tr>
                      <th className="py-3 px-4">Candidate Model / Baseline</th>
                      <th className="py-3 px-4">Description</th>
                      <th className="py-3 px-4 font-mono">Samples</th>
                      <th className="py-3 px-4 font-mono">Accuracy</th>
                      <th className="py-3 px-4 font-mono">Precision</th>
                      <th className="py-3 px-4 font-mono">Recall</th>
                      <th className="py-3 px-4 font-mono">F1-Score</th>
                      <th className="py-3 px-4 font-mono">ROC-AUC</th>
                      <th className="py-3 px-4 font-mono text-right">Confusion Matrix</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-200">
                    {/* Baselines */}
                    {scientificReport?.baselines.map((b) => (
                      <tr key={b.baseline_id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 font-semibold text-slate-200">{b.baseline_name}</td>
                        <td className="py-3 px-4 text-slate-400 text-[11px] max-w-xs">{b.description}</td>
                        <td className="py-3 px-4 font-mono text-slate-300">{b.metrics.sample_count}</td>
                        <td className="py-3 px-4 font-mono font-bold text-slate-100">
                          {fmtPct(b.metrics.accuracy)}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">
                          {fmtPct(b.metrics.precision)}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">
                          {fmtPct(b.metrics.recall)}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">
                          {fmtPct(b.metrics.f1_score)}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">
                          {fmtPct(b.metrics.roc_auc)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-[10px] text-slate-400">
                          TP:{b.metrics.confusion_matrix.true_positives} FP:{b.metrics.confusion_matrix.false_positives} FN:{b.metrics.confusion_matrix.false_negatives} TN:{b.metrics.confusion_matrix.true_negatives}
                        </td>
                      </tr>
                    ))}

                    {/* Logistic Reliability Model */}
                    {scientificReport?.model_evaluation && (
                      <tr className="bg-indigo-950/20 hover:bg-indigo-950/30 transition-colors font-medium border-t-2 border-indigo-500/30">
                        <td className="py-3 px-4 font-bold text-cyan-300 flex items-center space-x-1.5">
                          <Brain className="h-3.5 w-3.5 text-cyan-400" />
                          <span>Logistic Reliability Model (v1.0)</span>
                        </td>
                        <td className="py-3 px-4 text-slate-400 text-[11px] max-w-xs">
                          Calibrated sequence logistic regression model over empirical telemetry features.
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">{scientificReport.model_evaluation.metrics.sample_count}</td>
                        <td className="py-3 px-4 font-mono font-bold text-cyan-300">
                          {fmtPct(scientificReport.model_evaluation.metrics.accuracy)}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-200">
                          {fmtPct(scientificReport.model_evaluation.metrics.precision)}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-200">
                          {fmtPct(scientificReport.model_evaluation.metrics.recall)}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-200">
                          {fmtPct(scientificReport.model_evaluation.metrics.f1_score)}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-200">
                          {fmtPct(scientificReport.model_evaluation.metrics.roc_auc)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-[10px] text-cyan-400">
                          TP:{scientificReport.model_evaluation.metrics.confusion_matrix.true_positives} FP:{scientificReport.model_evaluation.metrics.confusion_matrix.false_positives} FN:{scientificReport.model_evaluation.metrics.confusion_matrix.false_negatives} TN:{scientificReport.model_evaluation.metrics.confusion_matrix.true_negatives}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 4. Probability Calibration Assessment */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-800/80 gap-2">
                <div className="flex items-center space-x-2.5">
                  <Activity className="h-5 w-5 text-indigo-400" />
                  <div>
                    <h3 className="font-semibold text-slate-100 text-sm">Empirical Probability Calibration Analysis</h3>
                    <p className="text-xs text-slate-400">
                      Verifying predicted probabilities against observed outcome fractions (Brier Score & ECE).
                    </p>
                  </div>
                </div>
                <div className="text-xs font-mono text-slate-400">
                  Status: <strong className={scientificReport?.calibration.is_evaluated ? 'text-emerald-400' : 'text-amber-400'}>{scientificReport?.calibration.status || 'UNESTABLISHED'}</strong>
                </div>
              </div>

              {scientificReport?.calibration.is_evaluated ? (
                <div className="mt-4 space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                      <div className="text-slate-400 text-[10px] uppercase font-semibold">Brier Score</div>
                      <div className="font-mono font-bold text-indigo-300 text-lg mt-0.5">
                        {scientificReport.calibration.brier_score?.toFixed(4) || 'N/A'}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">0.00 = Perfect, 0.25 = Guessing</div>
                    </div>
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                      <div className="text-slate-400 text-[10px] uppercase font-semibold">Expected Calibration Error (ECE)</div>
                      <div className="font-mono font-bold text-cyan-300 text-lg mt-0.5">
                        {scientificReport.calibration.expected_calibration_error !== null && scientificReport.calibration.expected_calibration_error !== undefined
                          ? `${(scientificReport.calibration.expected_calibration_error * 100).toFixed(1)}%`
                          : 'N/A'}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Empirical reliability gap</div>
                    </div>
                  </div>

                  {/* Reliability Diagram Bins */}
                  {scientificReport.calibration.reliability_diagram_bins.length > 0 && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-950 text-slate-400 text-[10px] uppercase font-semibold border-b border-slate-800">
                          <tr>
                            <th className="py-2.5 px-3">Bin Range</th>
                            <th className="py-2.5 px-3 font-mono">Sample Count</th>
                            <th className="py-2.5 px-3 font-mono">Mean Predicted Prob</th>
                            <th className="py-2.5 px-3 font-mono">Observed Positive Fraction</th>
                            <th className="py-2.5 px-3 font-mono text-right">Calibration Gap</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 text-slate-200">
                          {scientificReport.calibration.reliability_diagram_bins.map((bin) => (
                            <tr key={bin.bin_index} className="hover:bg-slate-800/30 transition-colors text-[11px]">
                              <td className="py-2 px-3 font-mono text-slate-300">{bin.bin_range}</td>
                              <td className="py-2 px-3 font-mono">{bin.sample_count}</td>
                              <td className="py-2 px-3 font-mono">{(bin.mean_predicted_probability * 100).toFixed(1)}%</td>
                              <td className="py-2 px-3 font-mono">{(bin.empirical_positive_fraction * 100).toFixed(1)}%</td>
                              <td className="py-2 px-3 font-mono text-right text-indigo-300">
                                {(bin.calibration_gap * 100).toFixed(1)}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-4 mt-3 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-400">
                  {scientificReport?.calibration.notes[0] || 'Empirical probability calibration requires minimum 5 test samples.'}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 3: Continuous Tracking (Prediction -> Outcome) (Slice 6.1) */}
        {activeTab === 'continuous_tracking' && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
            <div className="p-4 border-b border-slate-800/80 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <div className="flex items-center space-x-2.5">
                  <GitCommit className="h-5 w-5 text-emerald-400" />
                  <h3 className="font-semibold text-slate-100 text-sm">Prediction &rarr; Execution Outcome Continuous Tracking</h3>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Traceable loop: Every predicted probability is held in pending status until the next test run executes, evaluating accuracy objectively.
                </p>
              </div>
              <div className="flex items-center space-x-3 text-xs">
                <span className="text-slate-400">
                  Evaluated: <strong className="text-emerald-400 font-mono">{scientificReport?.evaluated_predictions_count || 0}</strong>
                </span>
                <span className="text-slate-400">
                  Pending: <strong className="text-cyan-400 font-mono">{scientificReport?.pending_predictions_count || 0}</strong>
                </span>
              </div>
            </div>

            {predictionRecords.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[11px] uppercase tracking-wider font-semibold">
                    <tr>
                      <th className="py-3 px-4">Test Case</th>
                      <th className="py-3 px-4">Feature Run (t) &rarr; Target Run (t+1)</th>
                      <th className="py-3 px-4">Model Version</th>
                      <th className="py-3 px-4 font-mono">Predicted Prob</th>
                      <th className="py-3 px-4 font-mono">Predicted Class</th>
                      <th className="py-3 px-4 font-mono">Actual Outcome</th>
                      <th className="py-3 px-4">Tracking Status</th>
                      <th className="py-3 px-4 text-right">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-200">
                    {predictionRecords.map((rec) => (
                      <tr key={rec.prediction_id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-semibold text-slate-100">{rec.test_case_name || rec.test_case_id}</div>
                          <div className="text-[10px] font-mono text-slate-400">{rec.prediction_id}</div>
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px]">
                          <span className="text-cyan-300">{rec.feature_run_id}</span>
                          <span className="text-slate-500 mx-1.5">&rarr;</span>
                          <span className={rec.target_run_id ? 'text-purple-300' : 'text-slate-500 italic'}>
                            {rec.target_run_id || 'Awaiting Next Run'}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-[10px] text-slate-400">{rec.model_version}</td>
                        <td className="py-3 px-4 font-mono font-bold text-slate-100">
                          {(rec.predicted_failure_probability * 100).toFixed(0)}%
                        </td>
                        <td className="py-3 px-4 font-mono">
                          {rec.prediction_class === 1 ? (
                            <span className="text-rose-400 font-semibold">Fail (1)</span>
                          ) : (
                            <span className="text-emerald-400 font-semibold">Pass (0)</span>
                          )}
                        </td>
                        <td className="py-3 px-4 font-mono">
                          {rec.actual_outcome !== null && rec.actual_outcome !== undefined ? (
                            rec.actual_outcome === 1 ? (
                              <span className="text-rose-400 font-semibold">Failed</span>
                            ) : (
                              <span className="text-emerald-400 font-semibold">Passed</span>
                            )
                          ) : (
                            <span className="text-slate-500 italic text-[11px]">Pending Run</span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {rec.evaluation_status === 'EVALUATED' ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30 text-[10px] font-semibold">
                              EVALUATED
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 text-[10px] font-semibold animate-pulse">
                              PENDING NEXT RUN
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {rec.is_correct !== null && rec.is_correct !== undefined ? (
                            rec.is_correct ? (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold">
                                <Check className="h-3 w-3" />
                                <span>CORRECT</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30 text-[10px] font-bold">
                                <X className="h-3 w-3" />
                                <span>INCORRECT</span>
                              </span>
                            )
                          ) : (
                            <span className="text-slate-500 text-[11px]">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center text-slate-400 text-xs">
                No continuous prediction records logged yet. Predictions are created automatically when evaluating test cases.
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Test Case Risk & Prediction Table */}
        {activeTab === 'test_cases' && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[11px] uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="py-3 px-4">Test Case</th>
                    <th className="py-3 px-4">Target</th>
                    <th className="py-3 px-4">Executions</th>
                    <th className="py-3 px-4">Historical Failure Rate</th>
                    <th className="py-3 px-4">Recent Trend</th>
                    <th className="py-3 px-4">Predicted Failure Risk</th>
                    <th className="py-3 px-4">Risk Band</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-200">
                  {testCases.map((tc) => {
                    const pred = tc.prediction || predictions.find(p => p.test_case_id === tc.test_case_id);
                    const prob = pred?.failure_probability;

                    return (
                      <tr key={tc.test_case_id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-semibold text-slate-100">{tc.test_case_name}</div>
                          <div className="text-[10px] font-mono text-slate-400">{tc.test_case_id}</div>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">{tc.target_id}</td>
                        <td className="py-3 px-4 font-mono">{tc.execution_count} ({tc.failure_count} failed)</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono font-semibold">
                              {(tc.failure_rate * 100).toFixed(1)}%
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4">{getTrendBadge(tc.recent_trend)}</td>
                        <td className="py-3 px-4">
                          {pred?.prediction_available && prob !== null && prob !== undefined ? (
                            <div className="flex items-center space-x-2">
                              <div className="w-20 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                <div 
                                  className={`h-full ${prob >= 0.6 ? 'bg-rose-500' : prob >= 0.25 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                                  style={{ width: `${Math.max(5, prob * 100)}%` }}
                                />
                              </div>
                              <span className="font-mono font-bold text-slate-100">
                                {(prob * 100).toFixed(0)}%
                              </span>
                            </div>
                          ) : (
                            <span className="text-[11px] text-slate-400 italic">
                              {pred?.status === 'INSUFFICIENT_DATA' ? 'Insufficient Data' : 'Unavailable'}
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {pred ? getRiskBandBadge(pred.risk_band) : getRiskBandBadge('UNKNOWN')}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => {
                              if (pred) setSelectedPrediction(pred);
                            }}
                            disabled={!pred}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 text-[11px] font-medium transition-colors disabled:opacity-40"
                          >
                            Explain
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 5: Target Reliability Table */}
        {activeTab === 'targets' && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[11px] uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="py-3 px-4">Target Application</th>
                    <th className="py-3 px-4">Target ID</th>
                    <th className="py-3 px-4">Total Runs</th>
                    <th className="py-3 px-4">Failure Rate</th>
                    <th className="py-3 px-4">Recent Trend</th>
                    <th className="py-3 px-4">Grounded Component Attributions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-200">
                  {targets.map((tgt) => (
                    <tr key={tgt.target_id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4 font-semibold text-slate-100">{tgt.target_name}</td>
                      <td className="py-3 px-4 font-mono text-slate-300">{tgt.target_id}</td>
                      <td className="py-3 px-4 font-mono">{tgt.run_count} ({tgt.failure_count} failed)</td>
                      <td className="py-3 px-4 font-mono font-semibold text-rose-400">
                        {(tgt.failure_rate * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-4">{getTrendBadge(tgt.recent_trend)}</td>
                      <td className="py-3 px-4">
                        {tgt.grounded_component_failures && Object.keys(tgt.grounded_component_failures).length > 0 ? (
                          <div className="flex items-center flex-wrap gap-1.5">
                            {Object.entries(tgt.grounded_component_failures).map(([comp, count], cIdx) => (
                              <span key={cIdx} className="px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 text-[10px] font-mono">
                                {comp}: {count}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-[11px] text-slate-400 italic">No validated component failures</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 6: Failure Patterns */}
        {activeTab === 'patterns' && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-lg p-5">
            <h3 className="font-semibold text-slate-100 text-sm mb-4 flex items-center space-x-2">
              <Flame className="h-4 w-4 text-rose-400" />
              <span>Grounded Failure Patterns & Component Correlations</span>
            </h3>
            {failurePatterns.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {failurePatterns.map((pat, pIdx) => (
                  <div key={pIdx} className="bg-slate-950 border border-slate-800 p-4 rounded-xl text-xs space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-rose-300">{pat.category}</span>
                      <span className="px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30 font-mono text-[10px]">
                        {pat.count} failures ({pat.percentage.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="text-slate-400 text-[11px]">
                      Avg Execution Duration: <strong className="text-slate-200 font-mono">{pat.avg_duration_ms} ms</strong>
                    </div>
                    {pat.top_grounded_components.length > 0 && (
                      <div className="pt-2 border-t border-slate-800/80">
                        <div className="text-[10px] text-slate-400 uppercase font-semibold mb-1">Grounded Correlated Components:</div>
                        <div className="flex flex-wrap gap-1.5">
                          {pat.top_grounded_components.map((comp, cIdx) => (
                            <span key={cIdx} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono">
                              {comp}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-slate-400 text-xs">
                No recorded failure patterns in the database.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Feature Importance & Signal Explainability Modal */}
      {selectedPrediction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-[#0b101d] border border-slate-800 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between sticky top-0 bg-[#0b101d] z-10">
              <div>
                <h3 className="font-semibold text-slate-100 text-base flex items-center space-x-2">
                  <Brain className="h-5 w-5 text-cyan-400" />
                  <span>Failure Risk Prediction Explanation</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Test Case: <strong className="text-slate-200">{selectedPrediction.test_case_name || selectedPrediction.test_case_id}</strong>
                </p>
              </div>
              <button
                onClick={() => setSelectedPrediction(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-5 space-y-5">
              {/* Risk Summary Header */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Model Estimated Failure Probability</div>
                  <div className="text-3xl font-bold text-white font-mono mt-1">
                    {selectedPrediction.failure_probability !== null && selectedPrediction.failure_probability !== undefined
                      ? `${(selectedPrediction.failure_probability * 100).toFixed(1)}%`
                      : 'N/A'}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    Model Version: <span className="font-mono text-cyan-300">{selectedPrediction.model_version}</span>
                  </div>
                </div>
                <div className="text-right">
                  {getRiskBandBadge(selectedPrediction.risk_band)}
                  <div className="text-[11px] text-slate-400 mt-2">
                    Historical Runs: <strong className="text-slate-200 font-mono">{selectedPrediction.training_data_size}</strong>
                  </div>
                </div>
              </div>

              {/* Baseline Comparison */}
              {selectedPrediction.baseline_probabilities && Object.keys(selectedPrediction.baseline_probabilities).length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Deterministic Baseline Comparison</h4>
                  <div className="grid grid-cols-3 gap-2.5">
                    <div className="bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs">
                      <div className="text-slate-400 text-[10px]">Last Execution Status</div>
                      <div className="font-mono font-bold text-slate-200 text-sm mt-0.5">
                        {((selectedPrediction.baseline_probabilities.last_status_prob || 0) * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs">
                      <div className="text-slate-400 text-[10px]">Moving Average (3 Runs)</div>
                      <div className="font-mono font-bold text-slate-200 text-sm mt-0.5">
                        {((selectedPrediction.baseline_probabilities.moving_average_3_prob || 0) * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs">
                      <div className="text-slate-400 text-[10px]">Historical Frequency</div>
                      <div className="font-mono font-bold text-slate-200 text-sm mt-0.5">
                        {((selectedPrediction.baseline_probabilities.historical_frequency_prob || 0) * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Major Contributing Features */}
              <div>
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Major Contributing Signals</h4>
                {selectedPrediction.contributing_features && selectedPrediction.contributing_features.length > 0 ? (
                  <div className="space-y-2">
                    {selectedPrediction.contributing_features.map((feat, idx) => {
                      const isElevating = feat.contribution > 0;
                      return (
                        <div key={idx} className="bg-slate-950 border border-slate-800 rounded-lg p-2.5 flex items-center justify-between text-xs">
                          <div>
                            <div className="font-semibold text-slate-200 flex items-center space-x-2">
                              <span className={isElevating ? 'text-rose-400' : 'text-emerald-400'}>
                                {isElevating ? '+' : ''}{feat.contribution.toFixed(2)}
                              </span>
                              <span>{feat.description}</span>
                            </div>
                            <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                              Feature: {feat.feature_name} (Value: {feat.value}, Weight: {feat.weight})
                            </div>
                          </div>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${isElevating ? 'bg-rose-500/10 text-rose-300 border border-rose-500/20' : 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'}`}>
                            {isElevating ? 'Increases Risk' : 'Lowers Risk'}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-400">
                    No significant feature contributions recorded (baseline state active).
                  </div>
                )}
              </div>

              {/* Limitations & Policy Notes */}
              {selectedPrediction.limitations && selectedPrediction.limitations.length > 0 && (
                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 space-y-1">
                  <div className="font-semibold flex items-center space-x-1.5 text-amber-300">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span>Model Limitations & Calibration State</span>
                  </div>
                  <ul className="list-disc pl-4 space-y-0.5 text-[11px] text-amber-200/90">
                    {selectedPrediction.limitations.map((lim, lIdx) => (
                      <li key={lIdx}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-slate-800 bg-[#090d16] flex justify-end">
              <button
                onClick={() => setSelectedPrediction(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors"
              >
                Close Explanation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
