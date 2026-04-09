import { useEffect, useMemo, useState } from "react";
import {
  type ColumnDef,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useQuery, type QueryKey } from "@tanstack/react-query";
import {
  ArrowDownAZ,
  ArrowUpAZ,
  ArrowUpDown,
  Loader2,
  Search,
  Check,
} from "lucide-react";
import { Input } from "~/components/ui/input";
import { Button, buttonVariants } from "~/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "~/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "~/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "~/components/ui/command";
import { Badge } from "~/components/ui/badge";
import { Separator } from "~/components/ui/separator";
import type {
  DRFPaginatedParams,
  DRFPaginatedResponse,
} from "~/shared/types/pagination.types";
import { cn } from "~/lib/utils";

export interface FilterOption {
  value: string;
  label: string;
  isDefault?: boolean;
}

export interface FilterConfig {
  key: string;
  label: string;
  options?: FilterOption[];
  type?: "single" | "multiple";
  isSearchable?: boolean;
  /** Si es false, no permite deseleccionar la opción actual (solo para single). Por defecto true. */
  allowEmpty?: boolean;
}

interface DataTableProps<TData> {
  /** Column definitions for TanStack Table. Use `meta.orderingKey` to map to backend ordering field if it differs from accessor. */
  columns: ColumnDef<TData, unknown>[];
  /** Base query key for React Query; pagination/search/filter params are appended automatically. */
  queryKey: QueryKey;
  /** Async fetcher receiving DRF pagination/search/filter params and returning a DRF paginated response. */
  queryFn: (params: DRFPaginatedParams) => Promise<DRFPaginatedResponse<TData>>;
  /** Initial page size (maps to DRF `page_size`). Default: 10. */
  initialPageSize?: number;
  /** Initial search term (maps to DRF SearchFilter `search`). */
  initialSearch?: string;
  /** Initial ordering param (e.g. "name" or "-created_at"), used when no column sort is active. */
  initialOrdering?: string;
  /** Initial filter params; keys are sent as query params (compatible with DjangoFilterBackend). */
  initialFilters?: Record<string, string | number | boolean | string[] | undefined>;
  /** Options for page size selector. Default: [10, 20, 50]. */
  pageSizeOptions?: number[];
  /** Toggle the search box (debounced). Default: true. */
  enableSearch?: boolean;
  /** Filter dropdown configs; each key maps to a query param. */
  filterConfigs?: FilterConfig[];
  /** Custom empty-state node when there are no rows. */
  emptyState?: React.ReactNode;
  /** Column ids (or accessorKey) to disable sorting/ordering on. */
  disableOrderingColumns?: string[];
}

