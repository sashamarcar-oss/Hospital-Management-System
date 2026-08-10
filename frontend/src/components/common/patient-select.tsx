import { useEffect, useState } from "react";
import { Check, ChevronsUpDown, Search, UserRound } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PatientSummary } from "@/lib/types";
import { cn, formatAge } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Input } from "@/components/ui/input";

export function PatientSelect({
  value,
  onChange,
  placeholder = "Search patient by name, number, phone…",
  excludePatientId,
  allowNone = false,
}: {
  value: number | null;
  onChange: (id: number | null) => void;
  placeholder?: string;
  excludePatientId?: number;
  allowNone?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [manualId, setManualId] = useState<number | null>(value);
  const [selected, setSelected] = useState<PatientSummary | null>(null);

  useEffect(() => {
    setManualId(value);
  }, [value]);

  const { data: results, isLoading } = useQuery({
    queryKey: ["patients", "search", query],
    queryFn: () =>
      api
        .get<PatientSummary[]>("/patients/search/", { params: { q: query, limit: 20 } })
        .then((r) => r.data),
    enabled: open,
  });

  const list = (results ?? []).filter((p) => p.id !== excludePatientId);

  const pick = (p: PatientSummary | null) => {
    setSelected(p);
    setManualId(p?.id ?? null);
    onChange(p?.id ?? null);
    setOpen(false);
  };

  return (
    <div className="space-y-2">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full justify-between font-normal"
          >
            {selected ? (
              <span className="flex items-center gap-2">
                <UserRound className="size-4 text-muted-foreground" />
                {selected.full_name}
                <span className="text-muted-foreground text-xs">
                  {selected.patient_number} · {formatAge(selected.date_of_birth)}
                </span>
              </span>
            ) : (
              <span className="text-muted-foreground">{placeholder}</span>
            )}
            <ChevronsUpDown className="size-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-full p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="Search patients…"
              value={query}
              onValueChange={setQuery}
            />
            <CommandList>
              <CommandEmpty>
                {isLoading ? "Searching…" : "No patients found"}
              </CommandEmpty>
              <CommandGroup>
                {list.map((p) => (
                  <CommandItem
                    key={p.id}
                    value={String(p.id)}
                    onSelect={() => pick(p)}
                    className="flex items-center justify-between"
                  >
                    <span>
                      <span className="font-medium">{p.full_name}</span>
                      <span className="text-muted-foreground ml-2 text-xs">
                        {p.patient_number} · {formatAge(p.date_of_birth)} · {p.gender}
                      </span>
                    </span>
                    {manualId === p.id && <Check className="size-4 text-primary" />}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
          <Input
            type="number"
            placeholder="Or enter patient ID"
            value={manualId ?? ""}
            onChange={(e) => {
              const id = e.target.value ? Number(e.target.value) : null;
              setManualId(id);
              onChange(id);
              setSelected(null);
            }}
            className="pl-8"
          />
        </div>
        {allowNone && manualId && (
          <Button variant="ghost" size="sm" type="button" onClick={() => pick(null)}>
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}
