"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type CommandItem = { label: string; href: string; keywords?: string };

export function CommandMenu({ items, className }: { items: CommandItem[]; className?: string }) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((item) => `${item.label} ${item.keywords ?? ""}`.toLowerCase().includes(needle));
  }, [items, query]);

  return (
    <div className={cn("border border-line bg-surface p-3", className)} role="search">
      <label className="sr-only" htmlFor="command-search">Search IPÌLẸ̀</label>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted" aria-hidden="true" />
        <Input id="command-search" value={query} onChange={(event) => setQuery(event.target.value)} className="pl-9" placeholder="Search pages" />
      </div>
      <div className="mt-2 max-h-64 overflow-y-auto" role="listbox" aria-label="Search results">
        {filtered.length ? filtered.map((item) => (
          <a key={item.href} href={item.href} className="block px-3 py-2 text-sm hover:bg-subtle" role="option">
            {item.label}
          </a>
        )) : <p className="px-3 py-2 text-sm text-muted">No matching pages.</p>}
      </div>
    </div>
  );
}