export function DataTable<TData>({
  columns,
  queryKey,
  queryFn,
  initialPageSize = 10,
  initialSearch = "",
  initialOrdering,
  initialFilters = {},
  pageSizeOptions = [10, 20, 50],
  enableSearch = true,
  filterConfigs = [],
  emptyState = <p className="text-sm text-muted-foreground">Sin resultados.</p>,
  disableOrderingColumns = [],
}: DataTableProps<TData>) {
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: initialPageSize,
  });
  const [search, setSearch] = useState(initialSearch);
  const [debouncedSearch, setDebouncedSearch] = useState(initialSearch);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [filters, setFilters] =
    useState<Record<string, string | number | boolean | string[] | undefined>>(
      initialFilters,
    );
  const [initializedFilters, setInitializedFilters] = useState<Set<string>>(
    new Set(Object.keys(initialFilters))
  );

  useEffect(() => {
    if (!filterConfigs || filterConfigs.length === 0) return;

    const newFilters: Record<string, string | number | boolean | string[] | undefined> = {};
    const newlyInitialized = new Set<string>();

    filterConfigs.forEach(config => {
      if (!initializedFilters.has(config.key)) {
        newlyInitialized.add(config.key);
        let defaults = config.options?.filter(o => o.isDefault).map(o => o.value) || [];

        if (defaults.length === 0 && config.allowEmpty === false && config.options && config.options.length > 0) {
          defaults = [config.options[0].value];
        }

        if (defaults.length > 0) {
          if (config.type === "multiple") {
            newFilters[config.key] = defaults;
          } else {
            newFilters[config.key] = defaults[0];
          }
        }
      }
    });

    if (newlyInitialized.size > 0) {
      setInitializedFilters(prev => {
        const updated = new Set(prev);
        newlyInitialized.forEach(k => updated.add(k));
        return updated;
      });

      if (Object.keys(newFilters).length > 0) {
        setFilters(prev => ({ ...prev, ...newFilters }));
        setPagination(prev => ({ ...prev, pageIndex: 0 }));
      }
    }
  }, [filterConfigs, initializedFilters]);

  const columnsWithOrderingControl = useMemo(() => {
    const shouldDisable = (col: ColumnDef<TData, unknown>) => {
      const colId = typeof col.id === "string" ? col.id : undefined;
      const accessor = (col as { accessorKey?: string }).accessorKey;
      const key = colId ?? accessor;
      return key ? disableOrderingColumns.includes(key) : false;
    };

    return columns.map((col) =>
      shouldDisable(col) ? { ...col, enableSorting: false } : col,
    );
  }, [columns, disableOrderingColumns]);

  useEffect(() => {
    const id = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(id);
  }, [search]);

  const orderingParam = useMemo(() => {
    if (sorting.length === 0) return initialOrdering;
    const sort = sorting[0];
    const column = columnsWithOrderingControl.find((col) => {
      const colId = typeof col.id === "string" ? col.id : undefined;
      const accessor = (col as { accessorKey?: string }).accessorKey;
      return (colId ?? accessor) === sort.id;
    });
    const orderingKey = (column?.meta as { orderingKey?: string } | undefined)
      ?.orderingKey;
    const targetKey = orderingKey ?? sort.id;
    return `${sort.desc ? "-" : ""}${targetKey}`;
  }, [sorting, initialOrdering, columnsWithOrderingControl]);

  const params: DRFPaginatedParams = {
    page: pagination.pageIndex + 1,
    page_size: pagination.pageSize,
    search: enableSearch ? debouncedSearch || undefined : undefined,
    ordering: orderingParam,
    ...filters,
  };

  const query = useQuery<DRFPaginatedResponse<TData>>({
    queryKey: [...queryKey, params],
    queryFn: () => queryFn(params),
    placeholderData: (prev) => prev,
    refetchOnWindowFocus: false,
  });

  const table = useReactTable({
    data: query.data?.results ?? [],
    columns: columnsWithOrderingControl,
    state: {
      sorting,
      pagination,
    },
    pageCount: query.data
      ? Math.ceil(query.data.count / pagination.pageSize)
      : -1,
    manualPagination: true,
    manualSorting: true,
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const totalCount = query.data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pagination.pageSize));

  const handleFilterChange = (key: string, value?: string | string[]) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }));
    setPagination((prev) => ({ ...prev, pageIndex: 0 }));
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2 items-center">
          {enableSearch && (
            <div className="relative w-64 max-w-xs">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPagination((prev) => ({ ...prev, pageIndex: 0 }));
                }}
                placeholder="Buscar..."
                className="pl-9"
              />
            </div>
          )}

          {filterConfigs.map((filter) => {
            const isMultiple = filter.type === "multiple";
            const rawValue = filters[filter.key];
            const selectedValues = new Set<string>();
            if (rawValue !== undefined && rawValue !== null) {
              if (Array.isArray(rawValue)) {
                rawValue.forEach((v) => selectedValues.add(String(v)));
              } else {
                selectedValues.add(String(rawValue));
              }
            }

            return (
              <Popover key={filter.key}>
                <PopoverTrigger className={buttonVariants({ variant: "outline", size: "sm", className: "h-9 border-dashed" })}>
                    {filter.label}
                    {selectedValues.size > 0 && (
                      <>
                        <Separator orientation="vertical" className="mx-2 h-4" />
                        <Badge
                          variant="secondary"
                          className="rounded-sm px-1 font-normal lg:hidden"
                        >
                          {selectedValues.size}
                        </Badge>
                        <div className="hidden space-x-1 lg:flex">
                          {selectedValues.size > 2 ? (
                            <Badge
                              variant="secondary"
                              className="rounded-sm px-1 font-normal"
                            >
                              {selectedValues.size} seleccionados
                            </Badge>
                          ) : (
                            filter.options
                              ?.filter((option) => selectedValues.has(option.value))
                              .map((option) => (
                                <Badge
                                  variant="secondary"
                                  key={option.value}
                                  className="rounded-sm px-1 font-normal"
                                >
                                  {option.label}
                                </Badge>
                              ))
                          )}
                        </div>
                      </>
                    )}
                </PopoverTrigger>
                <PopoverContent className="w-[200px] p-0" align="start">
                  <Command>
                    {filter.isSearchable && (
                      <CommandInput placeholder={`Buscar en ${filter.label.toLowerCase()}...`} />
                    )}
                    <CommandList>
                      <CommandEmpty>No se encontraron resultados.</CommandEmpty>
                      <CommandGroup>
                        {filter.options?.map((option) => {
                          const isSelected = selectedValues.has(option.value);
                          return (
                            <CommandItem
                              key={option.value}
                              onSelect={() => {
                                if (isMultiple) {
                                  const newSet = new Set(selectedValues);
                                  if (isSelected) {
                                    if (filter.allowEmpty === false && newSet.size <= 1) {
                                      return;
                                    }
                                    newSet.delete(option.value);
                                  } else {
                                    newSet.add(option.value);
                                  }
                                  handleFilterChange(
                                    filter.key,
                                    newSet.size > 0 ? Array.from(newSet) : undefined
                                  );
                                } else {
                                  if (isSelected) {
                                    if (filter.allowEmpty !== false) {
                                      handleFilterChange(filter.key, undefined);
                                    }
                                  } else {
                                    handleFilterChange(filter.key, option.value);
                                  }
                                }
                              }}
                            >
                              <div
                                className={cn(
                                  "mr-2 flex size-4 items-center justify-center rounded-sm border border-primary",
                                  isSelected
                                    ? "bg-primary text-primary-foreground"
                                    : "opacity-50 [&_svg]:invisible"
                                )}
                              >
                                <Check className={cn("size-4")} />
                              </div>
                              <span>{option.label}</span>
                            </CommandItem>
                          );
                        })}
                      </CommandGroup>
                      {selectedValues.size > 0 && filter.allowEmpty !== false && (
                        <>
                          <CommandSeparator />
                          <CommandGroup>
                            <CommandItem
                              onSelect={() => handleFilterChange(filter.key, undefined)}
                              className="justify-center text-center font-medium"
                            >
                              Limpiar
                            </CommandItem>
                          </CommandGroup>
                        </>
                      )}
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            );
          })}
        </div>

        <div className="flex items-center gap-2 sm:ml-auto">
          <span className="text-sm text-muted-foreground">
            Filas por página
          </span>
          <Select
            value={String(pagination.pageSize)}
            onValueChange={(value) =>
              setPagination((prev) => ({
                ...prev,
                pageSize: Number(value),
                pageIndex: 0,
              }))
            }
          >
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent align="end">
              {pageSizeOptions.map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="rounded-md border bg-card overflow-x-auto">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  if (header.isPlaceholder) return null;
                  const canSort = header.column.getCanSort();
                  const sortDir = header.column.getIsSorted();
                  return (
                    <TableHead
                      key={header.id}
                      onClick={
                        canSort
                          ? header.column.getToggleSortingHandler()
                          : undefined
                      }
                      className={cn(
                        canSort ? "cursor-pointer select-none" : "",
                        "align-middle",
                      )}
                    >
                      <div className="flex items-center gap-1">
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                        {canSort ? (
                          sortDir === "asc" ? (
                            <ArrowUpAZ className="size-4" />
                          ) : sortDir === "desc" ? (
                            <ArrowDownAZ className="size-4" />
                          ) : (
                            <ArrowUpDown className="size-4 text-muted-foreground" />
                          )
                        ) : null}
                      </div>
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {query.isLoading ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center"
                >
                  <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="size-4 animate-spin" /> Cargando...
                  </div>
                </TableCell>
              </TableRow>
            ) : table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
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
                  className="h-24 text-center"
                >
                  {emptyState}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={
              !table.getCanPreviousPage() || query.isLoading || query.isFetching
            }
          >
            Anterior
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={
              !table.getCanNextPage() || query.isLoading || query.isFetching
            }
          >
            Siguiente
          </Button>
          <span>
            Página {pagination.pageIndex + 1} de {totalPages || 1}
          </span>
        </div>
        <div>
          {query.isFetching
            ? "Actualizando..."
            : `Total: ${totalCount} registros`}
        </div>
      </div>
    </div>
  );
}
