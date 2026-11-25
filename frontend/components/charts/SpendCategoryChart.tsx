"use client";
import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { ChartShell, moneyAxisFormatter, useAxisStyle, useChartPalette } from "@/components/charts/ChartShell";
type Point={category:string;amount:string};
export function SpendCategoryChart({points}:{points:Point[]}) {
 const palette=useChartPalette(),axis=useAxisStyle();
 const option=useMemo<EChartsOption|null>(()=>!points.length?null:{
  color:[palette.accent],tooltip:{trigger:"axis",axisPointer:{type:"shadow"}},
  grid:{left:120,right:28,top:14,bottom:24},
  xAxis:{type:"value",axisLabel:{...axis.axisLabel,formatter:moneyAxisFormatter},splitLine:axis.splitLine,axisLine:axis.axisLine},
  yAxis:{type:"category",inverse:true,data:points.map(p=>p.category),axisLabel:{color:palette.muted,width:105,overflow:"truncate"},axisLine:axis.axisLine,axisTick:{show:false}},
  series:[{type:"bar",barMaxWidth:22,showBackground:true,backgroundStyle:{color:palette.line,opacity:.22,borderRadius:5},itemStyle:{borderRadius:[0,5,5,0]},data:points.map(p=>Number(p.amount))}]
 },[axis,palette,points]);
 return <ChartShell option={option} height={Math.max(230,points.length*42)} empty={!points.length} dataTable={{caption:"Spending by category",columns:["Category","Amount"],rows:points.map(p=>[p.category,p.amount])}}/>;
}
