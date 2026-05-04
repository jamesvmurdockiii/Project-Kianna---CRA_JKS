"""
Coral Reef Architecture — Measurement Layer for SpiNNaker / PyNN.

This module implements the information-theoretic measurement layer that
feeds the trophic-survival economy:

    * Per-stream mutual information (KSG k-NN and Gaussian-copula).
    * Joint mutual information across all active streams.
    * Bayesian Online Changepoint Detection (BOCPD) for regime-change
      signalling to the reef.

All estimators use **only NumPy and SciPy** — no PyTorch — to keep the
host-side code lightweight for SpiNNaker deployments.

Design Philosophy
-----------------
1. **Honest uncertainty**: every function returns a ``(value, source)``
   pair so the caller knows whether the estimate is genuine, proxied, or
   unavailable.
2. **Sample-complexity guards**: KSG is deprecated above 8 dimensions;
   joint MI falls back to per-stream proxies when history is too short.
3. **Serialisable state**: BOCPD supports pickle-friendly ``get_state`` /
   ``set_state`` for checkpointing across SpiNNaker runs.

References
----------
- Kraskov, Stogbauer & Grassberger (2004)  Estimating mutual information.
  *Physical Review E* 69:066138.
- Ince, Giordano, Kayser et al. (2017)  A novel estimator for mutual
  information.  *PLOS Computational Biology* 13(1):e1005036.
- Adams & MacKay (2007)  Bayesian Online Changepoint Detection.
  *arXiv:0710.3742*.

Author: Coral Reef Architecture team (v009bz SpiNNaker port)
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, Optional, Tuple

import numpy as np
from scipy.spatial import cKDTree
from scipy.special import digamma, gammaln
from scipy import linalg

# ---------------------------------------------------------------------------
# Module-level constants (mirrored from config for standalone use)
# ---------------------------------------------------------------------------

EPSILON: float = 1e-7
"""Numerical floor to prevent log(0) and division by zero."""

KSG_MAX_RELIABLE_DIM: int = 8
"""Dimensionality above which KSG is deprecated in favour of GCMI."""

MI_ESTIMATE_NAN: float = 0.0
"""Value returned when MI cannot be estimated."""

# =============================================================================
# 1.  KSG k-Nearest-Neighbour MI Estimator
# =============================================================================


def compute_ksg_mi(x: np.ndarray, y: np.ndarray, k: int = 4) -> float:
    """Estimate mutual information I(X;Y) via the KSG k-NN estimator.

    Uses the KSG algorithm (Kraskov et al. 2004, Eq. 8) which computes
    MI from the average log-distance to the k-th nearest neighbour in the
    joint (X,Y) space and the marginal counts within those distances.

    Parameters
    ----------
    x : np.ndarray, shape (n_samples,) or (n_samples, d_x)
        Samples of the first variable (or variable group).
    y : np.ndarray, shape (n_samples,) or (n_samples, d_y)
        Samples of the second variable (or variable group).
    k : int, default 4
        Number of nearest neighbours.  Must be >= 1 and < n_samples.

    Returns
    -------
    mi : float
        Estimated mutual information in **nats**.  Convert to bits by
        dividing by ``ln(2)``.

    Raises
    ------
    ValueError
        If inputs have mismatched lengths, insufficient samples, or
        invalid ``k``.

    References
    ----------
    Kraskov, Stogbauer & Grassberger (2004) PRL 69:066138.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    # Normalise shapes --------------------------------------------------------
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if y.ndim == 1:
        y = y.reshape(-1, 1)

    if x.shape[0] != y.shape[0]:
        raise ValueError(
            f"x and y must have the same number of samples; got "
            f"{x.shape[0]} and {y.shape[0]}"
        )

    n = x.shape[0]
    if n < k + 1:
        raise ValueError(
            f"Insufficient samples for KSG: n={n}, k={k}; need n >= k+1"
        )

    d_x = x.shape[1]
    d_y = y.shape[1]

    # Guard against very high dimensionality ----------------------------------
    if d_x + d_y > KSG_MAX_RELIABLE_DIM:
        raise ValueError(
            f"Joint dimension {d_x + d_y} exceeds KSG_MAX_RELIABLE_DIM "
            f"({KSG_MAX_RELIABLE_DIM}); use compute_gcmi instead"
        )

    # Z-score normalisation (KSG is distance-based) ---------------------------
    x = (x - np.mean(x, axis=0)) / (np.std(x, axis=0, ddof=1) + EPSILON)
    y = (y - np.mean(y, axis=0)) / (np.std(y, axis=0, ddof=1) + EPSILON)

    # Joint space
    xy = np.hstack([x, y])

    # Build k-d trees for efficient neighbour search --------------------------
    tree_xy = cKDTree(xy)
    tree_x = cKDTree(x)
    tree_y = cKDTree(y)

    # Query k-th nearest neighbour distances in joint space -------------------
    # k+1 because the point itself is the 0-th neighbour
    k_distances, _ = tree_xy.query(xy, k=k + 1, p=np.inf)
    # Take the k-th neighbour distance (index k)
    epsilon = k_distances[:, k]

    # Count marginal neighbours within epsilon --------------------------------
    # For each point, count how many x-neighbours are within epsilon
    # (excluding the point itself)
    nx = np.zeros(n, dtype=np.int64)
    ny = np.zeros(n, dtype=np.int64)

    for i in range(n):
        nx[i] = len(tree_x.query_ball_point(x[i], r=epsilon[i] + EPSILON)) - 1
        ny[i] = len(tree_y.query_ball_point(y[i], r=epsilon[i] + EPSILON)) - 1

    # KSG estimator (Eq. 8): psi(k) - <psi(nx+1) + psi(ny+1)> + psi(N)
    # where psi is the digamma function
    psi_k = digamma(k)
    psi_nx1 = digamma(nx + 1)
    psi_ny1 = digamma(ny + 1)
    psi_n = digamma(n)

    mi = psi_k - np.mean(psi_nx1 + psi_ny1) + psi_n

    # Clamp negative MI to zero (small-sample bias can produce negatives)
    return max(0.0, float(mi))


