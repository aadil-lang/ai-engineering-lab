export type TestMode =
  | 'FUNCTIONAL_QA'
  | 'EXPLORATORY_DOGFOODING'
  | 'UX_UI_REVIEW'
  | 'AI_LLM_EVALUATION'
  | 'REGRESSION_QA';

export type RunStatus =
  | 'QUEUED'
  | 'RUNNING'
  | 'PASSED'
  | 'FAILED'
  | 'ERROR'
  | 'CANCELLED';

export type ActionType =
  | 'NAVIGATE'
  | 'LOCATE'
  | 'CLICK'
  | 'INPUT'
  | 'SUBMIT'
  | 'ASSERT'
  | 'HOVER'
  | 'PRESS_KEY'
  | 'SCROLL'
  | 'FINISH'
  | 'CUSTOM';

export type ActionStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'PASSED'
  | 'FAILED'
  | 'SKIPPED';

export type EvidenceType =
  | 'DOM_SNAPSHOT'
  | 'SCREENSHOT'
  | 'NETWORK_HAR'
  | 'CONSOLE_LOG'
  | 'LLM_TRANSCRIPT'
  | 'PERFORMANCE_TRACE';

export type FailureCategory =
  | 'FUNCTIONAL_BUG'
  | 'ASSERTION_FAILURE'
  | 'TIMEOUT'
  | 'VISUAL_REGRESSION'
  | 'LLM_HALLUCINATION'
  | 'SECURITY_VULNERABILITY'
  | 'PERF_DEGRADATION'
  | 'NAVIGATION_TIMEOUT'
  | 'ELEMENT_NOT_FOUND'
  | 'ELEMENT_NOT_VISIBLE'
  | 'ELEMENT_NOT_INTERACTABLE'
  | 'INPUT_FAILED'
  | 'CLICK_FAILED'
  | 'ASSERTION_FAILED'
  | 'NETWORK_ERROR'
  | 'BROWSER_ERROR'
  | 'EXECUTION_TIMEOUT'
  | 'AGENT_BUDGET_EXCEEDED'
  | 'AGENT_LOOP_DETECTED'
  | 'INVALID_ACTION_SCHEMA'
  | 'GOAL_NOT_REACHED'
  | 'LLM_INFERENCE_ERROR';

export type Severity =
  | 'CRITICAL'
  | 'HIGH'
  | 'MEDIUM'
  | 'LOW'
  | 'INFO';

export type RunnerType = 'MOCK' | 'PLAYWRIGHT' | 'AI_AGENT';

export type AssessmentDimension =
  | 'RELIABILITY'
  | 'PERFORMANCE'
  | 'LOAD_CAPACITY'
  | 'FAILURE_RECOVERY'
  | 'SECURITY'
  | 'RESOURCE_BEHAVIOR'
  | 'OBSERVABILITY'
  | 'AI_RELIABILITY'
  | 'MAINTAINABILITY';

