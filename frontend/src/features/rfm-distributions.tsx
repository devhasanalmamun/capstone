import { useQuery } from "@tanstack/react-query"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type RfmBin } from "@/lib/api"
import { formatCurrency, formatNumber } from "@/lib/format"

type Metric = {
  key: "recency" | "frequency" | "monetary"
  label: string
  unit: string
  colorVar: string
  format: (v: number) => string
}

const METRICS: Metric[] = [
  {
    key: "recency",
    label: "Recency",
    unit: "days",
    colorVar: "var(--chart-1)",
    format: (v) => formatNumber(v, 0),
  },
  {
    key: "frequency",
    label: "Frequency",
    unit: "invoices",
    colorVar: "var(--chart-2)",
    format: (v) => formatNumber(v, 0),
  },
  {
    key: "monetary",
    label: "Monetary",
    unit: "USD",
    colorVar: "var(--chart-3)",
    format: (v) => formatCurrency(v),
  },
]

function MiniHistogram({ data, metric }: { data: RfmBin[]; metric: Metric }) {
  const chartConfig = {
    count: { label: "Customers", color: metric.colorVar },
  } satisfies ChartConfig

  return (
    <div className="bg-background p-6">
      <div className="mb-3 flex items-baseline justify-between">
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          {metric.label}
        </p>
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          {metric.unit}
        </p>
      </div>
      <ChartContainer config={chartConfig} className="aspect-[4/3] w-full">
        <BarChart data={data} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
          <CartesianGrid vertical={false} strokeDasharray="2 4" stroke="var(--border)" />
          <XAxis
            dataKey="midpoint"
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
            tick={{
              fontFamily: "var(--font-mono)",
              fontSize: 9,
              fill: "var(--muted-foreground)",
            }}
            tickFormatter={metric.format}
            minTickGap={20}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            tick={{
              fontFamily: "var(--font-mono)",
              fontSize: 9,
              fill: "var(--muted-foreground)",
            }}
            width={36}
            tickFormatter={(v: number) =>
              v >= 1000 ? `${(v / 1000).toFixed(0)}k` : `${v}`
            }
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                indicator="dot"
                labelFormatter={(_, payload) => {
                  const row = payload?.[0]?.payload as RfmBin | undefined
                  if (!row) return ""
                  return `${metric.format(row.bin_start)} – ${metric.format(row.bin_end)}`
                }}
              />
            }
          />
          <Bar dataKey="count" fill={metric.colorVar} />
        </BarChart>
      </ChartContainer>
    </div>
  )
}

export function RfmDistributions() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["rfm-distribution"],
    queryFn: () => api.rfmDistribution(30),
  })

  if (error) {
    return <p className="text-destructive">Failed to load distributions.</p>
  }
  if (isLoading || !data) {
    return <Skeleton className="h-64 w-full" />
  }

  return (
    <div className="grid grid-cols-1 gap-px bg-border md:grid-cols-3">
      {METRICS.map((m) => (
        <MiniHistogram key={m.key} data={data[m.key]} metric={m} />
      ))}
    </div>
  )
}
