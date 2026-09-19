"use client";

import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { ChartShell, moneyAxisFormatter, useAxisStyle, useChartPalette } from "@/components/charts/ChartShell";

export function NetWorthChart({
  points,
  height = 280,
}: {
  points: { label: string; net_worth: string }[];
  height?: number;
}) {
  const palette = useChartPalette();
  const axis = useAxisStyle();

  const option = useMemo<EChartsOption | null>(() => {
    if (!points.length) return null;
    return {
      color: [palette.accent],
      tooltip: { trigger: "axis" },
      grid: { left: 52, right: 16, top: 24, bottom: 32 },
      xAxis: {
        type: "category",
        data: points.map((p) => p.label),
        ...axis,
      },
      yAxis: {
        type: "value",
        axisLabel: { ...axis.axisLabel, formatter: moneyAxisFormatter },
        splitLine: axis.splitLine,
        axisLine: axis.axisLine,
      },
      series: [
        {
          name: "Net worth",
          type: "line",
          smooth: true,
          areaStyle: { color: palette.accent, opacity: 0.12 },
          data: points.map((p) => Number(p.net_worth)),
        },
      ],
    };
  }, [axis, palette, points]);

  return (
    <ChartShell
      option={option}
      height={height}
      empty={!points.length}
      dataTable={{
        caption: "Net worth over time",
        columns: ["Period", "Net worth"],
        rows: points.map((point) => [point.label, point.net_worth]),
      }}
    />
  );
}
