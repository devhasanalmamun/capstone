import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api, demo, type DemoPurchaseResult } from "@/lib/api"
import { formatCurrency } from "@/lib/format"

export function DemoPanel() {
  const [open, setOpen] = useState(false)
  const [customerId, setCustomerId] = useState<string>("")
  const [amount, setAmount] = useState<string>("")
  const [lastResult, setLastResult] = useState<DemoPurchaseResult | null>(null)
  const queryClient = useQueryClient()

  const { data: sampleCustomers } = useQuery({
    queryKey: ["demo-sample-customers"],
    queryFn: () => api.customers({ limit: 8, offset: 0 }),
    enabled: open,
    staleTime: Infinity,
  })

  const { data: history = [] } = useQuery({
    queryKey: ["demo-history"],
    queryFn: demo.history,
    enabled: open,
  })

  const purchase = useMutation({
    mutationFn: () => demo.purchase(Number(customerId), Number(amount)),
    onSuccess: (result) => {
      setLastResult(result)
      setAmount("")
      queryClient.invalidateQueries()
    },
  })

  const reset = useMutation({
    mutationFn: demo.reset,
    onSuccess: () => {
      setLastResult(null)
      queryClient.invalidateQueries()
    },
  })

  const canBuy =
    customerId.trim() !== "" &&
    amount.trim() !== "" &&
    Number(amount) > 0 &&
    !purchase.isPending

  return (
    <>
      {/* Toggle button */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 border border-foreground bg-background px-4 py-2.5 font-mono text-[10px] uppercase tracking-[0.22em] shadow-lg transition-colors hover:bg-foreground hover:text-background"
      >
        <span>Demo</span>
        <span className="text-[14px] leading-none">{open ? "×" : "↑"}</span>
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-16 right-6 z-50 w-[340px] border border-border bg-background shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border px-5 py-3">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              Purchase Simulator
            </p>
            {history.length > 0 && (
              <button
                type="button"
                onClick={() => reset.mutate()}
                disabled={reset.isPending}
                className="font-mono text-[9px] uppercase tracking-[0.2em] text-muted-foreground underline underline-offset-2 transition-colors hover:text-destructive disabled:opacity-40"
              >
                {reset.isPending ? "Resetting…" : "Reset all"}
              </button>
            )}
          </div>

          <div className="p-5 space-y-5">
            {/* Sample customer chips */}
            {sampleCustomers && (
              <div>
                <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
                  Sample customers
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {sampleCustomers.items.map((c) => (
                    <button
                      key={c.customer_id}
                      type="button"
                      onClick={() => { setCustomerId(String(c.customer_id)); setLastResult(null) }}
                      className={`border px-2.5 py-1 font-mono text-[10px] transition-colors ${
                        customerId === String(c.customer_id)
                          ? "border-foreground bg-foreground text-background"
                          : "border-border text-muted-foreground hover:border-foreground hover:text-foreground"
                      }`}
                    >
                      #{c.customer_id}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Inputs */}
            <div className="space-y-3">
              <div>
                <label className="mb-1.5 block font-mono text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
                  Customer ID
                </label>
                <input
                  type="number"
                  value={customerId}
                  onChange={(e) => { setCustomerId(e.target.value); setLastResult(null) }}
                  placeholder="e.g. 12747"
                  className="w-full border border-border bg-background px-3 py-2 font-mono text-sm tabular-nums text-foreground placeholder:text-muted-foreground/40 focus:border-foreground focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1.5 block font-mono text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
                  Purchase amount (£)
                </label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="e.g. 49.99"
                  className="w-full border border-border bg-background px-3 py-2 font-mono text-sm tabular-nums text-foreground placeholder:text-muted-foreground/40 focus:border-foreground focus:outline-none"
                />
              </div>
            </div>

            {/* Buy button */}
            <button
              type="button"
              onClick={() => purchase.mutate()}
              disabled={!canBuy}
              className="w-full border border-foreground bg-foreground py-2.5 font-mono text-[10px] uppercase tracking-[0.28em] text-background transition-opacity disabled:cursor-not-allowed disabled:opacity-30 enabled:hover:opacity-80"
            >
              {purchase.isPending ? "Processing…" : "Simulate Purchase"}
            </button>

            {/* Error */}
            {purchase.isError && (
              <p className="font-mono text-[10px] text-destructive">
                {purchase.error instanceof Error ? purchase.error.message : "Purchase failed"}
              </p>
            )}

            {/* Before / after result */}
            {lastResult && (
              <div className="border border-border p-4 space-y-3">
                <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
                  Customer #{lastResult.customer_id} — {formatCurrency(lastResult.amount)} added
                </p>
                <div className="grid grid-cols-2 gap-px bg-border text-[10px]">
                  {(["recency", "frequency", "monetary", "cluster"] as const).map((key) => (
                    <div key={key} className="bg-background px-3 py-2">
                      <p className="font-mono uppercase tracking-[0.16em] text-muted-foreground">{key}</p>
                      <p className="mt-1 font-mono tabular-nums">
                        <span className="text-muted-foreground line-through mr-1.5">
                          {key === "monetary"
                            ? formatCurrency(lastResult.before[key])
                            : lastResult.before[key]}
                        </span>
                        <span className="text-foreground font-medium">
                          {key === "monetary"
                            ? formatCurrency(lastResult.after[key])
                            : lastResult.after[key]}
                        </span>
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* History */}
            {history.length > 0 && (
              <div>
                <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
                  Session history ({history.length})
                </p>
                <div className="max-h-36 overflow-y-auto space-y-1">
                  {[...history].reverse().map((h, i) => (
                    <div key={i} className="flex items-center justify-between font-mono text-[10px]">
                      <span className="text-muted-foreground">{h.timestamp}</span>
                      <span className="text-muted-foreground">#{h.customer_id}</span>
                      <span className="text-foreground">+{formatCurrency(h.amount)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
