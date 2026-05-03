# flowsense-quant

Small Python library for turning structured multi-source signals (news, social, policy, etc.) into per-symbol factor rows and a single fused score, with an optional **market regime** hook (bull / bear / shock) that rescales factor-type weights before fusion.

Regime detection uses public index daily bars via [akshare](https://github.com/akfamily/akshare). **Numeric defaults in code are illustrative** (toy tables and a single placeholder benchmark for weighted regime). They are not production IC/decay-tuned values. Treat the published API as **schema + algorithm shape**; bring your own weights and index basket.

## Scope

**In this repository**

- `UnifiedSignal` / `RelatedStock` schemas
- `AlphaFactorFactory`: map signals → `AlphaFactor` rows (event / sentiment / flow / technical buckets)
- `SignalAggregator`: weighted average by factor type, with regime-dependent multipliers
- `RegimeDetector`: MA slope + volatility + volume ratio on major CN indices

**Not included** (handled in the OptimetricFlow product, not shipped here)

- Factor decay, rolling IC, or automatic weight updates from realized performance
- Live data collectors, alerting, or dashboard
- LLM prompt chains / parsers for raw text → `UnifiedSignal`
- Execution, portfolio construction, or brokerage integration

This split is intentional: the OSS layer is a **contract and a reference fusion flow** for SEO and integrations; it does not bundle proprietary alpha or operational pipelines.

### Parameters (what to override in production)

| Area | In this repo | In a real deployment |
|------|----------------|----------------------|
| Base factor-type weights | `ILLUSTRATIVE_BASE_WEIGHTS` in `signal_aggregator.py` | Your calibrated / rolling estimates |
| Regime multipliers | `ILLUSTRATIVE_REGIME_MULTIPLIERS` | Your regime-conditioned schedule |
| Weighted regime indices | Default is **one** placeholder benchmark; pass ``indices=[(symbol, market, weight), ...]`` to ``get_current_regime_weighted`` | Your chosen universe and weights |

Do not treat shipped literals as a recipe for OptimetricFlow’s internal tuning.

### Fusion (pseudocode)

No reliance on specific numbers from this README:

```
for each symbol:
    group factors by factor_type
    for each factor_type with rows:
        avg_score = confidence-weighted mean of scores for that type
    regime_weights = normalize(base_weight[type] * regime_multiplier[regime][type])
    fused[symbol] = sum(avg_score[type] * regime_weights[type]) / sum(regime_weights used)
```

Clip to \[-1, 1\], then sort symbols by `|fused|`.

## Requirements

- Python 3.8+
- `numpy`, `pandas`, `akshare` (declared in `pyproject.toml`)

## Install

From a clone of this repo (at the repository root):

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install .
```

If `pip install .` fails on your machine, you can run the example without installing by setting `PYTHONPATH` to the repo root (see below).

PyPI package name is `flowsense-quant` if/when published; until then, install from Git or local tree.

## Run the bundled example

The example builds fake structured signals, expands to factors, and fuses under a fixed regime (no network):

```bash
# From repository root, after `pip install .`:
python examples/alpha_signal_pipeline.py

# Or without installing:
PYTHONPATH=. python examples/alpha_signal_pipeline.py
```

You should see step-by-step prints: input signals → per-symbol factors → fused scores sorted by magnitude.

## Regime detection (optional, needs network)

`get_current_regime()` uses one public index. `get_current_regime_weighted()` takes an explicit `indices` list; if you omit it, the library uses a **single** demo benchmark (not a statement about which indices you should use in product). Requires outbound network and a working akshare install. If fetch fails, the result explains why in `metadata`.

```python
from flowsense_quant import RegimeDetector

d = RegimeDetector()
# explicit basket (example shape only)
r = d.get_current_regime_weighted(indices=[("000001", "sh", 0.6), ("399006", "sz", 0.4)])
print(r.regime, r.metadata)
```

## License

MIT — see [LICENSE](LICENSE).

## Links

- [OptimetricFlow](https://optimetricflow.cn)
- [optimetricflow.com](https://optimetricflow.com) (launching later)
