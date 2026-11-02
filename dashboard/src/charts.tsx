import {
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AnalyticsData } from "./types";

const formatNumber = (value: number, digits = 0) =>
  new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);

function lastValueIndex<T, K extends keyof T>(
  rows: readonly T[],
  key: K,
  isPresent: (value: T[K]) => boolean,
): number {
  for (let index = rows.length - 1; index >= 0; index -= 1) {
    if (isPresent(rows[index][key])) return index;
  }
  return -1;
}

export function OverviewChart({
  data,
  asOf,
}: {
  data: AnalyticsData["overview"]["series"];
  asOf: string;
}) {
  const actualIndex = lastValueIndex(data, "actual_demand", (value) => value !== null);
  const forecastIndex = lastValueIndex(data, "forecast_demand", (value) => value !== null);
  const supplyIndex = lastValueIndex(data, "supply", () => true);
  const actualWeek = actualIndex >= 0 ? data[actualIndex].week : null;
  const forecastWeek = forecastIndex >= 0 ? data[forecastIndex].week : null;
  const supplyWeek = supplyIndex >= 0 ? data[supplyIndex].week : null;
  const actualValue = actualIndex >= 0 ? data[actualIndex].actual_demand : null;
  const forecastValue = forecastIndex >= 0 ? data[forecastIndex].forecast_demand : null;
  const supplyValue = supplyIndex >= 0 ? data[supplyIndex].supply : null;
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 16, right: 120, left: 0, bottom: 4 }}>
        <XAxis dataKey="week" tickLine={false} axisLine={false} minTickGap={28} />
        <YAxis tickLine={false} axisLine={false} width={36} />
        <Tooltip
          contentStyle={{
            background: "var(--surface)",
            border: "1px solid var(--hairline)",
            borderRadius: 10,
          }}
          formatter={(value) => [formatNumber(Number(value ?? 0), 1), ""]}
          labelStyle={{ color: "var(--secondary)" }}
        />
        <ReferenceLine
          x={asOf}
          stroke="var(--ink)"
          strokeDasharray="2 4"
          label={{ value: "As of", position: "insideTopRight", fill: "var(--secondary)", fontSize: 11 }}
        />
        <Line dataKey="actual_demand" name="Actual demand" stroke="var(--ink)" strokeWidth={2} dot={false} connectNulls={false} animationDuration={600}>
        </Line>
        <Line dataKey="forecast_demand" name="Forecast demand" stroke="var(--ink)" strokeWidth={2} strokeDasharray="6 5" dot={false} connectNulls={false} animationDuration={600}>
        </Line>
        <Line dataKey="supply" name="Available supply" stroke="var(--muted-line)" strokeWidth={1.5} dot={false} animationDuration={600}>
        </Line>
        {actualWeek && actualValue !== null && <ReferenceDot x={actualWeek} y={actualValue} r={0} label={{ value: "Actual demand", position: "right", fill: "var(--secondary)", fontSize: 10 }} />}
        {forecastWeek && forecastValue !== null && <ReferenceDot x={forecastWeek} y={forecastValue} r={0} label={{ value: "Forecast", position: "right", fill: "var(--secondary)", fontSize: 10 }} />}
        {supplyWeek && supplyValue !== null && <ReferenceDot x={supplyWeek} y={supplyValue} r={0} label={{ value: "Available supply", position: "right", fill: "var(--secondary)", fontSize: 10 }} />}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ForecastChart({
  rows,
  asOf,
}: {
  rows: { week: string; actual: number | null; forecast: number | null }[];
  asOf: string;
}) {
  const actualIndex = lastValueIndex(rows, "actual", (value) => value !== null);
  const forecastIndex = lastValueIndex(rows, "forecast", (value) => value !== null);
  const actualWeek = actualIndex >= 0 ? rows[actualIndex].week : null;
  const forecastWeek = forecastIndex >= 0 ? rows[forecastIndex].week : null;
  const actualValue = actualIndex >= 0 ? rows[actualIndex].actual : null;
  const forecastValue = forecastIndex >= 0 ? rows[forecastIndex].forecast : null;
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={rows} margin={{ top: 16, right: 58, left: 0, bottom: 4 }}>
        <XAxis dataKey="week" tickLine={false} axisLine={false} minTickGap={24} />
        <YAxis tickLine={false} axisLine={false} width={36} />
        <Tooltip
          contentStyle={{
            background: "var(--surface)",
            border: "1px solid var(--hairline)",
            borderRadius: 10,
          }}
          formatter={(value) => [formatNumber(Number(value ?? 0), 2), ""]}
          labelStyle={{ color: "var(--secondary)" }}
        />
        <ReferenceLine
          x={asOf}
          stroke="var(--ink)"
          strokeDasharray="2 4"
          label={{ value: "As of", position: "insideTopRight", fill: "var(--secondary)", fontSize: 11 }}
        />
        <Line dataKey="actual" name="Actual" stroke="var(--ink)" strokeWidth={2} dot={false} connectNulls={false} animationDuration={600}>
        </Line>
        <Line dataKey="forecast" name="Forecast" stroke="var(--ink)" strokeWidth={2} strokeDasharray="6 5" dot={false} connectNulls={false} animationDuration={600}>
        </Line>
        {actualWeek && actualValue !== null && <ReferenceDot x={actualWeek} y={actualValue} r={0} label={{ value: "Actual", position: "right", fill: "var(--secondary)", fontSize: 10 }} />}
        {forecastWeek && forecastValue !== null && <ReferenceDot x={forecastWeek} y={forecastValue} r={0} label={{ value: "Forecast", position: "right", fill: "var(--secondary)", fontSize: 10 }} />}
      </LineChart>
    </ResponsiveContainer>
  );
}
