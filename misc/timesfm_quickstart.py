"""Minimal, project-agnostic TimesFM forecasting helper.

TimesFM (https://github.com/google-research/timesfm) is a zero-shot time-series
foundation model: feed it a sequence of numbers and it forecasts forward, with no
training required. This file is a clean starting point you can copy into any
project — it has no dependencies beyond timesfm, numpy, and (optionally) pandas.

It supports BOTH released APIs, because `pip install timesfm` may give you either
generation depending on your platform:
  * 2.5  -> timesfm.TimesFM_2p5_200M_torch  (checkpoint google/timesfm-2.5-200m-pytorch)
  * 1.x  -> timesfm.TimesFm                 (checkpoint google/timesfm-1.0-200m-pytorch)
`load_model()` auto-detects which one is installed.

Install once per machine (downloads the library; model weights download on first use
and require network access to Hugging Face):

    uv pip install "timesfm[torch]" numpy pandas
    # or:  pip install "timesfm[torch]" numpy pandas

Use as a library — point at any data and forecast it:

    from timesfm_quickstart import apply_timesfm
    point, low, high = apply_timesfm("sales.csv", value_column="revenue", horizon=12)
    point, low, high = apply_timesfm(my_dataframe, value_column="rent")
    point, low, high = apply_timesfm([100, 102, 105, ...])  # a plain list/array

Or manage the model yourself for repeated calls:

    from timesfm_quickstart import load_model, forecast
    model = load_model()
    point, low, high = forecast(model, my_numbers, horizon=12)

Or from the command line on a CSV (one numeric column = the history):

    python timesfm_quickstart.py timesfm_example.csv --column revenue --horizon 12
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

CHECKPOINT_2P5 = "google/timesfm-2.5-200m-pytorch"
CHECKPOINT_1X = "google/timesfm-1.0-200m-pytorch"


class _Forecaster:
    """Thin wrapper that hides the API differences between TimesFM 2.5 and 1.x."""

    def __init__(self, model, api: str, max_horizon: int):
        self._model = model
        self._api = api  # "2.5" or "1.x"
        self._max_horizon = max_horizon

    def forecast(
        self, history: Sequence[float], horizon: int = 12
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        series = np.asarray(history, dtype=float)
        if series.ndim != 1 or series.size < 2:
            raise ValueError("history must be a 1-D sequence with at least 2 points")
        if horizon > self._max_horizon:
            raise ValueError(f"horizon {horizon} exceeds max_horizon {self._max_horizon}")

        if self._api == "2.5":
            point, quantiles = self._model.forecast(horizon=horizon, inputs=[series])
            point_forecast = np.asarray(point[0])[:horizon]
            q = np.asarray(quantiles[0])
            if q.ndim == 2 and q.shape[1] >= 2:
                lower, upper = q[:horizon, 0], q[:horizon, -1]
            else:
                lower = upper = point_forecast
        else:  # 1.x
            point, quantiles = self._model.forecast([series], freq=[0])
            point_forecast = np.asarray(point[0])[:horizon]
            q = np.asarray(quantiles[0])  # shape: (horizon, num_quantiles); col 0 is the mean
            if q.ndim == 2 and q.shape[1] >= 3:
                lower, upper = q[:horizon, 1], q[:horizon, -1]
            else:
                lower = upper = point_forecast
        return point_forecast, lower, upper


def load_model(max_horizon: int = 64) -> _Forecaster:
    """Load and compile a TimesFM model once, then reuse it for many forecasts.

    Auto-detects the installed API generation (2.5 preferred, else 1.x).
    """
    import timesfm

    if hasattr(timesfm, "TimesFM_2p5_200M_torch"):
        import torch

        torch.set_float32_matmul_precision("high")
        model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(CHECKPOINT_2P5)
        model.compile(
            timesfm.ForecastConfig(
                max_context=512,
                max_horizon=max_horizon,
                normalize_inputs=True,
                use_continuous_quantile_head=True,  # gives prediction intervals
                force_flip_invariance=True,
                fix_quantile_crossing=True,
            )
        )
        return _Forecaster(model, "2.5", max_horizon)

    if hasattr(timesfm, "TimesFm"):
        model = timesfm.TimesFm(
            hparams=timesfm.TimesFmHparams(
                backend="cpu",
                per_core_batch_size=32,
                horizon_len=max_horizon,
                context_len=512,
            ),
            checkpoint=timesfm.TimesFmCheckpoint(huggingface_repo_id=CHECKPOINT_1X),
        )
        return _Forecaster(model, "1.x", max_horizon)

    raise ImportError(
        "Installed `timesfm` exposes neither TimesFM_2p5_200M_torch nor TimesFm. "
        "Try: pip install --upgrade 'timesfm[torch]'"
    )


def forecast(
    model: _Forecaster,
    history: Sequence[float],
    horizon: int = 12,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Forecast `horizon` steps ahead from a 1-D numeric `history`.

    Returns (point_forecast, lower_band, upper_band), each of length `horizon`.
    The bands are the lowest/highest quantiles TimesFM produces — a rough
    prediction interval, not a guarantee.
    """
    return model.forecast(history, horizon=horizon)


