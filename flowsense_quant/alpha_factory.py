"""
Alpha Factor Factory: converts multi-source raw signals into standardized Alpha Factors.

Factor categories:
  - EVENT_DRIVEN: Breaking news, policy, earnings reports
  - SENTIMENT: Social media, YouTube alt-data, news sentiment aggregation
  - FUND_FLOW: Northbound capital, block trades, margin trading
  - TECHNICAL: Chart patterns, RSI (used as filters only)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Literal, Any, Dict

from .schemas import UnifiedSignal


FactorType = Literal["EVENT_DRIVEN", "SENTIMENT", "FUND_FLOW", "TECHNICAL"]

# Signal source → factor type mapping
SOURCE_TO_FACTOR: Dict[str, FactorType] = {
    "news": "EVENT_DRIVEN",
    "policy": "EVENT_DRIVEN",
    "report": "EVENT_DRIVEN",
    "social": "SENTIMENT",
    "youtube": "SENTIMENT",
}

# Fine-grained event type → factor type mapping (takes priority over source)
EVENT_TYPE_TO_FACTOR: Dict[str, FactorType] = {
    "policy": "EVENT_DRIVEN",
    "earnings": "EVENT_DRIVEN",
    "breaking": "EVENT_DRIVEN",
    "industry": "EVENT_DRIVEN",
    "fund_flow": "FUND_FLOW",
    "northbound": "FUND_FLOW",
    "margin": "FUND_FLOW",
    "sentiment": "SENTIMENT",
    "social_buzz": "SENTIMENT",
    "technical_pattern": "TECHNICAL",
    "overbought_oversold": "TECHNICAL",
}


@dataclass
class AlphaFactor:
    """A single standardized Alpha Factor for downstream fusion."""
    symbol: str
    factor_type: FactorType
    score: float  # Normalized score, ideally [-1, 1]
    confidence: float = 1.0
    source_type: str = ""
    source_id: str = ""
    event_type: Optional[str] = None
    impact_sectors: List[str] = field(default_factory=list)
    impact_duration: Optional[str] = None
    reasoning: Optional[str] = None
    created_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "factor_type": self.factor_type,
            "score": self.score,
            "confidence": self.confidence,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "event_type": self.event_type,
            "impact_sectors": self.impact_sectors,
            "impact_duration": self.impact_duration,
            "reasoning": self.reasoning,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            **self.extra,
        }


class AlphaFactorFactory:
    """
    Generates standardized Alpha Factors from UnifiedSignal lists.

    Each signal's related_stocks are expanded into per-symbol factors.
    If a signal has no related_stocks, a sector-level factor is created.
    """

    @staticmethod
    def _source_to_factor_type(source_type: str, event_type: Optional[str] = None) -> FactorType:
        """Maps source_type / event_type to a factor category. event_type takes priority."""
        if event_type:
            et = str(event_type).strip()
            if et in EVENT_TYPE_TO_FACTOR:
                return EVENT_TYPE_TO_FACTOR[et]
        if source_type in SOURCE_TO_FACTOR:
            return SOURCE_TO_FACTOR[source_type]
        return "EVENT_DRIVEN"

    @staticmethod
    def _direction_to_score(direction: str, sentiment_score: Optional[float] = None) -> float:
        """Converts directional assessment to a numeric score."""
        if sentiment_score is not None:
            return max(-1.0, min(1.0, float(sentiment_score)))
        d = (direction or "").strip().lower()
        if d == "bullish":
            return 0.5
        if d == "bearish":
            return -0.5
        return 0.0

    @classmethod
    def from_unified_signals(
        cls,
        signals: List[UnifiedSignal],
        default_confidence: float = 0.7,
    ) -> List[AlphaFactor]:
        """
        Generates Alpha Factors from a list of UnifiedSignals.

        Each signal's related_stocks are expanded into per-symbol factors.
        Signals without related_stocks produce sector-level factors.
        """
        factors: List[AlphaFactor] = []
        for sig in signals:
            factor_type = cls._source_to_factor_type(sig.source_type, sig.event_type)
            score = max(-1.0, min(1.0, sig.sentiment_score))
            conf = sig.confidence
            created = datetime.utcnow()

            if sig.related_stocks:
                for rel in sig.related_stocks:
                    if not rel.code:
                        continue
                    s = cls._direction_to_score(rel.direction, score)
                    adj_score = s * (0.5 + 0.5 * rel.weight) if rel.weight else s
                    factors.append(AlphaFactor(
                        symbol=rel.code,
                        factor_type=factor_type,
                        score=adj_score,
                        confidence=conf * rel.weight if rel.weight else conf,
                        source_type=sig.source_type,
                        event_type=sig.event_type,
                        impact_sectors=list(sig.impact_sectors),
                        impact_duration=sig.impact_duration,
                        reasoning=sig.reasoning,
                        created_at=created,
                        extra={"name": rel.name},
                    ))
            else:
                for sector in sig.impact_sectors or ["market"]:
                    factors.append(AlphaFactor(
                        symbol=f"sector:{sector}",
                        factor_type=factor_type,
                        score=score,
                        confidence=conf,
                        source_type=sig.source_type,
                        event_type=sig.event_type,
                        impact_sectors=list(sig.impact_sectors or []),
                        impact_duration=sig.impact_duration,
                        reasoning=sig.reasoning,
                        created_at=created,
                    ))
        return factors
