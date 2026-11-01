# Limitations

- Forecast and anomaly results are demonstrations over synthetic data and are not operational recommendations.
- NumPy `Generator` stream output is only guaranteed stable when the pinned NumPy version is unchanged.
- Full-scale runtime and quality thresholds are measured by the final local run; do not infer them from starter results.
- Platform-specific timing varies. Hashes cover canonical exports, not SQLite file bytes.
