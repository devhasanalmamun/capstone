import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { Bar, BarChart, CartesianGrid, Cell, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type ChurnThreshold } from "@/lib/api"
import { formatNumber } from "@/lib/format"

const chartConfig = {
  count: { label: "Customers", color: "var(--primary)" },
} satisfies ChartConfig

function barColor(midpoint: number): string {
  // green → yellow → red across 0–1
  const r = Math.round(midpoint < 0.5 ? 255 * (midpoint * 2) : 255)
  const g = Math.round(midpoint < 0.5 ? 200 : 200 * (1 - (midpoint - 0.5) * 2))
  return `rgb(${r},${g},60)`
}

export function ChurnHistogram({
  threshold,
}: {
  threshold: ChurnThreshold
}) {
  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ["churn-distribution", threshold],
    queryFn: () => api.churnDistribution(20, threshold),
    placeholderData: keepPreviousData,
  })

  return (
    <figure className="bg-background p-6">
      <figcaption className="mb-4 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        <span>Figure 3.2</span>
        <span>Threshold: {threshold} Days</span>
      </figcaption>
      <h3 className="mb-1 font-heading text-xl font-medium tracking-tight">
        Churn probability density
      </h3>
      <p className="mb-4 max-w-prose text-sm leading-relaxed text-muted-foreground">
        Customers stack at the extremes &mdash; an artefact of the churn label
        being a threshold on Recency, which is itself a model input.
      </p>
      {error ? (
        <p className="text-destructive">Failed to load distribution.</p>
      ) : isLoading || !data ? (
        <Skeleton className="aspect-16/10 w-full" />
      ) : (
        <ChartContainer
          config={chartConfig}
          className={`aspect-16/10 w-full transition-opacity duration-200 ${isFetching ? "opacity-40 pointer-events-none" : "opacity-100"}`}
        >
          <BarChart accessibilityLayer data={data} margin={{ top: 8, right: 12, left: -4, bottom: 0 }}>
            <CartesianGrid vertical={false} strokeDasharray="2 4" stroke="var(--border)" />
            <XAxis
              dataKey="midpoint"
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              tick={{ fontFamily: "var(--font-mono)", fontSize: 10, fill: "var(--muted-foreground)" }}
              tickFormatter={(v: number) => v.toFixed(2)}
              minTickGap={20}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontFamily: "var(--font-mono)", fontSize: 10, fill: "var(--muted-foreground)" }}
              tickFormatter={(v: number) => formatNumber(v)}
              width={48}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  indicator="line"
                  labelFormatter={(_, payload) => {
                    const row = payload?.[0]?.payload as { bin_start: number; bin_end: number } | undefined
                    if (!row) return ""
                    return `${row.bin_start.toFixed(2)} – ${row.bin_end.toFixed(2)}`
                  }}
                />
              }
            />
            <Bar dataKey="count" fill="var(--color-count)">
              {data.map((entry) => (
                <Cell key={entry.midpoint} fill={barColor(entry.midpoint)} />
              ))}
            </Bar>
          </BarChart>
        </ChartContainer>
      )}
    </figure>
  )
}
