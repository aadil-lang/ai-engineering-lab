import math
import logging
from typing import Any
from backend.app.models.reliability import ReliabilityFeatureVector
from backend.app.models.cold_start import LocalCalibrationState, CalibrationObservation

logger = logging.getLogger("ai_qa_platform.cold_start_calibrator")


class ColdStartCalibrator:
    """
    Statistically grounded Empirical Bayes calibration engine for cross-application cold start.
    Incorporates local application evidence through log-odds intercept shifts without
    retraining global feature weights.
    """

    DEFAULT_PRIOR_STRENGTH_M: float = 5.0  # Equivalent pseudo-observations from global prior

    @staticmethod
    def logit(p: float, eps: float = 1e-6) -> float:
        """Safe logit function with numerical clamping."""
        clamped_p = max(eps, min(1.0 - eps, p))
        return math.log(clamped_p / (1.0 - clamped_p))

    @staticmethod
    def sigmoid(z: float) -> float:
        """Safe numerically clamped sigmoid function."""
        clamped_z = max(-20.0, min(20.0, z))
        return 1.0 / (1.0 + math.exp(-clamped_z))

    @classmethod
    def compute_local_calibration_state(
        cls,
        application_id: str,
        budget_k: int,
        local_observations: list[ReliabilityFeatureVector],
        global_train_prevalence: float,
        prior_strength_m: float = DEFAULT_PRIOR_STRENGTH_M,
    ) -> LocalCalibrationState:
        """
        Derives the local calibration state from up to K historical observations.
        """
        # Take at most budget_k observations
        calibration_set = local_observations[:budget_k]
        k_actual = len(calibration_set)

        if k_actual == 0:
            return LocalCalibrationState(
                application_id=application_id,
                budget_k=budget_k,
                actual_observations_count=0,
                cutoff_timestamp="",
                observed_failures=0,
                observed_passes=0,
                empirical_failure_rate=0.0,
                shrunk_failure_rate=round(global_train_prevalence, 4),
                intercept_shift=0.0,
                observation_run_ids=[],
            )

        observed_fails = sum(1 for v in calibration_set if v.label_next_failed == 1)
        observed_passes = k_actual - observed_fails
        empirical_rate = observed_fails / k_actual

        # Empirical Bayes shrinkage towards global prior base rate
        shrunk_rate = (observed_fails + prior_strength_m * global_train_prevalence) / (k_actual + prior_strength_m)

        # Intercept shift: logit(shrunk_local_rate) - logit(global_train_prevalence)
        logit_shrunk = cls.logit(shrunk_rate)
        logit_global = cls.logit(global_train_prevalence)
        intercept_shift = round(logit_shrunk - logit_global, 4)

        cutoff_ts = calibration_set[-1].timestamp if calibration_set else ""
        run_ids = [v.run_id for v in calibration_set]

        return LocalCalibrationState(
            application_id=application_id,
            budget_k=budget_k,
            actual_observations_count=k_actual,
            cutoff_timestamp=cutoff_ts,
            observed_failures=observed_fails,
            observed_passes=observed_passes,
            empirical_failure_rate=round(empirical_rate, 4),
            shrunk_failure_rate=round(shrunk_rate, 4),
            intercept_shift=intercept_shift,
            observation_run_ids=run_ids,
        )

    @classmethod
    def calibrate_probability(
        cls,
        p_global: float,
        calibration_state: LocalCalibrationState,
    ) -> float:
        """
        Applies local calibration shift to global prior probability.
        logit(p_calibrated) = logit(p_global) + intercept_shift
        """
        if calibration_state.budget_k == 0 or calibration_state.actual_observations_count == 0:
            return round(p_global, 4)

        logit_p = cls.logit(p_global)
        calibrated_logit = logit_p + calibration_state.intercept_shift
        p_calibrated = cls.sigmoid(calibrated_logit)
        return round(p_calibrated, 4)

    @classmethod
    def compute_local_baseline_probability(
        cls,
        calibration_state: LocalCalibrationState,
        current_vector: ReliabilityFeatureVector | None = None,
        global_train_prevalence: float = 0.05,
    ) -> float:
        """
        Computes Strategy B local baseline probability using ONLY local history.
        Uses Laplace smoothed local failure frequency: (k_f + 1) / (K + 2).
        If K=0, falls back to uninformative global prevalence.
        """
        if calibration_state.budget_k == 0 or calibration_state.actual_observations_count == 0:
            return round(global_train_prevalence, 4)

        k_f = calibration_state.observed_failures
        k_total = calibration_state.actual_observations_count

        # Laplace smoothed rate
        laplace_rate = (k_f + 1.0) / (k_total + 2.0)
        return round(laplace_rate, 4)
