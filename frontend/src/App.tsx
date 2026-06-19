import { useState } from "react"
import { SummaryCards } from "@/features/summary-cards"
import { ClusterTable } from "@/features/cluster-table"
import { CustomerTable } from "@/features/customer-table"
import { PcaScatter } from "@/features/pca-scatter"
import { ChurnHistogram } from "@/features/churn-histogram"
import { RfmDistributions } from "@/features/rfm-distributions"
import { ElbowPlot } from "@/features/elbow-plot"
import { Researchers } from "@/features/researchers"
import { DemoPanel } from "@/features/demo-panel"
import { SectionHeading } from "@/components/section-heading"
import { CHURN_THRESHOLDS, DEFAULT_THRESHOLD, type ChurnThreshold } from "@/lib/api"
import { cn } from "@/lib/utils"

const REVEAL =
  "animate-in fade-in-0 slide-in-from-bottom-2 duration-700 [animation-fill-mode:both]"

export default function App() {
  const [threshold, setThreshold] = useState<ChurnThreshold>(DEFAULT_THRESHOLD)

  return (
    <div className="min-h-svh bg-background text-foreground">
      <main className="mx-auto max-w-[1200px] px-6 pb-24 pt-12 md:px-10 md:pt-16">
        <header className={cn(REVEAL, "mb-20 md:mb-24")}>
          <div className="mb-10 flex items-center justify-between gap-4">
            <p className="font-mono text-[11px] uppercase tracking-[0.32em] text-muted-foreground">
              The Segmentation Report
            </p>
            <p className="font-mono text-[11px] uppercase tracking-[0.32em] text-muted-foreground">
              Vol. I &middot; 11 May 2026
            </p>
          </div>

          <div className="grid grid-cols-1 gap-y-8 md:grid-cols-12 md:gap-x-10">
            <h1 className="font-heading font-heading-display text-[44px] font-medium leading-[0.96] tracking-tight md:col-span-8 md:text-[80px]">
              Customer behaviour,
              <br className="hidden md:inline" /> in{" "}
              <em className="italic font-light text-primary">four</em> clusters.
            </h1>
            <div className="md:col-span-4 md:border-l md:border-border md:pl-6">
              <p className="text-base leading-relaxed text-foreground">
                Recency, frequency, and monetary value collapsed into
                per-customer segments &mdash; with a churn read attached to
                each.
              </p>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                Sourced from the UCI Online Retail dataset, December 2010
                through December 2011.
              </p>
              <dl className="mt-6 grid grid-cols-3 gap-4 border-t border-border pt-4 font-mono text-[10px] uppercase tracking-[0.18em]">
                <div>
                  <dt className="text-muted-foreground">Source</dt>
                  <dd className="mt-1.5 font-heading text-base normal-case tracking-normal text-foreground">
                    UCI
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Rows</dt>
                  <dd className="mt-1.5 font-heading text-base normal-case tracking-normal text-foreground">
                    541k
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Window</dt>
                  <dd className="mt-1.5 font-heading text-base normal-case tracking-normal text-foreground">
                    2010&ndash;11
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </header>

        <section className={cn(REVEAL, "delay-[90ms] mb-20")}>
          <SectionHeading number="01" label="Overview" caption="Four indicators" />
          <SummaryCards threshold={threshold} />
        </section>

        <section className={cn(REVEAL, "delay-[180ms] mb-20")}>
          <SectionHeading
            number="02"
            label="The Segments"
            caption="Means by cluster"
          />
          <ClusterTable threshold={threshold} />
        </section>

        <section className={cn(REVEAL, "delay-[270ms] mb-20")}>
          <SectionHeading
            number="03"
            label="Distribution"
            caption="PCA projection &middot; Churn density"
          />
          <div className="grid grid-cols-1 gap-px bg-border lg:grid-cols-2">
            <PcaScatter />
            <ChurnHistogram threshold={threshold} onThresholdChange={setThreshold} />
          </div>
        </section>

        <section className={cn(REVEAL, "delay-[360ms] mb-20")}>
          <SectionHeading
            number="04"
            label="Directory"
            caption="Per-customer detail"
          />
          <CustomerTable threshold={threshold} />
        </section>

        <section className={cn(REVEAL, "delay-[450ms] mb-20")}>
          <SectionHeading
            number="05"
            label="Method"
            caption="Why log-scale &middot; Why K=4"
          />
          <div className="space-y-6">
            <RfmDistributions />
            <ElbowPlot />
          </div>
        </section>

        <section className={cn(REVEAL, "delay-[540ms]")}>
          <SectionHeading
            number="06"
            label="Researchers"
            caption="Compiled by five undergraduates"

          />
          <Researchers />
        </section>

        <DemoPanel />

        <footer className={cn(REVEAL, "delay-[630ms] mt-28 text-center")}>
          <div className="mb-3 flex items-center justify-center gap-4 text-muted-foreground">
            <span className="h-px w-16 bg-border" />
            <span className="font-heading text-lg leading-none">¶</span>
            <span className="h-px w-16 bg-border" />
          </div>
          <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-muted-foreground">
            Set in Fraunces &amp; Geist &middot; End of report
          </p>
        </footer>
      </main>
    </div>
  )
}
