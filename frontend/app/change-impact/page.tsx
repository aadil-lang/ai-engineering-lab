'use client';

import React, { useState, useEffect } from 'react';
import { AppShell } from '@/components/AppShell';
import { changeImpactApi } from '@/lib/api';
import {
  ChangeImpactModel,
  AdaptiveRegressionPlanModel,
  BehavioralComparisonModel,
  RegressionFindingModel,
  ChangeSetModel,
} from '@/types';
import {
  GitCommit,
  GitBranch,
  Layers,
  Activity,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Shield,
  ArrowRight,
  Database,
  Cpu,
  FileCode,
  Sparkles,
  RefreshCw,
  Zap,
} from 'lucide-react';

export default function ChangeImpactPage() {
  const [activeTab, setActiveTab] = useState<'plan' | 'graph' | 'comparison' | 'findings'>('plan');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Demo / live state
  const [changeSet, setChangeSet] = useState<Partial<ChangeSetModel>>({
    base_commit: 'a1b2c3d4e5f6',
    candidate_commit: 'f6e5d4c3b2a1',
    repository: 'question-generator',
    changed_files: [
      'backend/app/question_generator/parser.py',
      'backend/app/prompts/question_gen_v13.prompt',
    ],
    changed_prompts: ['prompt_question_gen_v13'],
    changed_contracts: ['contract_4_options_present', 'contract_correct_answer_indicated'],
  });

  const [impact, setImpact] = useState<ChangeImpactModel | null>(null);
  const [plan, setPlan] = useState<AdaptiveRegressionPlanModel | null>(null);
  const [comparison, setComparison] = useState<BehavioralComparisonModel | null>(null);
  const [findings, setFindings] = useState<RegressionFindingModel[]>([]);

  // Analyze Change Handler
  const handleAnalyzeChange = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await changeImpactApi.analyzeChange({
        base_commit: changeSet.base_commit || 'base_sha_001',
        candidate_commit: changeSet.candidate_commit || 'cand_sha_002',
        repository: changeSet.repository || 'default_app',
        changed_files: changeSet.changed_files || [],
        changed_prompts: changeSet.changed_prompts || [],
      });
      setImpact(res);

      // Create Plan automatically
      const planRes = await changeImpactApi.createPlan({
        change_set_id: res.change_set_id,
        target_id: 'target_question_gen',
        application_id: 'question_generator_app',
      });
      setPlan(planRes);

      // Simulate a comparison
      const compRes = await changeImpactApi.compareRuns(planRes.plan_id, {
        baseline_run_id: 'run_baseline_101',
        candidate_run_id: 'run_candidate_102',
        baseline_results: { passed: true, errors: [] },
        candidate_results: { passed: false, errors: ['Output contains 3 options instead of 4'] },
        contract_evaluations: { contract_4_options_present: false, contract_correct_answer_indicated: true },
        evidence_ids: ['evi_dom_capture_99', 'evi_contract_violation_01'],
      });
      setComparison(compRes);

      const findRes = await changeImpactApi.getFindings(planRes.plan_id);
      setFindings(findRes);
    } catch (err: any) {
      setError(err?.message || 'Failed to analyze change impact.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleAnalyzeChange();
  }, []);

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded">
                Slice 8K
              </span>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Change-Aware Impact Analysis & Adaptive Regression
              </h1>
            </div>
            <p className="text-sm text-gray-400 mt-1">
              Deterministic impact reasoning across code, prompts, models, and contracts with evidence-driven scope expansion.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleAnalyzeChange}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors shadow-sm disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Re-analyze Impact
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-950/40 border border-red-800/60 rounded-lg text-red-300 text-sm flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* ChangeSet Details Ribbon */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-800/80 pb-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg border border-indigo-500/20">
                <GitCommit className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-gray-500 font-mono">CHANGE SET</div>
                <div className="text-sm font-bold text-gray-200">
                  {impact?.change_set_id || 'cs_detecting...'}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">BASE:</span>
                <span className="font-mono text-xs bg-gray-800 px-2 py-1 rounded text-gray-300">
                  {changeSet.base_commit?.slice(0, 8)}
                </span>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-600" />
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">CANDIDATE:</span>
                <span className="font-mono text-xs bg-indigo-950 border border-indigo-800 px-2 py-1 rounded text-indigo-300 font-semibold">
                  {changeSet.candidate_commit?.slice(0, 8)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">REPO:</span>
                <span className="text-xs text-gray-300 font-medium">
                  {changeSet.repository}
                </span>
              </div>
            </div>
          </div>

          {/* Changed Files & Types */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <div className="text-gray-400 mb-1.5 font-medium flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5 text-gray-500" />
                Modified Files & Prompts:
              </div>
              <div className="space-y-1">
                {changeSet.changed_files?.map((f, i) => (
                  <div key={i} className="font-mono bg-gray-950 px-2.5 py-1 rounded text-gray-300 border border-gray-800/60">
                    {f}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="text-gray-400 mb-1.5 font-medium flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-gray-500" />
                Behavioral Contracts Bound:
              </div>
              <div className="flex flex-wrap gap-1.5">
                {changeSet.changed_contracts?.map((c, i) => (
                  <span key={i} className="px-2 py-1 bg-amber-500/10 border border-amber-500/20 text-amber-300 rounded font-mono">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-gray-800">
          <button
            onClick={() => setActiveTab('plan')}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'plan'
                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Layers className="w-4 h-4" />
            Adaptive Regression Plan
            {plan && (
              <span className="ml-1 text-xs px-1.5 py-0.5 rounded-full bg-gray-800 text-gray-300">
                {plan.items.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('graph')}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'graph'
                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Activity className="w-4 h-4" />
            Impact Graph & Components
            {impact && (
              <span className="ml-1 text-xs px-1.5 py-0.5 rounded-full bg-gray-800 text-gray-300">
                {impact.affected_components.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('comparison')}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'comparison'
                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <RefreshCw className="w-4 h-4" />
            Behavioral Comparison
            {comparison && (
              <span className={`ml-1 text-xs px-1.5 py-0.5 rounded-full font-semibold ${
                comparison.classification === 'REGRESSION' ? 'bg-red-500/20 text-red-300' : 'bg-green-500/20 text-green-300'
              }`}>
                {comparison.classification}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('findings')}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'findings'
                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            Regression Findings
            {findings.length > 0 && (
              <span className="ml-1 text-xs px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-300 font-semibold">
                {findings.length}
              </span>
            )}
          </button>
        </div>

        {/* Tab 1: Adaptive Regression Plan */}
        {activeTab === 'plan' && plan && (
          <div className="space-y-6">
            {/* Scope Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-red-950/20 border border-red-900/40 rounded-xl">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold uppercase tracking-wider text-red-400">DEEP TESTS</div>
                  <span className="px-2 py-0.5 text-xs bg-red-500/20 text-red-300 rounded font-mono font-bold">
                    {plan.scope_summary.DEEP}
                  </span>
                </div>
                <div className="text-2xl font-black text-white mt-2">{plan.scope_summary.DEEP} Workflows</div>
                <p className="text-xs text-gray-400 mt-1">Directly affected behaviors, malformed outputs, and boundary cases.</p>
              </div>

              <div className="p-4 bg-amber-950/20 border border-amber-900/40 rounded-xl">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold uppercase tracking-wider text-amber-400">TARGETED TESTS</div>
                  <span className="px-2 py-0.5 text-xs bg-amber-500/20 text-amber-300 rounded font-mono font-bold">
                    {plan.scope_summary.TARGETED}
                  </span>
                </div>
                <div className="text-2xl font-black text-white mt-2">{plan.scope_summary.TARGETED} Workflows</div>
                <p className="text-xs text-gray-400 mt-1">Dependencies, downstream UI rendering, and historical failure hypotheses.</p>
              </div>

              <div className="p-4 bg-blue-950/20 border border-blue-900/40 rounded-xl">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold uppercase tracking-wider text-blue-400">SMOKE TESTS</div>
                  <span className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-300 rounded font-mono font-bold">
                    {plan.scope_summary.SMOKE}
                  </span>
                </div>
                <div className="text-2xl font-black text-white mt-2">{plan.scope_summary.SMOKE} Workflows</div>
                <p className="text-xs text-gray-400 mt-1">Critical application paths, root route health, and baseline integrity.</p>
              </div>
            </div>

            {/* Plan Items Table */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden shadow-sm">
              <div className="p-4 border-b border-gray-800 bg-gray-900/50 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Selected Regression Workflows</h3>
                  <p className="text-xs text-gray-400 mt-0.5">Every item includes structured, deterministic reasons for its inclusion.</p>
                </div>
                <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2 py-1 rounded border border-indigo-500/20">
                  Status: {plan.plan_status}
                </span>
              </div>

              <div className="divide-y divide-gray-800/60">
                {plan.items.map((item) => (
                  <div key={item.item_id} className="p-4 hover:bg-gray-850/50 transition-colors">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold uppercase ${
                          item.scope === 'DEEP'
                            ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                            : item.scope === 'TARGETED'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                        }`}>
                          {item.scope}
                        </span>
                        <span className="font-semibold text-gray-200 text-sm">{item.name}</span>
                        <span className="text-xs text-gray-500 font-mono">({item.workflow_id})</span>
                      </div>
                      <div className="text-xs font-mono text-gray-400">
                        Priority: <span className="text-white font-bold">{item.priority.toFixed(2)}</span>
                      </div>
                    </div>

                    <div className="space-y-1 mt-2">
                      <div className="text-xs text-gray-500 font-medium">Deterministic Reasons:</div>
                      <ul className="list-disc list-inside text-xs text-gray-300 space-y-0.5">
                        {item.reasons.map((r, ri) => (
                          <li key={ri} className="font-mono text-gray-300">
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {item.relevant_contracts && item.relevant_contracts.length > 0 && (
                      <div className="flex items-center gap-1.5 mt-2.5">
                        <span className="text-xs text-gray-500">Contracts:</span>
                        {item.relevant_contracts.map((c, ci) => (
                          <span key={ci} className="text-xs font-mono bg-gray-800 px-1.5 py-0.5 rounded text-amber-400">
                            {c}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Runtime Scope Expansions */}
            {plan.expansions && plan.expansions.length > 0 && (
              <div className="p-4 bg-indigo-950/20 border border-indigo-800/40 rounded-xl space-y-3">
                <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm">
                  <Zap className="w-4 h-4" />
                  Runtime Scope Expansions ({plan.expansions.length})
                </div>
                <div className="space-y-2">
                  {plan.expansions.map((exp) => (
                    <div key={exp.expansion_id} className="text-xs bg-gray-900/80 p-3 rounded border border-gray-800">
                      <div className="font-bold text-gray-200">{exp.trigger}</div>
                      <div className="text-gray-400 mt-1">{exp.reason}</div>
                      <div className="text-gray-500 font-mono mt-1">Evidence: {exp.evidence_ids.join(', ')}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Impact Graph & Components */}
        {activeTab === 'graph' && impact && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Affected Components */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-indigo-400" />
                  Affected Application Components ({impact.affected_components.length})
                </h3>

                <div className="space-y-3">
                  {impact.affected_components.map((comp) => (
                    <div key={comp.component_id} className="p-3 bg-gray-950 border border-gray-800 rounded-lg space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-gray-200 text-sm">{comp.name}</span>
                        <span className="text-xs font-mono uppercase px-2 py-0.5 bg-gray-800 text-indigo-300 rounded">
                          {comp.component_type}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400">{comp.reason}</div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {comp.confidence_factors.map((cf, i) => (
                          <span key={i} className="text-xs font-mono px-1.5 py-0.5 bg-gray-850 text-gray-400 rounded">
                            {cf}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Affected Workflows & 8E Memory */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Database className="w-4 h-4 text-amber-400" />
                  Affected Workflows & 8E Memory ({impact.affected_workflows.length})
                </h3>

                <div className="space-y-3">
                  {impact.affected_workflows.map((wf) => (
                    <div key={wf.workflow_id} className="p-3 bg-gray-950 border border-gray-800 rounded-lg space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-gray-200 text-sm">{wf.name}</span>
                        <span className={`text-xs font-mono px-2 py-0.5 rounded font-bold uppercase ${
                          wf.impact_level === 'HIGH' ? 'bg-red-500/20 text-red-300' : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {wf.impact_level}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400">{wf.reason}</div>

                      {wf.historical_failures && wf.historical_failures.length > 0 && (
                        <div className="p-2 bg-red-950/30 border border-red-900/50 rounded text-xs text-red-300">
                          <span className="font-bold">Historical 8E Memory Failure:</span>{' '}
                          {wf.historical_failures.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Behavioral Comparison */}
        {activeTab === 'comparison' && comparison && (
          <div className="space-y-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                <h3 className="text-sm font-semibold text-white">Execution Behavioral Comparison</h3>
                <span className={`px-2.5 py-1 text-xs font-bold rounded uppercase font-mono ${
                  comparison.classification === 'REGRESSION'
                    ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                    : 'bg-green-500/20 text-green-400 border border-green-500/30'
                }`}>
                  {comparison.classification}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="p-3 bg-gray-950 rounded border border-gray-800">
                  <div className="text-gray-500 font-mono">BASELINE RUN ID</div>
                  <div className="font-bold text-gray-200 mt-1">{comparison.baseline_run_id}</div>
                </div>
                <div className="p-3 bg-gray-950 rounded border border-gray-800">
                  <div className="text-gray-500 font-mono">CANDIDATE RUN ID</div>
                  <div className="font-bold text-gray-200 mt-1">{comparison.candidate_run_id}</div>
                </div>
              </div>

              {comparison.is_multi_variable_change && (
                <div className="p-3 bg-amber-950/40 border border-amber-800/60 rounded-lg text-amber-300 text-xs">
                  <div className="font-bold flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    Multi-Variable Attribution Blocked
                  </div>
                  <p className="mt-1">{comparison.attribution_note}</p>
                </div>
              )}

              <div className="text-xs text-gray-300">
                <span className="font-semibold text-gray-400">Summary: </span>
                {comparison.summary}
              </div>

              {comparison.contract_violations && comparison.contract_violations.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-xs font-semibold text-red-400">Contract Violations:</div>
                  <div className="space-y-1">
                    {comparison.contract_violations.map((cv, i) => (
                      <div key={i} className="text-xs font-mono bg-red-950/40 border border-red-900/60 text-red-300 px-3 py-1.5 rounded">
                        {cv}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 4: Regression Findings & Governance */}
        {activeTab === 'findings' && (
          <div className="space-y-6">
            {findings.length === 0 ? (
              <div className="p-8 text-center bg-gray-900 border border-gray-800 rounded-xl text-gray-400 text-sm">
                <CheckCircle2 className="w-8 h-8 text-green-400 mx-auto mb-2" />
                No regression findings detected for candidate revision.
              </div>
            ) : (
              <div className="space-y-4">
                {findings.map((f) => (
                  <div key={f.finding_id} className="p-5 bg-gray-900 border border-red-900/40 rounded-xl space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 bg-red-500/20 text-red-300 text-xs font-bold font-mono rounded">
                          {f.severity}
                        </span>
                        <h4 className="font-bold text-white text-sm">{f.title}</h4>
                      </div>
                      <span className="text-xs font-mono text-gray-500">{f.finding_id}</span>
                    </div>

                    <p className="text-xs text-gray-300">{f.description}</p>

                    <div className="p-3 bg-gray-950 border border-gray-800 rounded text-xs space-y-1">
                      <div className="text-gray-400 font-semibold">Recommended Action:</div>
                      <div className="text-amber-300">{f.recommended_action}</div>
                    </div>

                    {/* Human Governance Boundary Disclaimer */}
                    <div className="flex items-center gap-2 text-xs text-indigo-400 pt-2 border-t border-gray-800">
                      <Shield className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                      <span>
                        <strong>Human Governance Authorization Required:</strong> Regressions cannot be automatically overridden or merged without an explicit approval request.
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
