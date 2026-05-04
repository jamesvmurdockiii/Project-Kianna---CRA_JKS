"""
Dopamine-modulated STDP weight dependence for Coral Reef Architecture.

This module contains:
- :class:`DopamineModulatedWeightDependence` — a PyNN-compatible
  weight-dependence rule that documents and parameterises the
  reward-modulated STDP used by the CRA.
"""

from __future__ import annotations

from typing import Dict, Tuple

try:
    from pyNN.standardmodels.synapses import STDPWeightDependence
except Exception:  # pragma: no cover
    STDPWeightDependence = object  # type: ignore[misc,assignment]

from .polyp_state import STDP_W_MAX, STDP_W_MIN

class DopamineModulatedWeightDependence(STDPWeightDependence):
    """Reward-modulated weight dependence for STDP on SpiNNaker.

    This class extends PyNN's ``STDPWeightDependence`` to implement
    dopamine-modulated STDP following Izhikevich (2007) and
    Fremaux et al. (2010).

    The standard STDP weight change ``delta_w`` is multiplied by
    ``(1 + dopamine_ema)``, so that positive dopamine potentiates
    LTP and negative dopamine (or low EMA) suppresses it.

    Because sPyNNaker does not support arbitrary per-neuron state
    machines in the weight-dependence rule directly, the dopamine
    modulation is applied *host-side* by scaling the
    ``A_plus`` / ``A_minus`` parameters of the
    ``SpikePairRule`` before each ``sim.run()``.  This class therefore
    serves as a *documentation and parameter-holder* for the intended
    modulation, and also provides the static helper
    :py:meth:`modulated_parameters`.

    Parameters
    ----------
    w_min : float, optional
        Minimum synaptic weight.  Default 0.0.
    w_max : float, optional
        Maximum synaptic weight.  Default 5.0.
    dopamine_scale : float, optional
        Scaling factor for how strongly dopamine modulates the learning
        rate.  Default 1.0.

    Attributes
    ----------
    w_min, w_max, dopamine_scale : float
        Stored parameters.
    """

    # PyNN metadata required by the framework
    has_a_minus: bool = True

    default_parameters: Dict[str, float] = {
        "w_min": STDP_W_MIN,
        "w_max": STDP_W_MAX,
        "dopamine_scale": 1.0,
    }

    # Tell PyNN which parameters we expose
    parameter_names: Tuple[str, ...] = ("w_min", "w_max", "dopamine_scale")

    def __init__(
        self,
        w_min: float = STDP_W_MIN,
        w_max: float = STDP_W_MAX,
        dopamine_scale: float = 1.0,
        **extra,
    ):
        """Initialise the weight-dependence rule.

        Parameters
        ----------
        w_min : float, optional
            Floor for synaptic weights.  Default ``STDP_W_MIN`` (0.0).
        w_max : float, optional
            Ceiling for synaptic weights.  Default ``STDP_W_MAX`` (5.0).
        dopamine_scale : float, optional
            Multiplier for dopamine modulation.  Default 1.0.
        **extra
            Ignored – accepted for compatibility with PyNN's parameter
            introspection.
        """
        super().__init__()
        self.w_min = float(w_min)
        self.w_max = float(w_max)
        self.dopamine_scale = float(dopamine_scale)

    @staticmethod
    def modulated_parameters(
        base_a_plus: float,
        base_a_minus: float,
        dopamine_ema: float,
        dopamine_scale: float = 1.0,
    ) -> Tuple[float, float]:
        """Return dopamine-modulated STDP amplitudes.

        The modulation factor is ``(1 + dopamine_scale * dopamine_ema)``.
        This is applied to the *amplitudes* (``A_plus`` and ``A_minus``)
        of the ``SpikePairRule``, which is the standard way to implement
        reward-gated eligibility on SpiNNaker when the hardware STDP
        engine does not support per-neuron neuromodulator variables.

        Parameters
        ----------
        base_a_plus : float
            Baseline LTD/LTP amplitude for pre-after-post timing.
        base_a_minus : float
            Baseline LTD amplitude for post-after-pre timing.
        dopamine_ema : float
            Current dopamine EMA value (can be negative).
        dopamine_scale : float, optional
            Scaling factor.  Default 1.0.

        Returns
        -------
        tuple of float
            ``(modulated_a_plus, modulated_a_minus)``

        Notes
        -----
        The modulation is clipped so that amplitudes never go negative.
        A small minimum (``1e-6``) is enforced to prevent accidental
        STDP shutdown.
        """
        modulation = 1.0 + dopamine_scale * float(dopamine_ema)
        mod_plus = base_a_plus * modulation
        mod_minus = base_a_minus * modulation
        # Clip: never negative, never below epsilon
        eps = 1e-6
        mod_plus = max(eps, mod_plus)
        mod_minus = max(eps, mod_minus)
        return float(mod_plus), float(mod_minus)


# ---------------------------------------------------------------------------
# PolypNeuronType
# ---------------------------------------------------------------------------

