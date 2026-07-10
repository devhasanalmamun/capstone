import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { CartesianGrid, Scatter, ScatterChart, XAxis, YAxis, ZAxis } from "recharts"
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type PcaPoint } from "@/lib/api"

const CLUSTERS = [0, 1, 2, 3] as const

const chartConfig = {
  cluster0: { label: "Cluster 0", color: "var(--chart-1)" },
  cluster1: { label: "Cluster 1", color: "var(--chart-2)" },
  cluster2: { label: "Cluster 2", color: "var(--chart-3)" },
  cluster3: { label: "Cluster 3", color: "var(--chart-4)" },
} satisfies ChartConfig

export function PcaScatter() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["pca-scatter"],
    queryFn: api.pcaScatter,
  })

  const grouped = useMemo(() => {
    const out: Record<number, PcaPoint[]> = { 0: [], 1: [], 2: [], 3: [] }
    for (const p of data ?? []) out[p.cluster]?.push(p)
    return out
  }, [data])

  return (
    <figure className="bg-background p-6">
      <figcaption className="mb-4 flex items-baseline justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          Figure 3.1
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          PC1 &times; PC2
        </span>
      </figcaption>
      <h3 className="mb-1 font-heading text-xl font-medium tracking-tight">
        PCA projection of RFM space
      </h3>
      <p className="mb-4 max-w-prose text-sm leading-relaxed text-muted-foreground">
        Each point is a customer; colour denotes their assigned cluster. The
        first two principal components capture roughly 95% of the scaled RFM
        variance.
      </p>
      {error ? (
        <p className="text-destructive">Failed to load scatter.</p>
      ) : isLoading || !data ? (
        <Skeleton className="aspect-16/10 w-full" />
      ) : (
        <ChartContainer config={chartConfig} className="aspect-16/10 w-full">
          <ScatterChart accessibilityLayer margin={{ top: 8, right: 12, left: -4, bottom: 0 }}>
            <CartesianGrid strokeDasharray="2 4" stroke="var(--border)" />
            <XAxis
              type="number"
              dataKey="pca1"
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              tick={{ fontFamily: "var(--font-mono)", fontSize: 10, fill: "var(--muted-foreground)" }}
              tickFormatter={(v: number) => v.toFixed(1)}
            />
            <YAxis
              type="number"
              dataKey="pca2"
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              tick={{ fontFamily: "var(--font-mono)", fontSize: 10, fill: "var(--muted-foreground)" }}
              tickFormatter={(v: number) => v.toFixed(1)}
            />
            <ZAxis range={[18, 18]} />
            <ChartTooltip content={<ChartTooltipContent />} cursor={{ strokeDasharray: "3 3" }} />
            <ChartLegend content={<ChartLegendContent />} />
            {CLUSTERS.map((c) => (
              <Scatter
                key={c}
                name={`Cluster ${c}`}
                data={grouped[c]}
                fill={`var(--color-cluster${c})`}
                fillOpacity={0.55}
              />
            ))}
          </ScatterChart>
        </ChartContainer>
      )}
    </figure>
  )
}
