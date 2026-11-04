# Explicitly synthetic portfolio demonstration

`portfolio-v1.json` contains eight fictitious companies, simulated weekday adjusted prices and simulated carbon disclosures. **Nothing in this file is a real corporate observation or research conclusion.** No STOXX membership is asserted.

Generator: `backend/app/services/synthetic_portfolio.py`, fixed NumPy seed 20261103. Reproduce from backend with `.venv/bin/python -m app.services.synthetic_portfolio --output ../data/synthetic/portfolio-v1.json`. The portfolio API uses the same deterministic generator in memory; it never imports this demonstration into PostgreSQL or mixes it with real/private data. Tests compare the stored artifact with its generator.

There are 2,088 prices, eight synthetic disclosures and 260 common daily return intervals. The simulated weekday calendar is not a real exchange calendar. See [portfolio methodology](../../docs/portfolio-optimization.md) for formulas, normalization, constraints, labels and limitations.

`evaluation-v1.json` is the separate Task 06 historical scenario recipe (seed 20261106, IDs 20001–20008). `synthetic_history.py` generates rising/falling covariance regimes, delayed disclosures and universe entry/exit without future-centered calibration. The Evaluation API uses these explicitly simulated histories in memory; this is independent of the Task 05 one-window example and not real historical membership or prices. See [historical methodology](../../docs/historical-evaluation.md).
