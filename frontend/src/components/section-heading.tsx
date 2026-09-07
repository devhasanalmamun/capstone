type Props = {
  label: string
  caption?: string
  action?: React.ReactNode
}

export function SectionHeading({ label, caption, action }: Props) {
  return (
    <div className="mb-8 flex items-end justify-between gap-6 border-b border-border pb-3">
      <div className="flex items-baseline gap-5">
        <h2 className="font-heading text-3xl font-medium leading-none tracking-tight md:text-4xl">
          {label}
        </h2>
        {caption && (
          <span className="hidden font-mono text-[12px] uppercase tracking-[0.22em] text-muted-foreground md:inline">
            {caption}
          </span>
        )}
      </div>
      {action}
    </div>
  )
}
