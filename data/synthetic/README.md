# Explicitly synthetic portfolio demonstration

`portfolio-v1.json` contains eight fictitious companies, simulated weekday adjusted prices and simulated carbon disclosures. **Nothing in this file is a real corporate observation or research conclusion.** No STOXX membership is asserted.

Generator: `backend/app/services/synthetic_portfolio.py`, fixed NumPy seed 20261103. Reproduce from backend with `.venv/bin/python -m app.services.synthetic_portfolio --output ../data/synthetic/portfolio-v1.json`. The portfolio API uses the same deterministic generator in memory; it never imports this demonstration into PostgreSQL or mixes it with real/private data. Tests compare the stored artifact with its generator.

There are 2,088 prices, eight synthetic disclosures and 260 common daily return intervals. The simulated weekday calendar is not a real exchange calendar. See [portfolio methodology](../../docs/portfolio-optimization.md) for formulas, normalization, constraints, labels and limitations.
