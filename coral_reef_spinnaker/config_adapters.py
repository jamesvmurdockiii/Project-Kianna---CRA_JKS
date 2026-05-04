"""
Config adapters: map root ReefConfig to subsystem-local config contracts.

Each CRA subsystem (energy, learning, graph) has its own local config
dataclass. This module provides canonical mappings so the root config
remains the single source of truth.
"""

from __future__ import annotations

import math

from .config import ReefConfig, EnergyConfig, LearningConfig
from .reef_network import ReefNetworkConfig as GraphConfig
from .trading_bridge import TradingConfig


def energy_manager_config(cfg: ReefConfig) -> EnergyConfig:
    """Map root config to the EnergyManager-local config contract."""
    return cfg.energy


def learning_manager_config(cfg: ReefConfig) -> LearningConfig:
    """Map root config names to learning_manager.py names."""
    return cfg.learning


def graph_config(cfg: ReefConfig) -> GraphConfig:
    """Map root network config to reef_network.py graph config."""
    max_pop = cfg.lifecycle.max_population_hard
    return GraphConfig(
        hidden_dim=cfg.network.hidden_size,
        message_dim=cfg.network.message_size,
        wm_dim=cfg.network.wm_size,
        chemistry_dim=cfg.network.chemistry_size,
        tf_dim=cfg.network.tf_size,
        max_out_degree=max(1, int(cfg.network.max_out_degree_factor * math.sqrt(max_pop))),
        gap_junction_radius=2.0,
        ff_formation_bias=1.5,
        fb_formation_bias=1.2,
        activity_threshold=1,
        min_age_for_pruning=10,
        construction_cost=1.0,
        calcification_threshold=5.0,
        sensor_node_ids=[],
    )


def trading_config(cfg: ReefConfig) -> TradingConfig:
    """Map root learning config to trading bridge config."""
    return TradingConfig(
        evaluation_horizon_bars=cfg.learning.evaluation_horizon_bars,
        seed_output_scale=cfg.learning.seed_output_scale,
        output_scale_adaptation_alpha=cfg.learning.output_scale_adaptation_alpha,
        dopamine_gain=cfg.learning.dopamine_gain,
    )