@lru_cache(maxsize=4)
def get_model(max_horizon: int = 64) -> _Forecaster:
    """Cached `load_model` — repeated calls reuse the same loaded model."""
    return load_model(max_horizon=max_horizon)


def apply_timesfm(
    data: Any,
    value_column: str | None = None,
    horizon: int = 12,
    model: _Forecaster | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Point at some data and forecast it. Accepts a CSV path, a pandas
    DataFrame/Series, or any 1-D sequence of numbers.

    For tabular inputs, `value_column` selects the series (defaults to the last
    numeric column). The model is loaded once and cached unless you pass your own.

    Returns (point_forecast, lower_band, upper_band), each of length `horizon`.
    """
    series = _coerce_to_series(data, value_column)
    if model is None:
        model = get_model(max_horizon=max(horizon, 1))
    return forecast(model, series, horizon=horizon)


def _pick_numeric(df, column: str | None) -> np.ndarray:
    if column is not None:
        values = df[column]
    else:
        numeric = df.select_dtypes("number")
        if numeric.shape[1] == 0:
            raise ValueError("no numeric column found; pass value_column explicitly")
        values = numeric.iloc[:, -1]  # last numeric column by default
    return values.to_numpy(dtype=float)


def _coerce_to_series(data: Any, value_column: str | None) -> np.ndarray:
    if isinstance(data, (str, Path)):
        import pandas as pd

        return _pick_numeric(pd.read_csv(data), value_column)

    # Detect pandas DataFrame/Series by attribute, without importing pandas eagerly.
    if hasattr(data, "select_dtypes"):  # DataFrame
        return _pick_numeric(data, value_column)
    if hasattr(data, "to_numpy") and not isinstance(data, np.ndarray):  # Series
        return data.to_numpy(dtype=float)

    return np.asarray(data, dtype=float).ravel()


def _load_csv_column(path: str, column: str | None) -> np.ndarray:
    import pandas as pd

    return _pick_numeric(pd.read_csv(path), column)


def main() -> None:
    parser = argparse.ArgumentParser(description="Forecast a CSV time series with TimesFM.")
    parser.add_argument("csv", help="Path to a CSV file containing the history.")
    parser.add_argument("--column", help="Numeric column to forecast (default: last numeric).")
    parser.add_argument("--horizon", type=int, default=12, help="Steps to forecast (default: 12).")
    args = parser.parse_args()

    history = _load_csv_column(args.csv, args.column)
    model = load_model(max_horizon=max(args.horizon, 1))
    point_forecast, lower, upper = forecast(model, history, horizon=args.horizon)

    print(f"History: {history.size} points | forecasting {args.horizon} steps ahead\n")
    print(f"{'Step':<6}{'Forecast':<14}{'Low':<14}{'High':<14}")
    print("-" * 48)
    for i in range(args.horizon):
        print(f"{i + 1:<6}{point_forecast[i]:<14.4f}{lower[i]:<14.4f}{upper[i]:<14.4f}")


if __name__ == "__main__":
    main()
