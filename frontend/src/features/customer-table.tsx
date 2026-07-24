import { useState } from "react"
import { Dialog, Slider } from "radix-ui"
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import {
  type ColumnDef,
  type PaginationState,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { api, type ChurnThreshold, type Customer } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCurrency, formatNumber, formatPercent } from "@/lib/format"

const PAGE_SIZE = 25
const CLUSTER_OPTIONS = [0, 1, 2, 3]

const SWATCH_VARS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
]

const columns: ColumnDef<Customer>[] = [
  {
    accessorKey: "customer_id",
    header: "Customer",
    cell: ({ row }) => (
      <span className="font-mono tabular-nums">{row.original.customer_id}</span>
    ),
  },
  {
    accessorKey: "email",
    header: "Email",
    cell: ({ row }) => (
      <span className="font-mono text-xs text-muted-foreground select-all">{row.original.email ?? "—"}</span>
    ),
  },
  {
    accessorKey: "recency",
    header: () => <div className="text-right">Recency</div>,
    cell: ({ row }) => (
      <div className="text-right font-mono tabular-nums">
        {formatNumber(row.original.recency)}
      </div>
    ),
  },
  {
    accessorKey: "frequency",
    header: () => <div className="text-right">Frequency</div>,
    cell: ({ row }) => (
      <div className="text-right font-mono tabular-nums">
        {formatNumber(row.original.frequency)}
      </div>
    ),
  },
  {
    accessorKey: "monetary",
    header: () => <div className="text-right">Monetary</div>,
    cell: ({ row }) => (
      <div className="text-right font-mono tabular-nums">
        {formatCurrency(row.original.monetary)}
      </div>
    ),
  },
  {
    accessorKey: "cluster",
    header: () => <div className="text-right">Cluster</div>,
    cell: ({ row }) => (
      <div className="flex items-center justify-end gap-2">
        <span
          aria-hidden
          className="h-2 w-2"
          style={{
            background:
              SWATCH_VARS[row.original.cluster % SWATCH_VARS.length],
          }}
        />
        <span className="font-mono tabular-nums">{row.original.cluster}</span>
      </div>
    ),
  },
  {
    accessorKey: "churn_prob",
    header: () => <div className="text-right">Churn p</div>,
    cell: ({ row }) => (
      <div className="text-right font-mono tabular-nums">
        {formatPercent(row.original.churn_prob, 2)}
      </div>
    ),
  },
]

