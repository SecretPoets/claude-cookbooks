"""Minimal, project-agnostic TimesFM forecasting helper.

TimesFM (https://github.com/google-research/timesfm) is a zero-shot time-series
foundation model: feed it a sequence of numbers and it forecasts forward, with no
training required. This file is a clean starting point you can copy into any
project — it has no dependencies beyond timesfm, numpy, and (optionally) pandas.

Install once per machine (downloads the library + model weights on first use):

    uv pip install "timesfm[torch]" numpy pandas
    # or:  pip install "timesfm[torch]" numpy pandas

Use as a library:

    from timesfm_quickstart import load_model, forecast
    model = load_model()
    point, low, high = forecast(model, my_numbers, horizon=12)

Or from the command line on a CSV (one numeric column = the history):

    python timesfm_quickstart.py sales.csv --column revenue --horizon 12
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

import numpy as np

# Default checkpoint: the 200M-parameter TimesFM 2.5 model with a quantile head.
DEFAULT_CHECKPOINT = "google/timesfm-2.5-200m-pytorch"


def load_model(checkpoint: str = DEFAULT_CHECKPOINT, max_horizon: int = 64):
    """Load and compile a TimesFM model once, then reuse it for many forecasts."""
    import timesfm
    import torch

    torch.set_float32_matmul_precision("high")
    model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(checkpoint)
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
    return model


def forecast(
    model,
    history: Sequence[float],
    horizon: int = 12,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Forecast `horizon` steps ahead from a 1-D numeric `history`.

    Returns (point_forecast, lower_band, upper_band), each of length `horizon`.
    The bands are the lowest/highest quantiles TimesFM produces — a rough
    prediction interval, not a guarantee.
    """
    series = np.asarray(history, dtype=float)
    if series.ndim != 1 or series.size < 2:
        raise ValueError("history must be a 1-D sequence with at least 2 points")

    point, quantiles = model.forecast(horizon=horizon, inputs=[series])
    point_forecast = np.asarray(point[0])

    q = np.asarray(quantiles[0])
    if q.ndim == 2 and q.shape[1] >= 2:
        lower, upper = q[:, 0], q[:, -1]
    else:
        lower = upper = point_forecast
    return point_forecast, lower, upper


def _load_csv_column(path: str, column: str | None) -> np.ndarray:
    import pandas as pd

    df = pd.read_csv(path)
    if column is not None:
        values = df[column]
    else:
        numeric = df.select_dtypes("number")
        if numeric.shape[1] == 0:
            raise ValueError("no numeric column found; pass --column explicitly")
        values = numeric.iloc[:, -1]  # last numeric column by default
    return values.to_numpy(dtype=float)


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
