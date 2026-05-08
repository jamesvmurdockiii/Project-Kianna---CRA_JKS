# Tier 7.1a Real-ish/Public Adapter Contract

- Generated: `2026-05-08T20:39:34+00:00`
- Runner revision: `tier7_1a_realish_adapter_contract_20260508_0001`
- Status: **PASS**
- Criteria: `12/12`

## Selected Adapter

- Adapter: `nasa_cmapss_rul_streaming`
- Dataset family: NASA C-MAPSS / turbofan engine degradation
- Reason: Tier 6.2a found a narrow variable-delay signal. C-MAPSS is the first real-ish public stream family to test delayed sensor history -> future degradation/RUL structure without relying on private task generators.
- First executable tier: `Tier 7.1b`

## Source Audit

| Source | URL | Role | Verification |
| --- | --- | --- | --- |
| NASA Prognostics Center of Excellence Data Set Repository | https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/ | primary official source for C-MAPSS / turbofan degradation data access | source page checked 2026-05-08 |
| DASHlink Turbofan Engine Degradation Simulation Data Set | https://c3.ndc.nasa.gov/dashlink/resources/139/ | official NASA DASHlink landing page for the classic C-MAPSS turbofan data resource | source page checked 2026-05-08 |
| Numenta Anomaly Benchmark | https://github.com/numenta/NAB | secondary candidate for streaming anomaly adapter after C-MAPSS contract execution | source page checked 2026-05-08 |
| UCR/UEA Time Series Classification Archive | https://www.timeseriesclassification.com/ | future held-out time-series classification adapter source | source page checked 2026-05-08 |
| PhysioNet databases | https://www.physionet.org/about/database/ | future biosignal/event-stream adapter source after license/split audit | source page checked 2026-05-08 |

## Required Baselines

- constant/mean-RUL baseline
- monotone age-to-RUL baseline
- lag/ridge window baseline
- online LMS / linear readout baseline
- random reservoir online baseline
- fixed ESN train-prefix ridge baseline
- small GRU/LSTM if dependency/runtime budget is practical
- tree/boosting window baseline if scikit-learn is available
- CRA v2.2 fading-memory reference
- CRA v2.3 generic bounded recurrent-state baseline
- v2.3 state-reset/shuffled/no-update controls

## Leakage Controls

- train-unit statistics only for normalization
- no test-unit future RUL labels during online prediction
- chronological prediction within each engine unit
- unit-held-out evaluation
- predeclared sensor/channel selection before scoring
- prediction-before-update for online models
- data download/checksum manifest preserved
- all task transforms logged to JSON before model scoring

## Pass / Fail Boundary

- Contract pass means: the adapter is fully predeclared and safe to implement; it does not mean CRA is useful on C-MAPSS
- Next step: Tier 7.1b should implement a source/data preflight for NASA C-MAPSS, download or locate the data reproducibly, write checksums and license notes, then emit a tiny adapter smoke before full scoring.

## Nonclaims

- not a C-MAPSS result
- not a public usefulness claim
- not a baseline freeze
- not hardware or native transfer
- not evidence that variable-delay private diagnostics generalize
- not language, planning, AGI, or ASI evidence
