# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-notebook capstone project doing customer segmentation on the UCI Online Retail dataset (`data.csv`, ~541k transaction rows). All code lives in `capstone.ipynb`. There is no `requirements.txt`, no test suite, and no build step.

## Environment

- `.venv/` is a Python 3.14 virtualenv but is **empty** (only `pip` installed). The notebook itself declares Python 3.12 in its kernel metadata. Before running, install the runtime dependencies:
  ```
  source .venv/bin/activate
  pip install pandas numpy matplotlib seaborn scikit-learn jupyter
  ```
- Launch the notebook with `jupyter notebook capstone.ipynb` (or open in PyCharm — `.idea/` is checked in).

## Known bug to watch for

Cell 4 reads the dataset with an absolute path: `pd.read_csv('/data.csv', ...)`. This will fail on any machine where `data.csv` is not at the filesystem root. If you touch this cell, change it to a relative path (`'data.csv'`) rather than re-introducing the absolute one.

## Notebook architecture

The notebook is a linear pipeline — cells must execute top-to-bottom. The flow:

1. **Load + clean** (cells 4–8): drop rows with null `CustomerID`, filter out returns (`Quantity <= 0`), parse `InvoiceDate`, derive `TotalPrice = Quantity * UnitPrice`.
2. **RFM feature engineering** (cell 12): per-customer aggregation into `Recency` (days since last purchase, anchored to `max(InvoiceDate) + 1 day`), `Frequency` (invoice count), `Monetary` (sum of `TotalPrice`). This collapses ~350k filtered transactions to ~4,300 customer rows — the `rfm` DataFrame is the central object for everything downstream.
3. **Scaling** (cell 14): `log1p` first to tame the skew from high-value customers, then `StandardScaler`. The convention is **`rfm_scaled` for modeling, raw `rfm` for interpretation** — preserve this split when adding analysis.
4. **K selection** (cells 16, 18): elbow (WCSS) + silhouette scores for K=2..9. The notebook lands on K=4.
5. **K-Means + PCA viz** (cells 20, 22): clusters assigned on scaled data; PCA(2) is for visualization only, not for clustering.
6. **Churn model** (cell 24): a derived binary label `Churn = (Recency > 90)` fed into `LogisticRegression`. Note this label is essentially a thresholded version of one of the input features, so the high reported scores are largely tautological — flag this if asked to extend the model.

## Conventions when editing the notebook

- Random state is `42` everywhere — keep it that way for reproducibility across reruns.
- `KMeans` uses `n_init=10` in the final fit (cell 20) but defaults elsewhere; if you change one, change them together.
- Markdown cells explain each step in bullet form for a non-technical reader — match that style when adding new sections.
