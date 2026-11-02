export type Role = {
  role_id: string;
  title: string;
  family: string;
};

export type Project = {
  project_id: string;
  label: string;
};

export type ForecastMethod =
  | "moving_average_4w"
  | "pipeline_adjusted"
  | "pipeline_realization_adjusted";

export type ForecastTuple = [
  roleIndex: number,
  projectIndex: number | null,
  week: string,
  actual: number | null,
  movingAverage: number | null,
  pipelineAdjusted: number | null,
  realizationAdjusted: number | null,
];

export type HeatmapTuple = [family: string, week: string, gapFte: number];

export type DemandLineTuple = [
  demandLineId: string,
  projectId: string,
  requiredFte: number,
  minProficiency: number,
];

export type SupportingSkillTuple = [
  employeeSkillId: string,
  skillId: string,
  skillName: string,
  proficiency: number,
];

export type GapTraceTuple = [
  gapId: string,
  week: string,
  roleId: string,
  roleTitle: string,
  family: string,
  skillId: string,
  skillName: string,
  demandFte: number,
  supplyFte: number,
  gapFte: number,
  riskLevel: string,
  demandLines: DemandLineTuple[],
  supportingSkills: SupportingSkillTuple[],
  candidateActionIds: string[],
];

export type ActionTuple = [
  gapActionId: string,
  gapId: string | null,
  actionType: string,
  employeeId: string | null,
  skillId: string | null,
  owner: string,
  status: string,
  ruleId: string,
  estimatedCost: number,
  assumptions: string,
];

export type BacktestMetric = {
  horizon_weeks: number;
  origins: number;
  wape: number;
  bias: number;
};

export type AnalyticsData = {
  metadata: {
    dataset_scale: string;
    seed: number;
    as_of: string;
    generator_version: string;
    versions: Record<string, string | null>;
    record_counts: Record<string, number>;
  };
  overview: {
    anomalies_found: number;
    candidate_actions: number;
    data_health: string;
    open_gaps: number;
    overutilized_weeks: number;
    attention: { label: string; count: number; detail: string }[];
    series: {
      week: string;
      actual_demand: number | null;
      forecast_demand: number | null;
      supply: number;
    }[];
  };
  selectors: {
    roles: Role[];
    projects: Project[];
    methods: ForecastMethod[];
  };
  forecast: {
    as_of: string;
    series_columns: string[];
    series: ForecastTuple[];
    backtest: {
      as_of: string;
      backtest_method: string;
      forecast_weeks: number;
      methods: Record<ForecastMethod, BacktestMetric[]>;
      project_methods: Record<ForecastMethod, BacktestMetric[]>;
    };
  };
  skill_gaps: {
    weeks: string[];
    families: string[];
    heatmap_columns: string[];
    heatmap: HeatmapTuple[];
    trace_columns: string[];
    demand_line_columns: string[];
    support_columns: string[];
    traces: GapTraceTuple[];
  };
  decisions: {
    action_columns: string[];
    actions: ActionTuple[];
    owners: string[];
    statuses: string[];
    rules: string[];
  };
  data_health: {
    status: string;
    checks: { name: string; value: string | number | boolean; status: string }[];
    warnings: string[];
    reproducibility: {
      hash_match: boolean | null;
      status: string;
      seed: number;
      versions: Record<string, string | null>;
      file_count?: number;
      logical_database_hash_match?: boolean | null;
    };
  };
};

export type EvaluationData = {
  evaluation_only: true;
  label: string;
  seed: number;
  by_issue_type: {
    issue_type: string;
    injected: number;
    detected: number;
    true_positive: number;
    false_positive: number;
    false_negative: number;
    precision: number;
    recall: number;
    f1: number;
  }[];
  held_out: {
    seed: number;
    per_issue_type: Record<
      string,
      {
        precision: number;
        recall: number;
        f1: number;
        true_positive: number;
        false_positive: number;
        false_negative: number;
      }
    >;
  } | null;
  near_misses: { issue_type: string; records: number; detected: number }[];
};
