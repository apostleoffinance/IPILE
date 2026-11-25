"use client";
import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { ChartShell, moneyAxisFormatter, useAxisStyle, useChartPalette } from "@/components/charts/ChartShell";
type Point = { period_label: string; income: string; expenses: string; surplus: string };
export function InsightsCashFlowChart({ points }: { points: Point[] }) {
 const palette=useChartPalette(), axis=useAxisStyle();
 const option=useMemo<EChartsOption|null>(()=>!points.length?null:{
  color:[palette.accent,palette.warning,palette.gold],tooltip:{trigger:"axis"},
  legend:{data:["Income","Expenses","Surplus"],textStyle:{color:palette.muted},bottom:0},
  grid:{left:54,right:18,top:24,bottom:48},
  xAxis:{type:"category",data:points.map(p=>p.period_label),...axis},
  yAxis:{type:"value",axisLabel:{...axis.axisLabel,formatter:moneyAxisFormatter},splitLine:axis.splitLine,axisLine:axis.axisLine},
  series:[
   {name:"Income",type:"bar",barMaxWidth:28,data:points.map(p=>Number(p.income))},
   {name:"Expenses",type:"bar",barMaxWidth:28,data:points.map(p=>Number(p.expenses))},
   {name:"Surplus",type:"line",smooth:true,symbolSize:7,data:points.map(p=>Number(p.surplus))}
  ]
 },[axis,palette,points]);
 return <ChartShell option={option} height={310} empty={!points.length} dataTable={{caption:"Income, expenses and surplus by period",columns:["Period","Income","Expenses","Surplus"],rows:points.map(p=>[p.period_label,p.income,p.expenses,p.surplus])}}/>;
}
