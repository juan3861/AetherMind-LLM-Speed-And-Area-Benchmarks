# AetherMind Standalone LLM Speed & Area-Highlight Benchmarks

**Bare-metal inference speed telemetry, `llama.cpp` engine tuning (`MTP`, `PLD`, `FA`, `CPU_REPACK`, Thread Scaling, Vulkan vs. AVX2), and standalone area-focused model evaluations** extracted from `F:\rotor-llm\` and `F:\data\`.

> **Repository Separation Notice (For Humans & LLMs)**
> - **This Repository (`AetherMind-LLM-Speed-And-Area-Benchmarks`):** Focuses on **standalone inference speed**, **hardware/engine optimization sweeps** (`llama-bench`, `llama-server`, `MTP` context curves, `PLD` n-gram speculation, `-fa` sweeps, `CPU_REPACK` RAM cliffs, thread-affinity scaling), and **area-highlighted standalone evaluations** (Coding Duels, Battery 50 `ThinkON vs. ThinkOFF`, Early Fleet Championships, High-Caliber/Titan single runs).
> - **Companion Repository ([`juan3861/AetherMind-LLM-Benchmark-Lab`](https://github.com/juan3861/AetherMind-LLM-Benchmark-Lab)):** Houses the **multi-model cross-scale cognitive tournaments** (`35` bare-metal edge/mid models across `13 Cognitive Areas` / `39 Tests` and `10 Opus Hard` algorithmic challenges with `Lambda-RLM` recursive rescue).

---

## 1. Hardware Testbeds & Operational Laws

| Component | Verified Specification | Hardware Constraint & Tuning Implication |
|---|---|---|
| **CPU Host** | **Intel Xeon E5-2697 v3** (Haswell-EP, **14 Physical Cores / 28 Logical Threads**, 2.60 GHz, `AVX2/FMA/F16C/BMI2/REPACK`) | Dual-regime scaling: prefill (`PP`) scales up to `t=20–28`, whereas token generation (`TG`) saturates DRAM bandwidth and degrades under HyperThreading contention beyond `t=7–14`. |
| **System RAM** | **31.84 GiB (~32 GB) DDR4 Quad-Channel** | Hard ceiling for `CPU_REPACK` + `mmap` commit (`31.18 GB` commit on `Qwen3-30B-Q4_K_M` crashes; `IQ3_M` without repack runs cleanly in `29.28 GB`). |
| **Discrete GPU** | **AMD Radeon RX 580 Series** (Polaris 20 / GCN4, **8192 MiB / 8 GB GDDR5 VRAM**, ~7367 MiB idle free, Vulkan `1.3.260`, Adrenalin `26.5.2`, `warp size: 64`, `fp16: 0`, `int dot: 0`, `matrix cores: none`) | Delivers **`3.67×–4.51×` faster prefill** and **`1.57×–4.40×` faster TG** over CPU when tensors fit, but faces a **Windows 256 MB PCIe BAR (No-ReBAR) cliff**—models with contiguous tensor allocations `> 256 MB` throw `VK_ERROR_OUT_OF_HOST_MEMORY`. |
| **Inference Engines** | `llama.cpp` builds `dfc29b64e (10749)` CPU AVX2 (`ggml-cpu-haswell.dll`) & `6a1a922d2 (10819)` Vulkan (`ggml-vulkan.dll`), `llama-bench.exe`, `llama-server.exe`, `llama-cli.exe`, plus Native PyTorch FP32 (`DoryForCausalLM`) | Builds `10749+` enable `--spec-type draft-mtp` and `CPU_REPACK` (`--no-repack` toggle). |

### Operational Laws
1. **The `7.0 tok/s` Golden Rule (`Regra de Ouro`):** Interactive/agentic local loops require `>= 7.0 tok/s` steady token generation (`TG`). Checkpoints falling below this floor on target hardware are flagged or pruned.
2. **Strict `PP` vs. `TG` Separation:** Aggregated `tokens_total / wall_s` hides slow decoding behind fast prefill. All tables below isolate prompt processing (`PP`) from token generation (`TG`), and in Quality Battery runs isolate `completion_tokens` from `prefill_tokens`.

---

## 2. Top Speed & Engine Tuning Highlights

| Tuning / Speed Category | Winner / Case Study | Exact Benchmark Numbers | Key Hardware & Engine Insight |
|---|---|---|---|
| **Fastest GPU Vulkan (`pp512 / tg128`)** | **`MiniCPM5-1B-Q4_K_M`** (`ngl=999, t=14`) | **`1,111.39 tok/s` PP** / **`51.57 tok/s` TG** (`4.17×` PP & `4.15×` TG vs. CPU) | RX 580 Vulkan dominates compute-bound prefill (`3.67×–4.51×` across all 6 swept models). `LFM2.5-8B-A1B` MoE leads 7–8B GPU TG at **`31.31 tok/s`** (`342.46` `pp2048`). |
| **Fastest CPU AVX2 (`-ngl 0`)** | **`MiniCPM4-0.5B-Q4_K_M`** | **`63.58 tok/s` TG (`t=7`)** / **`715.35 tok/s` PP (`t=28`)** | Sub-1B edge leader on DDR4. At 8B MoE scale on CPU, `LFM2.5-8B-A1B` achieves **`24.11 tok/s` TG (`t=10`)** and `129.36 tok/s` PP (`t=20`). |
| **Best `MTP` Context Curve Gain** | **`Qwen3.6-35B-A3B-UD-Q4_K_M` + `MTP`** (`t=12`, `0x5555550`, `KV=q8_0`) | `MTP_1`: **`9.96`** (`+35.9%`, `90.9%` acc) @ short / **`9.49`** (`+26.5%`, `88.1%` acc) @ 2K / `8.21` @ 5K<br>`MTP_2`: **`10.78 tok/s`** (`+35.4%`, `INFERENCE_PROFILE`) & **`8.42 tok/s`** @ 5K (`+22.7%` vs `6.86` baseline)<br>`draft=4, t=8`: **`7.53 avg / 10.23 peak tok/s`**; Warm `draft=2, t=10`: `1.62 -> 7.05` (`4.35×`, `96.88%` acc) | **MoE vs. Dense split:** With only 3B active params, batched `MTP` verification is memory-cheap and keeps 35B MoE above `7.0 tok/s` through 5K ctx. On dense `Qwen3.8-27B`, `MTP` regresses (`2.15 -> 1.31–2.01 tok/s`). `UD-Q4_K_M` also beats Official `Q4_K_M` cold (`4.81` vs `4.27 tok/s`, `-29.0%` TTFT). |
| **`gpt-oss-20b` `CPU_REPACK` & PLD Tuning** | **`gpt-oss-20b-antidoom.i1-IQ4_XS`** (`11.25 GiB`, `t=10`, `0x15555`) | Baseline `Q4_K_M`: `18.05 PP / 13.10 TG` → `antidoom`: `26.36 PP / 9.48 TG` → `10C` affinity: `26.89 PP / 10.47 TG` → PLD tuned: `22.36 PP / 8.73 TG` (`10.96%` acc) → **`CPU_REPACK` (`10,422.42 MiB`): `31.29 tok/s` PP / `10.94 tok/s` TG** | Enabling AVX2 `CPU_REPACK` lifts prefill to a **`31.29 tok/s`** record (`+73.4%` vs baseline) and peaks `antidoom` TG at `10.94 tok/s` (`repack_live.log`; note `proof_gpt20b_repack_paid.json` logged PP `31.29` into `generation_speed`). |
| **`Qwen3-30B-A3B`: `IQ3_M` vs. `Q4_K_M` `CPU_REPACK`** | **`Qwen3-30B-A3B-IQ3_M`** (`13.11 GB`) | **`IQ3_M`: `7.05 tok/s` TG / `14.66` PP** (`29.28 GB` working set, `3/3` pass)<br>`Q4_K_M` (`17.35 GB`): **`FAIL` (`31.18 GB` commit)** | `Q4_K_M` triggers a **`13.83 GB` `CPU_REPACK` buffer** allocation that breaches the 31.84 GiB host RAM limit. `IQ3_M` avoids repack and passes the `7.0 tok/s` Golden Rule. |
| **Flash Attention (`-fa off` vs. `-fa on`)** | Multi-model `-r 5` & `8192` ctx sweep | Neutral (`0.944×–1.049×`) up to `p=2048`; at **`p=8192` GPU**, `-fa 1` is **`-10%` slower (`155.84` vs `173.04 tok/s`)** | Polaris Vulkan FA kernel degrades at long context (`8192`); `-fa` also has **zero accuracy impact** (`9/9` identical CPU/GPU parity on `Qwen2.5-Coder-7B`). |
| **Thread Scaling & Quantization Bandwidth** | `(optimal_pp, optimal_tg)` Law & `Qwen3.8-9B` | Small/mid models peak at **`(PP: t=20..28, TG: t=7..14)`**; `Qwen3.8-9B` `Q8_0` (`9.10 GiB`) `4.00 tok/s` → `IQ4_XS` (`4.98 GiB`) **`7.20 tok/s` CPU / `14.64 tok/s` GPU** | Prefill gains `+43%` to `+61%` from `t=7` to `t=20`, while small-model TG collapses `-31%` to `-70%` at `t=20–28` due to HT contention. Halving payload size scales dense CPU TG linearly (`1.77×`). |

---

## 3. Area-by-Area Highlight Winners

### Coding & Software Engineering
- **Overall Heavy Coder (13 Areas + Opus under Lambda-RLM):** **`gemma-4-12B-coder-fable5-composer2.5-v1`** (`Q4_K_M`, 6.87 GB, Xeon AVX2 @ `4.46 tok/s`) — **`33/39 (84.62%)`** baseline + **`4/10` Opus**, climbing to **`38/39 (97.44%, 12/13 perfect)` + `6/10` Opus** (`OPUS_04, 05, 06, 07, 08, 09`) under Lambda-RLM rescue (`proof_reteste_18_titas_fable_dual.json`). *Why:* Highest raw algorithmic synthesis across standalone 12B coders, best suited for offline/L2 tasks.
- **Pareto Concise Coding Champion (Battery 50 & 9-Task):** **`Qwen2.5-Coder-7B-Instruct`** (`Q4_K_M`, 4.36 GB, Xeon AVX2 @ `9.30 tok/s`) — **`9/9 (100%)`** at **`14.1 gen tok/correct`**, and **`88.67%` (`133/150`, IC95 `[86%, 92%]`)** across 50×3 runs (`54/57` Code, `57/66` Math, `22/27` Extract) at **`18.2 gen tok/correct`** in just `8m01s`. *Why:* `13.8×–15.6×` fewer generated tokens per correct solution than reasoning models while clearing `9 tok/s` on CPU.
- **8B vs. 9B Algorithmic Code & Opus Duel Winner:** **`RLM-Qwen3-8B-v0.1`** (`Q4_K_M`, 4.68 GB, RX 580 Vulkan) — **`9/10 -> 10/10` (`202.06s`)** in the AST/pytest Code Duel and **`2/10 -> 3/10`** in Opus Hard (`OPUS_04, 08, 10`), beating `Qwen3.8-9B-Heretic-IQ4_XS` (`8/10 -> 10/10` in `266.40s`, `1/10` Opus).
- **Fastest Code Fast-Path (Sub-2B):** **`Qwen2.5-Coder-1.5B-Instruct`** (`Q4_K_M`, 1.04 GB, Xeon AVX2) — **`25.54 tok/s` steady** (`460.28 ms` TTFT, `95.59–158.75` PP) with **`100%` Coding (`2/2`), JSON (`2/2`), Tool (`2/2`), and Instruction (`2/2`)** (`0/2` Math).
- **Architectural Outlier:** **`ProCreations-Dory-Beam-4B`** (`DoryForCausalLM` nGPT `Q5_K_M`) — **`29/39 -> 32/39`** + **`OPUS_06` zero-shot** despite running unoptimized FP32 PyTorch (`0.14–0.22 tok/s`) due to missing mainline `llama.cpp` nGPT kernels.

### Math, Reasoning & Quality Battery 50
- **Battery 50 Accuracy & Determinism King (`ThinkON`):** **`Qwen3-8B` (Thinking ON)** (`Q4_K_M`, Xeon AVX2) — **`98.00%` (`147/150`, `sd=0.0`, `100%` of scorable)** with **`66/66 (100%)` Math** and **`27/27 (100%)` Extract** (`3` `c6` code truncations), at `283.2 gen tok/correct` (`93m52s`).
- **Battery 50 Token-Efficiency Toggle (`ThinkOFF`):** **`Qwen3-8B` (Thinking OFF)** — **`90.67%` (`136/150`)** at **`16.4 gen tok/correct`** (**`17.3×` leaner** than ThinkON, beating `Coder-7B`'s `18.2`), achieving **`57/57 (100%)` Code**, **`27/27 (100%)` Extract**, and `0` truncations, while dropping only in multi-step `Math` (`52/66`).
- **Strongest R1 Distill Alternative:** **`DeepSeek-R1-Distill-Qwen-7B`** (`Q4_K_M`, Xeon AVX2) — **`92.00%` (`[83%, 100%]`)** on Battery 50 (`66/66` Math, `55/57` Code, `17/27` Extract) and **`9/9` (`100%`)** on the 9-task baseline, at `250.6–288.7 gen tok/correct`.
- **Lambda-RLM Reasoning Rescues:**
  - **`ai9stars/G9v3-3B`** (`Q4_K_M`, 1.77 GB, RX 580 Vulkan @ `20.06–21.74 tok/s` bare-metal): **`27/39 (69.23%) -> 38/39 (97.44%)`** (`12/13` areas `3/3`!) + `1/10` Opus (`OPUS_08`).
  - **`unsloth-Phi-4-reasoning-14B`** (`Q4_K_M`, 8.43 GB, Xeon AVX2 @ `1.83–2.50 tok/s`): **`3/39 (7.7%) -> 31/39 (79.5%)`** (`+28` rescued from `<think>` token exhaustion) + `1/10` Opus.
  - **`Qwen3-1.7B-Q6_K`** (`22/39 -> 36/39`, `0/10 -> 4/10` Opus) and **`IBM-Grok4-UltraFast-Coder-1B`** (`1/39 -> 25–30/39`, `3/10` Opus in retest).

### Multi-Area Early Championship & 13-Area Generalists
- **CPU Early Championship Overall Winner:** **`Qwen3-4B-Instruct-2507-RLM-SFT-v3`** (`Q4_K_M`, Xeon AVX2 `-t 14`) — **`10/10 (100%)`** across all 5 Campeonato dimensions (`JSON`, `Tool`, `Instruction`, `Math`, `Code`) with **`0` truncations** and **`11.01 tok/s` steady** (`>7.0` PASS).
- **Sub-3B Gateway Champion:** **`MiniCPM5-2B`** (`Q4_K_M`, 1.45 GB, Xeon AVX2) — **`100% (8/8` scorable, `2` truncations)**, **`407.27 ms` TTFT**, **`17.43 tok/s` steady**, and the **only sub-4B model to pass `math_trap`**.
- **GPU Uncensored L1 Generalist:** **`Qwen3.8-9B-Distill-Heretic-Uncensored`** (`IQ4_XS`, 4.99 GB, RX 580 Vulkan `-ngl 99 -fa 1`) — **`9/10 (90%)`** Campeonato at **`14.17 tok/s` steady** (`2.01×` CPU `IQ4_XS`), plus **`33/39 (84.62%)`** on the 13-Area suite.
- **13-Area Bare-Metal Generalist Champion:** **`RLM-Qwen3-8B-v0.1`** (`Q4_K_M`, 4.68 GB, RX 580 Vulkan `-ngl 33`) — **`37/39 (94.87%)`** across 13 cognitive areas (`11/13` perfect `3/3`) at **`8.29 tok/s` effective** (`7.78` raw).

### High-Caliber, Titans & Challengers
- **High-Caliber L1 Speed King (16.8B MoE):** **`Ring-mini 2.0`** (`Q4_K_M`, 9.23 GB, Xeon AVX2 `-t 10`) — **`20.82 tok/s` TG / `30.61` PP** (`1,045 ms` TTFT, `5,194 MB` RAM), fitting 100% in RAM as the fastest high-caliber interactive loop model.
- **High-Caliber L2 Balanced Brain (20B Dense):** **`GPT-OSS 20B`** (`Q4_K_M`, 10.82 GB, Xeon AVX2 `-t 10`) — **`13.10 tok/s` TG / `18.05` PP** (`10,077 MB` RAM), clearing the `7.0 tok/s` floor out of the box.
- **High-Caliber L2 Deep Brain (35B MoE + MTP):** **`Qwen3.6-35B-A3B-UD-Q4_K_M + MTP`** (`21.11 + 1.51 GB`) — **`7.05 tok/s` TG (`11.11` PP, `2,699 ms` TTFT)** when warm in RAM (`4.35×` speedup over `1.62 tok/s` unwarmed baseline).
- **Standalone 30B/26B MoE Titans:** **`Qwen_Qwen3-30B-A3B` (`Q4_K_M`, 17.35 GB)** hits **`8.14 tok/s` TG** (`21/39` areas, **`2/10` Opus** `OPUS_04, 05`), while **`gemma-4-26B-A4B-it-Claude-Opus-Distill-v2`** scores **`29/39 (74.36%)`** areas + `1/10` Opus (`OPUS_08`).
- **Challenger Approvals (`>= 7.0 tok/s`):** `qwen2.5-coder-1.5b-instruct` (`23.25 tok/s` TG / `158.75` PP), `MiniCPM5-2B` (`15.19` TG / `89.02` PP), `granite-4.2-3b` (`13.47` TG / `68.35` PP). *(Blacklisted failures: `Agents-A1-IQ4_XS` at `1.56 tok/s`, `IBM Granite-4.0-h-small` at `2.11 tok/s`, dense `Qwen3.8-27B` at `1.68–2.15 tok/s`.)*

### High-Speed Edge & Micro (`<= 1.5B`)
- **CPU Micro Speed King:** **`MiniCPM4-0.5B-Q4_K_M`** — **`63.58 tok/s` TG (`t=7`) / `715.35 tok/s` PP (`t=28`)**.
- **GPU Micro Speed King:** **`MiniCPM5-1B-Q4_K_M`** — **`51.57 tok/s` TG / `1,111.39 tok/s` PP** (Vulkan `ngl=999`).
- **Ultra-Compact Edge Runners (CPU AVX2):** `SmolLM2-360M` (`50.41 tok/s`), `Qwen2.5-0.5B` (`48.06 tok/s` TG; `61.33%` Battery 50 in `86.2s` for 150 runs), `Qwen3-0.6B` (`47.47 tok/s`), `LFM2-1.2B` (`41.21 tok/s`), `Llama-3.2-1B` (`38.63 tok/s`), `NasledieLab-Qwen3.5-0.8B-Karpy` (`25.00 tok/s` weighted TG / `167.18` PP), `MobileLLM-R1.5-950M` (`14.96 tok/s`).

---

## 4. Full Navigation Index

| Resource | Contents & Purpose |
|---|---|
| **[`SPEED_AND_HARDWARE_TUNING_DOSSIER.md`](SPEED_AND_HARDWARE_TUNING_DOSSIER.md)** | Full hardware/PCIe BAR analysis, GPU Vulkan vs. CPU AVX2 `llama-bench` rankings, parsed server log telemetry, `gpt-oss-20b` optimization journey, `MTP` context curve (`short`–`5K`) & Official vs. UD duels, thread/`-fa`/`PP` sweeps, and `CPU_REPACK` / quantization bandwidth analysis. |
| **[`STANDALONE_AREA_HIGHLIGHTS_CATALOG.md`](STANDALONE_AREA_HIGHLIGHTS_CATALOG.md)** | Complete catalog of standalone & area-focused benchmarks across 4 categories: Multi-Area Generalists & Campeonato, Coding Specialists (`gemma4-coder`, `Qwen2.5-Coder`, `8B vs 9B`, `Dory-Beam-4B`), Reasoning/Math/Battery 50 (`Qwen3-8B ThinkON/OFF`, `G9v3-3B`, `Phi-4-14B`), and High-Caliber/Titans/Challengers. |
| **[`raw_data/`](raw_data/)** | **62 raw telemetry files:** [`raw_data/speed/`](raw_data/speed/) (31 JSON, JSONL, TXT, and parsed `.log` summaries) + [`raw_data/areas/`](raw_data/areas/) (22 JSON/JSONL proof artifacts) + [`raw_data/areas/logs/`](raw_data/areas/logs/) (9 raw `campeonato_*.log` runs). |
| **[`registry_docs/`](registry_docs/)** | **4 canonical laboratory docs:** [`LLM_BENCHMARK_AND_PRUNING_REGISTRY.md`](registry_docs/LLM_BENCHMARK_AND_PRUNING_REGISTRY.md), [`INVENTARIO_E_BENCHMARKS_COMPLETO_DE_TODOS_OS_MODELOS.md`](registry_docs/INVENTARIO_E_BENCHMARKS_COMPLETO_DE_TODOS_OS_MODELOS.md), [`RELATORIO_TECNICO_GPU_CPU_E_BENCHMARKS.md`](registry_docs/RELATORIO_TECNICO_GPU_CPU_E_BENCHMARKS.md), and [`ROTOR_FLEET_STATE.md`](registry_docs/ROTOR_FLEET_STATE.md). |
| **[`scripts/`](scripts/)** | **30 reproducible harnesses & launchers:** [`scripts/speed/`](scripts/speed/) (17 Python sweeps, `.bat` MTP launchers, and `mtp_benchmark.html`) + [`scripts/areas/`](scripts/areas/) (13 standalone, duel, Battery, Titan, and Dory benchmark scripts). |
