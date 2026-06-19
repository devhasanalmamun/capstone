const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000"

export type Summary = {
  total_customers: number
  total_revenue: number
  churn_rate: number
  num_clusters: number
}

export type ClusterStats = {
  cluster: number
  size: number
  mean_recency: number
  mean_frequency: number
  mean_monetary: number
  churn_rate: number
}

export type Customer = {
  customer_id: number
  recency: number
  frequency: number
  monetary: number
  cluster: number
  churn_prob: number
}

export type CustomerList = {
  total: number
  items: Customer[]
}

export type PcaPoint = {
  customer_id: number
  pca1: number
  pca2: number
  cluster: number
}

export type ChurnBin = {
  bin_start: number
  bin_end: number
  midpoint: number
  count: number
}

export type RfmBin = ChurnBin

export type RfmDistributions = {
  recency: RfmBin[]
  frequency: RfmBin[]
  monetary: RfmBin[]
}

export type ElbowPoint = {
  k: number
  wcss: number
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const CHURN_THRESHOLDS = [30, 60, 90, 120, 180] as const
export type ChurnThreshold = (typeof CHURN_THRESHOLDS)[number]
export const DEFAULT_THRESHOLD: ChurnThreshold = 90

export type Meta = {
  min_date: string
  max_date: string
  total_rows: number
}

export const api = {
  meta: () => fetchJson<Meta>("/meta"),
  summary: (threshold: ChurnThreshold = DEFAULT_THRESHOLD) =>
    fetchJson<Summary>(`/summary?threshold=${threshold}`),
  clusters: (threshold: ChurnThreshold = DEFAULT_THRESHOLD) =>
    fetchJson<ClusterStats[]>(`/clusters?threshold=${threshold}`),
  customers: (params: { cluster?: number; limit?: number; offset?: number; threshold?: ChurnThreshold; churn_min?: number; churn_max?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.cluster !== undefined) q.set("cluster", String(params.cluster))
    if (params.limit !== undefined) q.set("limit", String(params.limit))
    if (params.offset !== undefined) q.set("offset", String(params.offset))
    if (params.threshold !== undefined) q.set("threshold", String(params.threshold))
    if (params.churn_min !== undefined) q.set("churn_min", String(params.churn_min))
    if (params.churn_max !== undefined) q.set("churn_max", String(params.churn_max))
    const qs = q.toString()
    return fetchJson<CustomerList>(`/customers${qs ? `?${qs}` : ""}`)
  },
  pcaScatter: () => fetchJson<PcaPoint[]>("/charts/pca-scatter"),
  churnDistribution: (bins = 20, threshold: ChurnThreshold = DEFAULT_THRESHOLD) =>
    fetchJson<ChurnBin[]>(`/charts/churn-distribution?bins=${bins}&threshold=${threshold}`),
  rfmDistribution: (bins = 30) =>
    fetchJson<RfmDistributions>(`/charts/rfm-distribution?bins=${bins}`),
  elbow: () => fetchJson<ElbowPoint[]>("/charts/elbow"),
}

export type DemoPurchaseResult = {
  customer_id: number
  amount: number
  timestamp: string
  before: { recency: number; frequency: number; monetary: number; cluster: number }
  after: { recency: number; frequency: number; monetary: number; cluster: number }
}

export const demo = {
  purchase: (customer_id: number, amount: number) =>
    fetchJson<DemoPurchaseResult>("/demo/purchase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer_id, amount }),
    }),
  reset: () =>
    fetchJson<{ status: string }>("/demo/reset", { method: "POST" }),
  history: () => fetchJson<DemoPurchaseResult[]>("/demo/history"),
}
