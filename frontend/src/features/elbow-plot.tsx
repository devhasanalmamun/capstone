import { useQuery } from "@tanstack/react-query"
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  XAxis,
  YAxis,
} from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { formatNumber } from "@/lib/format"

const chartConfig = {
  wcss: { label: "WCSS", color: "var(--chart-1)" },
} satisfies ChartConfig

export function ElbowPlot() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["elbow"],
    queryFn: api.elbow,
  })

  return (
    <figure className="bg-background p-6">
      <figcaption className="mb-4 flex items-baseline justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          Figure 5.2
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          K = 1 .. 9
        </span>
      </figcaption>
      <h3 className="mb-1 font-heading text-xl font-medium tracking-tight">
        Elbow method
      </h3>
      <p className="mb-4 max-w-prose text-sm leading-relaxed text-muted-foreground">
        Within-cluster sum of squares (WCSS) plotted against K. The curve
        bends sharply around K=4, the chosen segment count.
      </p>
      {error ? (
        <p className="text-destructive">Failed to load elbow.</p>
      ) : isLoading || !data ? (
        <Skeleton className="aspect-[16/8] w-full" />
      ) : (
        <ChartContainer config={chartConfig} className="aspect-[16/8] w-full">
          <LineChart data={data} margin={{ top: 16, right: 16, left: -4, bottom: 8 }}>
            <CartesianGrid vertical={false} strokeDasharray="2 4" stroke="var(--border)" />
            <XAxis
              dataKey="k"
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              tick={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fill: "var(--muted-foreground)",
              }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fill: "var(--muted-foreground)",
              }}
              width={48}
              tickFormatter={(v: number) =>
                v >= 1000 ? `${(v / 1000).toFixed(0)}k` : formatNumber(v)
              }
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  indicator="line"
                  labelFormatter={(label) => `K = ${label}`}
                  formatter={(value) => [formatNumber(Number(value)), "WCSS"]}
                />
              }
            />
            <ReferenceLine
              x={4}
              stroke="var(--primary)"
              strokeDasharray="3 3"
              strokeWidth={1}
              label={{
                value: "K = 4",
                position: "top",
                fill: "var(--primary)",
                fontSize: 10,
                fontFamily: "var(--font-mono)",
              }}
            />
            <Line
              type="monotone"
              dataKey="wcss"
              stroke="var(--color-wcss)"
              strokeWidth={2}
              dot={{ fill: "var(--color-wcss)", r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ChartContainer>
      )}
    </figure>
  )
}
