# Shadow decision latency — quiet-host diagnostic pilot

**Date:** 2026-10-06 (host clock; local time UTC-3)  
**Question:** Is the existing `<5.0 ms` assertion defensible for the typical warm-path decision?  
**Threshold status:** **FROZEN — unchanged.** This pilot is diagnostic and does not recalibrate or certify long-term stationarity.

## Verdict

**The current 5 ms assertion passes this quiet-host pilot with useful margin on its actual estimator. Keep the threshold unchanged for now.** Across 10 blocks of 20 observations, every block's upper-middle order statistic—the exact statistic used by `test_decision_latency_is_micro`—was **2.880–3.143 ms**; median of those block statistics was **3.039 ms**. All 10 block host windows classified `QUIET`.

This is a **single-session pilot**, not 10 independent host sessions and not a cross-regime calibration. It supports retaining the current threshold; it does not establish a universal latency guarantee.

## Design and integrity

- 10 fresh `ShadowRouter` instances; each receives one warm-up, then 20 timed calls with the same `BODY` and `_router` fixture as the test.
- 200 latency samples total. Each sample records epoch start, monotonic start, duration, process CPU-time delta, measured milliseconds, and a host-window ID; the JSONL is flushed per record.
- Host telemetry is **block-level**, not a fresh full host snapshot for every ~3 ms call: a separate probe thread measures a 2-second interval overlapping the timestamps of **all 20 samples** in that block. It includes raw CPU-seconds, busy cores, busy %, physical/logical counts, oversubscription, available RAM, memory load, process count, CPU-frequency observation, and contaminant processes. This temporal linkage is diagnostic but cannot assign a unique CPU state to each individual call.
- The Windows process CPU-time counter is coarse relative to a 3 ms call in this environment: deltas frequently quantize to 0 or 15.625 ms. Preserve the raw field, but do not use it to infer per-call CPU consumption. The frequency query returned one value, not 28 per-core measurements; frequency is supporting telemetry only.
- Preflight topology agrees: **14 physical / 28 logical** by the project probe, `os.cpu_count()`, `GetActiveProcessorCount()`, and `NUMBER_OF_PROCESSORS`.
- Preflight was `QUIET` (`oversub=0.337`). During blocks: **10/10 QUIET**, `oversub=0.203–0.441`; 3.8–5.8 GB available RAM, memory load 81–84%.
- No artificial load was started. No contaminated blocks were replaced.
- Working tree at collection: `HEAD=d734697bf26569a558e67c94d4b49c3669fe2891`. `router/shadow.py` was **untracked** in that tree; this artifact measures that exact working-tree file, not a clean checkout of HEAD. The manifest records its SHA-256 and marks the missing HEAD blob. Do not attribute this result to a committed implementation without reviewing that file.

## Results

| host block | verdict | oversub | n | upper-middle (test estimator), ms | median, ms | max, ms |
|---|---|---:|---:|---:|---:|---:|
| 01 | QUIET | 0.348 | 20 | 2.966 | 2.965 | 163.651 |
| 02 | QUIET | 0.295 | 20 | 2.988 | 2.979 | 159.344 |
| 03 | QUIET | 0.302 | 20 | 3.035 | 3.030 | 181.811 |
| 04 | QUIET | 0.241 | 20 | 3.143 | 3.143 | 161.062 |
| 05 | QUIET | 0.281 | 20 | 3.122 | 3.113 | 161.836 |
| 06 | QUIET | 0.203 | 20 | 2.988 | 2.987 | 169.683 |
| 07 | QUIET | 0.366 | 20 | 3.088 | 3.083 | 160.066 |
| 08 | QUIET | 0.263 | 20 | 2.880 | 2.876 | 177.706 |
| 09 | QUIET | 0.342 | 20 | 3.073 | 3.064 | 193.279 |
| 10 | QUIET | 0.441 | 20 | 3.044 | 3.043 | 159.374 |

Pooled across 200 samples: median **3.033 ms**, 190/200 below 5 ms, max **193.279 ms**. The 10 samples at/above 5 ms were all sample `i=0`—the first measured call after the warm-up—in their respective blocks. This pattern also appeared when reproducing the test's 20-call loop directly in one process: first measured call **171.427 ms**, then upper-middle **2.888 ms**, median **2.882 ms**. The cause of this first-call outlier is **not established**; it is preserved rather than discarded. It does not influence the existing upper-middle estimator.

The exact assertion `test_decision_latency_is_micro` passed in a run with the shell safety wrapper removed from the subprocess environment (`pytest ... -q`: **1 passed, rc=0**). A separate invocation reported the test as passed but then exited nonzero because the host's safe-delete wrapper timed out/fail-closed during temp cleanup; that is environment cleanup, not an assertion failure.

## Instrument correction and preserved invalid run

The first pilot was retained as:

`shadow_latency_pilot_raw_20261006_INVALID_POSTWARMUP_HOLD.jsonl`

It inserted a 150 ms controller hold between warm-up and measurement. This artificial gap plausibly changed the first-call scheduling state, so it is **not used** for the verdict. It was renamed, not deleted.

The corrected run removed that hold and records the warm-up-to-first-sample gap (about 0.61–0.67 ms). The raw records show every sample timestamp inside its contemporaneous host-probe window.

## Interpretation and next step

- **Verified fact:** this 200-sample, single-session diagnostic pilot has all 10 host windows `QUIET`; the test's exact block estimator stays below 5 ms in every block.
- **Test result:** the existing latency assertion passes when test cleanup is not intercepted by the shell safety wrapper.
- **Not established:** long-term stationarity, behavior under `MINOR_LOAD`/`CONTAMINATED`, cause of the repeatable first measured-call spike, or behavior on a clean committed `router/shadow.py`.
- **Decision:** do **not** change the 5.0 ms threshold based on this pilot. Keep it frozen; if cross-session assurance is needed, repeat on distinct sessions with the same frozen instrument and source hashes, and resolve the untracked implementation lineage first.

## Artifacts and hashes

- Raw corrected JSONL: `evidence/bench/shadow_latency_pilot_raw_20261006.jsonl`  
  SHA-256: `0128729da63e05ba1ece18d14a92e96d329acc1e2b16d184bf98c265809caeec`
- Preserved invalid first JSONL: `evidence/bench/shadow_latency_pilot_raw_20261006_INVALID_POSTWARMUP_HOLD.jsonl`  
  SHA-256: `f46e192b34037abe5e41e39fdb16cbad7ef55e2de91a5c39f7bafd576c207b3e`
- Instrument used for corrected run (`E:\rotor_tmp\shadow_latency_regime_probe.py`)  
  SHA-256: `755fce4a8d2590d1b61ccfdabf402ae4307d847cc4664e99eab29e2f0a672e38`
- `tests/test_shadow.py` working-tree SHA-256: `fdebd40ee8231691c9fe509df6b3bb6a8a2b8a91214b0693f79e63af38dd7bf7`
- `router/shadow.py` working-tree SHA-256 (untracked at collection): `bc1e9f29415800718d50c02a3852a5b93d7dfe9493181da43ad2d3b55528e4cb`
- `scratch/regime_probe.py` working-tree SHA-256: `a1dfdcaed04fcf4d98c9216cd44f616fdb4bb21d7638fcfa099b3bd031a2f91e`
