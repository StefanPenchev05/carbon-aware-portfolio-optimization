export interface PortfolioConfiguration {
  data_mode: "real" | "synthetic";
  company_ids: number[];
  start_date: string;
  end_date: string;
  as_of: string;
  risk_aversion: number;
  carbon_penalty: number;
  long_gross: number;
  short_gross: number;
  max_weight: number;
  selection: "auto" | "manual";
  long_ids: number[];
  short_ids: number[];
  carbon_metric: "scope1+2-market-based";
  penalties: number[];
  min_assets: number;
  min_candidates: number;
  min_observations: number;
  shrinkage: number;
}
export interface PortfolioReadiness {
  status: string;
  synthetic: boolean;
  provenance: string;
  blockers: string[];
  available_companies: { id: number; name: string; sector: string }[];
  selected_count: number;
  eligible_count: number;
  price_count: number;
  adjusted_price_count: number;
  emission_count: number;
  aligned_observations: number;
  long_ids: number[];
  short_ids: number[];
}
export interface Position {
  company_id: number;
  name: string;
  sleeve: "long" | "short";
  weight: number;
  carbon_score: number;
  emissions_tco2e: number;
}
export interface PortfolioResult {
  carbon_penalty: number;
  positions: Position[];
  expected_return_annual: number;
  variance_annual: number;
  volatility_annual: number;
  carbon_exposure_score: number;
  long_exposure: number;
  short_exposure: number;
  gross_exposure: number;
  net_exposure: number;
  objective_value: number;
  solver: string;
  solver_status: string;
  max_constraint_violation: number;
}
export interface PortfolioResponse {
  status: string;
  message: string;
  configuration: PortfolioConfiguration;
  readiness: PortfolioReadiness;
  warnings: string[];
  estimates: {
    observations: number;
    start_date: string;
    end_date: string;
    as_of: string;
    selection_method: string;
    shrinkage: number;
    covariance_repair: string;
    assets: {
      company_id: number;
      name: string;
      carbon_score: number;
      emissions_tco2e: number;
      expected_return_annual: number;
      disclosure_date: string;
      disclosure_year: number;
      original_emission: {
        scope1: number;
        scope2: number;
        units: string;
        methodology: string;
      };
    }[];
  } | null;
  portfolio: PortfolioResult | null;
  comparison: {
    traditional: PortfolioResult;
    carbon_aware: PortfolioResult;
    difference: {
      expected_return_annual: number;
      volatility_annual: number;
      carbon_exposure_score: number;
      composition_l1: number;
      long_exposure: number;
      short_exposure: number;
      weights: Record<string, number>;
    };
  } | null;
  sensitivity: {
    portfolios: PortfolioResult[];
    carbon_nonincreasing: boolean;
    carbon_reduced: boolean;
    tolerance: number;
  } | null;
}
