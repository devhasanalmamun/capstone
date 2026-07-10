import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { demo, auth, type DemoPurchaseResult } from "@/lib/api"
import { formatCurrency } from "@/lib/format"

export function DemoPanel() {
  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loggedInCustomer, setLoggedInCustomer] = useState<{ customerId: number; email: string } | null>(null)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [amount, setAmount] = useState<string>("")
  const [lastResult, setLastResult] = useState<DemoPurchaseResult | null>(null)
  const queryClient = useQueryClient()

  const { data: history = [] } = useQuery({
    queryKey: ["demo-history"],
    queryFn: demo.history,
    enabled: open,
  })

  const loginMutation = useMutation({
    mutationFn: () => auth.login(email, password),
    onSuccess: (data) => {
      setLoggedInCustomer({ customerId: data.customer_id, email: data.email })
      setLoginError(null)
    },
    onError: (err) => {
      setLoginError(err instanceof Error ? err.message : "Login failed")
    },
  })

  const purchase = useMutation({
    mutationFn: () => {
      if (!loggedInCustomer) throw new Error("Please log in first")
      return demo.purchase(loggedInCustomer.customerId, Number(amount))
    },
    onSuccess: (result) => {
      setLastResult(result)
      setAmount("")
      queryClient.invalidateQueries({ queryKey: ["meta"] })
      queryClient.invalidateQueries({ queryKey: ["summary"] })
      queryClient.invalidateQueries({ queryKey: ["clusters"] })
      queryClient.invalidateQueries({ queryKey: ["customers"] })
      queryClient.invalidateQueries({ queryKey: ["churn-distribution"] })
      queryClient.invalidateQueries({ queryKey: ["demo-history"] })
    },
  })

  const reset = useMutation({
    mutationFn: demo.reset,
    onSuccess: () => {
      setLastResult(null)
      setLoggedInCustomer(null)
      setEmail("")
      setPassword("")
      setLoginError(null)
      queryClient.invalidateQueries({ queryKey: ["meta"] })
      queryClient.invalidateQueries({ queryKey: ["summary"] })
      queryClient.invalidateQueries({ queryKey: ["clusters"] })
      queryClient.invalidateQueries({ queryKey: ["customers"] })
      queryClient.invalidateQueries({ queryKey: ["churn-distribution"] })
      queryClient.invalidateQueries({ queryKey: ["demo-history"] })
    },
  })

  const canLogin =
    email.trim() !== "" &&
    password.trim() !== "" &&
    !loginMutation.isPending

  const canBuy =
    loggedInCustomer !== null &&
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
            {loggedInCustomer === null ? (
              <>
                {/* Login Inputs */}
                <div className="space-y-3">
                  <div>
                    <label className="mb-1.5 block font-mono text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
                      Email
                    </label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value)
                        setLoginError(null)
                        setLastResult(null)
                      }}
                      placeholder="e.g. customer@example.com"
                      className="w-full border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground/40 focus:border-foreground focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block font-mono text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
                      Password
                    </label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value)
                        setLoginError(null)
                        setLastResult(null)
                      }}
                      placeholder="Password"
                      className="w-full border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground/40 focus:border-foreground focus:outline-none"
                    />
                  </div>
                </div>

                {/* Login button */}
                <button
                  type="button"
                  onClick={() => loginMutation.mutate()}
                  disabled={!canLogin}
                  className="w-full border border-foreground bg-foreground py-2.5 font-mono text-[10px] uppercase tracking-[0.28em] text-background transition-opacity disabled:cursor-not-allowed disabled:opacity-30 enabled:hover:opacity-80"
                >
                  {loginMutation.isPending ? "Logging in…" : "Login"}
                </button>

                {/* Login Error */}
                {loginError && (
                  <p className="font-mono text-[10px] text-destructive">
                    {loginError}
                  </p>
                )}
              </>
            ) : (
              <>
                {/* Logged in status */}
                <div className="border border-border p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1 pr-2">
                      <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
                        Authenticated User
                      </p>
                      <p className="font-mono text-xs font-semibold text-foreground truncate" title={loggedInCustomer.email}>
                        {loggedInCustomer.email}
                      </p>
                      <p className="font-mono text-[10px] text-muted-foreground">
                        ID: #{loggedInCustomer.customerId}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setLoggedInCustomer(null)
                        setEmail("")
                        setPassword("")
                        setLastResult(null)
                      }}
                      className="border border-border px-2.5 py-1 font-mono text-[9px] uppercase tracking-[0.16em] hover:bg-destructive hover:text-destructive-foreground hover:border-destructive transition-colors text-muted-foreground"
                    >
                      Logout
                    </button>
                  </div>
                </div>

                {/* Purchase amount input */}
                <div className="space-y-3">
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

                {/* Purchase button */}
                <button
                  type="button"
                  onClick={() => purchase.mutate()}
                  disabled={!canBuy}
                  className="w-full border border-foreground bg-foreground py-2.5 font-mono text-[10px] uppercase tracking-[0.28em] text-background transition-opacity disabled:cursor-not-allowed disabled:opacity-30 enabled:hover:opacity-80"
                >
                  {purchase.isPending ? "Processing…" : "Simulate Purchase"}
                </button>

                {/* Purchase Error */}
                {purchase.isError && (
                  <p className="font-mono text-[10px] text-destructive">
                    {purchase.error instanceof Error ? purchase.error.message : "Purchase failed"}
                  </p>
                )}
              </>
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
