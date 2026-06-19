const RESEARCHERS = [
  { name: "S.M. Tahmidul Islam", roll: "21223203044" },
  { name: "Hasan Al Mamun", roll: "21223203037" },
  { name: "Mahbubul Alam Marin", roll: "2122303026" },
  { name: "Mahbubur Raman Mahfuj", roll: "21223203036" },
  { name: "Aminul Islam", roll: "21223203025" },
]

export function Researchers() {
  return (
    <div className="grid grid-cols-1 gap-px bg-border sm:grid-cols-2 lg:grid-cols-5">
      {RESEARCHERS.map((r, i) => (
        <div
          key={r.roll}
          className="flex min-h-[180px] flex-col justify-start bg-background p-7 pb-8 transition-colors hover:bg-secondary/50"
        >
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Researcher &middot; {String(i + 1).padStart(2, "0")}
          </p>
          <div>
            <p className="font-heading text-[22px] font-medium leading-[1.1] tracking-tight mt-6">
              {r.name}
            </p>
            <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              {r.roll}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
