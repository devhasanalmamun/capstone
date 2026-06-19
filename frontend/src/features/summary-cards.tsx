import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { api, type ChurnThreshold } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCurrency, formatNumber, formatPercent } from "@/lib/format"

export function SummaryCards({ threshold }: { threshold: ChurnThreshold }) {
  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ["summary", threshold],
    queryFn: () => api.summary(threshold),
    placeholderData: keepPreviousData,
  })

  if (error) {
    return <p className="text-destructive">Failed to load summary.</p>
  }

  const cards = [
    { label: "Customers", value: data && formatNumber(data.total_customers) },
    { label: "Revenue", value: data && formatCurrency(data.total_revenue) },
    { label: "Churn rate", value: data && formatPercent(data.churn_rate) },
    { label: "Clusters", value: data && formatNumber(data.num_clusters) },
  ]

  return (
    <div className={`grid grid-cols-2 gap-px bg-border md:grid-cols-4 transition-opacity duration-200 ${isFetching && !isLoading ? "opacity-40" : "opacity-100"}`}>
      {cards.map((c) => (
        <div key={c.label} className="bg-background p-7 pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            {c.label}
          </p>
          <div className="mt-5 font-heading text-[44px] font-medium leading-none tracking-tight tabular-nums">
            {isLoading || !c.value ? <Skeleton className="h-10 w-32" /> : c.value}
          </div>
        </div>
      ))}
    </div>
  )
}
