# Transaction Log & Behavioral Segmentation Analysis

This document provides a comprehensive technical and business breakdown explaining the presentation statement: **"The data to fix this already exists — it is sitting unused in the transaction log."**, along with codebase verification.

---

## Question 1: Why does the presentation say "The data to fix this already exists — it is sitting unused in the transaction log"?

### 1. What is "The Transaction Log"?
In e-commerce systems and in this codebase (`data.csv` / SQLite database), the **transaction log** is the raw sales audit ledger. Every time a customer places an order, the system automatically logs raw item-level fields:
- `CustomerID` (Unique customer identifier)
- `InvoiceNo` (Order invoice number)
- `InvoiceDate` (Purchase timestamp)
- `Quantity` (Number of items ordered)
- `UnitPrice` (Price per item)

---

### 2. Why is it considered "sitting unused"?
In traditional retail and non-ML marketing workflows, transaction logs are stored **only for accounting, tax compliance, and order fulfillment**. Retailers treat them as static receipt archives rather than a dynamic behavioral dataset.

Because transaction logs sit unanalyzed:
1. **Blanket Email Campaigns ("Everyone gets the same email")**:
   - The retailer treats all **4,339 customers** identically in a single email list.
   - A single email campaign sent to all customers at £2 per contact costs **£8,678**.
2. **Extreme Revenue Disparity**:
   - Empirical verification of the project dataset (`data.csv`) shows that **the top 10% of customers account for 61.3% of all revenue**.
   - Sending generic discount vouchers to top spenders wastes profit margins on customers who would buy anyway.
3. **Unnoticed Customer Churn**:
   - Without processing raw purchase timestamps into a **Recency signal**, a customer who hasn't purchased in 240 days (lapsing/churned) receives the exact same marketing message as a customer who purchased yesterday.

---

### 3. How the Codebase Unlocks this "Unused" Data
The FastAPI backend pipeline (`backend/app/pipeline.py`) transforms raw audit log receipts into **Recency, Frequency, and Monetary (RFM)** behavioral feature vectors:

```
[Raw Transaction Log] ──(Aggregation & Feature Engineering)──> [RFM Behavioral Profiles]
  - InvoiceDate       ──> Recency (R)   : Days since last order
  - InvoiceNo         ──> Frequency (F) : Count of unique purchases
  - Quantity * Price  ──> Monetary (M)  : Total customer revenue spend
```

- **Recency ($R$)**: Calculates days quiet relative to the snapshot date, detecting customer churn risk early.
- **Frequency ($F$)**: Identifies repeat loyal customers versus one-off buyers.
- **Monetary ($M$)**: Isolates the top 10% revenue engines from low-spend buyers.

These RFM vectors are scaled (`log1p` + `StandardScaler`) and fed into **K-Means Clustering** ($K=4$) and **Logistic Regression Churn Models**, enabling targeted segmentation (**C2 Champions, C1 At-Risk Mid-Value, C0 New/Occasional, C3 Hibernating**) instead of wasteful blanket marketing.

---

## Question 2: Do I need to fix anything in the codebase regarding this?

### Verification Result: **NO, no code fixes are needed.**

The codebase is fully implemented, verified, and functioning correctly end-to-end:

1. **Data Cleaning & Ingestion (`backend/app/pipeline.py`)**:
   - Successfully loads `data.csv`, removes null `CustomerID` records, and filters out returns (`Quantity <= 0`).
2. **Feature Engineering & Transformation (`backend/app/pipeline.py`)**:
   - Correctly aggregates raw receipts into Recency, Frequency, and Monetary metrics, applies `log1p` scaling, fits `StandardScaler`, and computes $K=4$ K-Means clusters.
3. **Multi-Threshold Churn Modeling (`backend/app/main.py`)**:
   - Fits and maintains Logistic Regression churn prediction models across 5 retention windows (30, 60, 90, 120, and 180 days), defaulting to 90 days.
4. **Web & Mobile Application Integration (`frontend/` & `capstone_app/`)**:
   - Both the React Web Dashboard and Flutter Mobile App are fully connected to the FastAPI backend API, rendering live RFM distributions, cluster breakdown tables, PCA scatter plots, and real-time purchase re-clustering simulations.

---

### Summary Script for Presentation / Supervisor Review:

> *"E-commerce retailers automatically capture customer purchase timestamps, order counts, and transaction values in their raw database logs. However, these logs typically sit unused for marketing purposes. By transforming raw receipt line items into Recency, Frequency, and Monetary (RFM) behavioral signals, our system turns static audit logs into intelligent customer segments (C2 Champions, C1 At-Risk, C0 New, C3 Hibernating), eliminating wasteful blanket marketing."*
