from __future__ import annotations

import os
import hashlib
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
    raw_df: pd.DataFrame


def build(data_path: Path | None = None) -> PipelineResult:
    """Run the segmentation pipeline and return the per-customer table plus
    the elbow curve (WCSS per K) used to motivate the cluster count."""
    path = data_path or Path(os.environ.get("DATA_CSV", DEFAULT_DATA_PATH))

    raw_data = pd.read_csv(path, encoding="ISO-8859-1")
    df = pd.DataFrame(raw_data.dropna(subset=["CustomerID"]))
    df = pd.DataFrame(df[df["Quantity"] > 0])
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]

    snapshot_date = pd.Timestamp.now()
    rfm = pd.DataFrame(df.groupby("CustomerID").agg({
        "InvoiceDate": "max",
        "InvoiceNo": "nunique",
        "TotalPrice": "sum",
    }))
    recency = (snapshot_date - pd.to_datetime(rfm["InvoiceDate"])) / pd.Timedelta(days=1)
    rfm["InvoiceDate"] = pd.Series(recency, index=rfm.index).astype(int)
    rfm.columns = pd.Index(["Recency", "Frequency", "Monetary"])

    scaler = StandardScaler()
    rfm_scaled = scaler.fit_transform(np.log1p(rfm))

    elbow: list[tuple[int, float]] = []
    for k in ELBOW_K_RANGE:
        model_k = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        model_k.fit(rfm_scaled)
        elbow.append((k, model_k.inertia_))

    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
    rfm["Cluster"] = kmeans.fit_predict(rfm_scaled)

    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    rfm[["PCA1", "PCA2"]] = pca.fit_transform(rfm_scaled)

    # Get email and password mapping from df and join
    emails_passwords = pd.DataFrame(df.groupby("CustomerID").agg({
        "Email": "first",
        "Password": "first",
    }))
    rfm = rfm.join(emails_passwords)

    return PipelineResult(
        rfm=pd.DataFrame(rfm.reset_index()),
        elbow=elbow,
        scaler=scaler,
        kmeans=kmeans,
        pca=pca,
        min_date=pd.Timestamp(df["InvoiceDate"].min()),
        max_date=pd.Timestamp(df["InvoiceDate"].max()),
        raw_df=df,
    )


def compute_rfm_for_threshold(
    df: pd.DataFrame,
    threshold: int,
    scaler: StandardScaler,
    kmeans: KMeans,
    pca: PCA,
    model: LogisticRegression,
) -> pd.DataFrame:
    """Compute threshold-window specific RFM, Cluster, and Churn metrics."""
    snapshot_date = pd.Timestamp.now()
    
    # Filter transactions within threshold window
    inv_dates = pd.to_datetime(df["InvoiceDate"])
    days_series = (snapshot_date - inv_dates) / pd.Timedelta(days=1)
    window_mask = days_series <= threshold
    df_window = pd.DataFrame(df[window_mask])
    
    # Group by CustomerID for window Frequency and Monetary
    window_rfm = pd.DataFrame(df_window.groupby("CustomerID").agg({
        "InvoiceNo": "nunique",
        "TotalPrice": "sum",
    }))
    window_rfm.columns = pd.Index(["Frequency", "Monetary"])
    
    # Base recency across all time for each customer
    base_rfm = pd.DataFrame(df.groupby("CustomerID").agg({
        "InvoiceDate": "max",
        "Email": "first",
        "Password": "first",
    }))
    recency = (snapshot_date - pd.to_datetime(base_rfm["InvoiceDate"])) / pd.Timedelta(days=1)
    base_rfm["Recency"] = pd.Series(recency, index=base_rfm.index).astype(int)
    base_rfm = base_rfm[["Recency", "Email", "Password"]]
    
    rfm = base_rfm.join(window_rfm, how="left")
    rfm["Frequency"] = rfm["Frequency"].fillna(0).astype(int)
    rfm["Monetary"] = rfm["Monetary"].fillna(0.0).astype(float)
    
    # Predict Cluster
    rfm_feats = rfm[["Recency", "Frequency", "Monetary"]]
    rfm_scaled = scaler.transform(np.log1p(rfm_feats))
    rfm["Cluster"] = kmeans.predict(rfm_scaled)
    pca_coords = pca.transform(rfm_scaled)
    rfm["PCA1"] = pca_coords[:, 0]
    rfm["PCA2"] = pca_coords[:, 1]
    
    # Predict Churn and Churn_Prob
    rfm["Churn"] = (rfm["Recency"] > threshold).astype(int)
    rfm["Churn_Prob"] = model.predict_proba(rfm_feats)[:, 1]
    
    return pd.DataFrame(rfm.reset_index())


