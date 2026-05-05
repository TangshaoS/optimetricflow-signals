# Quick Start Guide 🚀

This guide will walk you through the basic usage of **OptimetricFlow Signals**.

## 1. Installation

Ensure you have Python 3.8+ installed.

```bash
pip install flowsense-quant
```

*(Note: If not yet on PyPI, install from source as shown in the main README.)*

## 2. Basic Workflow

The core of the library is transforming raw signals into fused alpha scores.

### Step 1: Define Signals

Create structured signals using the `UnifiedSignal` schema.

```python
from flowsense_quant import UnifiedSignal, RelatedStock

signal = UnifiedSignal(
    source_type="news",
    event_type="policy",
    sentiment_score=0.8,
    confidence=0.9,
    signal_direction="bullish",
    related_stocks=[
        RelatedStock(code="002049", name="Unigroup", weight=1.0)
    ]
)
```

### Step 2: Convert to Factors

Use the `AlphaFactorFactory` to map these signals to standardized factors.

```python
from flowsense_quant import AlphaFactorFactory

factors = AlphaFactorFactory.from_unified_signals([signal])
```

### Step 3: Detect Market Regime

Adjust your strategy based on current market conditions.

```python
from flowsense_quant import RegimeDetector

detector = RegimeDetector()
regime = detector.get_current_regime() # Default uses SSE Composite
```

### Step 4: Signal Fusion

Aggregate multiple factors into a single score per symbol.

```python
from flowsense_quant import SignalAggregator

aggregator = SignalAggregator()
fused_results = aggregator.aggregate(factors, regime=regime)

for result in fused_results:
    print(f"Symbol: {result.symbol}, Score: {result.fused_score}")
```

## 3. Next Steps

- Explore the `examples/` directory for full pipeline demonstrations.
- Visit [optimetricflow.cn](https://optimetricflow.cn) for the enterprise version with live data and real-time alerts.
