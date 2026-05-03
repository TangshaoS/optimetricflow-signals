"""
Unified Signal Data Structures.

Defines the standard schema for multi-source market signals,
used as input for the Alpha Factor pipeline.
"""

from typing import List, Optional, Literal
from dataclasses import dataclass, field


@dataclass
class RelatedStock:
    """A stock associated with a signal, including directional bias and weight."""
    code: str
    name: str
    direction: Literal["bullish", "bearish", "neutral"] = "neutral"
    weight: float = 0.5


@dataclass
class UnifiedSignal:
    """
    Multi-dimensional structured signal output from analyzers.

    This is the standard interface between data collectors/analyzers
    and the Alpha Factor pipeline.

    Attributes:
        source_type: Origin of the signal (e.g., 'news', 'social', 'report').
        event_type: Category of the event (e.g., 'policy', 'earnings', 'breaking').
        sentiment_score: Fine-grained score in [-1, 1].
        confidence: Confidence level in [0, 1].
        impact_sectors: List of affected industry sectors.
        related_stocks: List of stocks affected by this signal.
        impact_duration: Expected duration ('short_term', 'mid_term', 'long_term').
        reasoning: Brief explanation of the signal's rationale.
        signal_direction: Overall directional assessment.
    """
    source_type: Literal["news", "policy", "report", "social", "youtube", "global"]
    sentiment_score: float
    confidence: float = 0.7
    event_type: Optional[str] = None
    impact_sectors: List[str] = field(default_factory=list)
    related_stocks: List[RelatedStock] = field(default_factory=list)
    impact_duration: Optional[str] = None
    reasoning: Optional[str] = None
    signal_direction: Literal["bullish", "bearish", "neutral"] = "neutral"
