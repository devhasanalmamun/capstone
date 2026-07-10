import { useState } from "react"
import { Slider } from "radix-ui"
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
                      className="border-border hover:bg-muted/40"
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
    </div>
  )
}
