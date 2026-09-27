import {
  TestRun,
  TestRunCreate,
  ApplicationTarget,
  TestCase,
  Evidence,
  Failure,
  Metric,
  Assessment,
  EngineeringDiagnosis,
  RemediationTask,
  RemediationTaskCreate,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body.detail) errorDetail = body.detail;
    } catch {}
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  // System Health
  async getHealth(): Promise<any> {
    const url = process.env.NEXT_PUBLIC_API_URL ? `${process.env.NEXT_PUBLIC_API_URL.replace('/api/v1', '')}/health` : '/health';
    const res = await fetch(url);
    if (!res.ok) throw new Error('Backend offline');
    return res.json();
  },

  // Targets
  async getTargets(): Promise<ApplicationTarget[]> {
    return fetchJson<ApplicationTarget[]>('/targets');
  },

  async getTarget(id: string): Promise<ApplicationTarget> {
    return fetchJson<ApplicationTarget>(`/targets/${id}`);
  },

  // Test Cases
  async getTestCases(targetId?: string, testMode?: string): Promise<TestCase[]> {
    const params = new URLSearchParams();
    if (targetId) params.append('target_id', targetId);
    if (testMode) params.append('test_mode', testMode);
    return fetchJson<TestCase[]>(`/test-cases?${params.toString()}`);
  },

  // Runs
  async triggerRun(payload: TestRunCreate): Promise<TestRun> {
    return fetchJson<TestRun>('/runs', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getRuns(options?: {
    limit?: number;
    offset?: number;
    application_id?: string;
    test_mode?: string;
    status?: string;
  }): Promise<{ items: TestRun[]; total: number }> {
    const params = new URLSearchParams();
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.offset) params.append('offset', options.offset.toString());
    if (options?.application_id) params.append('application_id', options.application_id);
    if (options?.test_mode) params.append('test_mode', options.test_mode);
    if (options?.status) params.append('status', options.status);
    return fetchJson<{ items: TestRun[]; total: number }>(`/runs?${params.toString()}`);
  },

  async getRun(runId: string): Promise<TestRun> {
    return fetchJson<TestRun>(`/runs/${runId}`);
  },

  // Evidence
  async getRunEvidence(runId: string): Promise<Evidence[]> {
    return fetchJson<Evidence[]>(`/runs/${runId}/evidence`);
  },

  async getEvidenceDetail(runId: string, evidenceId: string): Promise<Evidence> {
    return fetchJson<Evidence>(`/runs/${runId}/evidence/${evidenceId}`);
  },

  // Failures & Metrics
  async getRunFailures(runId: string): Promise<Failure[]> {
    return fetchJson<Failure[]>(`/runs/${runId}/failures`);
  },

  async getRunMetrics(runId: string): Promise<Metric[]> {
    return fetchJson<Metric[]>(`/runs/${runId}/metrics`);
  },

  // Failure Diagnosis (Slice 4)
  async getRunDiagnosis(runId: string, autoDiagnose: boolean = true): Promise<EngineeringDiagnosis | null> {
    return fetchJson<EngineeringDiagnosis | null>(`/runs/${runId}/diagnosis?auto_diagnose=${autoDiagnose}`);
  },

  async triggerRunDiagnosis(runId: string): Promise<EngineeringDiagnosis> {
    return fetchJson<EngineeringDiagnosis>(`/runs/${runId}/diagnose`, {
      method: 'POST',
    });
  },

  async listDiagnoses(limit: number = 50, offset: number = 0): Promise<EngineeringDiagnosis[]> {
    return fetchJson<EngineeringDiagnosis[]>(`/diagnoses?limit=${limit}&offset=${offset}`);
  },

  async getDiagnosis(diagnosisId: string): Promise<EngineeringDiagnosis> {
    return fetchJson<EngineeringDiagnosis>(`/diagnoses/${diagnosisId}`);
  },

  // Remediations & Fix Verification (Slice 5)
  async triggerRunRemediation(
    runId: string,
    autoApply: boolean = false,
    targetRepository: string = 'local_workspace',
    targetBranch: string = 'main'
  ): Promise<RemediationTask> {
    const params = new URLSearchParams({
      auto_apply: String(autoApply),
      target_repository: targetRepository,
      target_branch: targetBranch,
    });
    return fetchJson<RemediationTask>(`/runs/${runId}/remediate?${params.toString()}`, {
      method: 'POST',
    });
  },

  async getRunRemediations(runId: string): Promise<RemediationTask[]> {
    return fetchJson<RemediationTask[]>(`/runs/${runId}/remediations`);
  },

  async createRemediation(payload: RemediationTaskCreate): Promise<RemediationTask> {
    return fetchJson<RemediationTask>('/remediations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async applyAndVerifyRemediation(taskId: string): Promise<RemediationTask> {
    return fetchJson<RemediationTask>(`/remediations/${taskId}/apply-verify`, {
      method: 'POST',
    });
  },

  async getRemediation(taskId: string): Promise<RemediationTask> {
    return fetchJson<RemediationTask>(`/remediations/${taskId}`);
  },

  async listRemediations(limit: number = 50, offset: number = 0): Promise<RemediationTask[]> {
    return fetchJson<RemediationTask[]>(`/remediations?limit=${limit}&offset=${offset}`);
  },

  // Assessments
  async getAssessments(applicationId?: string): Promise<Assessment[]> {
    const params = new URLSearchParams();
    if (applicationId) params.append('application_id', applicationId);
    return fetchJson<Assessment[]>(`/assessments?${params.toString()}`);
  },

  // Historical Reliability & Predictive QA (Slice 6)
  async getReliabilitySummary(): Promise<import('@/types').ReliabilitySummary> {
    return fetchJson<import('@/types').ReliabilitySummary>('/reliability/summary');
  },

  async getReliabilityTargets(): Promise<import('@/types').TargetReliability[]> {
    return fetchJson<import('@/types').TargetReliability[]>('/reliability/targets');
  },

  async getTargetReliability(targetId: string): Promise<import('@/types').TargetReliability> {
    return fetchJson<import('@/types').TargetReliability>(`/reliability/targets/${targetId}`);
  },

  async getReliabilityTestCases(): Promise<import('@/types').TestCaseReliability[]> {
    return fetchJson<import('@/types').TestCaseReliability[]>('/reliability/test-cases');
  },

  async getTestCaseReliability(testCaseId: string): Promise<import('@/types').TestCaseReliability> {
    return fetchJson<import('@/types').TestCaseReliability>(`/reliability/test-cases/${testCaseId}`);
  },

  async getReliabilityTrends(): Promise<import('@/types').TrendAnalysis> {
    return fetchJson<import('@/types').TrendAnalysis>('/reliability/trends');
  },

  async getFailurePatterns(): Promise<import('@/types').FailurePattern[]> {
    return fetchJson<import('@/types').FailurePattern[]>('/reliability/failure-patterns');
  },

  async getReliabilityPredictions(): Promise<import('@/types').TestCasePrediction[]> {
    return fetchJson<import('@/types').TestCasePrediction[]>('/reliability/predictions');
  },

  async getTestCasePrediction(testCaseId: string): Promise<import('@/types').TestCasePrediction> {
    return fetchJson<import('@/types').TestCasePrediction>(`/reliability/predictions/${testCaseId}`);
  },

  async getQAPrioritization(): Promise<import('@/types').QAPrioritizationItem[]> {
    return fetchJson<import('@/types').QAPrioritizationItem[]>('/reliability/prioritization');
  },

  async trainReliabilityModel(): Promise<import('@/types').ModelEvaluationMetrics> {
    return fetchJson<import('@/types').ModelEvaluationMetrics>('/reliability/train', {
      method: 'POST',
    });
  },

  async getModelStatus(): Promise<import('@/types').ModelEvaluationMetrics> {
    return fetchJson<import('@/types').ModelEvaluationMetrics>('/reliability/model/status');
  },

  async getDatasetAudit(): Promise<import('@/types').DatasetAuditReport> {
    return fetchJson<import('@/types').DatasetAuditReport>('/reliability/audit');
  },

  async getDatasetProvenance(): Promise<import('@/types').DatasetProvenanceRecord[]> {
    return fetchJson<import('@/types').DatasetProvenanceRecord[]>('/reliability/provenance');
  },

  async getScientificEvaluation(): Promise<import('@/types').ContinuousScientificEvaluationReport> {
    return fetchJson<import('@/types').ContinuousScientificEvaluationReport>('/reliability/scientific-evaluation');
  },

  async getPredictionRecords(testCaseId?: string): Promise<import('@/types').PredictionRecord[]> {
    const url = testCaseId ? `/reliability/prediction-records?test_case_id=${encodeURIComponent(testCaseId)}` : '/reliability/prediction-records';
    return fetchJson<import('@/types').PredictionRecord[]>(url);
  },

  async getDatasetDiagnostics(): Promise<import('@/types').DatasetDiagnosticsReport> {
    return fetchJson<import('@/types').DatasetDiagnosticsReport>('/reliability/dataset-diagnostics');
  },

  async getPopulationSeparation(minTrainSize: number = 20, stepSize: number = 5): Promise<import('@/types').PopulationSeparationReport> {
    return fetchJson<import('@/types').PopulationSeparationReport>(`/reliability/population-separation?min_train_size=${minTrainSize}&step_size=${stepSize}`);
  },

  async getWalkForwardEvaluation(
    population: import('@/types').PopulationType = 'ALL_HISTORICAL',
    minTrainSize: number = 20,
    stepSize: number = 5
  ): Promise<import('@/types').WalkForwardEvaluationReport> {
    return fetchJson<import('@/types').WalkForwardEvaluationReport>(
      `/reliability/walk-forward-evaluation?population=${population}&min_train_size=${minTrainSize}&step_size=${stepSize}`
    );
  },

  // Slice 7.0: Cross-Application Cold-Start & Calibration
  async getColdStartExperiment(experimentId?: string): Promise<import('@/types').ColdStartExperiment> {
    const url = experimentId ? `/reliability/cold-start/${encodeURIComponent(experimentId)}` : '/reliability/cold-start';
    return fetchJson<import('@/types').ColdStartExperiment>(url);
  },

  async getColdStartSummary(): Promise<any> {
    return fetchJson<any>('/reliability/cold-start/summary');
  },

  async getColdStartPredictions(experimentId: string, appId?: string, k?: number): Promise<any[]> {
    const params = new URLSearchParams();
    if (appId) params.append('application_id', appId);
    if (k !== undefined) params.append('budget_k', k.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    return fetchJson<any[]>(`/reliability/cold-start/${encodeURIComponent(experimentId)}/predictions${query}`);
  },

  async getColdStartFailures(experimentId: string): Promise<import('@/types').ColdStartFailureAnalysis[]> {
    return fetchJson<import('@/types').ColdStartFailureAnalysis[]>(`/reliability/cold-start/${encodeURIComponent(experimentId)}/failures`);
  },

  async getColdStartFeatureAblation(experimentId: string): Promise<import('@/types').FeatureAblationExperimentResult[]> {
    return fetchJson<import('@/types').FeatureAblationExperimentResult[]>(`/reliability/cold-start/${encodeURIComponent(experimentId)}/feature-ablation`);
  },

  // Slice 7.1: Uncertainty-Aware Cold-Start Reliability & Decision Utility
  async getUncertaintyExperiment(experimentId?: string): Promise<import('@/types').UncertaintyExperiment> {
    const url = experimentId ? `/reliability/uncertainty/${encodeURIComponent(experimentId)}` : '/reliability/uncertainty';
    return fetchJson<import('@/types').UncertaintyExperiment>(url);
  },

  async getUncertaintySummary(): Promise<any> {
    return fetchJson<any>('/reliability/uncertainty/summary');
  },

  async getUncertaintyPredictions(experimentId: string, appId?: string, k?: number): Promise<import('@/types').PredictionUncertainty[]> {
    const params = new URLSearchParams();
    if (appId) params.append('application_id', appId);
    if (k !== undefined) params.append('budget_k', k.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    return fetchJson<import('@/types').PredictionUncertainty[]>(`/reliability/uncertainty/${encodeURIComponent(experimentId)}/predictions${query}`);
  },

  async getRiskCoverageCurve(experimentId: string): Promise<import('@/types').RiskCoveragePoint[]> {
    return fetchJson<import('@/types').RiskCoveragePoint[]>(`/reliability/uncertainty/${encodeURIComponent(experimentId)}/risk-coverage`);
  },

  async getUncertaintyCalibrationBuckets(experimentId: string): Promise<import('@/types').UncertaintyBucketSummary[]> {
    return fetchJson<import('@/types').UncertaintyBucketSummary[]>(`/reliability/uncertainty/${encodeURIComponent(experimentId)}/calibration`);
  },

  async getDecisionPolicyResults(experimentId: string): Promise<import('@/types').SelectivePredictionResult[]> {
    return fetchJson<import('@/types').SelectivePredictionResult[]>(`/reliability/uncertainty/${encodeURIComponent(experimentId)}/decision-policy`);
  },

  // Slice 7.2: Reliability Control Plane & Agent Tools
  async getToolCapabilities(): Promise<import('@/types').ToolCapability[]> {
    return fetchJson<import('@/types').ToolCapability[]>('/tools');
  },

  async getToolDefinition(name: string): Promise<import('@/types').ToolDefinitionDetail> {
    return fetchJson<import('@/types').ToolDefinitionDetail>(`/tools/${encodeURIComponent(name)}`);
  },

  async invokeTool<T = any>(
    name: string,
    payload: Record<string, any>,
    context?: Record<string, any>
  ): Promise<import('@/types').ToolEnvelope<T>> {
    return fetchJson<import('@/types').ToolEnvelope<T>>(`/tools/${encodeURIComponent(name)}/invoke`, {
      method: 'POST',
      body: JSON.stringify({
        payload,
        context: context || {},
      }),
    });
  },

  async getRecentToolAudit(limit: number = 25): Promise<import('@/types').AuditEventRecord[]> {
    return fetchJson<import('@/types').AuditEventRecord[]>(`/tools/audit/recent?limit=${limit}`);
  },

  // Slice 7.5: Git / PR / CI Engineering Lifecycle Integration
  async getLifecycleStatus(): Promise<import('@/types').GitStatusModel> {
    return fetchJson<import('@/types').GitStatusModel>('/lifecycle/status');
  },

  async getLifecycleDiff(baseSha?: string, headSha?: string): Promise<any> {
    const params = new URLSearchParams();
    if (baseSha) params.append('base_sha', baseSha);
    if (headSha) params.append('head_sha', headSha);
    const query = params.toString() ? `?${params.toString()}` : '';
    return fetchJson<any>(`/lifecycle/diff${query}`);
  },

  async getLifecycleCommits(limit: number = 10): Promise<import('@/types').GitCommitModel[]> {
    return fetchJson<import('@/types').GitCommitModel[]>(`/lifecycle/commits?limit=${limit}`);
  },

  async getLifecyclePRs(repository?: string): Promise<import('@/types').PullRequestModel[]> {
    const query = repository ? `?repository=${encodeURIComponent(repository)}` : '';
    return fetchJson<import('@/types').PullRequestModel[]>(`/lifecycle/pull-requests${query}`);
  },

  async createLifecyclePR(payload: {
    title: string;
    source_branch: string;
    target_branch?: string;
    description?: string;
  }): Promise<import('@/types').PullRequestModel> {
    return fetchJson<import('@/types').PullRequestModel>('/lifecycle/pull-requests', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getLifecyclePRDetail(prId: string): Promise<{
    pull_request: import('@/types').PullRequestModel;
    reviews: import('@/types').PRReviewModel[];
  }> {
    return fetchJson<{
      pull_request: import('@/types').PullRequestModel;
      reviews: import('@/types').PRReviewModel[];
    }>(`/lifecycle/pull-requests/${encodeURIComponent(prId)}`);
  },

  async reviewLifecyclePR(prId: string): Promise<import('@/types').PRReviewModel> {
    return fetchJson<import('@/types').PRReviewModel>(`/lifecycle/pull-requests/${encodeURIComponent(prId)}/review`, {
      method: 'POST',
    });
  },

  async getCIRuns(commitSha: string): Promise<import('@/types').CIRunModel[]> {
    return fetchJson<import('@/types').CIRunModel[]>(`/lifecycle/ci/${encodeURIComponent(commitSha)}`);
  },

  async triggerCIRun(commitSha?: string, workflow: string = 'pytest_unit'): Promise<import('@/types').CIRunModel> {
    return fetchJson<import('@/types').CIRunModel>('/lifecycle/ci/run', {
      method: 'POST',
      body: JSON.stringify({ commit_sha: commitSha, workflow }),
    });
  },

  async getReleaseReadiness(commitSha: string, prId?: string): Promise<import('@/types').ReleaseReadinessModel> {
    const query = prId ? `?pr_id=${encodeURIComponent(prId)}` : '';
    return fetchJson<import('@/types').ReleaseReadinessModel>(`/lifecycle/release-readiness/${encodeURIComponent(commitSha)}${query}`);
  },

  // Slice 7.6: Real GitHub API Integrations
  async getGitHubRepository(repo?: string): Promise<import('@/types').GitHubRepositoryModel> {
    const query = repo ? `?repository=${encodeURIComponent(repo)}` : '';
    return fetchJson<import('@/types').GitHubRepositoryModel>(`/github/repository${query}`);
  },

  async getGitHubPRs(repo?: string, state: string = 'open'): Promise<import('@/types').GitHubPullRequestModel[]> {
    const params = new URLSearchParams();
    if (repo) params.append('repository', repo);
    params.append('state', state);
    return fetchJson<import('@/types').GitHubPullRequestModel[]>(`/github/pull-requests?${params.toString()}`);
  },

  async getGitHubPRDetail(number: number, repo?: string): Promise<{
    pull_request: import('@/types').GitHubPullRequestModel;
    synchronized: import('@/types').SynchronizedPRModel;
  }> {
    const query = repo ? `?repository=${encodeURIComponent(repo)}` : '';
    return fetchJson<{
      pull_request: import('@/types').GitHubPullRequestModel;
      synchronized: import('@/types').SynchronizedPRModel;
    }>(`/github/pull-requests/${number}${query}`);
  },

  async getGitHubPRDiff(number: number, repo?: string): Promise<{
    pr_number: number;
    diff: string;
    files: Array<{ sha: string; filename: string; status: string; additions: number; deletions: number }>;
  }> {
    const query = repo ? `?repository=${encodeURIComponent(repo)}` : '';
    return fetchJson<any>(`/github/pull-requests/${number}/diff${query}`);
  },

  async reviewGitHubPR(number: number, repo?: string): Promise<{
    review: import('@/types').PRReviewModel;
    synchronized: import('@/types').SynchronizedPRModel;
  }> {
    const query = repo ? `?repository=${encodeURIComponent(repo)}` : '';
    return fetchJson<any>(`/github/pull-requests/${number}/review${query}`, {
      method: 'POST',
    });
  },

  async publishGitHubLabComment(
    number: number,
    payload: {
      commit_sha: string;
      lab_status: string;
      ci_status?: string;
      evidence_ids?: string[];
      release_readiness_state?: string;
    },
    repo?: string
  ): Promise<{ success: boolean; comment_body: string }> {
    const query = repo ? `?repository=${encodeURIComponent(repo)}` : '';
    return fetchJson<any>(`/github/pull-requests/${number}/comments${query}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getGitHubCIStatus(commitSha: string, repo?: string): Promise<{
    commit_sha: string;
    gate_status: string;
    passed: boolean;
    workflow_run?: import('@/types').GitHubWorkflowRunModel;
  }> {
    const query = repo ? `?repository=${encodeURIComponent(repo)}` : '';
    return fetchJson<any>(`/github/actions/${encodeURIComponent(commitSha)}${query}`);
  },

  async getGitHubChecks(commitSha: string, repo?: string): Promise<any[]> {
    const query = repo ? `?repository=${encodeURIComponent(repo)}` : '';
    return fetchJson<any[]>(`/github/checks/${encodeURIComponent(commitSha)}${query}`);
  },

  // Slice 7.7: Prompt Reliability Lab
  async listPrompts(): Promise<import('@/types').PromptDefinitionModel[]> {
    return fetchJson<import('@/types').PromptDefinitionModel[]>('/prompt-lab/prompts');
  },

  async getPrompt(promptId: string): Promise<{
    prompt: import('@/types').PromptDefinitionModel;
    versions: import('@/types').PromptVersionModel[];
  }> {
    return fetchJson<any>(`/prompt-lab/prompts/${encodeURIComponent(promptId)}`);
  },

  async createPrompt(payload: { prompt_id: string; name: string; description?: string }): Promise<import('@/types').PromptDefinitionModel> {
    return fetchJson<import('@/types').PromptDefinitionModel>('/prompt-lab/prompts', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async createPromptVersion(promptId: string, payload: any): Promise<import('@/types').PromptVersionModel> {
    return fetchJson<import('@/types').PromptVersionModel>(`/prompt-lab/prompts/${encodeURIComponent(promptId)}/versions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getPromptVersion(promptId: string, version: number): Promise<import('@/types').PromptVersionModel> {
    return fetchJson<import('@/types').PromptVersionModel>(`/prompt-lab/prompts/${encodeURIComponent(promptId)}/versions/${version}`);
  },

  async listEvaluationSuites(): Promise<import('@/types').EvaluationSuiteModel[]> {
    return fetchJson<import('@/types').EvaluationSuiteModel[]>('/prompt-lab/evaluation-suites');
  },

  async getEvaluationSuite(suiteId: string, version?: number): Promise<{
    suite: import('@/types').EvaluationSuiteModel;
    version?: import('@/types').EvaluationSuiteVersionModel | null;
  }> {
    const query = version ? `?version=${version}` : '';
    return fetchJson<any>(`/prompt-lab/evaluation-suites/${encodeURIComponent(suiteId)}${query}`);
  },

  async runEvaluation(payload: {
    prompt_id: string;
    prompt_version: number;
    suite_id: string;
    suite_version: number;
    model?: string;
  }): Promise<import('@/types').EvaluationRunModel> {
    return fetchJson<import('@/types').EvaluationRunModel>('/prompt-lab/evaluations/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getEvaluation(runId: string): Promise<{
    run: import('@/types').EvaluationRunModel;
    diagnoses: import('@/types').PromptDiagnosisModel[];
  }> {
    return fetchJson<any>(`/prompt-lab/evaluations/${encodeURIComponent(runId)}`);
  },

  async comparePromptVersions(
    promptId: string,
    v1: number,
    v2: number,
    suiteId: string,
    suiteVersion: number
  ): Promise<import('@/types').PromptComparisonResultModel> {
    return fetchJson<import('@/types').PromptComparisonResultModel>(
      `/prompt-lab/evaluations/compare/versions?prompt_id=${encodeURIComponent(promptId)}&v1=${v1}&v2=${v2}&suite_id=${encodeURIComponent(suiteId)}&suite_version=${suiteVersion}`
    );
  },
};







