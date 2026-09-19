"use client";

import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { ChartShell, moneyAxisFormatter, useAxisStyle, useChartPalette } from "@/components/charts/ChartShell";
import type { CashFlowDay } from "@/lib/api";

export function CashFlowChart({
  days,
  height = 300,
}: {
  days: CashFlowDay[];
  height?: number;
}) {
  const palette = useChartPalette();
  const axis = useAxisStyle();

  const option = useMemo<EChartsOption | null>(() => {
    if (!days.length) return null;
    return {
      color: [palette.accent, palette.warning, palette.gold, palette.ink],
      tooltip: { trigger: "axis" },
      legend: {
        data: ["Income", "Expenses", "Giving", "Closing cash"],
        textStyle: { color: palette.muted },
        bottom: 0,
      },
      grid: { left: 48, right: 16, top: 24, bottom: 48 },
      xAxis: {
        type: "category",
        data: days.map((d) => d.date.slice(5)),
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
          name: "Income",
          type: "bar",
          stack: "flow",
          data: days.map((d) => Number(d.income)),
        },
        {
          name: "Expenses",
          type: "bar",
          stack: "out",
          data: days.map((d) => Number(d.expenses)),
        },
        {
          name: "Giving",
          type: "bar",
          stack: "out",
          data: days.map((d) => Number(d.giving)),
        },
        {
          name: "Closing cash",
          type: "line",
          smooth: true,
          data: days.map((d) => Number(d.closing_cash)),
        },
      ],
    };
  }, [axis, days, palette]);

  return (
    <ChartShell
      option={option}
      height={height}
      empty={!days.length}
      dataTable={{
        caption: "Cash flow by day",
        columns: ["Date", "Income", "Expenses", "Giving", "Closing cash"],
        rows: days.map((day) => [day.date, day.income, day.expenses, day.giving, day.closing_cash]),
      }}
    />
  );
}