def train_churn_model(rfm_base: pd.DataFrame, threshold: int) -> LogisticRegression:
    """Train and return a LogisticRegression model for the given churn threshold."""
    churn = (rfm_base["Recency"] > threshold).astype(int)
    features = rfm_base[["Recency", "Frequency", "Monetary"]]
    x_train, _, y_train, _ = train_test_split(
        features, churn, test_size=0.2, random_state=RANDOM_STATE, stratify=churn,
    )
    model = LogisticRegression()
    model.fit(x_train, y_train)
    return model


def predict_churn(rfm_base: pd.DataFrame, model: LogisticRegression, threshold: int) -> pd.DataFrame:
    """Add Churn and Churn_Prob columns to rfm_base using the pre-fitted model and threshold."""
    rfm = rfm_base.copy()
    rfm["Churn"] = (rfm["Recency"] > threshold).astype(int)
    features = rfm[["Recency", "Frequency", "Monetary"]]
    rfm["Churn_Prob"] = model.predict_proba(features)[:, 1]
    return rfm


def compute_churn(rfm_base: pd.DataFrame, threshold: int) -> pd.DataFrame:
    """Return rfm_base with Churn and Churn_Prob columns added for the given threshold."""
    model = train_churn_model(rfm_base, threshold)
    return predict_churn(rfm_base, model, threshold)


import re

def slugify_product_name(name: str) -> str:
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s

def get_product_image_url(product_id: str, product_name: str) -> str:
    slug = slugify_product_name(product_name)
    if not slug:
        slug = product_id.lower()
    return f"https://picsum.photos/seed/{slug}/400/400"


def get_products_catalog(data_path: Path | None = None) -> list[dict]:
    """Extract unique products from the raw transactions dataset and assign images/metadata."""
    path = data_path or Path(os.environ.get("DATA_CSV", DEFAULT_DATA_PATH))
    df = pd.read_csv(path, encoding="ISO-8859-1")
    df = df.dropna(subset=["StockCode", "Description"])
    df = df[df["UnitPrice"] > 0]
    
    # Clean stock code and description strings
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    df["Description"] = df["Description"].astype(str).str.strip()
    
    # Group by StockCode and aggregate Description (first) and UnitPrice (median)
    prod_df = df.groupby("StockCode").agg({
        "Description": "first",
        "UnitPrice": "median"
    }).reset_index()
    
    catalog = []
    for _, row in prod_df.iterrows():
        stock_code = row["StockCode"]
        # Skip special codes that are not physical products (e.g., POST for postage, M for manual, etc.)
        if len(stock_code) < 3 or stock_code.lower() in ("post", "dot", "m", "d", "c2", "bank charges", "pads"):
            continue
            
        raw_name = row["Description"]
        name = raw_name.title()
        price = float(row["UnitPrice"])
        
        # Categorize products using keyword matching
        name_lower = name.lower()
        if any(w in name_lower for w in ["holder", "box", "bag", "wallet", "case", "backpack", "hanger", "organizer", "rack", "pocket"]):
            category = "Accessories"
        elif any(w in name_lower for w in ["light", "lamp", "clock", "battery", "led", "phone", "usb", "alarm"]):
            category = "Electronics"
        elif any(w in name_lower for w in ["chair", "table", "desk", "stool", "cabinet", "shelf", "cushion", "mirror", "frame"]):
            category = "Furniture"
        else:
            category = "Lifestyle"
            
        # Generate a stable/deterministic rating between 4.0 and 5.0 based on StockCode hash
        h = int(hashlib.md5(stock_code.encode()).hexdigest(), 16)
        rating = round(4.0 + (h % 11) * 0.1, 1)
        
        description = f"This high-quality {name} (Item Code: {stock_code}) is a great addition to your collection. Features premium materials and classic design."
        image_url = get_product_image_url(stock_code, name)
        
        catalog.append({
            "id": stock_code,
            "name": name,
            "description": description,
            "price": price,
            "imageUrl": image_url,
            "rating": rating,
            "category": category
        })
        
    return catalog

