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


PRODUCT_IMAGE_MAP = {
    "10002": "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?auto=format&fit=crop&w=400&q=80",  # Inflatable Political Globe
    "10080": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=400&q=80",  # Groovy Cactus Inflatable
    "10120": "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?auto=format&fit=crop&w=400&q=80",  # Doggy Rubber
    "10123C": "https://images.unsplash.com/photo-1582738411706-bfc8e691d1c2?auto=format&fit=crop&w=400&q=80", # Hearts Wrapping Tape
    "10124A": "https://images.unsplash.com/photo-1516962215378-7fa2e137ae93?auto=format&fit=crop&w=400&q=80", # Spots On Red Bookcover Tape
    "10124G": "https://images.unsplash.com/photo-1607344645866-009c320c5ab8?auto=format&fit=crop&w=400&q=80", # Army Camo Bookcover Tape
    "10125": "https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?auto=format&fit=crop&w=400&q=80",  # Mini Funky Design Tapes
    "10133": "https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?auto=format&fit=crop&w=400&q=80",  # Colouring Pencils Brown Tube
    "10135": "https://images.unsplash.com/photo-1580582932707-520aed937b7b?auto=format&fit=crop&w=400&q=80",  # Colouring Pencils Brown Tube
    "11001": "https://images.unsplash.com/photo-1585336261026-875a60a1c92f?auto=format&fit=crop&w=400&q=80",  # Asstd Design Racing Car Pen
    "15030": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?auto=format&fit=crop&w=400&q=80",  # Fan Black Frame
    "15034": "https://images.unsplash.com/photo-1563245372-f21724e3856d?auto=format&fit=crop&w=400&q=80",  # Paper Pocket Traveling Fan
    "15036": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=400&q=80",  # Assorted Colours Silk Fan
    "15039": "https://images.unsplash.com/photo-1606760227091-3dd870d97f1d?auto=format&fit=crop&w=400&q=80",  # Sandalwood Fan
    "15044A": "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=400&q=80", # Pink Paper Parasol
    "15044B": "https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=400&q=80", # Blue Paper Parasol
    "15044C": "https://images.unsplash.com/photo-1541781774459-bb2af2f05b55?auto=format&fit=crop&w=400&q=80", # Purple Paper Parasol
    "15044D": "https://images.unsplash.com/photo-1508873696983-2df515122519?auto=format&fit=crop&w=400&q=80", # Red Paper Parasol
    "15056BL": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=400&q=80",# Edwardian Parasol Black
    "15056N": "https://images.unsplash.com/photo-1578328819058-b69f3a3b0f6b?auto=format&fit=crop&w=400&q=80", # Edwardian Parasol Natural
    "15056P": "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=400&q=80", # Edwardian Parasol Pink
    "15056bl": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=400&q=80",# Edwardian Parasol Black
    "15056n": "https://images.unsplash.com/photo-1578328819058-b69f3a3b0f6b?auto=format&fit=crop&w=400&q=80", # Edwardian Parasol Natural
    "15056p": "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=400&q=80", # Edwardian Parasol Pink
    "15058A": "https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=400&q=80", # Blue Polkadot Garden Parasol
    "15058B": "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=400&q=80", # Pink Polkadot Garden Parasol
    "15058C": "https://images.unsplash.com/photo-1508873696983-2df515122519?auto=format&fit=crop&w=400&q=80", # Ice Cream Design Garden Parasol
    "15060B": "https://images.unsplash.com/photo-1519869325930-281384150729?auto=format&fit=crop&w=400&q=80", # Fairy Cake Design Umbrella
    "15060b": "https://images.unsplash.com/photo-1519869325930-281384150729?auto=format&fit=crop&w=400&q=80", # Fairy Cake Design Umbrella
    "16008": "https://images.unsplash.com/photo-1503792501406-2c40da09e1e2?auto=format&fit=crop&w=400&q=80",  # Small Folding Scissor
    "16010": "https://images.unsplash.com/photo-1588854337236-6889d631faa8?auto=format&fit=crop&w=400&q=80",  # Folding Camping Scissor
    "16011": "https://images.unsplash.com/photo-1572375992501-4b0892d50c69?auto=format&fit=crop&w=400&q=80",  # Animal Stickers
    "16012": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=400&q=80",  # Food/Drink Sponge Stickers
    "16014": "https://images.unsplash.com/photo-1589254065878-42c9da997008?auto=format&fit=crop&w=400&q=80",  # Small Chinese Style Scissor
    "16015": "https://images.unsplash.com/photo-1503792501406-2c40da09e1e2?auto=format&fit=crop&w=400&q=80",  # Medium Chinese Style Scissor
    "16016": "https://images.unsplash.com/photo-1589254065878-42c9da997008?auto=format&fit=crop&w=400&q=80",  # Large Chinese Style Scissor
    "16020C": "https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=400&q=80", # Clear Stationery Box Set
    "16033": "https://images.unsplash.com/photo-1585336261026-875a60a1c92f?auto=format&fit=crop&w=400&q=80",  # Mini Highlighter Pens
    "16043": "https://images.unsplash.com/photo-1588854337236-6889d631faa8?auto=format&fit=crop&w=400&q=80",  # Pop Art Push Down Rubber
    "16045": "https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?auto=format&fit=crop&w=400&q=80",  # Popart Wooden Pencils Asst
    "16046": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?auto=format&fit=crop&w=400&q=80",  # Teatime Pen Case & Pens
    "16048": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=400&q=80",  # Teatime Round Pencil Sharpener
    "16049": "https://images.unsplash.com/photo-1585336261026-875a60a1c92f?auto=format&fit=crop&w=400&q=80",  # Teatime Gel Pens Asst
    "16052": "https://images.unsplash.com/photo-1588854337236-6889d631faa8?auto=format&fit=crop&w=400&q=80",  # Teatime Push Down Rubber
    "16054": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=400&q=80",  # Popart Rect Pencil Sharpener Asst
    "16151A": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=400&q=80", # Flowers Handbag Blue And Orange
    "16156L": "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=400&q=80", # Wrap, Carousel
    "16156S": "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=400&q=80", # Wrap Pink Fairy Cakes
    "16161G": "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=400&q=80", # Wrap Bad Hair Day
    "16161M": "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=400&q=80", # Wrap Pink Flock
    "16161P": "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=400&q=80", # Wrap English Rose
    "16161U": "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=400&q=80", # Wrap Suki And Friends
    "16162L": "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?auto=format&fit=crop&w=400&q=80", # The King Gift Bag
    "16162M": "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?auto=format&fit=crop&w=400&q=80", # The King Gift Bag 25X24X12Cm
    "16168M": "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?auto=format&fit=crop&w=400&q=80", # Funky Monkey Gift Bag Medium
    "16169E": "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=400&q=80", # Wrap 50'S Christmas
    "16169K": "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=400&q=80", # Wrap Folk Art
    "16169M": "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=400&q=80", # Wrap Daisy Carpet
    "16169N": "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=400&q=80", # Wrap Blue Russian Folkart
    "16169P": "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=400&q=80", # Wrap Green Russian Folkart
    "16202A": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=400&q=80", # Pastel Pink Photo Album
    "16202B": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=400&q=80", # Pastel Blue Photo Album
    "16202E": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=400&q=80", # Black Photo Album
    "16206B": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=400&q=80", # Red Purse With Pink Heart
    "16207A": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=400&q=80", # Pink Strawberry Handbag
    "16207B": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=400&q=80", # Pink Heart Red Handbag
    "16216":  "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=400&q=80", # Letter Shape Pencil Sharpener
    "16218":  "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=400&q=80", # Cartoon Pencil Sharpeners
    "16219":  "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=400&q=80", # House Shape Pencil Sharpener
}

