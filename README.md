# Customer Segmentation on E-Commerce Data

Customer segmentation on the [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail) dataset using RFM features + K-Means, with churn prediction via logistic regression.

The project has three pieces:

- **`capstone.ipynb`** — the exploratory notebook (the original capstone deliverable).
- **`backend/`** — a FastAPI service that runs the same RFM + K-Means + churn pipeline on startup and exposes the results as JSON.
- **`frontend/`** — a Vite + React + shadcn/ui single-page dashboard that reads from the backend.

## Dataset

`data.csv` — ~541k transactions from a UK-based online retailer (Dec 2010 – Dec 2011). Columns: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`.

## Setup

Python deps for both the notebook and backend share one virtualenv at the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install matplotlib seaborn jupyter  # only needed for the notebook
```

### Without a virtualenv

If you'd rather skip the venv, install the same packages into your user site-packages:

```bash
pip install --user -r backend/requirements.txt
pip install --user matplotlib seaborn jupyter  # only needed for the notebook
```

On newer macOS / Debian-based systems where the system Python is PEP 668 "externally managed", either use a managed Python (Homebrew, pyenv, conda) or add `--break-system-packages` to the commands above — though a venv is still the cleaner option.

Wherever you install them, the "Running" commands below assume `python` resolves to that interpreter. Drop the `../.venv/bin/` prefix from the uvicorn command if you're not using the venv.

Frontend deps:

```bash
cd frontend
yarn install
```

## Running

### Notebook

```bash
jupyter notebook capstone.ipynb
```

Run cells top-to-bottom — the pipeline is linear and each step depends on the previous.

> **Note:** cell 4 currently reads `pd.read_csv('/data.csv', ...)` (absolute path). Change it to `'data.csv'` to load the file from the project directory.

### Backend

From the `backend/` directory:

```bash
../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The pipeline runs once on startup (a few seconds) and loads the resulting `rfm` DataFrame into memory. Swagger UI at <http://127.0.0.1:8000/docs>.

Endpoints:

- `GET /summary` — totals (customers, revenue, churn rate, cluster count)
- `GET /clusters` — per-cluster stats (size, mean RFM, churn rate)
- `GET /customers?cluster=&limit=&offset=` — paginated customer list

### Frontend

From the `frontend/` directory, with the backend already running:

```bash
yarn dev
```

Dashboard at <http://localhost:5173>. CORS is open to that origin.

## Pipeline (notebook + backend share this)

1. **Load + clean** — drop null `CustomerID`, filter out returns, derive `TotalPrice`.
2. **RFM features** — collapse transactions to one row per customer with `Recency`, `Frequency`, `Monetary`.
3. **Scaling** — `log1p` + `StandardScaler` to handle the heavy skew from high-value customers.
4. **Cluster selection** — elbow (WCSS) + silhouette across K=2..9; lands on K=4.
5. **K-Means** — clusters fit on scaled RFM, visualized in 2D via PCA.
6. **Churn model** — binary label `Churn = (Recency > 90 days)`, fit with logistic regression on raw RFM.

## Caveats

- The churn label is derived from `Recency`, which is also a model input — high reported scores are largely a tautology, not predictive power. The dashboard's churn probability distribution will look bimodal at 0 and 1 for the same reason.
- PCA is used for visualization only; clustering happens in the full scaled-RFM space.
