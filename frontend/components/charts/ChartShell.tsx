"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

function readToken(name: string, fallback: string) {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

export function useChartPalette() {
  const [palette, setPalette] = useState({
    ink: "#050807",
    muted: "#4a5c56",
    accent: "#003d35",
    gold: "#c9a45c",
    warning: "#b45309",
    critical: "#b42318",
    line: "#d8d4cb",
    surface: "#ffffff",
  });

  useEffect(() => {
    function sync() {
      setPalette({
        ink: readToken("--color-text-primary", "#050807"),
        muted: readToken("--color-text-secondary", "#4a5c56"),
        accent: readToken("--color-accent-primary", "#003d35"),
        gold: readToken("--color-accent-gold", "#c9a45c"),
        warning: readToken("--color-status-warning", "#b45309"),
        critical: readToken("--color-status-critical", "#b42318"),
        line: readToken("--color-border", "#d8d4cb"),
        surface: readToken("--color-bg-surface", "#ffffff"),
      });
    }
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  return palette;
}

export function ChartShell({
  option,
  height = 280,
  empty,
  dataTable,
}: {
  option: EChartsOption | null;
  height?: number;
  empty?: boolean;
  dataTable?: {
    caption: string;
    columns: string[];
    rows: (string | number)[][];
  };
}) {
  if (empty || !option) {
    return (
      <div
        className="flex items-center justify-center border border-line bg-surface text-sm text-muted"
        style={{ height }}
      >
        Not enough data to chart yet.
      </div>
    );
  }
  return (
    <div className="border border-line bg-surface p-2">
      <div role="img" aria-label={dataTable?.caption ?? "Financial chart"}>
        <ReactECharts option={option} style={{ height, width: "100%" }} opts={{ renderer: "canvas" }} />
      </div>
      {dataTable ? (
        <details className="border-t border-line px-2 pt-2 text-sm">
          <summary className="cursor-pointer text-muted">View data table</summary>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-left text-xs">
              <caption className="sr-only">{dataTable.caption}</caption>
              <thead className="border-b border-line text-muted">
                <tr>{dataTable.columns.map((column) => <th key={column} className="px-2 py-2 font-medium">{column}</th>)}</tr>
              </thead>
              <tbody>
                {dataTable.rows.map((row, index) => (
                  <tr key={index} className="border-b border-line last:border-0">
                    {row.map((value, cellIndex) => <td key={cellIndex} className="px-2 py-2 tabular">{value}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ) : null}
    </div>
  );
}

export function moneyAxisFormatter(value: number) {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}m`;
  if (abs >= 1_000) return `${(value / 1_000).toFixed(0)}k`;
  return String(value);
}

export function useAxisStyle() {
  const palette = useChartPalette();
  return useMemo(
    () => ({
      axisLine: { lineStyle: { color: palette.line } },
      axisLabel: { color: palette.muted, fontSize: 11 },
      splitLine: { lineStyle: { color: palette.line, opacity: 0.45 } },
    }),
    [palette],
  );
}