# =============================================================================
# 2.  Gaussian-Copula Mutual Information (GCMI)
# =============================================================================


def compute_gcmi(x: np.ndarray, y: np.ndarray) -> float:
    """Estimate mutual information via Gaussian-copula (rank-Gaussianization).

    The GCMI method (Ince et al. 2017):
    1. Convert each marginal to uniform via rank transformation.
    2. Convert uniform to Gaussian via the inverse-CDF (ppf).
    3. Compute MI of the resulting Gaussian variables analytically from
       the covariance matrix.

    This estimator is robust to arbitrary marginal distributions and
    works well in high dimensions where KSG would require prohibitive
    sample sizes.

    Parameters
    ----------
    x : np.ndarray, shape (n_samples,) or (n_samples, d_x)
        Samples of the first variable (or variable group).
    y : np.ndarray, shape (n_samples,) or (n_samples, d_y)
        Samples of the second variable (or variable group).

    Returns
    -------
    mi : float
        Estimated mutual information in **nats**.

    Raises
    ------
    ValueError
        If inputs have mismatched lengths or insufficient samples.

    References
    ----------
    Ince, Giordano, Kayser et al. (2017) PLOS Comput Biol 13(1):e1005036.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if y.ndim == 1:
        y = y.reshape(-1, 1)

    if x.shape[0] != y.shape[0]:
        raise ValueError(
            f"x and y must have the same number of samples; got "
            f"{x.shape[0]} and {y.shape[0]}"
        )

    n = x.shape[0]
    if n < 3:
        raise ValueError(f"GCMI requires at least 3 samples; got {n}")

    d_x = x.shape[1]
    d_y = y.shape[1]

    # Step 1: rank transform each marginal to uniform [0, 1] ----------------
    def _rank_gaussianize(z: np.ndarray) -> np.ndarray:
        """Convert each column of z to Gaussian via rank-normalisation."""
        z_out = np.empty_like(z)
        for col in range(z.shape[1]):
            # Average ranks (handles ties)
            ranks = np.argsort(np.argsort(z[:, col], kind="mergesort"), kind="mergesort")
            # Convert to uniform with 0.5/n offset to avoid 0 and 1
            uniform = (ranks + 0.5) / len(ranks)
            # Inverse CDF of standard Gaussian
            z_out[:, col] = np.sqrt(2) * _erfcinv(2 * (1 - uniform))
        return z_out

    xg = _rank_gaussianize(x)
    yg = _rank_gaussianize(y)

    # Step 2: stack and compute covariance ------------------------------------
    zg = np.hstack([xg, yg])
    d_total = d_x + d_y

    # Sample covariance (unbiased)
    cov = np.cov(zg, rowvar=False, ddof=1)

    # Ensure positive definiteness
    cov += np.eye(d_total) * 1e-6

    # Step 3: analytical MI for Gaussian variables ----------------------------
    # I(X;Y) = -0.5 * log( |C_xy| / (|C_x| * |C_y|) )
    # where |.| denotes determinant
    cov_x = cov[:d_x, :d_x]
    cov_y = cov[d_x:, d_x:]

    try:
        sign_xy, logdet_xy = np.linalg.slogdet(cov)
        sign_x, logdet_x = np.linalg.slogdet(cov_x)
        sign_y, logdet_y = np.linalg.slogdet(cov_y)

        if sign_xy <= 0 or sign_x <= 0 or sign_y <= 0:
            # Covariance is singular; MI is undefined
            warnings.warn("Singular covariance in GCMI; returning 0.0")
            return 0.0

        mi = -0.5 * (logdet_xy - logdet_x - logdet_y)
    except np.linalg.LinAlgError:
        warnings.warn("LinAlgError in GCMI; returning 0.0")
        return 0.0

    # Clamp to non-negative
    return max(0.0, float(mi))


def _erfcinv(y: np.ndarray) -> np.ndarray:
    """Inverse complementary error function, vectorised.

    Uses the relationship ``erfcinv(y) = erfinv(1 - y)``.
    SciPy provides ``scipy.special.erfinv`` which is numerically stable.
    """
    from scipy.special import erfinv

    return erfinv(1.0 - y)


# =============================================================================
# 3.  Unified stream MI measurement with auto-selection
# =============================================================================


def measure_stream_mutual_information(
    x: np.ndarray,
    y: np.ndarray,
    method: str = "auto",
    ksg_k: int = 4,
) -> Tuple[float, str]:
    """Estimate mutual information between two continuous variables.

    Automatically selects the estimator based on dimensionality and
    sample size:

    * ``dim <= KSG_MAX_RELIABLE_DIM`` and ``n >= 30`` → KSG
    * ``dim > KSG_MAX_RELIABLE_DIM`` or ``n < 30`` → GCMI

    Parameters
    ----------
    x : np.ndarray
        First variable samples, shape (n_samples,) or (n_samples, d_x).
    y : np.ndarray
        Second variable samples, shape (n_samples,) or (n_samples, d_y).
    method : {"auto", "ksg", "gcmi"}, default "auto"
        Estimator selection.  "auto" chooses based on dimensionality.
    ksg_k : int, default 4
        k parameter for KSG (used only when KSG is selected).

    Returns
    -------
    mi : float
        Estimated mutual information in **nats**.  Returns 0.0 on failure.
    source : str
        One of ``"ksg"``, ``"gcmi"``, or ``"failed"``.

    References
    ----------
    - Kraskov, Stogbauer, Grassberger (2004) PRL 69:066138
    - Ince, Giordano, Kayser et al. (2017) PLOS Comput Biol
    """
    x = np.asarray(x)
    y = np.asarray(y)

    if x.size == 0 or y.size == 0:
        return MI_ESTIMATE_NAN, "failed"

    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if y.ndim == 1:
        y = y.reshape(-1, 1)

    n = x.shape[0]
    d_total = x.shape[1] + y.shape[1]

    # Insufficient samples guard
    if n < 3:
        return MI_ESTIMATE_NAN, "failed"

    # Determine method --------------------------------------------------------
    if method == "auto":
        if d_total <= KSG_MAX_RELIABLE_DIM and n >= 30:
            method = "ksg"
        else:
            method = "gcmi"

    # Estimate ----------------------------------------------------------------
    try:
        if method == "ksg":
            mi = compute_ksg_mi(x, y, k=ksg_k)
            return mi, "ksg"
        elif method == "gcmi":
            mi = compute_gcmi(x, y)
            return mi, "gcmi"
        else:
            raise ValueError(f"Unknown method: {method}")
    except Exception as exc:
        # On any failure, try the other method as fallback
        try:
            if method == "ksg":
                mi = compute_gcmi(x, y)
                return mi, "gcmi_fallback"
            else:
                if d_total <= KSG_MAX_RELIABLE_DIM and n >= ksg_k + 1:
                    mi = compute_ksg_mi(x, y, k=ksg_k)
                    return mi, "ksg_fallback"
        except Exception:
            pass
        warnings.warn(f"MI estimation failed: {exc}")
        return MI_ESTIMATE_NAN, "failed"


# =============================================================================
# 4.  Joint stream MI across all active streams
# =============================================================================


def measure_joint_stream_mi(
    streams: Dict[str, np.ndarray],
    joint_mi_min_samples_factor: int = 10,
) -> Tuple[float, str]:
    """Joint mutual information across all active streams.

    Computes the total information available to the reef by estimating
    the joint MI among all active (non-NaN, non-empty) input streams.
    Falls back through a cascade of increasingly coarse proxies when
    genuine estimation is infeasible.

    Cascade
    -------
    1. **Genuine joint MI** (GCMI on all streams stacked) — attempted
       when ``n_samples >= d_total * joint_mi_min_samples_factor``.
    2. **Per-stream mean proxy** — average of pairwise MI estimates
       between consecutive streams.
    3. **Stream innovation proxy** — total variance of the stacked
       streams as a crude information proxy.
    4. **Insufficient history** — honest NaN when all histories are
       too short (< 3 samples).

    Parameters
    ----------
    streams : dict[str, np.ndarray]
        Mapping from stream name to 1-D or 2-D sample array.
        Each array has shape (n_samples,) or (n_samples, d_i).
    joint_mi_min_samples_factor : int, default 10
        Required ``n_samples >= d_total * factor`` for genuine joint MI.

    Returns
    -------
    mi : float
        Estimated joint information in **nats**.  0.0 when unavailable.
    source : str
        One of:
        - ``"joint_stream_mi"`` — genuine GCMI estimate on stacked streams
        - ``"stream_mi_proxy"`` — per-stream mean/median proxy
        - ``"stream_innovation_proxy"`` — active-stream innovation proxy
        - ``"insufficient_history"`` — honest NaN (histories too short)

    Notes
    -----
    The source tag is consumed by the trophic-economy layer to weight
    ``sensory_budget_s``.  A ``"joint_stream_mi"`` source gives full
    confidence; proxies are down-weighted by the caller.
    """
    # Filter to active (non-empty) streams ------------------------------------
    active = {
        name: np.asarray(arr)
        for name, arr in streams.items()
        if arr is not None and np.asarray(arr).size > 0
    }

    if not active:
        return MI_ESTIMATE_NAN, "insufficient_history"

    # Normalise all to 2-D and check lengths ----------------------------------
    processed: Dict[str, np.ndarray] = {}
    n_samples: Optional[int] = None
    total_dims = 0

    for name, arr in active.items():
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
        if n_samples is None:
            n_samples = arr.shape[0]
        elif arr.shape[0] != n_samples:
            # Truncate to shortest length
            n_samples = min(n_samples, arr.shape[0])
        total_dims += arr.shape[1]
        processed[name] = arr

    if n_samples is None or n_samples < 3:
        return MI_ESTIMATE_NAN, "insufficient_history"

    # Truncate all to common length -------------------------------------------
    for name in processed:
        processed[name] = processed[name][:n_samples]

    # Attempt 1: genuine joint GCMI -------------------------------------------
    required_samples = total_dims * joint_mi_min_samples_factor
    if n_samples >= required_samples and total_dims <= KSG_MAX_RELIABLE_DIM * 2:
        try:
            stacked = np.hstack(list(processed.values()))
            # Joint MI proxy: total covariance determinant vs marginal product
            # For multi-variable MI we use total correlation approach
            mi = _estimate_total_correlation(stacked)
            if mi >= 0:
                return mi, "joint_stream_mi"
        except Exception:
            pass

    # Attempt 2: per-stream mean/median proxy ---------------------------------
    try:
        pairwise_mis = []
        stream_names = list(processed.keys())
        for i in range(len(stream_names)):
            for j in range(i + 1, len(stream_names)):
                mi_val, _ = measure_stream_mutual_information(
                    processed[stream_names[i]],
                    processed[stream_names[j]],
                    method="auto",
                )
                pairwise_mis.append(mi_val)

        if pairwise_mis:
            # Use median for robustness against outlier pairs
            proxy_mi = float(np.median(pairwise_mis))
            return max(0.0, proxy_mi), "stream_mi_proxy"
    except Exception:
        pass

    # Attempt 3: stream innovation proxy --------------------------------------
    try:
        stacked = np.hstack(list(processed.values()))
        # Total variance as information proxy (higher variance = more info)
        total_var = float(np.sum(np.var(stacked, axis=0, ddof=1)))
        # Normalise by dimension to get per-dim proxy
        proxy_mi = total_var / total_dims
        return max(0.0, proxy_mi), "stream_innovation_proxy"
    except Exception:
        pass

    # Attempt 4: honest failure -----------------------------------------------
    return MI_ESTIMATE_NAN, "insufficient_history"


def _estimate_total_correlation(z: np.ndarray) -> float:
    """Estimate total correlation (multi-information) of a stacked variable set.

    Total correlation = sum of marginal entropies - joint entropy.
    For Gaussian variables this reduces to a determinant formula.

    Parameters
    ----------
    z : np.ndarray, shape (n_samples, d_total)
        Stacked observations from all streams.

    Returns
    -------
    tc : float
        Estimated total correlation in nats.
    """
    n, d = z.shape
    if n < d + 1:
        return 0.0

    # Rank-Gaussianize first (same as GCMI)
    zg = np.empty_like(z)
    for col in range(d):
        ranks = np.argsort(np.argsort(z[:, col], kind="mergesort"), kind="mergesort")
        uniform = (ranks + 0.5) / n
        zg[:, col] = np.sqrt(2) * _erfcinv(2 * (1 - uniform))

    # Sample covariance
    cov = np.cov(zg, rowvar=False, ddof=1)
    cov += np.eye(d) * 1e-6  # regularise

    # Total correlation = -0.5 * (log|C| - sum_i log|C_ii|)
    # where C_ii are the 1x1 marginal covariances (just variances)
    sign, logdet = np.linalg.slogdet(cov)
    if sign <= 0:
        return 0.0

    marginal_logdets = np.sum(np.log(np.diag(cov) + EPSILON))

    tc = -0.5 * (logdet - marginal_logdets)
    return max(0.0, float(tc))


# =============================================================================
# 5.  Bayesian Online Changepoint Detector (BOCPD)
# =============================================================================


class BayesianOnlineChangepointDetector:
    """Bayesian Online Changepoint Detection with adaptive tail-mass truncation.

    Implements the recursive message-passing algorithm of Adams & MacKay
    (2007) with two practical extensions for SpiNNaker deployment:

    1. **Adaptive tail-mass truncation**: instead of a hard posterior cap,
       the run-length distribution is truncated when the tail mass falls
       below a threshold.  This keeps memory bounded without distorting
       the posterior when changepoints are frequent.
    2. **Serialisable state**: ``get_state`` / ``set_state`` support
       checkpointing across SpiNNaker runs.

    The observation model is a univariate Gaussian with unknown mean and
    variance, using the Normal-Inverse-Gamma conjugate prior.

    Parameters
    ----------
    hazard_rate : float, default 1e-3
        Prior probability of a changepoint at each step (constant hazard).
    mu0 : float, default 0.0
        Prior mean for the Gaussian likelihood.
    kappa0 : float, default 1.0
        Prior pseudo-observations for the mean (confidence).
    alpha0 : float, default 1.0
        Prior shape for the inverse-Gamma variance.
    beta0 : float, default 1.0
        Prior scale for the inverse-Gamma variance.
    tail_mass_threshold : float, default 1e-4
        Tail mass below which truncation occurs.
    max_run_length : int, default 1000
        Hard cap on run-length history.

    Attributes
    ----------
    run_length_ : np.ndarray
        Posterior probability P(run_length_t | x_{1:t}).
    time_step_ : int
        Current time step (0-indexed).

    References
    ----------
    Adams & MacKay (2007) "Bayesian Online Changepoint Detection",
    arXiv:0710.3742.
    """

    def __init__(
        self,
        hazard_rate: float = 1e-3,
        mu0: float = 0.0,
        kappa0: float = 1.0,
        alpha0: float = 1.0,
        beta0: float = 1.0,
        tail_mass_threshold: float = 1e-4,
        max_run_length: int = 1000,
    ) -> None:
        self.hazard_rate = hazard_rate
        self.mu0 = mu0
        self.kappa0 = kappa0
        self.alpha0 = alpha0
        self.beta0 = beta0
        self.tail_mass_threshold = tail_mass_threshold
        self.max_run_length = max_run_length

        # Prior parameters for each possible run length (r = 0, 1, 2, ...)
        # These grow dynamically; each entry stores (mu, kappa, alpha, beta)
        # for the posterior given that the current run has length r+1.
        self._mu_params: list = [mu0]
        self._kappa_params: list = [kappa0]
        self._alpha_params: list = [alpha0]
        self._beta_params: list = [beta0]

        # Run-length posterior P(run_length = r | data up to t)
        # Initially: P(run_length = 0) = 1.0 (changepoint at t=0)
        self._run_length: np.ndarray = np.ones(1)

        self._time_step: int = 0
        self._max_posterior_rl: int = 0  # MAP run length

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, observation: float) -> float:
        """Incorporate a new observation and update the run-length posterior.

        Parameters
        ----------
        observation : float
            The new scalar observation.

        Returns
        -------
        predictive_log_likelihood : float
            Log-likelihood of the observation under the predictive
            distribution (higher = more predictable).  Useful as a
            surprise signal to the trophic layer.
        """
        obs = float(observation)

        # 1. Compute predictive probability for each run length ----------------
        pred_probs = self._predictive_probabilities(obs)

        # 2. Grow the posterior (message-passing, Adams & MacKay Eq. 3-4) -----
        # P(r_t = r+1, r_{t-1} = r, x_{1:t}) ∝
        #   P(r_{t-1}=r | x_{<t}) * (1-H) * p(x_t | r_{t-1}=r)
        # P(r_t = 0, x_{1:t}) ∝
        #   sum_r P(r_{t-1}=r | x_{<t}) * H * p(x_t | r_{t-1}=r)

        H = self.hazard_rate
        growth_probs = self._run_length * pred_probs * (1.0 - H)
        cp_prob = np.sum(self._run_length * pred_probs * H)

        # New posterior: [cp_prob, growth_probs]
        new_posterior = np.empty(len(growth_probs) + 1)
        new_posterior[0] = cp_prob
        new_posterior[1:] = growth_probs

        # Normalise
        evidence = np.sum(new_posterior)
        if evidence > EPSILON:
            new_posterior /= evidence
        else:
            # Degenerate case: reset to uniform
            new_posterior = np.ones_like(new_posterior) / len(new_posterior)

        # 3. Update sufficient statistics for each run length ------------------
        # New run length 0: reset to prior
        new_mu = [self.mu0]
        new_kappa = [self.kappa0]
        new_alpha = [self.alpha0]
        new_beta = [self.beta0]

        # Existing runs: update with new observation
        for i in range(len(self._mu_params)):
            mu_post, kappa_post, alpha_post, beta_post = self._update_sufficient_stats(
                self._mu_params[i],
                self._kappa_params[i],
                self._alpha_params[i],
                self._beta_params[i],
                obs,
            )
            new_mu.append(mu_post)
            new_kappa.append(kappa_post)
            new_alpha.append(alpha_post)
            new_beta.append(beta_post)

        # 4. Adaptive tail-mass truncation -------------------------------------
        self._run_length = new_posterior
        self._mu_params = new_mu
        self._kappa_params = new_kappa
        self._alpha_params = new_alpha
        self._beta_params = new_beta

        self._truncate_posterior()

        # 5. Update time step and MAP estimate ---------------------------------
        self._time_step += 1
        self._max_posterior_rl = int(np.argmax(self._run_length))

        # Return log predictive likelihood
        return float(np.log(evidence + EPSILON))

    def posterior_run_length(self) -> np.ndarray:
        """Return the current run-length posterior distribution.

        Returns
        -------
        run_length_probs : np.ndarray, shape (max_run_length+1,)
            P(run_length = r | observations).  Index 0 is the probability
            that a changepoint occurred at the most recent step.
        """
        return np.array(self._run_length, copy=True)

    @property
    def changepoint_probability(self) -> float:
        """Probability that a changepoint occurred at the current step.

        Returns
        -------
        p_cp : float
            P(run_length = 0 | observations) = probability of a
            changepoint at the most recent observation.
        """
        if len(self._run_length) > 0:
            return float(self._run_length[0])
        return 0.0

    @property
    def expected_run_length(self) -> float:
        """Expected run length under the posterior.

        Returns
        -------
        E[r] : float
            Sum of r * P(run_length = r | data).
        """
        return float(np.sum(np.arange(len(self._run_length)) * self._run_length))

    @property
    def time_step(self) -> int:
        """Current time step (number of observations processed)."""
        return self._time_step

    def most_likely_run_length(self) -> int:
        """Return the maximum-a-posteriori run length.

        Returns
        -------
        map_rl : int
            The run length with highest posterior probability.
        """
        return self._max_posterior_rl

    # ------------------------------------------------------------------
    # Serialisation (checkpointing for SpiNNaker runs)
    # ------------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        """Return a pickle-friendly state dictionary.

        The state captures everything needed to resume detection from
        the exact same posterior after a SpiNNaker checkpoint / reboot.

        Returns
        -------
        state : dict
            Contains all hyperparameters and the current run-length
            posterior with sufficient statistics.
        """
        return {
            "hazard_rate": self.hazard_rate,
            "mu0": self.mu0,
            "kappa0": self.kappa0,
            "alpha0": self.alpha0,
            "beta0": self.beta0,
            "tail_mass_threshold": self.tail_mass_threshold,
            "max_run_length": self.max_run_length,
            "time_step": self._time_step,
            "run_length": self._run_length.copy(),
            "mu_params": list(self._mu_params),
            "kappa_params": list(self._kappa_params),
            "alpha_params": list(self._alpha_params),
            "beta_params": list(self._beta_params),
            "max_posterior_rl": self._max_posterior_rl,
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore the detector from a state dictionary.

        Parameters
        ----------
        state : dict
            State dictionary previously returned by ``get_state()``.
        """
        self.hazard_rate = state["hazard_rate"]
        self.mu0 = state["mu0"]
        self.kappa0 = state["kappa0"]
        self.alpha0 = state["alpha0"]
        self.beta0 = state["beta0"]
        self.tail_mass_threshold = state["tail_mass_threshold"]
        self.max_run_length = state["max_run_length"]
        self._time_step = state["time_step"]
        self._run_length = np.array(state["run_length"])
        self._mu_params = list(state["mu_params"])
        self._kappa_params = list(state["kappa_params"])
        self._alpha_params = list(state["alpha_params"])
        self._beta_params = list(state["beta_params"])
        self._max_posterior_rl = state["max_posterior_rl"]

    def __getstate__(self) -> Dict[str, Any]:
        """Support ``pickle.dumps(detector)``."""
        return self.get_state()

    def __setstate__(self, state: Dict[str, Any]) -> None:
        """Support ``pickle.loads(data)``."""
        # __init__ is not called by pickle; set all attributes directly
        self.hazard_rate = state.get("hazard_rate", 1e-3)
        self.mu0 = state.get("mu0", 0.0)
        self.kappa0 = state.get("kappa0", 1.0)
        self.alpha0 = state.get("alpha0", 1.0)
        self.beta0 = state.get("beta0", 1.0)
        self.tail_mass_threshold = state.get("tail_mass_threshold", 1e-4)
        self.max_run_length = state.get("max_run_length", 1000)
        self._time_step = state.get("time_step", 0)
        self._run_length = np.array(state.get("run_length", np.ones(1)))
        self._mu_params = list(state.get("mu_params", [self.mu0]))
        self._kappa_params = list(state.get("kappa_params", [self.kappa0]))
        self._alpha_params = list(state.get("alpha_params", [self.alpha0]))
        self._beta_params = list(state.get("beta_params", [self.beta0]))
        self._max_posterior_rl = state.get("max_posterior_rl", 0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _predictive_probabilities(self, obs: float) -> np.ndarray:
        """Compute p(x_t | run_length_{t-1} = r) for all r.

        Uses the Student-t predictive distribution of the Normal-Inverse-Gamma.

        Parameters
        ----------
        obs : float
            New observation.

        Returns
        -------
        probs : np.ndarray
            Predictive probability density for each run length.
        """
        probs = np.zeros(len(self._mu_params))
        for i in range(len(self._mu_params)):
            mu = self._mu_params[i]
            kappa = self._kappa_params[i]
            alpha = self._alpha_params[i]
            beta = self._beta_params[i]

            # Student-t predictive: df = 2*alpha, loc = mu, scale = sqrt(beta*(kappa+1)/(alpha*kappa))
            df = 2.0 * alpha
            loc = mu
            scale = np.sqrt(beta * (kappa + 1.0) / (alpha * kappa))

            if df > 0 and scale > EPSILON:
                # log pdf of Student-t
                from scipy.stats import t

                log_prob = t.logpdf(obs, df=df, loc=loc, scale=scale)
                probs[i] = np.exp(log_prob)
            else:
                probs[i] = EPSILON

        return probs

    def _update_sufficient_stats(
        self,
        mu: float,
        kappa: float,
        alpha: float,
        beta: float,
        obs: float,
    ) -> Tuple[float, float, float, float]:
        """Update Normal-Inverse-Gamma posterior with one observation.

        Parameters
        ----------
        mu, kappa, alpha, beta : float
            Current posterior parameters.
        obs : float
            New observation.

        Returns
        -------
        mu_post, kappa_post, alpha_post, beta_post : float
            Updated parameters.
        """
        kappa_post = kappa + 1.0
        mu_post = (kappa * mu + obs) / kappa_post
        alpha_post = alpha + 0.5
        beta_post = beta + (kappa / kappa_post) * 0.5 * (obs - mu) ** 2

        return mu_post, kappa_post, alpha_post, beta_post

    def _truncate_posterior(self) -> None:
        """Adaptive tail-mass truncation of the run-length posterior.

        Two truncation criteria:
        1. **Tail mass**: if cumulative probability of run lengths > R
           falls below ``tail_mass_threshold``, truncate at R.
        2. **Hard cap**: never exceed ``max_run_length`` entries.
        """
        # Criterion 1: adaptive tail mass
        cumsum = np.cumsum(self._run_length[::-1])[::-1]
        tail_idx = np.searchsorted(cumsum, self.tail_mass_threshold, side="left")

        if tail_idx < len(self._run_length):
            # Truncate and renormalise, but always keep at least the
            # changepoint-probability entry (index 0)
            keep = max(tail_idx, 1)
            self._run_length = self._run_length[:keep]
            self._mu_params = self._mu_params[:keep]
            self._kappa_params = self._kappa_params[:keep]
            self._alpha_params = self._alpha_params[:keep]
            self._beta_params = self._beta_params[:keep]

        # Criterion 2: hard cap
        if len(self._run_length) > self.max_run_length:
            self._run_length = self._run_length[: self.max_run_length]
            self._mu_params = self._mu_params[: self.max_run_length]
            self._kappa_params = self._kappa_params[: self.max_run_length]
            self._alpha_params = self._alpha_params[: self.max_run_length]
            self._beta_params = self._beta_params[: self.max_run_length]

        # Renormalise after truncation
        total = np.sum(self._run_length)
        if total > EPSILON:
            self._run_length /= total


# =============================================================================
# 6.  Gram-Schmidt Orthonormalisation (TF Identity Basis)
# =============================================================================


def orthonormalize_basis(vectors: np.ndarray, epsilon: float = 1e-10) -> np.ndarray:
    """Gram-Schmidt orthonormalisation of a set of vectors.

    Produces an orthonormal basis for the subspace spanned by the input
    vectors.  Used in the CRA to give each polyp a unique developmental
    identity (transcription-factor basis, O'Leary & Nakagawa 2002).

    Parameters
    ----------
    vectors : np.ndarray, shape (n_vectors, dim)
        Input vectors to orthonormalise.  May be linearly dependent.
    epsilon : float, default 1e-10
        Tolerance for detecting linear dependence.  Vectors with norm
        < epsilon after projection removal are skipped.

    Returns
    -------
    basis : np.ndarray, shape (m, dim)
        Orthonormal basis vectors (m <= n_vectors).  Each row has unit
        L2 norm and pairwise inner products are zero.

    Notes
    -----
    Uses the modified Gram-Schmidt algorithm for numerical stability.
    """
    vectors = np.asarray(vectors, dtype=np.float64)

    if vectors.ndim != 2:
        raise ValueError(f"Expected 2-D array; got shape {vectors.shape}")

    n_vectors, dim = vectors.shape
    basis_list = []

    for i in range(n_vectors):
        v = vectors[i].copy()

        # Subtract projections onto existing basis vectors
        for b in basis_list:
            v -= np.dot(v, b) * b

        # Check if the residual is non-negligible
        norm = np.linalg.norm(v)
        if norm > epsilon:
            basis_list.append(v / norm)

    if not basis_list:
        # All vectors were linearly dependent; return empty basis
        return np.empty((0, dim), dtype=np.float64)

    return np.stack(basis_list, axis=0)


# =============================================================================
# 7.  Warmup / Sample-Complexity Helpers
# =============================================================================


def warmup_min_samples(d_eff: int, tau: float, warmup_factor: int = 10) -> int:
    """Minimum samples needed for reliable MI estimation.

    The KSG estimator requires approximately ``10 * d_eff * tau`` samples
    for reliable density estimation, where ``d_eff`` is the effective
    dimensionality and ``tau`` is the autocorrelation time of the data.

    Parameters
    ----------
    d_eff : int
        Effective dimensionality of the joint variable space.
    tau : float
        Estimated autocorrelation time (in steps).  tau = 1 for IID data;
        higher for temporally correlated streams.
    warmup_factor : int, default 10
        Multiplier (empirical rule-of-thumb from Kraskov et al. 2004).

    Returns
    -------
    min_samples : int
        Floor on the number of samples required.  MI estimates from fewer
        samples should be tagged as ``insufficient_history``.

    References
    ----------
    Kraskov, Stogbauer & Grassberger (2004) PRL 69:066138, supplement.
    """
    if d_eff < 1:
        d_eff = 1
    if tau < 1.0:
        tau = 1.0

    min_samples = int(warmup_factor * d_eff * tau)
    # Absolute floor: KSG needs at least k+1 = 5 samples
    return max(min_samples, 5)


def estimate_autocorrelation_time(x: np.ndarray, max_lag: int = 20) -> float:
    """Estimate the integrated autocorrelation time of a univariate series.

    Uses the initial positive sequence estimator (Geyer 1992) truncated
    at the first negative autocovariance.

    Parameters
    ----------
    x : np.ndarray, shape (n_samples,)
        Input time series.
    max_lag : int, default 20
        Maximum lag to consider.

    Returns
    -------
    tau : float
        Estimated autocorrelation time.  tau >= 1.0 always.
    """
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError(f"Expected 1-D array; got shape {x.shape}")

    n = len(x)
    if n < 2:
        return 1.0

    # Centre the data
    x_centered = x - np.mean(x)
    c0 = np.var(x, ddof=1)

    if c0 < EPSILON:
        return 1.0  # Constant series has no autocorrelation

    # Compute autocorrelations up to max_lag
    tau = 1.0
    for lag in range(1, min(max_lag, n - 1)):
        # Autocovariance at lag
        c_lag = np.mean(x_centered[:-lag] * x_centered[lag:])
        rho = c_lag / c0

        if rho < 0:
            # Initial positive sequence truncation (Geyer 1992)
            break
        tau += 2.0 * rho

    return max(1.0, tau)


# =============================================================================
# 8.  Convenience: batch MI estimation for reef streams
# =============================================================================


def estimate_stream_mi_batch(
    streams: Dict[str, np.ndarray],
    target: np.ndarray,
) -> Dict[str, Tuple[float, str]]:
    """Estimate MI between each stream and a target variable.

    Parameters
    ----------
    streams : dict[str, np.ndarray]
        Input streams, each shape (n_samples, d_i).
    target : np.ndarray
        Target variable, shape (n_samples,) or (n_samples, d_t).

    Returns
    -------
    mi_results : dict[str, (float, str)]
        Mapping from stream name to (MI estimate, source tag).
    """
    results = {}
    for name, stream in streams.items():
        mi, source = measure_stream_mutual_information(stream, target)
        results[name] = (mi, source)
    return results
