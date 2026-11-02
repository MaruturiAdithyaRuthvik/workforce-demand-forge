import * as Dialog from "@radix-ui/react-dialog";
import * as Select from "@radix-ui/react-select";
import * as Tooltip from "@radix-ui/react-tooltip";
import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { Command } from "cmdk";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Check,
  ChevronDown,
  Command as CommandIcon,
  Database,
  FileCheck2,
  GitBranch,
  Grid2X2,
  Layers3,
  Moon,
  Search,
  Sun,
  X,
} from "lucide-react";
import {
  Fragment,
  useCallback,
  useEffect,
  lazy,
  useMemo,
  useState,
  Suspense,
  type ReactNode,
} from "react";
import type {
  ActionTuple,
  AnalyticsData,
  EvaluationData,
  ForecastMethod,
  GapTraceTuple,
} from "./types";

const OverviewChart = lazy(() => import("./charts").then((module) => ({ default: module.OverviewChart })));
const ForecastChart = lazy(() => import("./charts").then((module) => ({ default: module.ForecastChart })));

type PageId = "overview" | "forecast" | "gaps" | "decisions" | "health";
type ThemeMode = "system" | "light" | "dark";
type Action = {
  id: string;
  gapId: string | null;
  type: string;
  employee: string | null;
  skill: string | null;
  owner: string;
  status: string;
  rule: string;
  cost: number;
  assumptions: string;
};

const pages: { id: PageId; label: string; icon: typeof Activity }[] = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "forecast", label: "Demand and forecast", icon: Activity },
  { id: "gaps", label: "Skill gaps", icon: Grid2X2 },
  { id: "decisions", label: "Decisions", icon: GitBranch },
  { id: "health", label: "Anomalies and data health", icon: FileCheck2 },
];

const methods: { id: ForecastMethod; label: string }[] = [
  { id: "moving_average_4w", label: "Moving average" },
  { id: "pipeline_adjusted", label: "Pipeline" },
  { id: "pipeline_realization_adjusted", label: "Realization-adjusted" },
];

const compactAction = (row: ActionTuple): Action => ({
  id: row[0],
  gapId: row[1],
  type: row[2],
  employee: row[3],
  skill: row[4],
  owner: row[5],
  status: row[6],
  rule: row[7],
  cost: row[8],
  assumptions: row[9],
});

function readPage(): PageId {
  const value = new URLSearchParams(window.location.search).get("page");
  return pages.some((page) => page.id === value) ? (value as PageId) : "overview";
}

function initialTheme(): ThemeMode {
  const saved = window.localStorage.getItem("workforce-theme");
  return saved === "light" || saved === "dark" ? saved : "system";
}

function isoWeek(dateString: string): string {
  const date = new Date(`${dateString}T00:00:00Z`);
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return `${date.getUTCFullYear()}W${String(week).padStart(2, "0")}`;
}