export function CustomerTable({ threshold }: { threshold: ChurnThreshold }) {
  const [cluster, setCluster] = useState<number | "all">("all")
  const [churnRange, setChurnRange] = useState<[number, number]>([0, 1])
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(null)
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: PAGE_SIZE,
  })

  const { data, isLoading, isFetching, isPlaceholderData, error } = useQuery({
    queryKey: [
      "customers",
      cluster,
      pagination.pageIndex,
      pagination.pageSize,
      threshold,
      churnRange,
    ],
    queryFn: () =>
      api.customers({
        cluster: cluster === "all" ? undefined : cluster,
        limit: pagination.pageSize,
        offset: pagination.pageIndex * pagination.pageSize,
        threshold,
        churn_min: churnRange[0],
        churn_max: churnRange[1],
      }),
    placeholderData: keepPreviousData,
  })

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    rowCount: data?.total ?? 0,
    state: { pagination },
    onPaginationChange: setPagination,
  })

  const pageIndex = table.getState().pagination.pageIndex
  const pageCount = Math.max(1, table.getPageCount())

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-4">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground mr-auto">
          {data ? `${formatNumber(data.total)} matching records` : " "}
        </p>

        {/* Churn probability range slider */}
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground whitespace-nowrap">
            Churn p
          </span>
          <Slider.Root
            min={0}
            max={1}
            step={0.01}
            value={churnRange}
            onValueChange={(v) => {
              setChurnRange(v as [number, number])
              setPagination((p) => ({ ...p, pageIndex: 0 }))
            }}
            className="relative flex w-36 touch-none select-none items-center"
          >
            <Slider.Track className="relative h-px w-full grow bg-border">
              <Slider.Range className="absolute h-full bg-foreground" />
            </Slider.Track>
            <Slider.Thumb className="block h-3 w-3 border border-foreground bg-background transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-foreground" />
            <Slider.Thumb className="block h-3 w-3 border border-foreground bg-background transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-foreground" />
          </Slider.Root>
          <span className="w-24 font-mono text-[10px] tabular-nums text-muted-foreground">
            {Math.round(churnRange[0] * 100)}% – {Math.round(churnRange[1] * 100)}%
          </span>
        </div>

        {/* Cluster filter */}
        <Select
          value={String(cluster)}
          onValueChange={(v) => {
            setPagination((p) => ({ ...p, pageIndex: 0 }))
            setCluster(v === "all" ? "all" : Number(v))
          }}
        >
          <SelectTrigger className="h-9 w-44 border-foreground/30 font-mono text-xs uppercase tracking-wider">
            <SelectValue placeholder="Filter" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all" className="font-mono text-xs uppercase tracking-wider">
              All clusters
            </SelectItem>
            {CLUSTER_OPTIONS.map((c) => (
              <SelectItem
                key={c}
                value={String(c)}
                className="font-mono text-xs uppercase tracking-wider"
              >
                Cluster {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {error ? (
        <p className="text-destructive">Failed to load customers.</p>
      ) : isLoading || !data ? (
        <Skeleton className="h-96 w-full" />
      ) : (
        <div
          className={cn(
            "transition-opacity duration-200",
            (isPlaceholderData || isFetching) && "opacity-40",
          )}
        >
          <div className="border-b border-border">
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow
                    key={headerGroup.id}
                    className="border-border hover:bg-transparent"
                  >
                    {headerGroup.headers.map((header) => (
                      <TableHead
                        key={header.id}
                        className="h-9 px-4 font-mono text-[10px] font-normal uppercase tracking-[0.18em] text-muted-foreground"
                      >
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows.length ? (
                  table.getRowModel().rows.map((row) => (
                    <TableRow
                      key={row.id}
                      onClick={() => setSelectedCustomerId(row.original.customer_id)}
                      className="border-border hover:bg-muted/40 cursor-pointer transition-colors"
                    >
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id} className="px-4 py-3">
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext(),
                          )}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell
                      colSpan={columns.length}
                      className="h-24 px-4 text-center font-mono text-xs uppercase tracking-widest text-muted-foreground"
                    >
                      No matching customers
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
          <div className="mt-4 flex items-center justify-between font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            <span>
              Page {pageIndex + 1} / {pageCount}
            </span>
            <div className="flex items-center gap-6">
              <button
                type="button"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className="cursor-pointer uppercase tracking-[0.22em] text-foreground transition-colors hover:text-primary disabled:cursor-not-allowed disabled:text-muted-foreground/40 disabled:hover:text-muted-foreground/40"
              >
                &larr; Previous
              </button>
              <button
                type="button"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className="cursor-pointer uppercase tracking-[0.22em] text-foreground transition-colors hover:text-primary disabled:cursor-not-allowed disabled:text-muted-foreground/40 disabled:hover:text-muted-foreground/40"
              >
                Next &rarr;
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedCustomerId !== null && (
        <CustomerTransactionsModal
          customerId={selectedCustomerId}
          threshold={threshold}
          onClose={() => setSelectedCustomerId(null)}
        />
      )}
    </div>
  )
}

function CustomerTransactionsModal({
  customerId,
  threshold,
  onClose,
}: {
  customerId: number
  threshold: ChurnThreshold
  onClose: () => void
}) {
  const [ignoreThreshold, setIgnoreThreshold] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ["customer-transactions", customerId, threshold, ignoreThreshold],
    queryFn: () => api.customerTransactions(customerId, threshold, ignoreThreshold),
  })

  return (
    <Dialog.Root open={true} onOpenChange={(open) => { if (!open) onClose() }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-background/60 backdrop-blur-xs animate-in fade-in-0" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 border border-border bg-background p-6 shadow-2xl duration-200 animate-in fade-in-0 zoom-in-95 max-h-[85vh] flex flex-col">
          {/* Header */}
          <div className="flex items-start justify-between border-b border-border pb-4">
            <div>
              <div className="flex items-center gap-2">
                <Dialog.Title className="font-mono text-base font-semibold tracking-wider text-foreground">
                  Customer #{customerId}
                </Dialog.Title>
                {data?.cluster !== undefined && (
                  <span
                    className="inline-flex items-center gap-1.5 px-2 py-0.5 font-mono text-[10px] uppercase font-medium border"
                    style={{
                      borderColor: SWATCH_VARS[data.cluster % SWATCH_VARS.length],
                      color: SWATCH_VARS[data.cluster % SWATCH_VARS.length],
                    }}
                  >
                    Cluster {data.cluster}
                  </span>
                )}
              </div>
              {data?.email && (
                <p className="mt-1 font-mono text-xs text-muted-foreground select-all">
                  {data.email}
                </p>
              )}
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                onClick={onClose}
                className="cursor-pointer border border-border bg-muted/20 px-2.5 py-1 font-mono text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                ✕ Close
              </button>
            </Dialog.Close>
          </div>

          {/* Threshold Filter Toggle Control */}
          <div className="my-3 flex items-center justify-between border-b border-border pb-3">
            <label className="flex items-center gap-2 cursor-pointer select-none font-mono text-[11px] uppercase tracking-wider text-muted-foreground hover:text-foreground">
              <input
                type="checkbox"
                checked={ignoreThreshold}
                onChange={(e) => setIgnoreThreshold(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-border accent-primary cursor-pointer"
              />
              <span>Show All Transactions (Ignore {threshold}-Day Threshold)</span>
            </label>
            {ignoreThreshold && (
              <span className="font-mono text-[10px] uppercase tracking-wider text-primary font-medium bg-primary/10 px-2 py-0.5 border border-primary/20">
                All-Time View
              </span>
            )}
          </div>

          {/* Body */}
          {isLoading ? (
            <div className="py-12 text-center font-mono text-xs uppercase tracking-widest text-muted-foreground">
              Loading transaction history…
            </div>
          ) : error || !data ? (
            <div className="py-12 text-center font-mono text-xs text-destructive">
              Failed to load transaction history.
            </div>
          ) : (
            <>
              {/* Summary Stats Header */}
              <div className="mb-4 grid grid-cols-3 gap-px bg-border text-[11px]">
                <div className="bg-muted/10 p-2.5 text-center font-mono">
                  <span className="block text-[9px] uppercase tracking-widest text-muted-foreground">Recency</span>
                  <span className="font-semibold text-foreground">{data.recency} days</span>
                </div>
                <div className="bg-muted/10 p-2.5 text-center font-mono">
                  <span className="block text-[9px] uppercase tracking-widest text-muted-foreground">Frequency</span>
                  <span className="font-semibold text-foreground">{data.frequency} orders</span>
                </div>
                <div className="bg-muted/10 p-2.5 text-center font-mono">
                  <span className="block text-[9px] uppercase tracking-widest text-muted-foreground">Total Revenue</span>
                  <span className="font-semibold text-foreground">{formatCurrency(data.monetary)}</span>
                </div>
              </div>

              {/* Transactions List */}
              <div className="flex-1 overflow-y-auto border border-border">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border bg-muted/20 hover:bg-transparent">
                      <TableHead className="h-8 px-3 font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Invoice No</TableHead>
                      <TableHead className="h-8 px-3 font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Exact Date & Time</TableHead>
                      <TableHead className="h-8 px-3 font-mono text-[9px] uppercase tracking-wider text-muted-foreground text-right">Quantity</TableHead>
                      <TableHead className="h-8 px-3 font-mono text-[9px] uppercase tracking-wider text-muted-foreground text-right">Transaction Value</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.transactions.length ? (
                      data.transactions.map((tx, idx) => (
                        <TableRow key={idx} className="border-border hover:bg-muted/30">
                          <TableCell className="px-3 py-2 font-mono text-xs font-medium tabular-nums">{tx.invoice_no}</TableCell>
                          <TableCell className="px-3 py-2 font-mono text-xs text-muted-foreground tabular-nums">{tx.invoice_date}</TableCell>
                          <TableCell className="px-3 py-2 font-mono text-xs text-right tabular-nums">{formatNumber(tx.quantity)}</TableCell>
                          <TableCell className="px-3 py-2 font-mono text-xs text-right font-medium tabular-nums text-foreground">{formatCurrency(tx.total_value)}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4} className="h-16 text-center font-mono text-xs text-muted-foreground">
                          No transactions found
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Footer Total */}
              <div className="mt-4 border-t border-border pt-3 flex items-center justify-between font-mono text-xs">
                <span className="text-muted-foreground uppercase tracking-wider">
                  Total Transactions: <strong className="text-foreground">{data.total_transactions}</strong> ({formatNumber(data.total_quantity_all)} items)
                </span>
                <div className="flex items-center gap-2">
                  <span className="uppercase tracking-widest text-muted-foreground text-[10px]">Total Value of All Transactions:</span>
                  <span className="text-base font-bold text-foreground bg-muted/40 px-2.5 py-1 border border-border">
                    {formatCurrency(data.total_value_all)}
                  </span>
                </div>
              </div>
            </>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
