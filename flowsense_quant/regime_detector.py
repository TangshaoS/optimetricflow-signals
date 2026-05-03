"""
Market Regime Detection: Three-state (Bull / Bear / Shock) rule engine.

Used to rescale factor-type weights during signal fusion. Implementation is a small
MA-slope + volume-confirmation heuristic on **public** index daily bars (akshare).

Open-source note: default multi-index inputs are not disclosed here; callers pass
explicit ``indices=`` for weighted mode. The single-index helpers keep a minimal
default suitable for demos only.
"""

from dataclasses import dataclass
from typing import Optional, Literal, List, Tuple, Sequence

import pandas as pd

try:
    import akshare as ak
except ImportError:
    ak = None


RegimeType = Literal["BULL", "BEAR", "SHOCK"]


@dataclass
class RegimeResult:
    """Current market regime and metadata."""
    regime: RegimeType
    short_ma: Optional[float] = None
    long_ma: Optional[float] = None
    volatility: Optional[float] = None
    metadata: Optional[dict] = None


def fetch_index_daily(
    symbol: str = "000001",
    market: str = "sh",
    lookback_days: int = 60,
) -> Optional[pd.DataFrame]:
    """
    Fetches daily index K-line data via akshare.

    Args:
        symbol: Index code (e.g., '000001' for Shanghai Composite).
        market: Market prefix ('sh' or 'sz').
        lookback_days: Number of trading days to return.

    Returns:
        DataFrame with 'date', 'close', and optionally 'volume' columns.
    """
    if not ak:
        return None
    try:
        full_symbol = f"{market}{symbol}"
        df = ak.stock_zh_index_daily(symbol=full_symbol)
        if df is None or df.empty:
            return None
        df = df.copy()
        if "date" not in df.columns and "日期" in df.columns:
            df["date"] = pd.to_datetime(df["日期"])
        elif "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        if "close" not in df.columns and "收盘" in df.columns:
            df["close"] = pd.to_numeric(df["收盘"], errors="coerce")
        if "volume" not in df.columns and "成交量" in df.columns:
            df["volume"] = pd.to_numeric(df["成交量"], errors="coerce")
        df = df.dropna(subset=["date", "close"]).sort_values("date")
        return df.tail(lookback_days)
    except Exception:
        return None


class RegimeDetector:
    """
    Three-state rule engine for market regime identification.

    Uses moving average crossover + realized volatility + volume ratio
    to classify the current market as BULL, BEAR, or SHOCK.

    Example:
        >>> detector = RegimeDetector()
        >>> result = detector.get_current_regime()
        >>> print(result.regime)  # 'BULL', 'BEAR', or 'SHOCK'
    """

    def __init__(
        self,
        short_window: int = 5,
        long_window: int = 20,
        volatility_window: int = 20,
        bull_threshold: float = 0.002,
        bear_threshold: float = -0.002,
    ):
        self.short_window = short_window
        self.long_window = long_window
        self.volatility_window = volatility_window
        self.bull_threshold = bull_threshold
        self.bear_threshold = bear_threshold

    def _compute_features(self, df: pd.DataFrame) -> dict:
        """Computes MA crossover slope, volatility, and volume ratio."""
        if df is None or len(df) < self.long_window:
            return {}
        series = df["close"]
        short_ma = series.rolling(self.short_window, min_periods=1).mean().iloc[-1]
        long_ma = series.rolling(self.long_window, min_periods=1).mean().iloc[-1]
        ret = series.pct_change().dropna()
        vol = ret.tail(self.volatility_window).std() if len(ret) >= self.volatility_window else 0.0

        if long_ma and long_ma != 0:
            slope_proxy = (short_ma - long_ma) / long_ma
        else:
            slope_proxy = 0.0

        vol_ratio = 1.0
        if "volume" in df.columns:
            v_series = df["volume"]
            v_short = v_series.tail(self.short_window).mean()
            v_long = v_series.tail(self.long_window).mean()
            if v_long > 0:
                vol_ratio = float(v_short / v_long)

        return {
            "short_ma": float(short_ma),
            "long_ma": float(long_ma),
            "volatility": float(vol) if pd.notna(vol) else 0.0,
            "slope_proxy": slope_proxy,
            "volume_ratio": vol_ratio,
        }

    def detect_from_dataframe(
        self, df: pd.DataFrame, date_col: str = "date", close_col: str = "close"
    ) -> RegimeResult:
        """Detects regime from a DataFrame with date and close columns."""
        if df is None or df.empty or close_col not in df.columns:
            return RegimeResult(regime="SHOCK", metadata={"reason": "no_data"})

        df = df.sort_values(date_col).copy()
        features = self._compute_features(df)
        if not features:
            return RegimeResult(regime="SHOCK", metadata={"reason": "insufficient_data"})

        slope = features["slope_proxy"]
        v_ratio = features.get("volume_ratio", 1.0)

        # Volume-confirmed trend: amplify slope when volume is expanding
        adjusted_slope = slope * (1.2 if v_ratio > 1.1 else 0.8)

        if adjusted_slope >= self.bull_threshold:
            regime: RegimeType = "BULL"
        elif adjusted_slope <= self.bear_threshold:
            regime = "BEAR"
        else:
            regime = "SHOCK"

        return RegimeResult(
            regime=regime,
            short_ma=features.get("short_ma"),
            long_ma=features.get("long_ma"),
            volatility=features.get("volatility"),
            metadata={"slope_proxy": slope, "volume_ratio": v_ratio, "adjusted_slope": adjusted_slope},
        )

    def get_current_regime_weighted(
        self,
        indices: Optional[Sequence[Tuple[str, str, float]]] = None,
        lookback_days: int = 60,
    ) -> RegimeResult:
        """
        Multi-index weighted regime detection.

        Pass ``indices`` as ``(symbol, market, weight)`` rows, e.g.
        ``[("000001", "sh", 1.0)]`` for a single benchmark. Weights are normalized
        after dropping failed fetches. If ``indices`` is omitted, uses one liquid
        broad benchmark only (OSS placeholder — override for your basket).
        """
        if indices is None:
            indices = [("000001", "sh", 1.0)]
        total_score = 0.0
        total_weight = 0.0
        valid_meta = {}

        for symbol, market, weight in indices:
            df = fetch_index_daily(symbol=symbol, market=market, lookback_days=lookback_days)
            if df is not None and not df.empty:
                res = self.detect_from_dataframe(df, date_col="date", close_col="close")
                score = 1.0 if res.regime == "BULL" else (-1.0 if res.regime == "BEAR" else 0.0)
                total_score += score * weight
                total_weight += weight
                valid_meta[f"{market}{symbol}"] = res.regime

        if total_weight == 0:
            return RegimeResult(regime="SHOCK", metadata={"reason": "all_fetch_failed"})

        final_score = total_score / total_weight
        if final_score >= 0.3:
            final_regime = "BULL"
        elif final_score <= -0.3:
            final_regime = "BEAR"
        else:
            final_regime = "SHOCK"

        return RegimeResult(
            regime=final_regime,
            metadata={"weighted_score": final_score, "details": valid_meta},
        )

    def get_current_regime(
        self,
        index_symbol: str = "000001",
        index_market: str = "sh",
        lookback_days: int = 60,
    ) -> RegimeResult:
        """Single-index regime detection (backward compatible)."""
        return self.get_current_regime_weighted(
            [(index_symbol, index_market, 1.0)], lookback_days
        )
