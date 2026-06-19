import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { api, type ChurnThreshold } from "@/lib/api"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCurrency, formatNumber, formatPercent } from "@/lib/format"

const SWATCH_VARS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
]

export function ClusterTable({ threshold }: { threshold: ChurnThreshold }) {
  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ["clusters", threshold],
    queryFn: () => api.clusters(threshold),
    placeholderData: keepPreviousData,
  })

  if (error) return <p className="text-destructive">Failed to load clusters.</p>
  if (isLoading || !data) return <Skeleton className="h-56 w-full" />

  return (
    <div className={`border-b border-border [&_td]:px-4 [&_th]:px-4 transition-opacity duration-200 ${isFetching ? "opacity-40" : "opacity-100"}`}>
      <Table>
        <TableHeader>
          <TableRow className="border-border hover:bg-transparent">
            <TableHead className="h-9 w-16 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Cluster
            </TableHead>
            <TableHead className="h-9 text-right font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Size
            </TableHead>
            <TableHead className="h-9 text-right font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Avg Recency
            </TableHead>
            <TableHead className="h-9 text-right font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Avg Frequency
            </TableHead>
            <TableHead className="h-9 text-right font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Avg Monetary
            </TableHead>
            <TableHead className="h-9 text-right font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Churn rate
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((c) => (
            <TableRow key={c.cluster} className="border-border hover:bg-muted/40">
              <TableCell className="py-4">
                <div className="flex items-center gap-3">
                  <span
                    aria-hidden
                    className="h-2.5 w-2.5"
                    style={{ background: SWATCH_VARS[c.cluster % SWATCH_VARS.length] }}
                  />
                  <span className="font-heading text-lg leading-none">{c.cluster}</span>
                </div>
              </TableCell>
              <TableCell className="py-4 text-right font-mono tabular-nums">
                {formatNumber(c.size)}
              </TableCell>
              <TableCell className="py-4 text-right font-mono tabular-nums">
                {formatNumber(c.mean_recency, 1)}
              </TableCell>
              <TableCell className="py-4 text-right font-mono tabular-nums">
                {formatNumber(c.mean_frequency, 1)}
              </TableCell>
              <TableCell className="py-4 text-right font-mono tabular-nums">
                {formatCurrency(c.mean_monetary)}
              </TableCell>
              <TableCell className="py-4 text-right font-mono tabular-nums">
                {formatPercent(c.churn_rate)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
