export interface Correlation {
  status: string;
  message: string | null;
  valid_pairs: number;
  distinct_companies: number;
  coefficient_pearson: number | null;
  coefficient_spearman: number | null;
  warnings: string[];
  exclusions: Record<string, number>;
  points: { company: string; x: number; y: number }[];
}
export interface Series {
  company_id: number;
  company: string;
  status: string;
  blockers: string[];
  price_count: number;
  valid_returns: number;
  completeness: number | null;
  annualized_volatility: number | null;
  cumulative_return: number | null;
  daily: {
    date: string;
    close: number;
    currency: string;
    simple_return: number | null;
    log_return: number | null;
  }[];
}
export interface Data {
  series: Series[];
  carbon: {
    id: number;
    company_id: number;
    year: number;
    value: number | null;
    issue: string | null;
    methodology: string;
    disclosure_date: string | null;
  }[];
}
