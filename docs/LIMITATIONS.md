# Limitations

- Forecast and anomaly results are demonstrations over synthetic data and are not operational recommendations.
- NumPy `Generator` stream output is only guaranteed stable when the pinned NumPy version is unchanged.
- Full-scale generation and validation completed in 66.73 seconds on the recorded Windows/Python 3.14.7 environment; other machines and operating systems were not benchmarked.
- The `make` executable is not installed in the current Windows environment. Its commands were run through the equivalent `uv run wdf ...` and `uv run pytest` commands.
- The small synthetic sample's 4-week moving-average WAPE is greater than 1.0 at each backtest horizon; the pipeline-adjusted method performed better here, but these results are not generalizable.
- Platform-specific timing varies. Hashes cover canonical exports, not SQLite file bytes.
