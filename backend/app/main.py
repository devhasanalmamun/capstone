from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
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

from .pipeline import build, compute_churn, train_churn_model, predict_churn

CHURN_THRESHOLD_OPTIONS = {30, 60, 90, 120, 180}
DEFAULT_THRESHOLD = 90


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
    demo_log: list[dict] = []
    app.state.demo_log = demo_log

    # Train and store models for each threshold and baseline dataframes
    app.state.churn_models = {}
    app.state.rfm_by_threshold = {}
    for threshold in CHURN_THRESHOLD_OPTIONS:
        model = train_churn_model(app.state.rfm, threshold)
        app.state.churn_models[threshold] = model
        app.state.rfm_by_threshold[threshold] = predict_churn(app.state.rfm, model, threshold)

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
    amount: float


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

    rfm.at[idx, "Monetary"] = float(rfm.at[idx, "Monetary"]) + body.amount
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
            df_t.at[idx_t, "Monetary"] = rfm.at[idx, "Monetary"]
            df_t.at[idx_t, "Frequency"] = rfm.at[idx, "Frequency"]
            df_t.at[idx_t, "Recency"] = rfm.at[idx, "Recency"]
            df_t.at[idx_t, "Cluster"] = rfm.at[idx, "Cluster"]
            df_t.at[idx_t, "PCA1"] = rfm.at[idx, "PCA1"]
            df_t.at[idx_t, "PCA2"] = rfm.at[idx, "PCA2"]
            
            model = request.app.state.churn_models[t]
            row_feats = pd.DataFrame(
                [[0, rfm.at[idx, "Frequency"], rfm.at[idx, "Monetary"]]],
                columns=["Recency", "Frequency", "Monetary"]
            )
            df_t.at[idx_t, "Churn"] = 0
            df_t.at[idx_t, "Churn_Prob"] = float(model.predict_proba(row_feats)[0, 1])

    # Refresh cached response payloads
    refresh_all_caches(request.app)

    now = pd.Timestamp.now()
    if now > request.app.state.max_date:
        request.app.state.max_date = now

    entry = {
        "customer_id": customer_id,
        "amount": body.amount,
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

    # Recompute threshold dataframes from original RFM
    for threshold in CHURN_THRESHOLD_OPTIONS:
        model = request.app.state.churn_models[threshold]
        request.app.state.rfm_by_threshold[threshold] = predict_churn(request.app.state.rfm, model, threshold)

    # Refresh cached response payloads
    refresh_all_caches(request.app)
    return {"status": "reset"}


@app.get("/demo/history", response_model=list[DemoPurchaseResult])
def demo_history(request: Request) -> list[DemoPurchaseResult]:
    return [DemoPurchaseResult(**e) for e in request.app.state.demo_log]