export interface ApplicationTarget {
  target_id: string;
  name: string;
  target_type: string;
  base_url: string;
  environment: string;
  version: string;
  description: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface TestAction {
  action_id: string;
  action_type: ActionType;
  description: string;
  thought?: string | null;
  selector?: string | null;
  timestamp: string;
  status: ActionStatus;
  input_data: Record<string, any>;
  output_data: Record<string, any>;
  duration_ms: number;
  error_message?: string | null;
  evidence_ids: string[];
}

export interface Evidence {
  evidence_id: string;
  run_id: string;
  action_id?: string | null;
  evidence_type: EvidenceType;
  title: string;
  artifact_path?: string | null;
  mime_type?: string;
  payload: any;
  metadata: Record<string, any>;
  timestamp: string;
}

export interface Failure {
  failure_id: string;
  run_id: string;
  action_id?: string | null;
  category: FailureCategory;
  severity: Severity;
  title: string;
  message: string;
  stack_trace?: string | null;
  suggested_remediation?: string | null;
  failed_action?: string | null;
  selector?: string | null;
  timestamp: string;
}

export interface Metric {
  metric_id: string;
  run_id: string;
  name: string;
  value: number;
  unit: string;
  tags: Record<string, string>;
  timestamp: string;
}

export interface TestCase {
  test_case_id: string;
  target_id: string;
  name: string;
  test_mode: TestMode;
  description: string;
  steps: any[];
  assertions: any[];
  tags: string[];
  created_at: string;
}

export interface TestRun {
  run_id: string;
  application_id: string;
  application_version: string;
  test_mode: TestMode;
  runner_type?: RunnerType;
  execution_source?: ExecutionSource;
  feature_vector_version?: string;
  test_case_id?: string | null;
  status: RunStatus;
  started_at: string;
  finished_at?: string | null;
  duration_ms: number;
  environment_id: string;
  browser_context_id?: string | null;
  session_id?: string | null;
  natural_language_goal?: string | null;
  max_agent_steps?: number;
  agent_thought_trace?: any[];
  actions: TestAction[];
  evidence_ids: string[];
  failure_ids: string[];
  metrics_summary: Record<string, number>;
  logs: string[];
  created_at: string;
}

export interface TestRunCreate {
  application_id: string;
  test_mode: TestMode;
  runner_type?: RunnerType;
  execution_source?: ExecutionSource;
  test_case_id?: string | null;
  application_version?: string;
  environment_id?: string;
  simulate_failure?: boolean;
  custom_scenario?: string | null;
  target_url_override?: string | null;
  natural_language_goal?: string | null;
  max_agent_steps?: number;
  action_delay_ms?: number;
}

export interface DimensionScore {
  dimension: AssessmentDimension;
  score: number;
  status: string;
  summary: string;
  findings_count: number;
}

export interface Assessment {
  assessment_id: string;
  application_id: string;
  overall_score: number;
  status: string;
  dimensions: DimensionScore[];
  findings_ids: string[];
  recommendations: string[];
  started_at: string;
  finished_at?: string | null;
}

export interface DeterministicSignal {
  signal_type: string;
  summary: string;
  details: Record<string, any>;
}

export interface ReproductionStep {
  step_number: number;
  action: string;
  target?: string | null;
  expected?: string | null;
  observed?: string | null;
}

export type ClaimType =
  | 'OBSERVED_FACT'
  | 'ROOT_CAUSE'
  | 'COMPONENT'
  | 'IMPACT'
  | 'RECOMMENDATION';

export type GroundingStatus =
  | 'SUPPORTED'
  | 'PARTIALLY_SUPPORTED'
  | 'UNSUPPORTED'
  | 'CONTRADICTED'
  | 'UNKNOWN';

export interface DiagnosisClaim {
  claim_id: string;
  text: string;
  claim_type: ClaimType;
  evidence_refs: string[];
  grounding_status: GroundingStatus;
  confidence: number;
  explanation: string;
}

export interface GroundingSummary {
  total_claims: number;
  supported_claims: number;
  partially_supported_claims: number;
  unsupported_claims: number;
  contradicted_claims: number;
  grounding_score: number;
  is_grounded: boolean;
  grounding_notes: string[];
}

export interface EngineeringDiagnosis {
  diagnosis_id: string;
  run_id: string;
  failure_id?: string | null;
  title: string;
  root_cause_summary: string;
  failure_category: FailureCategory;
  confidence_score: number;
  suspected_component: string;
  deterministic_signals: DeterministicSignal[];
  reproduction_steps: ReproductionStep[];
  suggested_fix: string;
  code_diff_suggestion?: string | null;
  regression_test_spec: string;
  severity: Severity;
  evidence_bundle_summary: string;
  claims?: DiagnosisClaim[];
  grounding_score?: number;
  is_grounded?: boolean;
  grounded_root_cause?: string | null;
  grounded_suspected_component?: string | null;
  grounded_confidence_score?: number | null;
  validation_notes?: string[];
  created_at: string;
}

export type RemediationStatus =
  | 'PENDING'
  | 'ANALYZING'
  | 'PROPOSED'
  | 'APPLYING'
  | 'VALIDATING'
  | 'TESTING'
  | 'RESOLVED'
  | 'FAILED'
  | 'REJECTED';

export type FileChangeOperation = 'MODIFY' | 'CREATE' | 'DELETE';

export interface FileChange {
  path: string;
  operation: FileChangeOperation;
  diff: string;
  original_content?: string | null;
  new_content?: string | null;
}

export interface CodeChange {
  change_id: string;
  task_id: string;
  summary: string;
  rationale: string;
  files: FileChange[];
  diff: string;
  risk_notes?: string | null;
  tests_to_run: string[];
  validation_results: Record<string, any>;
  created_at: string;
}

export interface RemediationAttempt {
  attempt_id: string;
  task_id: string;
  attempt_number: number;
  status: RemediationStatus;
  started_at: string;
  completed_at?: string | null;
  build_result: Record<string, any>;
  test_result: Record<string, any>;
  error_output?: string | null;
}

export interface RegressionVerification {
  verification_id: string;
  task_id: string;
  original_run_id: string;
  verification_run_id?: string | null;
  status: string;
  failed_before: boolean;
  failed_after: boolean;
  regression_detected: boolean;
  summary: string;
  timestamp: string;
}

export interface RemediationTask {
  task_id: string;
  run_id: string;
  diagnosis_id: string;
  status: RemediationStatus;
  target_repository: string;
  target_branch: string;
  base_commit: string;
  code_changes: CodeChange[];
  attempts: RemediationAttempt[];
  verifications: RegressionVerification[];
  created_at: string;
  updated_at: string;
}

export interface RemediationTaskCreate {
  run_id: string;
  diagnosis_id?: string;
  target_repository?: string;
  target_branch?: string;
  auto_apply?: boolean;
}

export type TrendStatus = 'IMPROVING' | 'STABLE' | 'DEGRADING' | 'INSUFFICIENT_DATA';
export type RiskBand = 'LOW' | 'MEDIUM' | 'HIGH' | 'UNKNOWN';
export type PredictionStatus =
  | 'PREDICTION_AVAILABLE'
  | 'PREDICTION_UNAVAILABLE'
  | 'INSUFFICIENT_DATA'
  | 'NO_DATA'
  | 'TRAINING'
  | 'TRAINED';

export interface FeatureImportance {
  feature_name: string;
  weight: number;
  value: number;
  contribution: number;
  description: string;
}

export interface TestCasePrediction {
  test_case_id: string;
  test_case_name?: string | null;
  target_id: string;
  prediction_timestamp: string;
  failure_probability?: number | null;
  risk_band: RiskBand;
  status: PredictionStatus;
  model_version: string;
  feature_snapshot: Record<string, number>;
  training_data_size: number;
  prediction_available: boolean;
  contributing_features: FeatureImportance[];
  limitations: string[];
  baseline_probabilities: Record<string, number>;
}

export interface ReliabilitySummary {
  total_runs: number;
  total_failures: number;
  failure_rate: number;
  successful_remediation_rate: number;
  regression_rate: number;
  avg_remediation_attempts: number;
  avg_execution_duration_ms: number;
  prediction_coverage_pct: number;
  active_targets_count: number;
  active_test_cases_count: number;
  overall_trend: TrendStatus;
}

export interface TargetReliability {
  target_id: string;
  target_name: string;
  run_count: number;
  failure_count: number;
  failure_rate: number;
  recent_trend: TrendStatus;
  grounded_component_failures: Record<string, number>;
}

export interface TestCaseReliability {
  test_case_id: string;
  test_case_name: string;
  target_id: string;
  execution_count: number;
  failure_count: number;
  failure_rate: number;
  recent_trend: TrendStatus;
  last_run_status?: string | null;
  last_run_timestamp?: string | null;
  prediction?: TestCasePrediction | null;
}

export interface FailurePattern {
  category: string;
  count: number;
  percentage: number;
  avg_duration_ms: number;
  top_grounded_components: string[];
}

export interface TrendPoint {
  time_bucket: string;
  total_runs: number;
  failed_runs: number;
  failure_rate: number;
}

export interface TrendAnalysis {
  overall_trend: TrendStatus;
  historical_failure_rate: number;
  recent_failure_rate: number;
  data_points: TrendPoint[];
  trend_description: string;
}

export interface ModelEvaluationMetrics {
  model_version: string;
  trained_at: string;
  train_samples: number;
  test_samples: number;
  accuracy?: number | null;
  precision?: number | null;
  recall?: number | null;
  f1_score?: number | null;
  roc_auc?: number | null;
  brier_score?: number | null;
  baseline_accuracies: Record<string, number>;
  is_calibrated: boolean;
  status: PredictionStatus;
  notes: string[];
}

export interface QAPrioritizationItem {
  priority_rank: number;
  test_case_id: string;
  test_case_name: string;
  target_id: string;
  risk_band: RiskBand;
  failure_probability?: number | null;
  trend: TrendStatus;
  reason: string;
}

// Slice 6.1: Scientific Validation & Continuous Tracking Types
export type DatasetStatus = 'NO_DATA' | 'INSUFFICIENT_DATA' | 'USABLE';
export type PredictionEvaluationStatus = 'PENDING' | 'EVALUATED' | 'OBSOLETE';
export type EvaluationSplitType = 'TRAIN' | 'VALIDATION' | 'TEST';

export interface ConfusionMatrix {
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  true_negatives: number;
}

export interface ClassificationMetrics {
  sample_count: number;
  accuracy?: number | null;
  precision?: number | null;
  recall?: number | null;
  f1_score?: number | null;
  roc_auc?: number | null;
  confusion_matrix: ConfusionMatrix;
  notes: string[];
}

export interface DatasetAuditReport {
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  passed_runs: number;
  total_test_cases: number;
  runs_with_repeated_executions: number;
  total_usable_reliability_records: number;
  total_usable_prediction_samples: number;
  positive_labels_count: number;
  negative_labels_count: number;
  unique_test_cases_count: number;
  earliest_execution_timestamp?: string | null;
  latest_execution_timestamp?: string | null;
  samples_per_test_case: Record<string, number>;
  single_execution_test_cases_count: number;
  repeated_execution_test_cases_count: number;
  status: DatasetStatus;
  status_reason: string;
}

export interface DatasetProvenanceRecord {
  sample_id: string;
  test_case_id: string;
  feature_run_id: string;
  target_run_id: string;
  feature_timestamp: string;
  target_timestamp: string;
  feature_vector_version: string;
  feature_names: string[];
  target_label: number;
}

export interface SplitEvaluationMetrics {
  split_name: EvaluationSplitType;
  sample_count: number;
  time_range_start?: string | null;
  time_range_end?: string | null;
  positive_count: number;
  negative_count: number;
  metrics: ClassificationMetrics;
}

export interface BaselineEvaluation {
  baseline_id: string;
  baseline_name: string;
  description: string;
  metrics: ClassificationMetrics;
}

export interface CalibrationMetrics {
  is_evaluated: boolean;
  brier_score?: number | null;
  expected_calibration_error?: number | null;
  reliability_diagram_bins: Array<{
    bin_index: number;
    bin_range: string;
    sample_count: number;
    mean_predicted_probability: number;
    empirical_positive_fraction: number;
    calibration_gap: number;
  }>;
  status: string;
  notes: string[];
}

export interface PredictionRecord {
  prediction_id: string;
  test_case_id: string;
  test_case_name?: string | null;
  feature_run_id: string;
  predicted_failure_probability: number;
  predicted_risk_band: RiskBand;
  prediction_class: number;
  model_version: string;
  feature_vector_version: string;
  prediction_timestamp: string;
  target_run_id?: string | null;
  actual_outcome?: number | null;
  is_correct?: boolean | null;
  evaluation_status: PredictionEvaluationStatus;
  evaluated_at?: string | null;
}

export interface ContinuousScientificEvaluationReport {
  dataset_audit: DatasetAuditReport;
  provenance_samples: DatasetProvenanceRecord[];
  splits: SplitEvaluationMetrics[];
  baselines: BaselineEvaluation[];
  model_evaluation?: SplitEvaluationMetrics | null;
  calibration: CalibrationMetrics;
  evaluated_predictions_count: number;
  pending_predictions_count: number;
  prediction_records: PredictionRecord[];
  evaluation_summary_notes: string[];
}

// Slice 6.3: Dataset Diagnostics & Model Failure Analysis Types
export interface FeatureDistributionStat {
  feature_name: string;
  train_mean: number;
  train_std: number;
  train_min: number;
  train_max: number;
  test_mean: number;
  test_std: number;
  test_min: number;
  test_max: number;
  is_constant: boolean;
  is_near_constant: boolean;
  distribution_shift: string;
}

export interface FeaturePredictivenessStat {
  feature_name: string;
  training_correlation?: number | null;
  association_description: string;
  is_statistically_informative: boolean;
}

export interface TestCaseHeterogeneityStat {
  test_case_id: string;
  total_executions: number;
  transition_count: number;
  failures_count: number;
  passes_count: number;
  failure_rate: number;
  dominant_runner: string;
  autocorrelation_lag1?: number | null;
  is_dominant: boolean;
}

export interface SequenceAnalysisReport {
  sequence_name: string;
  total_runs: number;
  failures: number;
  passes: number;
  failure_rate: number;
  transition_counts: Record<string, number>;
  autocorrelation_lag1?: number | null;
  is_alternating_harness_pattern: boolean;
  description: string;
}

export interface TestDistributionShiftReport {
  train_test_case_count: number;
  test_test_case_count: number;
  known_test_cases_in_test: string[];
  unseen_test_cases_in_test: string[];
  known_samples_count: number;
  unseen_samples_count: number;
  known_accuracy?: number | null;
  unseen_accuracy?: number | null;
  known_metrics?: ClassificationMetrics | null;
  unseen_metrics?: ClassificationMetrics | null;
}

export interface ModelComparisonItem {
  model_id: string;
  model_name: string;
  version: string;
  description: string;
  accuracy?: number | null;
  precision?: number | null;
  recall?: number | null;
  f1_score?: number | null;
  roc_auc?: number | null;
  brier_score?: number | null;
  confusion_matrix: ConfusionMatrix;
}

export interface DatasetDiagnosticsReport {
  generated_at: string;
  total_runs: number;
  total_transitions: number;
  train_count: number;
  val_count: number;
  test_count: number;
  class_balance: {
    train_samples: number;
    train_failures: number;
    train_passes: number;
    train_failure_rate: number;
    validation_samples: number;
    validation_failures: number;
    validation_passes: number;
    validation_failure_rate: number;
    test_samples: number;
    test_failures: number;
    test_passes: number;
    test_failure_rate: number;
    training_majority_class: number;
    majority_class_test_accuracy: number;
  };
  brier_interpretation: {
    model_v1_0_brier: number;
    prevalence_baseline_brier: number;
    training_prevalence: number;
    explanation: string;
  };
  feature_distributions: FeatureDistributionStat[];
  feature_predictiveness: FeaturePredictivenessStat[];
  test_case_heterogeneity: TestCaseHeterogeneityStat[];
  demo_shop_analysis?: SequenceAnalysisReport | null;
  distribution_shift: TestDistributionShiftReport;
  failure_sources: Record<string, number>;
  model_comparisons: ModelComparisonItem[];
  data_quality_warnings: string[];
  root_diagnostic_findings: string[];
  recommended_next_experiment: string[];
}

export type ExecutionSource =
  | 'REAL_PLAYWRIGHT'
  | 'REAL_AI_AGENT'
  | 'CONTROLLED_DEFECT'
  | 'SYNTHETIC_MOCK'
  | 'DEMO_HARNESS'
  | 'UNKNOWN';

export type PopulationType =
  | 'ALL_HISTORICAL'
  | 'REAL_EXECUTIONS_ONLY'
  | 'REAL_PLAYWRIGHT_ONLY'
  | 'REAL_AI_AGENT_ONLY'
  | 'CONTROLLED_AND_DEMO';

export interface PopulationAuditSummary {
  population_id: PopulationType;
  population_name: string;
  description: string;
  total_runs: number;
  total_transitions: number;
  failures_count: number;
  passes_count: number;
  failure_rate: number;
  status: DatasetStatus;
  status_reason: string;
  included_sources: ExecutionSource[];
}

export interface WalkForwardFoldMetric {
  fold_index: number;
  train_start_timestamp?: string | null;
  train_end_timestamp?: string | null;
  test_start_timestamp?: string | null;
  test_end_timestamp?: string | null;
  train_sample_count: number;
  test_sample_count: number;
  train_failure_rate: number;
  test_failure_rate: number;
  model_metrics: Record<string, ClassificationMetrics>;
  brier_scores: Record<string, number>;
}

export interface WalkForwardModelAggregate {
  model_id: string;
  model_name: string;
  mean_accuracy?: number | null;
  std_accuracy?: number | null;
  mean_brier_score?: number | null;
  std_brier_score?: number | null;
  mean_roc_auc?: number | null;
  std_roc_auc?: number | null;
  mean_f1?: number | null;
  std_f1?: number | null;
  mean_ece?: number | null;
  std_ece?: number | null;
}

export interface WalkForwardEvaluationReport {
  population: PopulationType;
  population_name: string;
  total_samples: number;
  min_train_size: number;
  step_size: number;
  num_folds: number;
  status: string;
  status_reason: string;
  folds: WalkForwardFoldMetric[];
  model_aggregates: WalkForwardModelAggregate[];
  scientific_conclusions: string[];
}

export interface PopulationSeparationReport {
  generated_at: string;
  total_runs: number;
  total_transitions: number;
  source_breakdown: Record<string, number>;
  populations: PopulationAuditSummary[];
  walk_forward_reports: Record<string, WalkForwardEvaluationReport>;
  primary_insights: string[];
}

// ========================================================
// Slice 7.0 — Cold-Start Calibration Types
// ========================================================

export interface SafeMetricValue {
  metric_name: string;
  value?: number | null;
  status: string;
  reason?: string | null;
  lower_ci?: number | null;
  upper_ci?: number | null;
  confidence_level?: number;
  is_high_uncertainty?: boolean;
}

export interface ModelPerformanceReport {
  name: string;
  sample_count: number;
  positive_count: number;
  negative_count: number;
  predicted_positive_count: number;
  predicted_negative_count: number;
  accuracy: SafeMetricValue;
  precision: SafeMetricValue;
  recall: SafeMetricValue;
  f1_score: SafeMetricValue;
  roc_auc: SafeMetricValue;
  brier_score: SafeMetricValue;
  confusion_matrix: ConfusionMatrix;
}

export interface OperationalMetrics {
  failures_detected: number;
  failures_missed: number;
  false_alarms: number;
  total_eval_samples: number;
  fraction_selected_for_qa: number;
  qa_workload_reduction_pct: number;
}

export interface ColdStartEvaluationResult {
  result_id: string;
  held_out_application_id: string;
  budget_k: number;
  evaluation_sample_count: number;
  evaluation_failures_count: number;
  evaluation_passes_count: number;
  evaluation_failure_rate: number;
  strategy_a_global: ModelPerformanceReport;
  strategy_b_local: ModelPerformanceReport;
  strategy_c_calibrated: ModelPerformanceReport;
  delta_brier_calib_vs_global: number;
  delta_auc_calib_vs_global?: number | null;
  delta_accuracy_calib_vs_global: number;
  delta_brier_calib_vs_local: number;
  delta_auc_calib_vs_local?: number | null;
  operational_metrics_global: OperationalMetrics;
  operational_metrics_calibrated: OperationalMetrics;
  uncertainty_level: string;
  uncertainty_reasons: string[];
}

export interface WalkForwardStepResult {
  step_index: number;
  run_id: string;
  target_run_id: string;
  timestamp: string;
  cumulative_local_observations: number;
  observed_label: number;
  global_prob: number;
  local_prob: number;
  calibrated_prob: number;
  calibrated_prediction: number;
}

export interface WalkForwardColdStartResult {
  held_out_application_id: string;
  min_initial_observations: number;
  total_steps: number;
  failures_observed: number;
  passes_observed: number;
  steps: WalkForwardStepResult[];
  global_metrics: ModelPerformanceReport;
  local_metrics: ModelPerformanceReport;
  calibrated_metrics: ModelPerformanceReport;
}

export interface ColdStartFailureAnalysis {
  failure_id: string;
  run_id: string;
  target_run_id: string;
  application_id: string;
  test_case_id: string;
  failure_timestamp: string;
  feature_timestamp: string;
  observed_label: number;
  global_prob: number;
  calibrated_prob: number;
  classification_outcome_global: string;
  classification_outcome_calibrated: string;
  preceding_duration_ratio: number;
  preceding_console_errors: number;
  preceding_failed_steps: number;
  preceding_consecutive_fails: number;
  preceding_telemetry_deterioration_detected: boolean;
  explanation: string;
}

export interface FeatureAblationModelResult {
  model_name: string;
  feature_count: number;
  features_used: string[];
  accuracy: number;
  brier_score: number;
  roc_auc?: number | null;
  roc_auc_status: string;
}

export interface FeatureAblationExperimentResult {
  held_out_application_id: string;
  budget_k: number;
  model_a_all_features: FeatureAblationModelResult;
  model_b_no_absolute_features: FeatureAblationModelResult;
  model_c_relative_only_features: FeatureAblationModelResult;
  conclusion: string;
}

export interface ApplicationShiftItem {
  feature_name: string;
  category: string;
  train_mean: number;
  train_std: number;
  test_mean: number;
  test_std: number;
  standardized_shift: number;
  shift_detected: boolean;
}

export interface ApplicationShiftReport {
  held_out_application_id: string;
  train_applications: string[];
  shifts: ApplicationShiftItem[];
  raw_feature_avg_shift: number;
  relative_feature_avg_shift: number;
  summary: string;
}

export interface ColdStartExperiment {
  experiment_id: string;
  created_at: string;
  protocol_version: string;
  parent_snapshot_id: string;
  snapshot_id: string;
  model_version: string;
  feature_vector_version: string;
  calibration_method: string;
  applications_evaluated: string[];
  budget_k_values: number[];
  evaluation_results: ColdStartEvaluationResult[];
  walk_forward_results: WalkForwardColdStartResult[];
  failure_analyses: ColdStartFailureAnalysis[];
  feature_ablation_results: FeatureAblationExperimentResult[];
  shift_reports: ApplicationShiftReport[];
  hypotheses_verdicts: Record<string, string>;
  scientific_summary: string[];
}

// ========================================================
// Slice 7.1 — Uncertainty-Aware Cold-Start & Decision Utility Types
// ========================================================

export type UncertaintyBucketLevel = 'LOW' | 'MEDIUM' | 'HIGH';
export type AbstentionDecision = 'ACCEPT' | 'ABSTAIN';

export interface PredictionUncertainty {
  prediction_id: string;
  prediction_run_id: string;
  target_run_id: string;
  application_id: string;
  test_case_id: string;
  timestamp: string;
  budget_k: number;
  calibration_k: number;
  p_mean: number;
  p_lower: number;
  p_upper: number;
  uncertainty_width: number;
  effective_evidence: number;
  observed_label: number;
  decision: AbstentionDecision;
  uncertainty_bucket: UncertaintyBucketLevel;
  brier_contribution: number;
  absolute_error: number;
}

export interface UncertaintyBucketSummary {
  bucket_level: UncertaintyBucketLevel;
  lower_bound: number;
  upper_bound: number;
  sample_count: number;
  failure_count: number;
  mean_uncertainty: number;
  mean_predicted_prob: number;
  observed_failure_rate: number;
  brier_score: number;
  mean_absolute_error: number;
}

export interface DecisionPolicy {
  policy_id: string;
  selection_method: string;
  threshold_tau: number;
  training_applications: string[];
  training_sample_count: number;
  training_coverage: number;
  training_selective_brier: number;
  training_abstention_rate: number;
}

export interface SelectivePredictionResult {
  policy_id: string;
  threshold_tau: number;
  test_application_id: string;
  total_test_samples: number;
  accepted_sample_count: number;
  abstain_sample_count: number;
  test_coverage: number;
  test_abstention_rate: number;
  accepted_failures_count: number;
  accepted_passes_count: number;
  accepted_failure_rate: number;
  accepted_brier_score: number;
  overall_brier_score: number;
  selective_brier_improvement: number;
  risk_reduction_pct: number;
}

export interface RiskCoveragePoint {
  coverage: number;
  abstention_rate: number;
  threshold_tau: number;
  accepted_count: number;
  selective_brier: number;
  selective_mae: number;
  baseline_random_brier: number;
}

export interface ApplicationShiftUncertainty {
  application_id: string;
  standardized_shift_mean: number;
  raw_shift_mean: number;
  relative_shift_mean: number;
  mean_uncertainty_k0: number;
  mean_uncertainty_k5: number;
  uncertainty_reduction_k0_to_k5: number;
}

export interface HypothesisVerdict {
  hypothesis_id: string;
  title: string;
  verdict: 'SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'NOT_SUPPORTED' | 'INSUFFICIENT_EVIDENCE';
  empirical_metric_name: string;
  empirical_metric_value?: number | null;
  threshold_criterion: string;
  description: string;
  is_deterministic: boolean;
}

export interface UncertaintyColdStartResult {
  application_id: string;
  budget_k: number;
  prediction_count: number;
  observed_failures: number;
  mean_predicted_prob: number;
  mean_uncertainty: number;
  median_uncertainty: number;
  min_uncertainty: number;
  max_uncertainty: number;
  brier_score: number;
  coverage_default_policy: number;
  selective_brier_default_policy: number;
  abstention_rate_default_policy: number;
}

export interface UncertaintyExperiment {
  experiment_id: string;
  created_at: string;
  protocol_version: string;
  parent_snapshot_id: string;
  snapshot_id: string;
  model_version: string;
  uncertainty_method_version: string;
  decision_policy_version: string;
  training_applications: string[];
  test_applications: string[];
  budget_k_values: number[];
  total_eval_predictions: number;
  cold_start_results: UncertaintyColdStartResult[];
  predictions: PredictionUncertainty[];
  decision_policies: DecisionPolicy[];
  selective_results: SelectivePredictionResult[];
  risk_coverage_curve: RiskCoveragePoint[];
  uncertainty_buckets: UncertaintyBucketSummary[];
  shift_uncertainty_analysis: ApplicationShiftUncertainty[];
  hypotheses_verdicts: HypothesisVerdict[];
  scientific_summary: string[];
}

// Slice 7.2: Tool Contracts & Reliability Control Plane
export interface ToolCapability {
  name: string;
  version: string;
  mode: 'READ_ONLY' | 'ACTION';
  description: string;
  permission_mode?: string;
}

export interface ToolDefinitionDetail {
  name: string;
  description: string;
  mode: 'READ_ONLY' | 'ACTION';
  version: string;
  permission_mode: string;
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
}

export interface AuditEventRecord {
  event_id: string;
  request_id: string;
  tool_name: string;
  tool_version: string;
  application_id?: string | null;
  session_id?: string | null;
  actor: string;
  timestamp: string;
  request_sha256: string;
  response_sha256?: string | null;
  result_status: string;
  error_code?: string | null;
  execution_time_ms: number;
}

export interface ToolEnvelope<T = any> {
  success: boolean;
  data?: T;
  error?: {
    error_code: string;
    message: string;
    details?: Record<string, any>;
    recoverable: boolean;
  };
  metadata: {
    tool_name: string;
    tool_version: string;
    request_id: string;
    timestamp: string;
    session_id?: string | null;
    application_id?: string | null;
    execution_time_ms: number;
    provenance: {
      snapshot_id: string;
      model_version: string;
      feature_schema_version: string;
      dataset_timestamp: string;
      source_run_ids: string[];
    };
  };
}

// Slice 7.5: Git / PR / CI Lifecycle Integration
export interface GitStatusModel {
  repository: string;
  branch: string;
  commit_sha: string;
  parent_commit_sha?: string | null;
  is_clean: boolean;
  changed_files: Array<{ path: string; status: string }>;
  untracked_files: string[];
  ahead: number;
  behind: number;
}

export interface GitCommitModel {
  commit_sha: string;
  parent_commit_sha?: string | null;
  author: string;
  email: string;
  timestamp: string;
  message: string;
  files_changed: string[];
}

export interface ReviewFindingModel {
  file: string;
  line: number;
  category: 'BUG' | 'SECURITY' | 'CORRECTNESS' | 'PERFORMANCE' | 'MAINTAINABILITY' | 'TESTING' | 'API_CONTRACT' | 'REGRESSION_RISK';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  title: string;
  description: string;
  evidence: string;
  confidence: number;
  epistemic_status: 'OBSERVED' | 'INFERRED' | 'HYPOTHESIS';
}

export interface PRReviewModel {
  review_id: string;
  pr_id: string;
  commit_sha: string;
  status: 'PENDING' | 'APPROVED' | 'CHANGES_REQUESTED' | 'COMMENTED' | 'DISMISSED';
  summary: string;
  findings: ReviewFindingModel[];
  created_at: string;
}

export interface PullRequestModel {
  id: string;
  repository: string;
  number: number;
  title: string;
  description: string;
  source_branch: string;
  target_branch: string;
  head_sha: string;
  base_sha: string;
  status: 'OPEN' | 'CHANGES_REQUESTED' | 'APPROVED' | 'CI_FAILED' | 'LAB_FAILED' | 'READY_TO_MERGE' | 'MERGED' | 'CLOSED';
  created_at: string;
  updated_at: string;
  merged_at?: string | null;
  closed_at?: string | null;
}

export interface CIRunModel {
  id: string;
  commit_sha: string;
  workflow: string;
  status: 'PENDING' | 'RUNNING' | 'PASSED' | 'FAILED' | 'CANCELLED';
  started_at: string;
  completed_at?: string | null;
  duration_ms: number;
  tests_total: number;
  tests_passed: number;
  tests_failed: number;
  output_summary?: string | null;
  artifacts: string[];
}

export interface ReleaseReadinessModel {
  commit_sha: string;
  pr_id?: string | null;
  overall_state: 'NOT_READY' | 'BLOCKED' | 'READY_FOR_HUMAN_REVIEW' | 'READY_FOR_RELEASE';
  review_status: 'PENDING' | 'PASSED' | 'FAILED' | 'SKIPPED' | 'ABSTAINED';
  ci_status: 'PENDING' | 'PASSED' | 'FAILED' | 'SKIPPED' | 'ABSTAINED';
  lab_status: 'PENDING' | 'PASSED' | 'FAILED' | 'SKIPPED' | 'ABSTAINED';
  evidence_status: 'PENDING' | 'PASSED' | 'FAILED' | 'SKIPPED' | 'ABSTAINED';
  blockers: string[];
  generated_at: string;
}

// Slice 7.6: Real GitHub Integration Models
export interface GitHubRepositoryModel {
  github_id: number;
  owner: string;
  name: string;
  full_name: string;
  default_branch: string;
  is_private: boolean;
  html_url: string;
  description?: string | null;
}

export interface GitHubPullRequestModel {
  github_id: number;
  number: number;
  title: string;
  body: string;
  state: 'open' | 'closed';
  head_branch: string;
  base_branch: string;
  head_sha: string;
  base_sha: string;
  author_login: string;
  html_url: string;
  is_draft: boolean;
  created_at: string;
  updated_at: string;
  merged_at?: string | null;
  closed_at?: string | null;
}

export interface SynchronizedPRModel {
  repository: string;
  pull_request_number: number;
  head_branch: string;
  base_branch: string;
  head_commit_sha: string;
  base_commit_sha: string;
  github_state: string;
  local_lifecycle_state: string;
  created_at: string;
  updated_at: string;
  last_verified_commit_sha?: string | null;
  ci_verified_commit_sha?: string | null;
}

export interface GitHubWorkflowRunModel {
  github_run_id: number;
  workflow_name: string;
  head_sha: string;
  head_branch: string;
  status: 'queued' | 'in_progress' | 'completed';
  conclusion?: 'success' | 'failure' | 'cancelled' | 'timed_out' | 'skipped' | 'neutral' | null;
  html_url: string;
  started_at: string;
  completed_at?: string | null;
  duration_ms: number;
  jobs_summary?: string | null;
}

// Prompt Reliability Lab Models (Slice 7.7)
export interface StructuredPromptComponentsModel {
  role?: string;
  objective?: string;
  context?: string;
  instructions?: string[];
  constraints?: string[];
  examples?: Record<string, any>[];
  failure_handling?: string;
  tool_rules?: string[];
  validation_rules?: string[];
}

export interface PromptDefinitionModel {
  prompt_id: string;
  name: string;
  description: string;
  created_at: string;
}

export interface PromptVersionModel {
  prompt_id: string;
  version: number;
  template: string;
  variables_schema: Record<string, any>;
  output_schema?: Record<string, any> | null;
  components?: StructuredPromptComponentsModel | null;
  parent_version?: number | null;
  change_reason?: string | null;
  status: 'DRAFT' | 'CANDIDATE' | 'EVALUATING' | 'PASSED' | 'DEPLOYED' | 'REJECTED' | 'ROLLED_BACK';
  is_evaluated: boolean;
  created_at: string;
}

export interface EvaluationCaseModel {
  case_id: string;
  input: Record<string, any>;
  expected_behavior: string;
  expected_output?: string | Record<string, any> | null;
  constraints: string[];
  sources: Record<string, any>[];
  tools: string[];
  evaluation_strategy: 'EXACT_MATCH' | 'JSON_SCHEMA' | 'RULE_BASED' | 'CODE_EXECUTION' | 'SQL_EXECUTION' | 'GROUNDING' | 'SEMANTIC_JUDGE' | 'LLM_AS_JUDGE' | 'HUMAN_REVIEW' | 'COMPOSITE';
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  tags: string[];
  category: 'NORMAL' | 'AMBIGUOUS' | 'MISSING_INPUT' | 'CONTRADICTORY' | 'LONG_CONTEXT' | 'INJECTION' | 'MALFORMED' | 'OUT_OF_DISTRIBUTION' | 'BOUNDARY' | 'CONFLICTING_EXAMPLES' | 'REGRESSION';
}

export interface EvaluationSuiteModel {
  suite_id: string;
  name: string;
  description: string;
  created_at: string;
}

export interface EvaluationSuiteVersionModel {
  suite_id: string;
  version: number;
  description: string;
  cases: EvaluationCaseModel[];
  is_frozen: boolean;
  created_at: string;
}

export interface EvaluatorResultModel {
  evaluator_name: string;
  strategy: string;
  status: 'PASS' | 'FAIL' | 'PARTIAL' | 'UNKNOWN' | 'ABSTAINED' | 'NOT_APPLICABLE';
  score?: number | null;
  confidence?: number | null;
  rationale: string;
  evidence: Record<string, any>[];
  metadata: Record<string, any>;
}

export interface CaseEvaluationResultModel {
  case_id: string;
  category: string;
  severity: string;
  overall_status: 'PASS' | 'FAIL' | 'PARTIAL' | 'UNKNOWN' | 'ABSTAINED' | 'NOT_APPLICABLE';
  evaluator_results: EvaluatorResultModel[];
  failure_causes: string[];
  evidence_ids: string[];
  confidence?: number | null;
  timestamp: string;
}

export interface DiagnosticFactModel {
  epistemic_type: 'OBSERVED' | 'INFERRED' | 'HYPOTHESIS';
  statement: string;
  evidence_refs: string[];
}

export interface PromptDiagnosisModel {
  diagnosis_id: string;
  evaluation_run_id: string;
  case_id: string;
  primary_cause: string;
  confidence: number;
  facts: DiagnosticFactModel[];
  observed_summary: string;
  inferred_summary: string;
  hypothesis_summary: string;
  created_at: string;
}

export interface EvaluationRunModel {
  evaluation_run_id: string;
  prompt_id: string;
  prompt_version: number;
  suite_id: string;
  suite_version: number;
  model: string;
  generation_parameters: Record<string, any>;
  status: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  partial_cases: number;
  unknown_cases: number;
  abstained_cases: number;
  pass_rate: number;
  case_results: CaseEvaluationResultModel[];
  diagnoses: PromptDiagnosisModel[];
  started_at: string;
  completed_at?: string | null;
  duration_ms: number;
}

export interface CaseTransitionRecordModel {
  case_id: string;
  category: string;
  severity: string;
  status_v1: string;
  status_v2: string;
  transition: 'NEW_PASS' | 'NEW_FAILURE' | 'REGRESSION' | 'FIXED_FAILURE' | 'UNCHANGED';
  rationale_diff: string;
}

export interface PromptComparisonResultModel {
  prompt_id: string;
  v1_version: number;
  v2_version: number;
  suite_id: string;
  suite_version: number;
  v1_run_id: string;
  v2_run_id: string;
  v1_pass_rate: number;
  v2_pass_rate: number;
  pass_rate_delta: number;
  total_cases: number;
  regressions_count: number;
  fixed_failures_count: number;
  unchanged_count: number;
  new_passes_count: number;
  new_failures_count: number;
  critical_regressions: CaseTransitionRecordModel[];
  transitions: CaseTransitionRecordModel[];
  deterministic_pass_rates: Record<string, number>;
  grounding_pass_rates: Record<string, number>;
  semantic_pass_rates: Record<string, number>;
}

export interface EvaluationSnapshotModel {
  snapshot_id: string;
  protocol_version: string;
  prompt_id: string;
  prompt_version: number;
  suite_id: string;
  suite_version: number;
  model: string;
  model_parameters: Record<string, any>;
  dataset_provenance: Record<string, any>;
  evaluation_run_id: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  pass_rate: number;
  evaluator_versions: Record<string, string>;
  sha256_hash: string;
  timestamp: string;
}

// =========================================================================
// GOVERNANCE & CHANGE AUTHORIZATION TYPES (Slice 7.8)
// =========================================================================

export type RecommendationType =
  | 'CODE_CHANGE'
  | 'PROMPT_CHANGE'
  | 'MODEL_CONFIGURATION_CHANGE'
  | 'RAG_CONFIGURATION_CHANGE'
  | 'TOOL_PERMISSION_CHANGE'
  | 'DEPLOYMENT'
  | 'ROLLBACK'
  | 'OTHER';

export type ApprovalRequestStatus =
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'CANCELLED'
  | 'SUPERSEDED';

export type DecisionType = 'APPROVE' | 'REJECT';

export type AuthorizationStatus = 'ACTIVE' | 'USED' | 'EXPIRED' | 'REVOKED';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface GovernanceRecommendationModel {
  recommendation_id: string;
  recommendation_type: RecommendationType;
  subject_type: string;
  subject_id: string;
  source_system: string;
  source_run_id?: string | null;
  source_evaluation_id?: string | null;
  source_diagnosis_id?: string | null;
  source_evidence_ids: string[];
  proposed_action: string;
  rationale: string;
  epistemic_status: string;
  risk_level: RiskLevel;
  effective_risk?: RiskLevel | null;
  created_at: string;
  expires_at?: string | null;
}

export interface EvidencePackageModel {
  package_id: string;
  subject_type: string;
  subject_id: string;
  git_commit_sha?: string | null;
  prompt_version?: string | null;
  model_version?: string | null;
  evaluation_snapshot_id?: string | null;
  ci_run_id?: string | null;
  lab_verification_id?: string | null;
  diagnosis_ids: string[];
  recommendation_ids: string[];
  observations: string[];
  failures: string[];
  regressions: string[];
  verification_results: Record<string, any>;
  created_at: string;
  content_hash: string;
}

export interface ApprovalRequestModel {
  approval_request_id: string;
  recommendation_id?: string | null;
  change_type: RecommendationType;
  subject_type: string;
  subject_id: string;
  current_version?: string | null;
  proposed_version?: string | null;
  proposed_commit_sha?: string | null;
  evaluation_snapshot_id?: string | null;
  lab_verification_id?: string | null;
  ci_verification_id?: string | null;
  evidence_package_id: string;
  risk_level: RiskLevel;
  required_approval_count: number;
  status: ApprovalRequestStatus;
  created_at: string;
  expires_at?: string | null;
}

export interface HumanDecisionModel {
  decision_id: string;
  approval_request_id: string;
  decision: DecisionType;
  decision_maker_id: string;
  actor_type: 'HUMAN';
  decision_timestamp: string;
  decision_reason: string;
  evidence_acknowledged: boolean;
  version_acknowledged: boolean;
  commit_acknowledged: boolean;
}

export interface ChangeAuthorizationModel {
  authorization_id: string;
  approval_request_id: string;
  decision_id: string;
  authorized_change_type: RecommendationType;
  authorized_subject: string;
  authorized_version?: string | null;
  authorized_commit_sha?: string | null;
  authorization_scope: string;
  evidence_package_id: string;
  evidence_package_hash: string;
  issued_at: string;
  expires_at: string;
  status: AuthorizationStatus;
}

export interface GovernanceAuditRecordModel {
  event_id: string;
  event_type: string;
  actor_type: 'SYSTEM' | 'AI_AGENT' | 'HUMAN';
  actor_id: string;
  subject_type: string;
  subject_id: string;
  previous_state?: string | null;
  new_state?: string | null;
  timestamp: string;
  evidence_package_id?: string | null;
  approval_request_id?: string | null;
  authorization_id?: string | null;
  content_hash: string;
  details: Record<string, any>;
}






