export interface Source {
  id: number;
  name: string;
  reference: string;
  synthetic: boolean;
  imported_at: string;
  notes: string;
  retrieved_at?: string | null;
  license_reference?: string | null;
}
export interface Company {
  original_sector?: string | null;
  classification_system?: string | null;
  sector_mapping_notes?: string | null;
  id: number;
  name: string;
  isin: string;
  ticker: string;
  exchange: string;
  sector: string;
  currency: string;
  source: Source;
}
export interface Price {
  date: string;
  close: number;
  adjusted_close: number | null;
  adjustment_method?: string;
  currency: string;
  source: Source;
}
export interface Emission {
  scope1_status?: "reported" | "estimated" | "unknown";
  scope2_status?: "reported" | "estimated" | "unknown";
  scope3_status?: "reported" | "estimated" | "unknown";
  scope2_basis?: string;
  disclosure_date?: string | null;
  disclosure_reference?: string | null;
  year: number;
  scope1: number | null;
  scope2: number | null;
  scope3: number | null;
  units: string;
  methodology: string;
  notes: string;
  source: Source;
}