KEYWORD_IMAGE_PATTERNS = [
    (["globe"], "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?auto=format&fit=crop&w=400&q=80"),
    (["cactus"], "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=400&q=80"),
    (["rubber", "eraser"], "https://images.unsplash.com/photo-1588854337236-6889d631faa8?auto=format&fit=crop&w=400&q=80"),
    (["tape"], "https://images.unsplash.com/photo-1582738411706-bfc8e691d1c2?auto=format&fit=crop&w=400&q=80"),
    (["pencil"], "https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?auto=format&fit=crop&w=400&q=80"),
    (["pen"], "https://images.unsplash.com/photo-1585336261026-875a60a1c92f?auto=format&fit=crop&w=400&q=80"),
    (["fan"], "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?auto=format&fit=crop&w=400&q=80"),
    (["parasol", "umbrella"], "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=400&q=80"),
    (["scissor"], "https://images.unsplash.com/photo-1503792501406-2c40da09e1e2?auto=format&fit=crop&w=400&q=80"),
    (["sticker"], "https://images.unsplash.com/photo-1572375992501-4b0892d50c69?auto=format&fit=crop&w=400&q=80"),
    (["highlighter"], "https://images.unsplash.com/photo-1585336261026-875a60a1c92f?auto=format&fit=crop&w=400&q=80"),
    (["sharpener"], "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=400&q=80"),
    (["handbag", "bag", "purse", "wallet"], "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=400&q=80"),
    (["wrap", "wrapping"], "https://images.unsplash.com/photo-1513883049090-d0b7439799bf?auto=format&fit=crop&w=400&q=80"),
    (["album", "notebook", "book", "journal"], "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=400&q=80"),
    (["mug", "cup", "teacup", "coffee"], "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=400&q=80"),
    (["cushion", "pillow"], "https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?auto=format&fit=crop&w=400&q=80"),
    (["candle", "votive", "t-light", "holder", "candlestick"], "https://images.unsplash.com/photo-1603006905003-be475563bc59?auto=format&fit=crop&w=400&q=80"),
    (["lantern", "light", "lamp"], "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=400&q=80"),
    (["clock"], "https://images.unsplash.com/photo-1563861826100-9cb868fdbe1c?auto=format&fit=crop&w=400&q=80"),
    (["mirror"], "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=400&q=80"),
    (["box", "tin", "chest", "case"], "https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=400&q=80"),
    (["card", "greeting"], "https://images.unsplash.com/photo-1531346878377-a5be20888e57?auto=format&fit=crop&w=400&q=80"),
    (["toy", "game", "doll", "bear"], "https://images.unsplash.com/photo-1558060370-d644479cb6f7?auto=format&fit=crop&w=400&q=80"),
    (["kitchen", "apron", "towel", "bowl", "plate", "dish"], "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=400&q=80"),
]

DEFAULT_IMAGE = "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?auto=format&fit=crop&w=400&q=80"

def get_product_image_url(product_id: str, product_name: str) -> str:
    if product_id in PRODUCT_IMAGE_MAP:
        return PRODUCT_IMAGE_MAP[product_id]
    
    name_lower = product_name.lower()
    for keywords, url in KEYWORD_IMAGE_PATTERNS:
        if any(kw in name_lower for kw in keywords):
            return url
            
    return DEFAULT_IMAGE


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