function formatNumber(value: number, digits = 0): string {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatMethod(method: ForecastMethod): string {
  return methods.find((entry) => entry.id === method)?.label ?? method;
}

function useAnalytics(): { data: AnalyticsData | null; error: string | null } {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/data/analytics.json")
      .then(async (response) => {
        if (!response.ok) throw new Error(`Analytics request failed (${response.status}).`);
        return (await response.json()) as AnalyticsData;
      })
      .then((value) => {
        if (active) setData(value);
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Analytics could not be loaded.");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  return { data, error };
}

function LoadingState() {
  return (
    <main className="main-content" aria-label="Loading dashboard">
      <div className="skeleton skeleton-title" />
      <div className="skeleton-figures">
        {Array.from({ length: 5 }, (_, index) => (
          <div className="skeleton-figure" key={index}>
            <div className="skeleton skeleton-label" />
            <div className="skeleton skeleton-value" />
          </div>
        ))}
      </div>
      <div className="skeleton skeleton-chart" />
    </main>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <main className="main-content">
      <div className="empty-state" role="alert">
        <AlertTriangle size={20} aria-hidden="true" />
        <h1>Dashboard data is unavailable</h1>
        <p>{message}</p>
        <p>Run the optional dashboard export, then reload this page.</p>
      </div>
    </main>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
  ariaLabel,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  ariaLabel: string;
}) {
  return (
    <label className="select-field">
      <span>{label}</span>
      <Select.Root value={value} onValueChange={onChange}>
        <Select.Trigger className="select-trigger" aria-label={ariaLabel}>
          <Select.Value />
          <Select.Icon>
            <ChevronDown size={14} aria-hidden="true" />
          </Select.Icon>
        </Select.Trigger>
        <Select.Portal>
          <Select.Content className="select-content" position="popper">
            <Select.Viewport>
              {options.map((option) => (
                <Select.Item className="select-item" key={option.value} value={option.value}>
                  <Select.ItemText>{option.label}</Select.ItemText>
                  <Select.ItemIndicator>
                    <Check size={14} aria-hidden="true" />
                  </Select.ItemIndicator>
                </Select.Item>
              ))}
            </Select.Viewport>
          </Select.Content>
        </Select.Portal>
      </Select.Root>
    </label>
  );
}

function PageTitle({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-title">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {children && <div className="title-actions">{children}</div>}
    </header>
  );
}

function SegmentedControl<T extends string>({
  label,
  value,
  choices,
  onChange,
}: {
  label: string;
  value: T;
  choices: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="segmented-wrap" role="group" aria-label={label}>
      {choices.map((choice) => (
        <button
          aria-pressed={choice.value === value}
          className={`segment ${choice.value === value ? "segment-active" : ""}`}
          key={choice.value}
          onClick={() => onChange(choice.value)}
          type="button"
        >
          {choice.label}
        </button>
      ))}
    </div>
  );
}

function ChartCard({
  title,
  subtitle,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel chart-panel ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

function OverviewPage({ data }: { data: AnalyticsData }) {
  const asOf = isoWeek(data.metadata.as_of);
  const figures = [
    { label: "Open gaps", value: data.overview.open_gaps, detail: "skill and role combinations" },
    { label: "Candidate actions", value: data.overview.candidate_actions, detail: "proposed decisions" },
    { label: "Over-utilized weeks", value: data.overview.overutilized_weeks, detail: "employee-weeks" },
    { label: "Anomalies found", value: data.overview.anomalies_found, detail: "detected records" },
    { label: "Data health", value: data.overview.data_health, detail: `${data.metadata.dataset_scale} dataset` },
  ];

  return (
    <>
      <PageTitle
        eyebrow={`${data.metadata.dataset_scale} dataset · As of ${data.metadata.as_of}`}
        title="Workforce overview"
        description="A current view of demand, available supply, and decisions that need review."
      />
      <section className="figure-row" aria-label="Summary metrics">
        {figures.map((figure) => (
          <div className="figure" key={figure.label}>
            <div className="figure-label">{figure.label}</div>
            <div className={figure.label === "Data health" ? "figure-value text-value" : "figure-value"}>
              {typeof figure.value === "number" ? formatNumber(figure.value) : figure.value}
            </div>
            <div className="figure-detail">{figure.detail}</div>
          </div>
        ))}
      </section>

      <ChartCard title="Demand and available supply" subtitle="Weekly FTE · forecast shown after the as-of week">
        <div className="chart-wrap overview-chart">
          <Suspense fallback={<div className="chart-loading" aria-label="Loading chart" />}>
            <OverviewChart data={data.overview.series} asOf={asOf} />
          </Suspense>
        </div>
      </ChartCard>

      <section className="attention-section">
        <div className="section-heading">
          <h2>What needs attention</h2>
          <span className="subtle">{data.overview.attention.length} items</span>
        </div>
        {data.overview.attention.length === 0 ? (
          <div className="empty-inline">No current items need attention.</div>
        ) : (
          <div className="attention-list">
            {data.overview.attention.map((item) => (
              <div className="attention-item" key={item.label}>
                <div className="attention-count">{formatNumber(item.count)}</div>
                <div>
                  <h3>{item.label}</h3>
                  <p>{item.detail}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

function ForecastPage({
  data,
  roleId,
  setRoleId,
  projectId,
  setProjectId,
  method,
  setMethod,
}: {
  data: AnalyticsData;
  roleId: string;
  setRoleId: (value: string) => void;
  projectId: string;
  setProjectId: (value: string) => void;
  method: ForecastMethod;
  setMethod: (value: ForecastMethod) => void;
}) {
  const roleOptions = data.selectors.roles.map((role) => ({
    value: role.role_id,
    label: `${role.title} · ${role.family}`,
  }));
  const projectOptions = [
    { value: "role-total", label: "Role total" },
    ...data.selectors.projects.map((project) => ({
      value: project.project_id,
      label: project.label,
    })),
  ];
  const selectedProjectIndex =
    projectId === "role-total"
      ? null
      : data.selectors.projects.findIndex((project) => project.project_id === projectId);
  const selectedRoleIndex = data.selectors.roles.findIndex((role) => role.role_id === roleId);
  const methodIndex = methods.findIndex((entry) => entry.id === method);
  const rows = data.forecast.series
    .filter((row) => row[0] === selectedRoleIndex && row[1] === selectedProjectIndex)
    .map((row) => ({
      week: row[2],
      actual: row[3],
      forecast: methodIndex === 0 ? row[4] : methodIndex === 1 ? row[5] : row[6],
    }));
  const backtest = data.forecast.backtest[
    selectedProjectIndex === null ? "methods" : "project_methods"
  ][method];
  const metrics = backtest.map((row) => ({
    ...row,
    horizon: `${row.horizon_weeks} weeks`,
  }));
  const role = data.selectors.roles[selectedRoleIndex];
  const backtestMetric = backtest.find((row) => row.horizon_weeks === 4);

  return (
    <>
      <PageTitle
        eyebrow="Demand planning"
        title="Demand and forecast"
        description="Compare observed demand with three forecast methods and review their rolling-origin performance."
      />
      <div className="filter-row">
        <SelectField
          label="Role"
          value={roleId}
          options={roleOptions}
          ariaLabel="Select role"
          onChange={setRoleId}
        />
        <SelectField
          label="Project"
          value={projectId}
          options={projectOptions}
          ariaLabel="Select project"
          onChange={setProjectId}
        />
        <SegmentedControl
          label="Forecast method"
          value={method}
          choices={methods.map(({ id, label }) => ({ value: id, label }))}
          onChange={setMethod}
        />
      </div>
      <ChartCard
        title={`${role?.title ?? "Selected role"}${selectedProjectIndex === null ? "" : ` · ${projectId}`}`}
        subtitle={`Weekly FTE · ${formatMethod(method)} · as of ${data.forecast.as_of}`}
      >
        {rows.length === 0 ? (
          <div className="empty-inline chart-empty">No data is available for this selection.</div>
        ) : (
          <div className="chart-wrap forecast-chart">
            <Suspense fallback={<div className="chart-loading" aria-label="Loading chart" />}>
              <ForecastChart rows={rows} asOf={isoWeek(data.forecast.as_of)} />
            </Suspense>
          </div>
        )}
      </ChartCard>

      <section className="panel backtest-panel">
        <div className="panel-heading backtest-heading">
          <div>
            <h2>Backtest performance</h2>
            <p>{data.forecast.backtest.backtest_method}</p>
          </div>
          {backtestMetric && (
            <div className="backtest-callout">
              <span>4-week WAPE</span>
              <strong>{formatNumber(backtestMetric.wape * 100, 1)}%</strong>
            </div>
          )}
        </div>
        <div className="table-scroll">
          <table className="data-table compact-table">
            <thead>
              <tr><th>Horizon</th><th>Origins</th><th>WAPE</th><th>Bias</th></tr>
            </thead>
            <tbody>
              {metrics.map((row) => (
                <tr key={row.horizon}>
                  <td>{row.horizon}</td>
                  <td className="mono">{row.origins}</td>
                  <td className="mono">{formatNumber(row.wape * 100, 2)}%</td>
                  <td className="mono">{formatNumber(row.bias * 100, 2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function traceFromRow(row: GapTraceTuple) {
  return {
    id: row[0],
    week: row[1],
    roleId: row[2],
    roleTitle: row[3],
    family: row[4],
    skillId: row[5],
    skillName: row[6],
    demand: row[7],
    supply: row[8],
    gap: row[9],
    risk: row[10],
    demandLines: row[11],
    supportingSkills: row[12],
    actionIds: row[13],
  };
}

function SkillGapsPage({ data }: { data: AnalyticsData }) {
  const [selectedCell, setSelectedCell] = useState<{ family: string; week: string } | null>(null);
  const matrix = useMemo(() => {
    const values = new Map<string, number>();
    for (const [family, week, gap] of data.skill_gaps.heatmap) {
      values.set(`${family}|${week}`, gap);
    }
    return values;
  }, [data.skill_gaps.heatmap]);
  const actionMap = useMemo(
    () => new Map(data.decisions.actions.map((action) => [action[0], compactAction(action)])),
    [data.decisions.actions],
  );
  const cellTraces = selectedCell
    ? data.skill_gaps.traces
        .filter((row) => row[4] === selectedCell.family && row[1] === selectedCell.week)
        .map(traceFromRow)
    : [];
  const [activeTraceId, setActiveTraceId] = useState<string | null>(null);
  const activeTrace = cellTraces.find((trace) => trace.id === activeTraceId) ?? cellTraces[0];

  function showCell(family: string, week: string) {
    setSelectedCell({ family, week });
    setActiveTraceId(null);
  }

  return (
    <>
      <PageTitle
        eyebrow="Supply and demand"
        title="Skill gaps"
        description="Role-family demand gaps by ISO week. Select a cell to inspect its source and candidate actions."
      />
      <section className="panel heatmap-panel">
        <div className="panel-heading">
          <div>
            <h2>Gap by role family and week</h2>
            <p>Positive values indicate a shortage; neutral cells have supply at or above demand.</p>
          </div>
          <div className="heat-legend"><span>Surplus</span><i className="heat-swatch neutral" /><i className="heat-swatch low" /><i className="heat-swatch mid" /><i className="heat-swatch high" /><span>Shortage</span></div>
        </div>
        <div className="heatmap-scroll" role="region" aria-label="Skill gaps heatmap" tabIndex={0}>
          <table className="heatmap">
            <thead>
              <tr>
                <th scope="col">Role family</th>
                {data.skill_gaps.weeks.map((week) => (
                  <th className="week-heading" key={week} scope="col" title={week}>{week.slice(-2)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.skill_gaps.families.map((family) => (
                <tr key={family}>
                  <th className="family-heading" scope="row">{family}</th>
                  {data.skill_gaps.weeks.map((week) => {
                    const gap = matrix.get(`${family}|${week}`) ?? 0;
                    const intensity = Math.min(1, Math.max(0, gap / 15));
                    const background =
                      gap <= 0
                        ? "var(--heat-neutral)"
                        : `color-mix(in srgb, var(--ink) ${Math.round(10 + intensity * 65)}%, var(--surface))`;
                    return (
                      <td key={week}>
                        <button
                          aria-label={`${family}, ${week}, gap ${formatNumber(gap, 2)} FTE`}
                          className="heat-cell"
                          onClick={() => showCell(family, week)}
                          style={{ backgroundColor: background }}
                          title={`${family} · ${week} · ${formatNumber(gap, 2)} FTE`}
                          type="button"
                        />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="heatmap-footnote">Each cell aggregates gap FTE across skills in the role family.</div>
      </section>

      <Dialog.Root open={selectedCell !== null} onOpenChange={(open) => !open && setSelectedCell(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="side-sheet">
            <div className="sheet-header">
              <div>
                <div className="eyebrow">Trace detail</div>
                <Dialog.Title>{selectedCell?.family ?? "Skill gap"} · {selectedCell?.week ?? ""}</Dialog.Title>
                <Dialog.Description>
                  Source demand, supporting skills, and actions for this heatmap cell.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button className="icon-button" aria-label="Close trace detail" type="button"><X size={18} /></button>
              </Dialog.Close>
            </div>
            {cellTraces.length === 0 ? (
              <div className="empty-inline sheet-empty">No individual gap records are linked to this cell.</div>
            ) : (
              <div className="sheet-body">
                <div className="trace-selector" aria-label="Gaps in selected cell">
                  {cellTraces.map((trace) => (
                    <button
                      className={activeTrace?.id === trace.id ? "trace-pill trace-pill-active" : "trace-pill"}
                      key={trace.id}
                      onClick={() => setActiveTraceId(trace.id)}
                      type="button"
                    >
                      {trace.skillName}
                    </button>
                  ))}
                </div>
                {activeTrace && (
                  <>
                    <div className="trace-summary">
                      <div><span>Gap</span><strong className="mono">{activeTrace.id}</strong></div>
                      <div><span>Role</span><strong>{activeTrace.roleTitle}</strong></div>
                      <div><span>Skill</span><strong>{activeTrace.skillName} <small className="mono">{activeTrace.skillId}</small></strong></div>
                      <div><span>Demand / supply</span><strong className="mono">{formatNumber(activeTrace.demand, 2)} / {formatNumber(activeTrace.supply, 2)} FTE</strong></div>
                      <div><span>Gap / risk</span><strong>{formatNumber(activeTrace.gap, 2)} FTE · {activeTrace.risk}</strong></div>
                    </div>
                    <section className="trace-section">
                      <h3>Source demand lines</h3>
                      {activeTrace.demandLines.length ? activeTrace.demandLines.map((line) => (
                        <div className="trace-row" key={line[0]}>
                          <span className="mono">{line[0]}</span>
                          <span>{line[1]}</span>
                          <span>{formatNumber(line[2], 2)} FTE · level {line[3]}+</span>
                        </div>
                      )) : <p className="subtle">No source lines attached.</p>}
                    </section>
                    <section className="trace-section">
                      <h3>Supporting employee skills</h3>
                      {activeTrace.supportingSkills.length ? activeTrace.supportingSkills.map((skill) => (
                        <div className="trace-row" key={skill[0]}>
                          <span className="mono">{skill[0]}</span>
                          <span>{skill[2]}</span>
                          <span>Level {skill[3]}</span>
                        </div>
                      )) : <p className="subtle">No supporting current skills were linked.</p>}
                    </section>
                    <section className="trace-section">
                      <h3>Candidate actions</h3>
                      {activeTrace.actionIds.length ? activeTrace.actionIds.map((id) => {
                        const action = actionMap.get(id);
                        return action ? (
                          <article className="action-trace" key={id}>
                            <div className="action-trace-title">
                              <strong>{action.type}</strong>
                              <span className="status-text">{action.status}</span>
                            </div>
                            <div className="mono">{action.id} · {action.rule}</div>
                            <p>{action.owner} · {action.assumptions}</p>
                          </article>
                        ) : null;
                      }) : <p className="subtle">No candidate actions are linked.</p>}
                    </section>
                  </>
                )}
              </div>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}

function DecisionsPage({ data }: { data: AnalyticsData }) {
  const [owner, setOwner] = useState("All owners");
  const [rule, setRule] = useState("All rules");
  const [status, setStatus] = useState("All statuses");
  const actions = useMemo(
    () => data.decisions.actions.map(compactAction),
    [data.decisions.actions],
  );
  const owners = useMemo(
    () => [...new Set([...data.decisions.owners, ...actions.map((action) => action.owner)])],
    [actions, data.decisions.owners],
  );
  const filtered = useMemo(
    () => actions
      .filter((action) =>
        (owner === "All owners" || action.owner === owner)
        && (rule === "All rules" || action.rule === rule)
        && (status === "All statuses" || action.status === status),
      )
      .sort((first, second) =>
        owners.indexOf(first.owner) - owners.indexOf(second.owner)
        || first.id.localeCompare(second.id),
      ),
    [actions, owners, owner, rule, status],
  );
  const columns = useMemo<ColumnDef<Action>[]>(() => [
    { accessorKey: "id", header: "Action", cell: (info) => <span className="mono">{info.getValue<string>()}</span> },
    { accessorKey: "type", header: "Action type" },
    { accessorKey: "owner", header: "Owner" },
    { accessorKey: "status", header: "Status", cell: (info) => <span className="status-pill">{info.getValue<string>()}</span> },
    { accessorKey: "rule", header: "Rule", cell: (info) => <span className="mono">{info.getValue<string>()}</span> },
    { accessorKey: "employee", header: "Candidate", cell: (info) => <span className="mono">{info.getValue<string | null>() ?? "—"}</span> },
    { accessorKey: "cost", header: "Estimated cost", cell: (info) => <span className="mono">{formatCurrency(info.getValue<number>())}</span> },
    { accessorKey: "assumptions", header: "Assumptions", cell: (info) => <span className="assumptions-cell">{info.getValue<string>()}</span> },
  ], []);
  // TanStack Table's hook returns an imperative API, so React Compiler correctly skips memoization.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: filtered,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 50 } },
  });
  const ownerCounts = owners.map((entry) => ({
    owner: entry,
    count: actions.filter((action) => action.owner === entry).length,
  }));
  const escalationCount = actions.filter((action) => action.status === "Escalated").length;

  return (
    <>
      <PageTitle
        eyebrow="Candidate actions"
        title="Decisions"
        description="Review proposed actions by owner, status, and decision rule."
      />
      <div className="decision-summary">
        {ownerCounts.map((entry) => (
          <button className="decision-owner" key={entry.owner} onClick={() => setOwner(entry.owner)} type="button">
            <span>{entry.owner}</span><strong>{formatNumber(entry.count)}</strong>
          </button>
        ))}
        <div className="decision-owner escalation-count">
          <span>Escalated</span><strong>{formatNumber(escalationCount)}</strong>
        </div>
      </div>
      <section className="panel table-panel">
        <div className="panel-heading decisions-heading">
          <div>
            <h2>Action queue</h2>
            <p>{formatNumber(filtered.length)} candidate actions</p>
          </div>
          <div className="filter-row compact-filters">
            <SelectField label="Owner" value={owner} ariaLabel="Filter by owner" onChange={setOwner} options={[
              { value: "All owners", label: "All owners" },
              ...owners.map((value) => ({ value, label: value })),
            ]} />
            <SelectField label="Status" value={status} ariaLabel="Filter by status" onChange={setStatus} options={[
              { value: "All statuses", label: "All statuses" },
              ...data.decisions.statuses.map((value) => ({ value, label: value })),
            ]} />
            <SelectField label="Rule" value={rule} ariaLabel="Filter by rule" onChange={setRule} options={[
              { value: "All rules", label: "All rules" },
              ...data.decisions.rules.map((value) => ({ value, label: value })),
            ]} />
          </div>
        </div>
        {filtered.length === 0 ? (
          <div className="empty-inline table-empty">No actions match these filters.</div>
        ) : (
          <div className="table-scroll">
            <table className="data-table decisions-table">
              <thead>
                {table.getHeaderGroups().map((group) => (
                  <tr key={group.id}>
                    {group.headers.map((header) => (
                      <th key={header.id}>
                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row, index, visibleRows) => (
                  <Fragment key={row.id}>
                    {(index === 0 || visibleRows[index - 1]?.original.owner !== row.original.owner) && (
                      <tr className="owner-group-row" key={`${row.original.owner}-group`}>
                        <th colSpan={columns.length} scope="rowgroup">
                          {row.original.owner}
                          <span>{formatNumber(filtered.filter((action) => action.owner === row.original.owner).length)} actions</span>
                        </th>
                      </tr>
                    )}
                    <tr>
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                      ))}
                    </tr>
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {filtered.length > 0 && (
          <div className="table-pagination">
            <span>
              Rows {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1}–
              {Math.min((table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize, filtered.length)}
              {" "}of {formatNumber(filtered.length)}
            </span>
            <div>
              <button disabled={!table.getCanPreviousPage()} onClick={() => table.previousPage()} type="button">Previous</button>
              <span>Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}</span>
              <button disabled={!table.getCanNextPage()} onClick={() => table.nextPage()} type="button">Next</button>
            </div>
          </div>
        )}
      </section>
    </>
  );
}

function AnomaliesPage({ data }: { data: AnalyticsData }) {
  const [evaluation, setEvaluation] = useState<EvaluationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    fetch("/data/evaluation.json")
      .then(async (response) => {
        if (!response.ok) throw new Error(`Evaluation request failed (${response.status}).`);
        return (await response.json()) as EvaluationData;
      })
      .then((value) => {
        if (active) setEvaluation(value);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Evaluation metrics could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <><PageTitle eyebrow="Evaluation only" title="Anomalies and data health" /><div className="skeleton skeleton-chart" /></>;
  }
  if (error || !evaluation) {
    return <><PageTitle eyebrow="Evaluation only" title="Anomalies and data health" /><div className="empty-state" role="alert"><AlertTriangle size={20} /><h2>Evaluation data is unavailable</h2><p>{error ?? "No evaluation metrics were exported."}</p></div></>;
  }

  return (
    <>
      <PageTitle
        eyebrow="Evaluation only"
        title="Anomalies and data health"
        description="Synthetic ground-truth comparisons are shown only on this page. Scores are not used by detection."
      />
      <div className="evaluation-banner"><Database size={16} aria-hidden="true" /><span>{evaluation.label}</span><span className="mono">seed {evaluation.seed}</span></div>
      <section className="panel table-panel">
        <div className="panel-heading"><div><h2>Detector performance</h2><p>Per issue type on the exported seed</p></div></div>
        <div className="table-scroll">
          <table className="data-table compact-table">
            <thead><tr><th>Issue type</th><th>Injected</th><th>Detected</th><th>Precision</th><th>Recall</th><th>F1</th><th>FP</th><th>FN</th></tr></thead>
            <tbody>{evaluation.by_issue_type.map((row) => (
              <tr key={row.issue_type}>
                <td className="mono">{row.issue_type}</td><td>{formatNumber(row.injected)}</td><td>{formatNumber(row.detected)}</td>
                <td>{formatNumber(row.precision * 100, 1)}%</td><td>{formatNumber(row.recall * 100, 1)}%</td><td>{formatNumber(row.f1 * 100, 1)}%</td>
                <td>{formatNumber(row.false_positive)}</td><td>{formatNumber(row.false_negative)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>

      {evaluation.held_out && (
        <section className="panel table-panel">
          <div className="panel-heading"><div><h2>Held-out seed</h2><p>Seed {evaluation.held_out.seed} · aggregate per-type results</p></div></div>
          <div className="table-scroll">
            <table className="data-table compact-table">
              <thead><tr><th>Issue type</th><th>Precision</th><th>Recall</th><th>F1</th><th>TP</th><th>FP</th><th>FN</th></tr></thead>
              <tbody>{Object.entries(evaluation.held_out.per_issue_type).map(([type, row]) => (
                <tr key={type}><td className="mono">{type}</td><td>{formatNumber(row.precision * 100, 1)}%</td><td>{formatNumber(row.recall * 100, 1)}%</td><td>{formatNumber(row.f1 * 100, 1)}%</td><td>{row.true_positive}</td><td>{row.false_positive}</td><td>{row.false_negative}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </section>
      )}

      <section className="panel table-panel">
        <div className="panel-heading"><div><h2>Near-miss cases</h2><p>Boundary examples that the detector should leave unflagged.</p></div></div>
        <div className="table-scroll">
          <table className="data-table compact-table">
            <thead><tr><th>Issue type</th><th>Near misses</th><th>Detected</th><th>Result</th></tr></thead>
            <tbody>{evaluation.near_misses.map((row) => (
              <tr key={row.issue_type}><td className="mono">{row.issue_type}</td><td>{row.records}</td><td>{row.detected}</td><td><span className={row.detected === 0 ? "health-good" : "health-bad"}>{row.detected === 0 ? "None flagged" : "Review required"}</span></td></tr>
            ))}</tbody>
          </table>
        </div>
      </section>

      <section className="panel health-panel">
        <div className="panel-heading"><div><h2>Validation checks</h2><p>Structural and derived-data checks from the same export.</p></div><span className={`health-status ${data.data_health.status.toLowerCase()}`}>{data.data_health.status}</span></div>
        <div className="health-checks">
          {data.data_health.checks.map((check) => (
            <div className="health-check" key={check.name}>
              <span className={`health-dot ${check.status}`} />
              <span>{check.name}</span>
              <strong>{String(check.value)}</strong>
            </div>
          ))}
        </div>
        {data.data_health.warnings.length > 0 && (
          <div className="warning-list">
            <h3>Validation warnings</h3>
            {data.data_health.warnings.map((warning) => <p key={warning}><AlertTriangle size={14} />{warning}</p>)}
          </div>
        )}
      </section>

      <section className="panel repro-panel">
        <div className="panel-heading"><div><h2>Reproducibility proof</h2><p>Metadata reported by the exporter; not a new verification run.</p></div></div>
        <div className="repro-grid">
          <div><span>Hash match</span><strong>{data.data_health.reproducibility.hash_match === true ? "Verified" : data.data_health.reproducibility.status}</strong></div>
          <div><span>Seed</span><strong className="mono">{data.data_health.reproducibility.seed}</strong></div>
          <div><span>Files</span><strong className="mono">{data.data_health.reproducibility.file_count ?? "—"}</strong></div>
          {Object.entries(data.data_health.reproducibility.versions).map(([name, version]) => (
            <div key={name}><span>{name}</span><strong className="mono">{version ?? "Not recorded"}</strong></div>
          ))}
        </div>
      </section>
    </>
  );
}

function CommandPalette({
  open,
  onOpenChange,
  navigate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  navigate: (page: PageId) => void;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay command-overlay" />
        <Dialog.Content className="command-dialog">
          <Dialog.Title className="visually-hidden">Navigate dashboard</Dialog.Title>
          <Dialog.Description className="visually-hidden">Search and select a dashboard page.</Dialog.Description>
          <Command label="Dashboard navigation">
            <div className="command-search">
              <Search size={16} aria-hidden="true" />
              <Command.Input autoFocus placeholder="Search pages…" />
              <Dialog.Close asChild><button className="kbd-close" aria-label="Close command palette" type="button">Esc</button></Dialog.Close>
            </div>
            <Command.List>
              <Command.Empty>No matching pages.</Command.Empty>
              <Command.Group heading="Navigate">
                {pages.map((page) => (
                  <Command.Item
                    key={page.id}
                    onSelect={() => { navigate(page.id); onOpenChange(false); }}
                    value={`${page.label} ${page.id}`}
                  >
                    <page.icon size={16} aria-hidden="true" />
                    <span>{page.label}</span>
                  </Command.Item>
                ))}
              </Command.Group>
            </Command.List>
          </Command>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export default function App() {
  const { data, error } = useAnalytics();
  const [page, setPage] = useState<PageId>(readPage);
  const [roleId, setRoleId] = useState(
    () => new URLSearchParams(window.location.search).get("role") ?? "",
  );
  const [projectId, setProjectId] = useState(
    () => new URLSearchParams(window.location.search).get("project") ?? "role-total",
  );
  const [method, setMethod] = useState<ForecastMethod>(() => {
    const value = new URLSearchParams(window.location.search).get("method");
    return methods.some((entry) => entry.id === value)
      ? (value as ForecastMethod)
      : "pipeline_realization_adjusted";
  });
  const [theme, setTheme] = useState<ThemeMode>(initialTheme);
  const [commandOpen, setCommandOpen] = useState(false);

  const navigate = useCallback((next: PageId) => {
    setPage(next);
    const url = new URL(window.location.href);
    url.searchParams.set("page", next);
    window.history.pushState({}, "", url);
  }, []);

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("page", page);
    if (roleId) url.searchParams.set("role", roleId);
    else url.searchParams.delete("role");
    if (projectId !== "role-total") url.searchParams.set("project", projectId);
    else url.searchParams.delete("project");
    url.searchParams.set("method", method);
    window.history.replaceState({}, "", url);
  }, [page, roleId, projectId, method]);

  useEffect(() => {
    function onPopState() {
      setPage(readPage());
      const params = new URLSearchParams(window.location.search);
      setRoleId(params.get("role") ?? "");
      setProjectId(params.get("project") ?? "role-total");
      const nextMethod = params.get("method");
      if (methods.some((entry) => entry.id === nextMethod)) setMethod(nextMethod as ForecastMethod);
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (theme === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.dataset.theme = theme;
    if (theme === "system") window.localStorage.removeItem("workforce-theme");
    else window.localStorage.setItem("workforce-theme", theme);
  }, [theme]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen(true);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  if (!data && !error) return <LoadingState />;
  if (error || !data) return <ErrorState message={error ?? "No dashboard data was exported."} />;

  const validRoleId = data.selectors.roles.some((role) => role.role_id === roleId)
    ? roleId
    : data.selectors.roles[0]?.role_id ?? "";
  const validProjectId = projectId === "role-total"
    || data.selectors.projects.some((project) => project.project_id === projectId)
    ? projectId
    : "role-total";

  return (
    <Tooltip.Provider delayDuration={250}>
      <div className="app-shell">
        <header className="topbar">
          <a className="brand" href="?page=overview" onClick={(event) => { event.preventDefault(); navigate("overview"); }}>
            <span className="brand-mark"><Layers3 size={17} aria-hidden="true" /></span>
            <span>Workforce <strong>demand forge</strong></span>
          </a>
          <div className="topbar-actions">
            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <button className="command-trigger" onClick={() => setCommandOpen(true)} type="button">
                  <Search size={15} aria-hidden="true" /><span>Search</span><kbd><CommandIcon size={11} /> K</kbd>
                </button>
              </Tooltip.Trigger>
              <Tooltip.Portal><Tooltip.Content className="tooltip-content">Open command palette</Tooltip.Content></Tooltip.Portal>
            </Tooltip.Root>
            <button
              aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              className="icon-button theme-toggle"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              type="button"
            >
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <span className="dataset-chip"><span className="online-dot" />{data.metadata.dataset_scale}</span>
          </div>
        </header>
        <div className="layout">
          <aside className="sidebar">
            <div className="sidebar-label">Workspace</div>
            <nav aria-label="Main navigation">
              {pages.map((entry) => (
                <button
                  aria-current={page === entry.id ? "page" : undefined}
                  className={page === entry.id ? "nav-link nav-link-active" : "nav-link"}
                  key={entry.id}
                  onClick={() => navigate(entry.id)}
                  type="button"
                >
                  <entry.icon size={17} aria-hidden="true" /><span>{entry.label}</span>
                </button>
              ))}
            </nav>
            <div className="sidebar-bottom">
              <div className="sidebar-label">Snapshot</div>
              <div className="snapshot-meta"><span>As of</span><strong>{data.metadata.as_of}</strong></div>
              <div className="snapshot-meta"><span>Seed</span><strong className="mono">{data.metadata.seed}</strong></div>
              <div className="snapshot-meta"><span>Data health</span><strong className="health-inline"><i />{data.data_health.status}</strong></div>
              <div className="sidebar-footer">Read-only analytics<br />No external network calls</div>
            </div>
          </aside>
          <main className="main-content" key={page}>
            {page === "overview" && <OverviewPage data={data} />}
            {page === "forecast" && (
              <ForecastPage
                data={data}
                roleId={validRoleId}
                setRoleId={setRoleId}
                projectId={validProjectId}
                setProjectId={setProjectId}
                method={method}
                setMethod={setMethod}
              />
            )}
            {page === "gaps" && <SkillGapsPage data={data} />}
            {page === "decisions" && <DecisionsPage data={data} />}
            {page === "health" && <AnomaliesPage data={data} />}
            <footer className="page-footer">
              <span>Snapshot seed <strong className="mono">{data.metadata.seed}</strong></span>
              <span>Generated synthetic data · {data.metadata.generator_version}</span>
            </footer>
          </main>
        </div>
        <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} navigate={navigate} />
      </div>
    </Tooltip.Provider>
  );
}
