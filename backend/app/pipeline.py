from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data.csv"
CHURN_THRESHOLD_DAYS = 90
N_CLUSTERS = 4
RANDOM_STATE = 42
ELBOW_K_RANGE = range(1, 10)


@dataclass
class PipelineResult:
    rfm: pd.DataFrame
    elbow: list[tuple[int, float]]
    scaler: StandardScaler
    kmeans: KMeans
    pca: PCA
    min_date: pd.Timestamp
    max_date: pd.Timestamp


def build(data_path: Path | None = None) -> PipelineResult:
    """Run the segmentation pipeline and return the per-customer table plus
    the elbow curve (WCSS per K) used to motivate the cluster count."""
    path = data_path or Path(os.environ.get("DATA_CSV", DEFAULT_DATA_PATH))

    df = pd.read_csv(path, encoding="ISO-8859-1")
    df = df.dropna(subset=["CustomerID"])
    df = df[df["Quantity"] > 0]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]

    snapshot_date = df["InvoiceDate"].max() + pd.Timedelta(days=1)
    rfm = df.groupby("CustomerID").agg({
        "InvoiceDate": lambda x: (snapshot_date - x.max()).days,
        "InvoiceNo": "count",
        "TotalPrice": "sum",
    })
    rfm.columns = ["Recency", "Frequency", "Monetary"]

    scaler = StandardScaler()
    rfm_scaled = scaler.fit_transform(np.log1p(rfm))

    elbow: list[tuple[int, float]] = []
    for k in ELBOW_K_RANGE:
        model_k = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        model_k.fit(rfm_scaled)
        elbow.append((k, float(model_k.inertia_)))

    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
    rfm["Cluster"] = kmeans.fit_predict(rfm_scaled)

    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    rfm[["PCA1", "PCA2"]] = pca.fit_transform(rfm_scaled)

    return PipelineResult(
        rfm=rfm.reset_index(),
        elbow=elbow,
        scaler=scaler,
        kmeans=kmeans,
        pca=pca,
        min_date=df["InvoiceDate"].min(),
        max_date=df["InvoiceDate"].max(),
    )


def compute_churn(rfm_base: pd.DataFrame, threshold: int) -> pd.DataFrame:
    """Return rfm_base with Churn and Churn_Prob columns added for the given threshold."""
    rfm = rfm_base.copy()
    rfm["Churn"] = (rfm["Recency"] > threshold).astype(int)
    features = rfm[["Recency", "Frequency", "Monetary"]]
    target = rfm["Churn"]
    x_train, _, y_train, _ = train_test_split(
        features, target, test_size=0.2, random_state=RANDOM_STATE, stratify=target,
    )
    model = LogisticRegression()
    model.fit(x_train, y_train)
    rfm["Churn_Prob"] = model.predict_proba(features)[:, 1]
    return rfm
