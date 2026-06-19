type Props = {
  number: string
  label: string
  caption?: string
  action?: React.ReactNode
}

export function SectionHeading({ number, label, caption, action }: Props) {
  return (
    <div className="mb-8 grid grid-cols-[64px_1fr] items-end gap-x-5 md:grid-cols-[96px_1fr] md:gap-x-8">
      <span
        aria-hidden
        className="font-heading font-heading-display text-[80px] font-light leading-[0.78] text-primary md:text-[112px]"
      >
        {number}
      </span>
      <div className="flex items-end justify-between gap-6 border-b border-border pb-3">
        <div className="flex items-baseline gap-5">
          <h2 className="font-heading text-xl font-medium leading-none tracking-tight md:text-2xl">
            {label}
          </h2>
          {caption && (
            <span className="hidden font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground md:inline">
              {caption}
            </span>
          )}
        </div>
        {action}
      </div>
    </div>
  )
}
