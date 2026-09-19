"use client";

import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { ChartShell, useChartPalette } from "@/components/charts/ChartShell";
import type { AllocationLine } from "@/lib/api";

export function AllocationChart({
  lines,
  height = 280,
}: {
  lines: AllocationLine[];
  height?: number;
}) {
  const palette = useChartPalette();

  const option = useMemo<EChartsOption | null>(() => {
    const data = lines
      .filter((line) => Number(line.amount) > 0)
      .map((line) => ({
        name: line.name,
        value: Number(line.amount),
        itemStyle: { color: line.funded ? undefined : palette.critical },
      }));
    if (!data.length) return null;
    return {
      color: [palette.accent, palette.gold, "#0a5c50", "#1d4e63", "#5b7c6e", "#8a6a2e"],
      tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
      legend: {
        type: "scroll",
        orient: "vertical",
        right: 8,
        top: "middle",
        textStyle: { color: palette.muted, fontSize: 11 },
      },
      series: [
        {
          type: "pie",
          radius: ["42%", "68%"],
          center: ["38%", "50%"],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: palette.surface, borderWidth: 2 },
          label: { color: palette.ink, formatter: "{b}" },
          data,
        },
      ],
    };
  }, [lines, palette]);

  return (
    <ChartShell
      option={option}
      height={height}
      empty={!lines.some((l) => Number(l.amount) > 0)}
      dataTable={{
        caption: "Money allocation",
        columns: ["Destination", "Amount", "Status"],
        rows: lines
          .filter((line) => Number(line.amount) > 0)
          .map((line) => [line.name, line.amount, line.funded ? "Funded" : "Needs attention"]),
      }}
    />
  );
}
