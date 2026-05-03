"""
Multi-signal weighted fusion: rescale factor-type weights by regime, then fuse per symbol.

Open-source note
----------------
Tables in this module are **illustrative only** (pedagogical defaults). They are not
production-calibrated weights. OptimetricFlow applies IC/decay-aware schedules that
stay private; integrate your own ``base_weights`` / ``regime_multipliers`` via
``SignalAggregator(...)`` for anything serious.

Fusion shape (conceptual)
-------------------------
For each symbol, group ``AlphaFactor`` rows by ``factor_type``. For each type present,
take a confidence-weighted average of scores, multiply by that type's weight for the
current regime (normalized), then combine types into one fused score in [-1, 1].
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from .alpha_factory import AlphaFactor, FactorType
from .regime_detector import RegimeResult, RegimeType


@dataclass
class FactorContribution:
    """Contribution of a single factor type to the fused score."""
    factor_type: FactorType
    weight: float
    weighted_score: float
    raw_avg_score: float
    count: int


@dataclass
class FusedSignal:
    """Fused signal for a single symbol or sector."""
    symbol: str
    fused_score: float  # Combined score, approx [-1, 1]
    contributions: List[FactorContribution] = field(default_factory=list)
    regime_used: Optional[RegimeType] = None
    n_factors: int = 0


# Illustrative base weights (neutral regime); replace in production.
ILLUSTRATIVE_BASE_WEIGHTS: Dict[FactorType, float] = {
    "EVENT_DRIVEN": 0.33,
    "SENTIMENT": 0.27,
    "FUND_FLOW": 0.22,
    "TECHNICAL": 0.18,
}

# Illustrative regime multipliers applied to base weights before renormalization.
ILLUSTRATIVE_REGIME_MULTIPLIERS: Dict[RegimeType, Dict[FactorType, float]] = {
    "BULL": {
        "EVENT_DRIVEN": 1.15,
        "SENTIMENT": 0.95,
        "FUND_FLOW": 1.05,
        "TECHNICAL": 0.85,
    },
    "BEAR": {
        "EVENT_DRIVEN": 0.85,
        "SENTIMENT": 1.15,
        "FUND_FLOW": 1.10,
        "TECHNICAL": 1.00,
    },
    "SHOCK": {
        "EVENT_DRIVEN": 1.00,
        "SENTIMENT": 1.20,
        "FUND_FLOW": 1.00,
        "TECHNICAL": 1.05,
    },
}

# Back-compat names (same illustrative tables).
DEFAULT_WEIGHTS = ILLUSTRATIVE_BASE_WEIGHTS
REGIME_WEIGHT_MULTIPLIERS = ILLUSTRATIVE_REGIME_MULTIPLIERS


class SignalAggregator:
    """
    Multi-signal weighted fusion engine.

    Adjusts factor type weights based on current market regime,
    then performs weighted averaging across all factors for each symbol.
    """

    def __init__(
        self,
        base_weights: Optional[Dict[FactorType, float]] = None,
        regime_multipliers: Optional[Dict[RegimeType, Dict[FactorType, float]]] = None,
    ):
        self.base_weights = base_weights or ILLUSTRATIVE_BASE_WEIGHTS.copy()
        self.regime_multipliers = regime_multipliers or ILLUSTRATIVE_REGIME_MULTIPLIERS

    def _get_weights_for_regime(self, regime: Optional[RegimeType]) -> Dict[FactorType, float]:
        """Computes normalized weights adjusted for the given market regime."""
        raw = {ft: self.base_weights.get(ft, 0.25) for ft in ["EVENT_DRIVEN", "SENTIMENT", "FUND_FLOW", "TECHNICAL"]}
        if regime and regime in self.regime_multipliers:
            for ft, mult in self.regime_multipliers[regime].items():
                raw[ft] = raw.get(ft, 0.25) * mult
        total = sum(raw.values()) or 1.0
        return {k: v / total for k, v in raw.items()}

    def _fuse_one_symbol(
        self,
        symbol: str,
        symbol_factors: List[AlphaFactor],
        weights: Dict[FactorType, float],
    ) -> FusedSignal:
        """Weighted fusion for a single symbol's factors."""
        by_type: Dict[FactorType, List[AlphaFactor]] = defaultdict(list)
        for f in symbol_factors:
            by_type[f.factor_type].append(f)

        contributions: List[FactorContribution] = []
        weighted_sum = 0.0
        total_weight_used = 0.0

        for ft in ["EVENT_DRIVEN", "SENTIMENT", "FUND_FLOW", "TECHNICAL"]:
            flist = by_type.get(ft, [])
            if not flist:
                continue
            w = weights.get(ft, 0.25)
            scores = [f.score for f in flist]
            confs = [f.confidence for f in flist]
            denom = sum(confs) or 1.0
            avg_score = sum(s * c for s, c in zip(scores, confs)) / denom
            weighted_score = avg_score * w
            weighted_sum += weighted_score
            total_weight_used += w
            contributions.append(FactorContribution(
                factor_type=ft,
                weight=w,
                weighted_score=weighted_score,
                raw_avg_score=avg_score,
                count=len(flist),
            ))

        if total_weight_used > 0:
            fused_score = weighted_sum / total_weight_used
        else:
            fused_score = 0.0
        fused_score = max(-1.0, min(1.0, fused_score))

        return FusedSignal(
            symbol=symbol,
            fused_score=fused_score,
            contributions=contributions,
            n_factors=len(symbol_factors),
        )

    def aggregate(
        self,
        factors: List[AlphaFactor],
        regime: Optional[RegimeResult] = None,
    ) -> List[FusedSignal]:
        """
        Groups factors by symbol and produces fused scores.

        Returns FusedSignal list sorted by |fused_score| descending.
        """
        if not factors:
            return []

        regime_type = regime.regime if regime else None
        weights = self._get_weights_for_regime(regime_type)

        by_symbol: Dict[str, List[AlphaFactor]] = defaultdict(list)
        for f in factors:
            by_symbol[f.symbol].append(f)

        result: List[FusedSignal] = []
        for symbol, symbol_factors in by_symbol.items():
            fused = self._fuse_one_symbol(symbol, symbol_factors, weights)
            fused.regime_used = regime_type
            result.append(fused)

        result.sort(key=lambda x: abs(x.fused_score), reverse=True)
        return result
