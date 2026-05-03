"""
Example: From News Signals to Alpha Factors — Complete Pipeline

This script demonstrates the core flowsense-quant workflow:
1. Create structured signals from raw news data
2. Convert signals to standardized Alpha Factors
3. Aggregate factors into per-symbol fused scores
"""

from flowsense_quant import (
    UnifiedSignal,
    RelatedStock,
    AlphaFactorFactory,
    SignalAggregator,
    RegimeDetector,
    RegimeResult,
)


def main():
    # ── Step 1: Simulate structured signals from multiple sources ──

    signals = [
        UnifiedSignal(
            source_type="news",
            event_type="policy",
            sentiment_score=0.7,
            confidence=0.85,
            signal_direction="bullish",
            impact_sectors=["Semiconductor", "AI"],
            related_stocks=[
                RelatedStock(code="002049", name="Unigroup", direction="bullish", weight=0.8),
                RelatedStock(code="603986", name="GigaDevice", direction="bullish", weight=0.6),
            ],
            reasoning="Government announces major semiconductor subsidy package",
        ),
        UnifiedSignal(
            source_type="social",
            event_type="sentiment",
            sentiment_score=-0.4,
            confidence=0.6,
            signal_direction="bearish",
            impact_sectors=["Real Estate"],
            related_stocks=[
                RelatedStock(code="001979", name="China Vanke", direction="bearish", weight=0.7),
            ],
            reasoning="Social media buzz indicates rising concerns about property market",
        ),
        UnifiedSignal(
            source_type="news",
            event_type="earnings",
            sentiment_score=0.5,
            confidence=0.9,
            signal_direction="bullish",
            impact_sectors=["Semiconductor"],
            related_stocks=[
                RelatedStock(code="603986", name="GigaDevice", direction="bullish", weight=0.9),
            ],
            reasoning="GigaDevice Q3 earnings beat expectations by 20%",
        ),
    ]

    print("=" * 60)
    print("Step 1: Created", len(signals), "structured signals")
    for i, sig in enumerate(signals):
        print(f"  [{i+1}] {sig.source_type}/{sig.event_type}: "
              f"score={sig.sentiment_score}, stocks={[r.code for r in sig.related_stocks]}")

    # ── Step 2: Convert to standardized Alpha Factors ──

    factors = AlphaFactorFactory.from_unified_signals(signals)

    print("\n" + "=" * 60)
    print(f"Step 2: Generated {len(factors)} Alpha Factors")
    for f in factors:
        print(f"  {f.symbol} | {f.factor_type:14s} | score={f.score:+.3f} | conf={f.confidence:.2f} | {f.reasoning[:50]}...")

    # ── Step 3: Fuse factors per symbol ──

    # Use a simulated regime (in production, use RegimeDetector.get_current_regime())
    regime = RegimeResult(regime="BULL")

    aggregator = SignalAggregator()
    fused = aggregator.aggregate(factors, regime=regime)

    print("\n" + "=" * 60)
    print(f"Step 3: Fused Signals (regime={regime.regime})")
    print(f"{'Symbol':>20s} | {'Score':>8s} | {'#Factors':>8s} | Breakdown")
    print("-" * 80)
    for fs in fused:
        breakdown = ", ".join(
            f"{c.factor_type}:{c.weighted_score:+.3f}" for c in fs.contributions
        )
        print(f"{fs.symbol:>20s} | {fs.fused_score:+8.4f} | {fs.n_factors:>8d} | {breakdown}")

    print("\n" + "=" * 60)
    print("Pipeline complete. Top signal:", fused[0].symbol if fused else "N/A")
    print("Product (live data, IC-weighting, alerts): https://optimetricflow.cn")


if __name__ == "__main__":
    main()
