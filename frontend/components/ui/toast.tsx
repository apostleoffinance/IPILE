"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

type ToastItem = {
  id: string;
  title: string;
  description?: string;
};

const ToastContext = React.createContext<{
  toast: (item: Omit<ToastItem, "id">) => void;
} | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = React.useState<ToastItem[]>([]);

  const toast = React.useCallback((item: Omit<ToastItem, "id">) => {
    const id = crypto.randomUUID();
    setItems((prev) => [...prev, { ...item, id }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((row) => row.id !== id));
    }, 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div
        className="pointer-events-none fixed bottom-20 right-4 z-[60] flex w-80 flex-col gap-2 md:bottom-6"
        aria-live="polite"
        aria-relevant="additions"
      >
        {items.map((item) => (
          <div
            key={item.id}
            className={cn("pointer-events-auto border border-line bg-surface px-4 py-3 shadow-soft")}
            role="status"
          >
            <p className="text-sm font-medium text-ink">{item.title}</p>
            {item.description ? <p className="mt-1 text-xs text-muted">{item.description}</p> : null}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) {
    return {
      toast: (item: Omit<ToastItem, "id">) => {
        if (typeof window !== "undefined") {
          window.console.info("[toast]", item.title, item.description ?? "");
        }
      },
    };
  }
  return ctx;
}
