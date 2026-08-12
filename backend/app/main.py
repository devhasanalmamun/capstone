from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import random
from contextlib import asynccontextmanager
from typing import Annotated

import numpy as np
import pandas as pd
from fastapi import FastAPI, Header, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "demo-jwt-secret-key-12345")
JWT_ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)

def create_token(payload: dict, expires_in: int = 3600) -> str:
    """Create a signed JWT-like token using standard library."""
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = payload.copy()
    payload["exp"] = int(time.time()) + expires_in
    
    header_json = json.dumps(header, separators=(',', ':'))
    payload_json = json.dumps(payload, separators=(',', ':'))
    
    header_b64 = base64.urlsafe_b64encode(header_json.encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
    
    signature = hmac.new(
        JWT_SECRET_KEY.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def verify_token(token: str) -> dict | None:
    """Verify a signed token and return its payload. Returns None if invalid or expired."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        # Reconstruct signature and compare
        expected_sig = hmac.new(
            JWT_SECRET_KEY.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        
        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None
            
        # Decode payload
        padding = "=" * ((4 - len(payload_b64) % 4) % 4)
        payload_data = base64.urlsafe_b64decode(payload_b64 + padding).decode()
        payload = json.loads(payload_data)
        
        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None
            
        return payload
    except Exception:
        return None

from .pipeline import build, compute_churn, train_churn_model, predict_churn, get_products_catalog, DEFAULT_DATA_PATH, compute_rfm_for_threshold
from .database import init_db, populate_products_if_empty, get_db_connection

CHURN_THRESHOLD_OPTIONS = {30, 60, 90, 120, 180}
DEFAULT_THRESHOLD = 90


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    price: float
    imageUrl: str
    rating: float
    category: str


class PurchaseItem(BaseModel):
    productId: str
    quantity: int


class Summary(BaseModel):
    total_customers: int
    total_revenue: float
    churn_rate: float
    num_clusters: int


class ClusterStats(BaseModel):
    cluster: int
    size: int
    mean_recency: float
    mean_frequency: float
    mean_monetary: float
    churn_rate: float


class Customer(BaseModel):
    customer_id: int
    recency: int
    frequency: int
    monetary: float
    cluster: int
    churn_prob: float
    email: str | None = None


class CustomerList(BaseModel):
    total: int
    items: list[Customer]


class TransactionItem(BaseModel):
    invoice_no: str
    invoice_date: str
    quantity: int
    total_value: float
    item_count: int


class CustomerTransactionsResponse(BaseModel):
    customer_id: int
    email: str | None = None
    recency: int
    frequency: int
    monetary: float
    cluster: int
    total_transactions: int
    total_quantity_all: int
    total_value_all: float
    transactions: list[TransactionItem]



class PcaPoint(BaseModel):
    customer_id: int
    pca1: float
    pca2: float
    cluster: int


class ChurnBin(BaseModel):
    bin_start: float
    bin_end: float
    midpoint: float
    count: int


class RfmBin(BaseModel):
    bin_start: float
    bin_end: float
    midpoint: float
    count: int


class RfmDistributions(BaseModel):
    recency: list[RfmBin]
    frequency: list[RfmBin]
    monetary: list[RfmBin]


class ElbowPoint(BaseModel):
    k: int
    wcss: float


def _clipped_histogram(values: np.ndarray, bins: int) -> list[RfmBin]:
    lo = float(np.min(values))
    hi = float(np.percentile(values, 99))
    if hi <= lo:
        hi = float(np.max(values))
    counts, edges = np.histogram(values, bins=bins, range=(lo, hi))
    return [
        RfmBin(
            bin_start=float(edges[i]),
            bin_end=float(edges[i + 1]),
            midpoint=float((edges[i] + edges[i + 1]) / 2),
            count=int(counts[i]),
        )
        for i in range(len(counts))
    ]


def build_summary_payload(rfm: pd.DataFrame) -> Summary:
    return Summary(
        total_customers=len(rfm),
        total_revenue=float(rfm["Monetary"].sum()),
        churn_rate=rfm["Churn"].mean(),
        num_clusters=rfm["Cluster"].nunique(),
    )


def build_clusters_payload(rfm: pd.DataFrame) -> list[ClusterStats]:
    grouped = (
        rfm.groupby("Cluster")
        .agg(
            size=("CustomerID", "count"),
            mean_recency=("Recency", "mean"),
            mean_frequency=("Frequency", "mean"),
            mean_monetary=("Monetary", "mean"),
            churn_rate=("Churn", "mean"),
        )
        .reset_index()
    )
    return [
        ClusterStats(
            cluster=int(r["Cluster"]),
            size=int(r["size"]),
            mean_recency=float(r["mean_recency"]),
            mean_frequency=float(r["mean_frequency"]),
            mean_monetary=float(r["mean_monetary"]),
            churn_rate=float(r["churn_rate"]),
        )
        for r in grouped.to_dict(orient="records")
    ]


def build_churn_dist_payload(rfm: pd.DataFrame, bins: int = 20) -> list[ChurnBin]:
    counts, edges = np.histogram(rfm["Churn_Prob"].to_numpy(), bins=bins, range=(0.0, 1.0))
    return [
        ChurnBin(
            bin_start=float(edges[i]),
            bin_end=float(edges[i + 1]),
            midpoint=float((edges[i] + edges[i + 1]) / 2),
            count=int(counts[i]),
        )
        for i in range(len(counts))
    ]


def build_rfm_dist_payload(rfm: pd.DataFrame, bins: int = 30) -> RfmDistributions:
    return RfmDistributions(
        recency=_clipped_histogram(rfm["Recency"].to_numpy(), bins),
        frequency=_clipped_histogram(rfm["Frequency"].to_numpy(), bins),
        monetary=_clipped_histogram(rfm["Monetary"].to_numpy(), bins),
    )


def build_pca_scatter_payload(rfm: pd.DataFrame) -> list[PcaPoint]:
    points: pd.DataFrame = rfm[["CustomerID", "PCA1", "PCA2", "Cluster"]].copy()  # type: ignore
    points["PCA1"] = points["PCA1"].round(1)
    points["PCA2"] = points["PCA2"].round(1)
    points = points.drop_duplicates(subset=["PCA1", "PCA2", "Cluster"])
    return [
        PcaPoint(
            customer_id=int(r["CustomerID"]),
            pca1=float(r["PCA1"]),
            pca2=float(r["PCA2"]),
            cluster=int(r["Cluster"]),
        )
        for r in points.to_dict(orient="records")
    ]


def refresh_all_caches(app: FastAPI):
    app.state.summary_cache = {
        t: build_summary_payload(app.state.rfm_by_threshold[t])
        for t in CHURN_THRESHOLD_OPTIONS
    }
    app.state.clusters_cache = {
        t: build_clusters_payload(app.state.rfm_by_threshold[t])
        for t in CHURN_THRESHOLD_OPTIONS
    }
    app.state.churn_dist_cache = {
        t: build_churn_dist_payload(app.state.rfm_by_threshold[t])
        for t in CHURN_THRESHOLD_OPTIONS
    }
    app.state.rfm_dist_cache = build_rfm_dist_payload(app.state.rfm)
    app.state.pca_scatter_cache = build_pca_scatter_payload(app.state.rfm)


@asynccontextmanager
async def lifespan(app: FastAPI):
    result = build()
    app.state.rfm = result.rfm
    app.state.rfm_original = result.rfm.copy()
    app.state.elbow = result.elbow
    app.state.scaler = result.scaler
    app.state.kmeans = result.kmeans
    app.state.pca = result.pca
    app.state.min_date = result.min_date
    app.state.max_date = result.max_date
    app.state.max_date_original = result.max_date
    app.state.raw_df = result.raw_df
    demo_log: list[dict] = []
    app.state.demo_log = demo_log

    # Initialize SQLite database and tables
    init_db()
    
    # Extract unique products from raw CSV if needed and seed the SQLite products table
    raw_products = get_products_catalog()
    populate_products_if_empty(raw_products)
    
    # Load products lookup into memory for O(1) existence checks and price validations
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products_catalog = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    app.state.products_catalog = products_catalog
    app.state.products_lookup = {p["id"]: p for p in products_catalog}

    # Train and store models for each threshold and threshold-window RFM dataframes
    app.state.churn_models = {}
    app.state.rfm_by_threshold = {}
    for threshold in CHURN_THRESHOLD_OPTIONS:
        model = train_churn_model(app.state.rfm, threshold)
        app.state.churn_models[threshold] = model
        app.state.rfm_by_threshold[threshold] = compute_rfm_for_threshold(
            app.state.raw_df,
            threshold,
            app.state.scaler,
            app.state.kmeans,
            app.state.pca,
            model,
        )

    # Cache response payloads
    refresh_all_caches(app)
    yield


app = FastAPI(title="Customer Segmentation API", lifespan=lifespan)

# Comma-separated list of allowed frontend origins. Always includes the local
# Vite dev server; add your deployed frontend URL via the CORS_ORIGINS env var,
# e.g. CORS_ORIGINS="https://my-frontend.onrender.com".
_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_env_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
allow_origins = _default_origins + _env_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _rfm_base(request: Request) -> pd.DataFrame:
    return request.app.state.rfm


def _rfm_with_churn(request: Request, threshold: int) -> pd.DataFrame:
    if threshold not in CHURN_THRESHOLD_OPTIONS:
        raise HTTPException(status_code=422, detail=f"threshold must be one of {sorted(CHURN_THRESHOLD_OPTIONS)}")
    return request.app.state.rfm_by_threshold[threshold]


class Meta(BaseModel):
    min_date: str
    max_date: str
    total_rows: int


@app.get("/health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/meta", response_model=Meta)
def get_meta(request: Request) -> Meta:
    return Meta(
        min_date=request.app.state.min_date.strftime("%B %Y"),
        max_date=request.app.state.max_date.strftime("%B %Y"),
        total_rows=len(request.app.state.rfm),
    )


@app.get("/summary", response_model=Summary)
def get_summary(
    request: Request,
    threshold: Annotated[int, Query()] = DEFAULT_THRESHOLD,
) -> Summary:
    if threshold not in CHURN_THRESHOLD_OPTIONS:
        raise HTTPException(status_code=422, detail=f"threshold must be one of {sorted(CHURN_THRESHOLD_OPTIONS)}")
    return request.app.state.summary_cache[threshold]


@app.get("/clusters", response_model=list[ClusterStats])
def get_clusters(
    request: Request,
    threshold: Annotated[int, Query()] = DEFAULT_THRESHOLD,
) -> list[ClusterStats]:
    if threshold not in CHURN_THRESHOLD_OPTIONS:
        raise HTTPException(status_code=422, detail=f"threshold must be one of {sorted(CHURN_THRESHOLD_OPTIONS)}")
    return request.app.state.clusters_cache[threshold]


@app.get("/customers", response_model=CustomerList)
def get_customers(
    request: Request,
    cluster: Annotated[int | None, Query(ge=0)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    threshold: Annotated[int, Query()] = DEFAULT_THRESHOLD,
    churn_min: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
    churn_max: Annotated[float, Query(ge=0.0, le=1.0)] = 1.0,
) -> CustomerList:
    rfm = _rfm_with_churn(request, threshold)
    if cluster is not None:
        rfm = rfm.loc[rfm["Cluster"] == cluster]
    rfm = rfm.loc[(rfm["Churn_Prob"] >= churn_min) & (rfm["Churn_Prob"] <= churn_max)]
    total = len(rfm)
    page: pd.DataFrame = rfm.iloc[offset : offset + limit]  # type: ignore
    items = [
        Customer(
            customer_id=int(r["CustomerID"]),
            recency=int(r["Recency"]),
            frequency=int(r["Frequency"]),
            monetary=float(r["Monetary"]),
            cluster=int(r["Cluster"]),
            churn_prob=float(r["Churn_Prob"]),
            email=r.get("Email"),
        )
        for r in page.to_dict(orient="records")
    ]
    return CustomerList(total=total, items=items)


@app.get("/customers/{customer_id}/transactions", response_model=CustomerTransactionsResponse)
def get_customer_transactions(
    customer_id: int,
    request: Request,
    threshold: Annotated[int, Query()] = DEFAULT_THRESHOLD,
    ignore_threshold: Annotated[bool, Query()] = False,
) -> CustomerTransactionsResponse:
    rfm = _rfm_with_churn(request, threshold)
    cust_df: pd.DataFrame = rfm[rfm["CustomerID"] == customer_id]  # type: ignore
    if cust_df.empty:
        raise HTTPException(status_code=404, detail=f"Customer #{customer_id} not found")
    
    cust_row: dict = cust_df.to_dict(orient="records")[0]
    
    now = pd.Timestamp.now()
    
    # Use pre-loaded in-memory raw_df and filter by CustomerID first for instant response times
    raw_df: pd.DataFrame = request.app.state.raw_df
    df = raw_df[raw_df["CustomerID"] == customer_id]
    if not df.empty and not ignore_threshold:
        days_series = (now - df["InvoiceDate"]) / pd.Timedelta(days=1)
        df = df[days_series <= threshold]
    
    tx_list: list[TransactionItem] = []
    
    if not df.empty:
        grouped = df.groupby("InvoiceNo").agg(
            invoice_date=("InvoiceDate", "max"),
            total_quantity=("Quantity", "sum"),
            total_value=("TotalPrice", "sum"),
            item_count=("InvoiceNo", "count")
        ).reset_index()
        
        grouped = grouped.sort_values("invoice_date", ascending=False)
        
        for _, r in grouped.iterrows():
            date_str = pd.Timestamp(r["invoice_date"]).strftime("%Y-%m-%d %H:%M:%S")
            tx_list.append(
                TransactionItem(
                    invoice_no=str(r["InvoiceNo"]),
                    invoice_date=date_str,
                    quantity=int(r["total_quantity"]),
                    total_value=round(float(r["total_value"]), 2),
                    item_count=int(r["item_count"])
                )
            )
            
    # Also fetch simulated purchases from database if available (filtered by threshold window unless ignore_threshold is True)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT invoice_no, quantity, price, timestamp FROM purchases WHERE customer_id = ?", (customer_id,))
        db_purchases = cursor.fetchall()
        conn.close()
        for p in db_purchases:
            ts = pd.to_datetime(p["timestamp"])
            days_ago = (now - ts).total_seconds() / 86400.0
            if ignore_threshold or days_ago <= threshold:
                tx_list.append(
                    TransactionItem(
                        invoice_no=str(p["invoice_no"]),
                        invoice_date=str(p["timestamp"]),
                        quantity=int(p["quantity"]),
                        total_value=round(float(p["price"] * p["quantity"]), 2),
                        item_count=1
                    )
                )
    except Exception:
        pass
        
    tx_list.sort(key=lambda x: x.invoice_date, reverse=True)
    
    total_val_all = sum(t.total_value for t in tx_list)
    total_qty_all = sum(t.quantity for t in tx_list)
    
    email_val = cust_row.get("Email")
    email_str = None if pd.isna(email_val) else str(email_val)
    
    return CustomerTransactionsResponse(
        customer_id=customer_id,
        email=email_str,
        recency=int(cust_row["Recency"]),
        frequency=int(cust_row["Frequency"]),
        monetary=round(float(cust_row["Monetary"]), 2),
        cluster=int(cust_row["Cluster"]),
        total_transactions=len(tx_list),
        total_quantity_all=total_qty_all,
        total_value_all=round(float(total_val_all), 2),
        transactions=tx_list
    )



@app.get("/charts/pca-scatter", response_model=list[PcaPoint])
def get_pca_scatter(request: Request) -> list[PcaPoint]:
    return request.app.state.pca_scatter_cache


@app.get("/charts/churn-distribution", response_model=list[ChurnBin])
def get_churn_distribution(
    request: Request,
    bins: Annotated[int, Query(ge=5, le=100)] = 20,
    threshold: Annotated[int, Query()] = DEFAULT_THRESHOLD,
) -> list[ChurnBin]:
    if threshold not in CHURN_THRESHOLD_OPTIONS:
        raise HTTPException(status_code=422, detail=f"threshold must be one of {sorted(CHURN_THRESHOLD_OPTIONS)}")
    if bins == 20:
        return request.app.state.churn_dist_cache[threshold]
    rfm = _rfm_with_churn(request, threshold)
    return build_churn_dist_payload(rfm, bins)


@app.get("/charts/rfm-distribution", response_model=RfmDistributions)
def get_rfm_distribution(
    request: Request,
    bins: Annotated[int, Query(ge=5, le=100)] = 30,
) -> RfmDistributions:
    if bins == 30:
        return request.app.state.rfm_dist_cache
    rfm = _rfm_base(request)
    return build_rfm_dist_payload(rfm, bins)


@app.get("/charts/elbow", response_model=list[ElbowPoint])
def get_elbow(request: Request) -> list[ElbowPoint]:
    return [ElbowPoint(k=k, wcss=wcss) for k, wcss in request.app.state.elbow]


@app.get("/products", response_model=list[ProductResponse])
def get_products(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=500)] = 20,
    search: Annotated[str | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
) -> list[ProductResponse]:
    # Query database directly using page and limit for pagination
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    
    if category:
        query += " AND LOWER(category) = ?"
        params.append(category.strip().lower())
        
    if search:
        query += " AND (LOWER(name) LIKE ? OR LOWER(id) LIKE ?)"
        params.append(f"%{search.strip().lower()}%")
        params.append(f"%{search.strip().lower()}%")
        
    # Order by id to ensure deterministic pagination order
    query += " ORDER BY id ASC"
    
    # Calculate offset
    offset = (page - 1) * limit
    
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [
        ProductResponse(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            price=row["price"],
            imageUrl=row["imageUrl"],
            rating=row["rating"],
            category=row["category"]
        )
        for row in rows
    ]


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str


@app.post("/auth/login", response_model=LoginResponse)
def auth_login(body: LoginRequest, request: Request) -> LoginResponse:
    rfm = request.app.state.rfm
    email_clean = body.email.strip().lower()
    password_clean = body.password.strip()

    mask = (
        (rfm["Email"].notna())
        & (rfm["Email"].astype(str).str.strip().str.lower() == email_clean)
        & (rfm["Password"].notna())
        & (rfm["Password"].astype(str).str.strip() == password_clean)
    )

    if not mask.any():
        raise HTTPException(status_code=401, detail="Invalid email or password")

    row = rfm.loc[mask].iloc[0]
    token = create_token({
        "customer_id": int(row["CustomerID"]),
        "email": str(row["Email"])
    }, expires_in=3600)  # Token valid for 1 hour
    
    return LoginResponse(token=token)


# ── Demo endpoints ────────────────────────────────────────────────────────────

class DemoPurchaseRequest(BaseModel):
    productId: str
    quantity: int


class DemoPurchaseResult(BaseModel):
    customer_id: int
    amount: float
    timestamp: str
    before: dict
    after: dict


@app.post("/demo/purchase", response_model=DemoPurchaseResult)
def demo_purchase(
    body: DemoPurchaseRequest,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None
) -> DemoPurchaseResult:
    token = None
    if credentials:
        token = credentials.credentials
    else:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header:
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            else:
                token = auth_header

    if not token:
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")
    
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token has expired. Please login again.")
        
    customer_id = payload["customer_id"]
    
    rfm = request.app.state.rfm
    mask = rfm["CustomerID"] == customer_id
    if not mask.any():
        raise HTTPException(status_code=404, detail="Customer not found")

    idx = int(rfm.index[mask][0])
    before = {
        "recency": int(rfm.at[idx, "Recency"]),
        "frequency": int(rfm.at[idx, "Frequency"]),
        "monetary": float(rfm.at[idx, "Monetary"]),
        "cluster": int(rfm.at[idx, "Cluster"]),
    }

    # 1. Log purchase in SQLite purchases table
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if product exists in database
    cursor.execute("SELECT * FROM products WHERE id = ?", (body.productId,))
    prod = cursor.fetchone()
    if not prod:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Product with ID '{body.productId}' not found in database.")
        
    product_price = prod["price"]
    
    # Generate unique 6-digit invoice number
    import random
    generated_invoice = str(random.randint(580000, 599999))
    
    now_str = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cursor.execute(
            """
            INSERT OR REPLACE INTO purchases (invoice_no, customer_id, product_id, price, quantity, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (generated_invoice, customer_id, body.productId, product_price, body.quantity, now_str)
        )
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database error while saving purchase: {str(e)}")
    finally:
        conn.close()
                
    total_amount = product_price * body.quantity

    rfm.at[idx, "Monetary"] = float(rfm.at[idx, "Monetary"]) + total_amount
    rfm.at[idx, "Frequency"] = int(rfm.at[idx, "Frequency"]) + 1
    rfm.at[idx, "Recency"] = 0

    row = np.array([[0, rfm.at[idx, "Frequency"], rfm.at[idx, "Monetary"]]], dtype=float)
    scaled = request.app.state.scaler.transform(np.log1p(row))
    rfm.at[idx, "Cluster"] = int(request.app.state.kmeans.predict(scaled)[0])
    pca_coords = request.app.state.pca.transform(scaled)[0]
    rfm.at[idx, "PCA1"] = float(pca_coords[0])
    rfm.at[idx, "PCA2"] = float(pca_coords[1])

    after = {
        "recency": int(rfm.at[idx, "Recency"]),
        "frequency": int(rfm.at[idx, "Frequency"]),
        "monetary": float(rfm.at[idx, "Monetary"]),
        "cluster": int(rfm.at[idx, "Cluster"]),
    }

    # Update each threshold's dataframe copy with new values and perform inference
    for t in CHURN_THRESHOLD_OPTIONS:
        df_t = request.app.state.rfm_by_threshold[t]
        mask_t = df_t["CustomerID"] == customer_id
        if mask_t.any():
            idx_t = df_t.index[mask_t][0]
            new_t_freq = int(df_t.at[idx_t, "Frequency"]) + 1
            new_t_monetary = float(df_t.at[idx_t, "Monetary"]) + total_amount
            new_t_recency = 0
            
            df_t.at[idx_t, "Frequency"] = new_t_freq
            df_t.at[idx_t, "Monetary"] = new_t_monetary
            df_t.at[idx_t, "Recency"] = new_t_recency
            
            row_scaled_t = request.app.state.scaler.transform(
                np.log1p(np.array([[new_t_recency, new_t_freq, new_t_monetary]], dtype=float))
            )
            df_t.at[idx_t, "Cluster"] = int(request.app.state.kmeans.predict(row_scaled_t)[0])
            pca_coords_t = request.app.state.pca.transform(row_scaled_t)[0]
            df_t.at[idx_t, "PCA1"] = float(pca_coords_t[0])
            df_t.at[idx_t, "PCA2"] = float(pca_coords_t[1])
            
            model = request.app.state.churn_models[t]
            row_feats_t = pd.DataFrame(
                [[new_t_recency, new_t_freq, new_t_monetary]],
                columns=["Recency", "Frequency", "Monetary"]
            )
            df_t.at[idx_t, "Churn"] = 0
            df_t.at[idx_t, "Churn_Prob"] = float(model.predict_proba(row_feats_t)[0, 1])

    # Refresh cached response payloads
    refresh_all_caches(request.app)

    now = pd.Timestamp.now()
    if now > request.app.state.max_date:
        request.app.state.max_date = now

    entry = {
        "customer_id": customer_id,
        "amount": total_amount,
        "timestamp": now.strftime("%H:%M:%S"),
        "before": before,
        "after": after,
    }
    request.app.state.demo_log.append(entry)
    return DemoPurchaseResult(**entry)


@app.post("/demo/reset")
def demo_reset(request: Request) -> dict:
    request.app.state.rfm = request.app.state.rfm_original.copy()
    request.app.state.max_date = request.app.state.max_date_original
    request.app.state.demo_log = []

    # Clear simulated purchases from SQLite database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM purchases")
        conn.commit()
        conn.close()
    except Exception:
        pass

    # Recompute threshold dataframes from raw_df
    for threshold in CHURN_THRESHOLD_OPTIONS:
        model = request.app.state.churn_models[threshold]
        request.app.state.rfm_by_threshold[threshold] = compute_rfm_for_threshold(
            request.app.state.raw_df,
            threshold,
            request.app.state.scaler,
            request.app.state.kmeans,
            request.app.state.pca,
            model,
        )

    # Refresh cached response payloads
    refresh_all_caches(request.app)
    return {"status": "reset"}


@app.get("/demo/history", response_model=list[DemoPurchaseResult])
def demo_history(request: Request) -> list[DemoPurchaseResult]:
    return [DemoPurchaseResult(**e) for e in request.app.state.demo_log]
