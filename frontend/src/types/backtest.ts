import type { PortfolioResult, PortfolioResponse } from "./portfolio";
export interface BacktestConfiguration {
  data_mode: "real" | "synthetic";
  start_date: string;
  end_date: string;
  window: "rolling" | "expanding";
  training_sessions: number;
  frequency: "monthly" | "quarterly";
  risk_aversion: number;
  carbon_penalty: number;
  penalties: number[];
  max_weight: number;
  long_gross: number;
  short_gross: number;
  company_ids: number[];
  sectors: string[];
  min_assets: number;
  min_candidates: number;
  min_observations: number;
  min_annual_observations: number;
  shrinkage: number;
  risk_free_rate: number | null;
}
export interface BacktestReadiness {
  status: string;
  synthetic: boolean;
  provenance: string;
  blockers: string[];
  company_count: number;
  price_count: number;
  adjusted_price_count: number;
  scheduled_periods: number;
  decision_dates: string[];
  exclusions: Record<string, number>;
}
export interface EvaluationMetrics {
  cumulative_return: number;
  annualized_return: number | null;
  annualized_volatility: number | null;
  sharpe_ratio: number | null;
  maximum_drawdown: number;
  daily_observations: number;
  evaluation_periods: number;
  annualization_reason: string | null;
  turnover_l1_total: number;
  turnover_l1_average: number;
  average_gross_exposure: number;
  average_net_exposure: number;
  average_long_positions: number;
  average_short_positions: number;
}
export interface HistoryStep {
  decision_date: string;
  training_start: string;
  training_end: string;
  holding_end: string;
  eligible_ids: number[];
  exclusions: Record<string, string>;
  in_sample: NonNullable<PortfolioResponse["estimates"]>;
  target_portfolio: PortfolioResult;
  pretrade_weights: Record<string, number>;
  weight_changes: Record<string, number>;
  turnover_l1: number;
  realized_period_return: number;
  sector_allocations: Record<
    string,
    { long: number; short: number; net: number }
  >;
}
export interface StrategyHistory {
  carbon_penalty: number;
  initial_date: string;
  daily: {
    date: string;
    realized_return: number;
    equity: number;
    cumulative_return: number;
    gross_exposure: number;
    net_exposure: number;
  }[];
  rebalances: HistoryStep[];
  financial: EvaluationMetrics;
  carbon: {
    average_rebalance_score: number;
    score_definition_changed: boolean;
    average_paired_difference_from_baseline: number | null;
  };
}
export interface BacktestResponse {
  reference_currency: string | null;
  status: string;
  message: string;
  configuration: BacktestConfiguration;
  readiness: BacktestReadiness;
  strategies: StrategyHistory[];
  assumptions: string[];
  warnings: string[];
}
