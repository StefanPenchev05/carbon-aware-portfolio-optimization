// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';
import { api } from './services/api';
vi.mock('./services/api', () => ({ api: { companies: vi.fn(), prices: vi.fn(), emissions: vi.fn() } }));
const source = { id: 1, name: 'Synthetic fixture', reference: 'fixture', synthetic: true, imported_at: '2025-01-01', notes: '' };
const company = { id: 1, name: 'Synthetic Energy', isin: 'ZZ0000000001', ticker: 'SEN', exchange: 'XTEST', sector: 'Energy', currency: 'EUR', source };
beforeEach(() => { vi.mocked(api.companies).mockResolvedValue([company]); vi.mocked(api.prices).mockResolvedValue([]); vi.mocked(api.emissions).mockResolvedValue([]); });
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it('loads companies, labels synthetic data and shows missing observations', async () => {
  render(<App/>);
  expect(await screen.findByText('No emissions observations available for this company.')).toBeTruthy();
  expect(screen.getByText('Synthetic demonstration')).toBeTruthy();
  expect(screen.getByText('No price observations available.')).toBeTruthy();
});
it('requests sector filtering', async () => {
  render(<App/>);
  await screen.findByText('No price observations available.');
  fireEvent.change(screen.getByLabelText('Sector'), { target: { value: 'Industrials' } });
  await waitFor(() => expect(api.companies).toHaveBeenLastCalledWith('Industrials', expect.any(AbortSignal)));
});
it('shows API failures', async () => {
  vi.mocked(api.companies).mockRejectedValue(new Error('Offline'));
  render(<App/>);
  expect((await screen.findByRole('alert')).textContent).toContain('Offline');
});
it('selects another company', async () => {
  vi.mocked(api.companies).mockResolvedValue([company, { ...company, id: 2, name: 'Synthetic Pharma' }]);
  render(<App/>);
  fireEvent.click(await screen.findByRole('button', { name: /Synthetic Pharma/ }));
  await waitFor(() => expect(api.prices).toHaveBeenLastCalledWith(2, expect.any(AbortSignal)));
});
