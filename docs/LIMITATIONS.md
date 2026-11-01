# Limitations

- Forecast and anomaly results are demonstrations over synthetic data and are not operational recommendations.
- NumPy `Generator` stream output is only guaranteed stable when the pinned NumPy version is unchanged.
- Full-scale generation and validation completed in 70.50 seconds with a sampled peak process-tree working set of 720.1 MiB on the recorded Windows/Python 3.14.7 environment; other machines and operating systems were not benchmarked.
- The `make` executable is not installed in the audited Windows environment. GNU Make targets exist; equivalent `uv run` commands were used.
- Detector metrics are perfect on the tested seeds because deterministic anomaly injection and rule detectors encode matching conditions. These results do not establish production detector accuracy; no false positives/negatives occurred on these generated cases.
- Forecast pipeline adjustment has lower WAPE at 4 and 8 weeks; moving average is better at 12 weeks. Pipeline adjustment has more negative bias at all horizons, and both methods underforecast in the audited full run.
- Zero availability occurred in 131 of 265,000 employee-weeks (0.049%). Leave is concentrated in four synthetic months (February, May, July, December), and only six fixed holidays are modeled.
- A deliberate exception fixture leaves one Active allocation on a Cancelled project to exercise cancellation handling.
- `docs/PROBLEM.md` is absent, so the existing traceability table cannot be verified line-by-line against the original ten-step specification. Explicit Contract recommendations and demand ramp-up/ramp-down curves are also not implemented as separate behaviors.
- Test coverage was 89% overall; CLI statements were not exercised by the Python unit tests, although the documented CLI workflows passed in a fresh clone.
- The small starter sample's moving-average WAPE exceeds 1.0 at all three horizons; this is a property of the synthetic sample, not a general forecast benchmark.
- Platform-specific timing varies. Hashes cover canonical exports, not SQLite file bytes.
