export interface Source { id: number; name: string; reference: string; synthetic: boolean; imported_at: string; notes: string }
export interface Company { id: number; name: string; isin: string; ticker: string; exchange: string; sector: string; currency: string; source: Source }
export interface Price { date: string; close: number; adjusted_close: number | null; currency: string; source: Source }
export interface Emission { year: number; scope1: number | null; scope2: number | null; scope3: number | null; units: string; methodology: string; notes: string; source: Source }
