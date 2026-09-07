import { useQuery } from "@tanstack/react-query"
import { Bar, BarChart, CartesianGrid, Label, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type RfmBin } from "@/lib/api"
import { formatCurrency, formatNumber } from "@/lib/format"

const AXIS_LABEL = {
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  letterSpacing: "0.22em",
  fill: "var(--muted-foreground)",
} as const

type Metric = {
  key: "recency" | "frequency" | "monetary"
  label: string
  unit: string
  colorVar: string
  format: (v: number) => string
  /** Shorter form for axis ticks; falls back to `format`. Tooltips always use `format`. */
  tickFormat?: (v: number) => string
  /** Right margin, in px, so the widest x tick is not clipped at the edge. */
  marginRight: number
}

const METRICS: Metric[] = [
  {
    key: "recency",
    label: "Recency",
    unit: "days",
    colorVar: "var(--chart-1)",
    format: (v) => formatNumber(v, 0),
    marginRight: 14,
  },
  {
    key: "frequency",
    label: "Frequency",
    unit: "invoices",
    colorVar: "var(--chart-2)",
    format: (v) => formatNumber(v, 0),
    marginRight: 14,
  },
  {
    key: "monetary",
    label: "Monetary",
    unit: "EUR",
    colorVar: "var(--chart-3)",
    format: (v) => formatCurrency(v),
    // Derived from formatCurrency so the symbol follows the configured currency.
    tickFormat: (v) =>
      v >= 1000 ? `${formatCurrency(v / 1000, 2)}k` : formatCurrency(v, 0),
    marginRight: 20,
  },
]

function MiniHistogram({ data, metric }: { data: RfmBin[]; metric: Metric }) {
  const chartConfig = {
    count: { label: "Customers", color: metric.colorVar },
  } satisfies ChartConfig

  return (
    <div className="bg-background px-4 py-6">
      <div className="mb-3 flex items-baseline justify-between">
        <p className="font-mono text-[12px] uppercase tracking-[0.22em] text-muted-foreground">
          {metric.label}
        </p>
        <p className="font-mono text-[12px] uppercase tracking-[0.22em] text-muted-foreground">
          {metric.unit}
        </p>
      </div>
      <ChartContainer config={chartConfig} className="h-[340px] w-full">
        <BarChart data={data} margin={{ top: 4, right: metric.marginRight, left: 0, bottom: 24 }}>
          <CartesianGrid vertical={false} strokeDasharray="2 4" stroke="var(--border)" />
          <XAxis
            dataKey="midpoint"
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
            tick={{
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              fill: "var(--muted-foreground)",
            }}
            tickFormatter={metric.tickFormat ?? metric.format}
            minTickGap={20}
          >
            <Label
              value={`${metric.label} (${metric.unit})`.toUpperCase()}
              position="insideBottom"
              offset={-16}
              style={AXIS_LABEL}
            />
          </XAxis>
          <YAxis
            tickLine={false}
            axisLine={false}
            tick={{
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              fill: "var(--muted-foreground)",
            }}
            width={56}
            tickFormatter={(v: number) =>
              v >= 1000 ? `${(v / 1000).toFixed(0)}k` : `${v}`
            }
          >
            <Label
              value="CUSTOMERS"
              angle={-90}
              position="insideLeft"
              style={{ ...AXIS_LABEL, textAnchor: "middle" }}
            />
          </YAxis>
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
    return <Skeleton className="h-[340px] w-full" />
  }

  return (
    <div className="grid grid-cols-1 gap-px bg-border md:grid-cols-3">
      {METRICS.map((m) => (
        <MiniHistogram key={m.key} data={data[m.key]} metric={m} />
      ))}
    </div>
  )
}
