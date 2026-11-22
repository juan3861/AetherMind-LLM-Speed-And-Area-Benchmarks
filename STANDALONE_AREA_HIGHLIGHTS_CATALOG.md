# Standalone & Area-Focused Model Benchmarks Catalog

**Hardware Laboratory Reference:**
- **CPU:** Intel Xeon E5-2697 v3 (14 physical cores / 28 logical threads, Haswell-EP AVX2 @ 2.60 GHz)
- **RAM:** 31.84 GB DDR4 Quad-Channel
- **GPU:** AMD Radeon RX 580 Series (8192 MiB / 8 GB GDDR5 VRAM, ~7367 MiB idle free, Polaris/GCN4, Vulkan API 1.3.260)
- **Inference Backends:** `llama.cpp` CPU AVX2 (`lc_b10749` / `lc/bin/llama-server.exe`), `llama.cpp` Vulkan (`lc_vulkan/llama-server.exe`), and Native PyTorch FP32 (`dory_ngpt_native_pytorch`)
- **Operational Golden Rule:** Minimum steady generation throughput floor = **7.0 tok/s** for interactive agentic loops (models failing this floor on target hardware are flagged/pruned).

---

## Executive Area Winners Summary

| Operational Specialty / Area | Champion Model | Quant / Size | Backend | Speed (`PP` / `TG`) | Winning Metric & Proof |
|---|---|---|---|---|---|
| **L0/L1 Multi-Area Generalist (Full Pass, Direct)** | `Qwen3-4B-Instruct-2507-RLM-SFT-v3` | `Q4_K_M` (~2.33 GB) | Xeon AVX2 (`-t 14`, `-ngl 0`) | `37.31` / `11.01` tok/s | **100% (10/10)** across all 5 Campeonato dims (`0` truncations), `11.01 tok/s` steady (`>7.0` PASS) |
| **L0/L1 Fast Gateway & Reasoning (Sub-3B)** | `MiniCPM5-2B` | `Q4_K_M` (1.45 GB) | Xeon AVX2 (`-t 14`, `-ngl 0`) | `63.84–89.02` / `17.43` tok/s | **100% (8/8 scored)** incl. `math_trap` (only small model to pass), `17.43 tok/s` steady |
| **L1 Large Uncensored Generalist (GPU Vulkan)** | `Qwen3.8-9B-Distill-Heretic-Uncensored` | `IQ4_XS` (4.99 GB) | RX 580 Vulkan (`-ngl 99`, `-fa 1`) | `10.88` cold (`57.50` warm) / `14.17` tok/s | **90% (9/10)** Campeonato (`100%` JSON/Tool/Instr/Code), `14.17 tok/s` steady (`2.01×` CPU IQ4_XS) |
| **13 Cognitive Areas Champion (39 Tests)** | `RLM-Qwen3-8B-v0.1` | `Q4_K_M` (4.68 GB) | RX 580 Vulkan (`-ngl 33`) | `7.78` raw / `8.29` eff tok/s | **37/39 (94.87%)** across 13 cognitive areas (`11/13` perfect 3/3 areas) |
| **13 Cognitive Areas + Lambda-RLM Rescue (12B Dense)** | `gemma-4-12B-coder-fable5-composer2.5-v1` | `Q4_K_M` (6.87 GB) | Xeon AVX2 (`-t 14`, `-ngl 0`) | `9.49` / `4.46` tok/s (single) | **33/39 (84.62%)** baseline & **38/39 (97.44%)** + **6/10 Opus** under Lambda-RLM |
| **Coding & Token-Efficiency Oracle (Quality Battery)** | `Qwen2.5-Coder-7B-Instruct` | `Q4_K_M` (4.36 GB) | Xeon AVX2 (`-t 14`, `-ngl 0`) | `43.05` / `9.30` tok/s | **9/9** (9-task) & **88.67% IC95 [86%, 92%]** (50×3=150 tasks) at **14.1–18.2 gen tok/correct** |
| **Fastest Code Fast-Path (Sub-2B)** | `Qwen2.5-Coder-1.5B-Instruct` | `Q4_K_M` (1.04 GB) | Xeon AVX2 (`-t 14`, `-ngl 0`) | `95.59–158.75` / `25.54` tok/s | **25.54 tok/s** steady (`460 ms` TTFT), **100%** Coding/JSON/Tool/Instruction |
| **8B vs 9B Algorithmic Coding Duel** | `RLM-Qwen3-8B-v0.1` | `Q4_K_M` (4.68 GB) | RX 580 Vulkan (`-ngl 33`) | `6.00–6.40` tok/s | **9/10 -> 10/10** Code Duel & **2/10 -> 3/10** Opus Hard (beats `9b-heretic` 8->10 & 1->1) |
| **Battery 50 Accuracy & Consistency (ThinkON)** | `Qwen3-8B` (Thinking ON) | `Q4_K_M` (4.68 GB) | Xeon AVX2 (`-t 14`, `-ngl 0`) | ~`7–9` tok/s | **98.0% (147/150, sd=0.0)** — **100% (147/147)** scorable (`66/66` Math, `27/27` Extract) |
| **Battery 50 Token-Efficiency (ThinkOFF)** | `Qwen3-8B` (Thinking OFF) | `Q4_K_M` (4.68 GB) | Xeon AVX2 (`-t 14`, `-ngl 0`) | ~`7–9` tok/s | **90.67% (136/150)** at **16.4 gen tok/correct** (`17.3×` leaner than ThinkON; `57/57` Code) |
| **High-Caliber Fleet Throughput (L1/L2 CPU)** | `Ring-mini 2.0` (16.8B MoE, 1.4B act.) | `Q4_K_M` (9.23 GB) | Xeon AVX2 (`-t 10`, `-ngl 0`) | `30.61` / `20.82` tok/s | **20.82 tok/s** (`1045 ms` TTFT, `5194 MB` RAM) — fastest high-caliber interactive model |
| **High-Caliber L2 Deep Brain (20B Dense CPU)** | `GPT-OSS 20B` | `Q4_K_M` (10.82 GB) | Xeon AVX2 (`-t 10`, `-ngl 0`) | `18.05` / `13.10` tok/s | **13.10 tok/s** cold (`4766 ms` TTFT, `10077 MB` RAM) — passes 7.0 tok/s Golden Rule out of the box |

---

## Category 1 — Standalone Multi-Area Generalists & Early Fleet Championship

Evaluated across `BENCHMARK_CAMPEONATO` Parts 1–4 (`raw_data/areas/BENCHMARK_CAMPEONATO_RESULTS.json`, `PART2`, `PART3_IQ4XS`, `PART4_GPU`, plus raw `llama-server` logs in `raw_data/areas/logs/campeonato_*.log`) and the 13-Area / 39-Test Generalist Suite (`proof_benchmark_13_areas_39_testes.json`).

### 1.1 Fleet Championship (`BENCHMARK_CAMPEONATO` Parts 1–4 — 10 Functional Probes)
- **Harness:** `scripts/areas/benchmark_campeonato.py` (`ctx=4096`, `temp=0.0`, `seed=42`, `threads=14`).
- **Dimensions (2 probes each):** `json` (`json_flat`, `json_nested`), `tool` (`tool_timer`, `tool_weather`), `instruction` (`instr_bullets`, `instr_one_word`), `math` (`math_discount`, `math_trap`), `coding` (`code_write`, `code_debug`). Truncated reasoning responses exit the scorable denominator and are tracked separately.

| Model | Arch / Params | Quant | Backend | Load (s) | Cold TTFT (ms) | Cold `PP` (tok/s) | Cold `TG` (tok/s) | Steady `TG` (tok/s) | Peak RAM (MB) | Golden Rule (`>=7.0`) | Scored / Total (Trunc) | `JSON` | `Tool` | `Instr` | `Math` | `Code` | No-Esc % |
|---|---|---|---|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---:|
| **Qwen3-4B-Instruct-2507-RLM-SFT-v3** | Qwen3 Dense 4B | `Q4_K_M` | Xeon AVX2 (`-t 14`, `-ngl 0`) | 14.69 | 616.40 | 37.31 | 9.81 | **11.01** | 3,181.26 | **PASS** | **10/10** (0) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | **100.0%** |
| **MiniCPM5-2B** | MiniCPM5 Dense 2.5B | `Q4_K_M` | Xeon AVX2 (`-t 14`, `-ngl 0`) | 10.40 | **407.27** | 63.84 | 16.39 | **17.43** | 2,037.19 | **PASS** | 8/10 (2) | 1/1 | 2/2 | 1/1 | 2/2 | 2/2 | **100.0%** (scorable) |
| **Qwen3.8-9B-Heretic-Uncensored (GPU)** | Qwen3 Dense 9B | `IQ4_XS` | RX 580 Vulkan (`-ngl 99`, `-fa 1`) | 13.33 | 2,482.62 | 10.88 (57.50 warm) | 12.05 | **14.17** | 7,069.26 | **PASS** | **10/10** (0) | 2/2 | 2/2 | 2/2 | 1/2 | 2/2 | **90.0%** |
| **Qwen3.8-9B-Heretic-Uncensored (CPU)** | Qwen3 Dense 9B | `IQ4_XS` | Xeon AVX2 (`-t 14`, `-fa 1`, `-ngl 0`) | 8.95 | 1,153.63 | 23.40 | 7.05 | **7.04** | 6,384.07 | **PASS** | **10/10** (0) | 2/2 | 2/2 | 2/2 | 1/2 | 2/2 | **90.0%** |
| **Qwen3.8-9B-Heretic-Uncensored (Q8_0)** | Qwen3 Dense 9B | `Q8_0` | Xeon AVX2 (`-t 14`, `-ngl 0`) | 43.03 | 3,929.91 | 6.87 | 3.73 | 4.21 | 9,972.89 | **FAIL** | **10/10** (0) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | **100.0%** |
| **Qwen2.5-Coder-1.5B-Instruct** | Qwen2.5 Dense 1.5B | `Q4_K_M` | Xeon AVX2 (`-t 14`, `-ngl 0`) | **7.63** | 460.28 | **95.59** | **23.95** | **25.54** | **1,175.27** | **PASS** | **10/10** (0) | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 | 80.0% |
| **Granite-3.1-2B-Instruct** *(Incumbent)* | Granite 3.1 Dense 2.5B | `Q4_K_M` | Xeon AVX2 (`-t 14`, `-ngl 0`) | 8.68 | 1,062.94 | 56.45 | 16.68 | **16.92** | 1,984.75 | **PASS** | **10/10** (0) | 1/2 | 2/2 | 2/2 | 1/2 | 2/2 | 80.0% |
| **Granite-4.2-3B** | Granite 4.2 Dense 3.6B | `Q4_K_M` | Xeon AVX2 (`-t 14`, `-ngl 0`) | 11.71 | 914.89 | 43.72 | 11.72 | **12.66** | 2,483.72 | **PASS** | **10/10** (0) | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 | 80.0% |
| **RLM-Qwen3-8B-v0.1** | Qwen3 Dense 8B | `Q4_K_M` | Xeon AVX2 (`-t 14`, `-ngl 0`) | 25.44 | 1,046.54 | 21.98 | 6.95 | **8.13** | 5,349.41 | **PASS** | **10/10** (0) | 1/2 | 1/2 | 1/2 | 1/2 | 2/2 | 60.0% |

#### Why They Stand Out (Category 1A Winners & Diagnostics)
- **Overall Operational Winner (`Qwen3-4B-Instruct-2507-RLM-SFT-v3`):** The **only** model in the Championship to pass the 7.0 tok/s Golden Rule on pure CPU (`11.01 tok/s` steady) **and** achieve **10/10 (100.0%)** across all 5 dimensions with **zero truncations**.
- **Sub-3B Gateway Champion (`MiniCPM5-2B`):** Fastest TTFT (`407.27 ms`) and `17.43 tok/s` steady. Because its native chat template runs in mandatory `reasoning` mode (`observed_reasoning_len=2275`), it was the **only sub-4B model to solve `math_trap`** (`5` vs the classic `100` trap that tripped `Granite-4.2-3B`, `Granite-3.1-2B`, and `Qwen2.5-Coder-1.5B`). Its 2 failures (`json_flat`, `instr_bullets`) were `UNUSABLE_TRUNCATED` at the 512/2048 budget ceiling, not logical errors (`100%` of scorable tasks).
- **CPU-to-GPU Revival (`Qwen3.8-9B-Heretic-Uncensored`):** In `Q8_0` on CPU, it scored **10/10 (100%)** but failed the speed floor (`4.21 tok/s`, `9.97 GB` RAM). Compressing to `IQ4_XS` (`5.36 GB`) rescued CPU speed to `7.04 tok/s` (barely passing Golden Rule, `90%` accuracy—missing 1 math probe), and offloading to the RX 580 via Vulkan (`-ngl 99 -fa 1`) **doubled steady generation to `14.17 tok/s`** (`57.50 tok/s` warm prefill in log task 50) at `7.07 GB` process memory footprint.
- **Note on `RLM-Qwen3-8B-v0.1` in CPU Campeonato:** Its GGUF lacked an embedded `tokenizer.chat_template`, causing `llama.cpp` to fall back to generic ChatML, which hurt strict JSON/tool adherence (`60%`) while preserving `100%` coding (`2/2`). When invoked via the proper RLM harness on GPU (`proof_benchmark_13_areas_39_testes.json`), its accuracy jumped to **94.87%**.

### 1.2 Standalone 13-Area Cognitive Suite (`proof_benchmark_13_areas_39_testes.json`)
Evaluated on **RX 580 8GB Vulkan** (`HeterogeneousRLMHarness`, port `8081`) across 13 cognitive areas × 3 tests = **39 bare-metal tests** per model (`117` total executions):

| Model | Arch / Params | Quant (VRAM) | Backend (`ngl`) | Load (s) | Raw `TG` (tok/s) | Eff `TG` (tok/s) | Total Time (s) | 13-Area Score | Perfect 3/3 Areas |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| **`RLM-Qwen3-8B-v0.1` (`8b-rlm`)** | Qwen3 Dense 8B | `Q4_K_M` (4.68 GB) | RX 580 Vulkan (`-ngl 33`) | 29.70 | **7.78** | **8.29** | 171.24 | **37/39 (94.87%)** | **11/13** |
| **`Qwen3.8-9B-Heretic` (`9b-heretic`)** | Qwen3 Dense 9B | `IQ4_XS` (4.99 GB) | RX 580 Vulkan (`-ngl 30`) | 29.68 | 7.02 | 7.31 | 237.19 | **33/39 (84.62%)** | **8/13** |
| **`Qwen3-4B-Instruct-2507-RLM-SFT-v3` (`4b-rlm`)** | Qwen3 Dense 4B | `Q4_K_M` (2.33 GB) | RX 580 Vulkan (`-ngl 99`) | **15.58** | **12.63** | **13.49** | **89.64** | 18/39 (46.15%) | **2/13** |

#### Area-by-Area Matrix (`proof_benchmark_13_areas_39_testes.json`)

| Area | `8b-rlm` (Score / tok/s) | `9b-heretic` (Score / tok/s) | `4b-rlm` (Score / tok/s) |
|---|---|---|---|
| `01_reflexo_triagem` (Triage) | **3/3** (`7.30`) | 2/3 (`7.79`) | **3/3** (`12.34`) |
| `02_engenharia_codigo` (Code Eng.) | 2/3 (`6.66`) | **3/3** (`6.65`) | 1/3 (`10.77`) |
| `03_matematica_provas` (Math) | **3/3** (`6.73`) | 2/3 (`5.91`) | **3/3** (`11.52`) |
| `04_automacao_so_rpa` (OS/RPA) | **3/3** (`7.58`) | **3/3** (`7.29`) | 1/3 (`11.34`) |
| `05_memoria_perene` (Memory) | **2/3** (`9.57`) | 1/3 (`5.88`) | **2/3** (`11.89`) |
| `06_metacognicao` (Metacognition) | **3/3** (`7.75`) | 2/3 (`7.36`) | 1/3 (`13.08`) |
| `07_cadinho_redteam` (Red-Team) | **3/3** (`8.36`) | **3/3** (`7.51`) | 0/3 (`12.50`) |
| `08_sintese_vocal` (Vocal/TTS) | **3/3** (`6.69`) | **3/3** (`5.59`) | 0/3 (`13.91`) |
| `09_multimodal_visao` (Vision/SVG) | **3/3** (`7.68`) | **3/3** (`7.95`) | 1/3 (`13.49`) |
| `10_planejamento_deliberativo` (Planning) | **3/3** (`7.67`) | **3/3** (`8.68`) | 2/3 (`13.79`) |
| `11_raciocinio_cientifico` (Science) | **3/3** (`10.37`) | 2/3 (`6.43`) | 1/3 (`13.49`) |
| `12_linguagem_discurso` (Discourse) | **3/3** (`7.12`) | **3/3** (`8.20`) | 2/3 (`12.97`) |
| `13_governador_hardware` (HW Gov.) | **3/3** (`7.62`) | **3/3** (`6.00`) | 1/3 (`13.04`) |

- **Why `RLM-Qwen3-8B-v0.1` (`8b-rlm`) Wins Category 1B:** Hits **37/39 (94.87%)** with 11 perfect areas, losing only 1 test in Code Eng (`2/3`) and 1 in Memory (`2/3`), while maintaining `8.29 tok/s` effective throughput on the RX 580 (`-ngl 33`). Meanwhile `4b-rlm` (`13.49 tok/s`) proved strong only in Triage (`3/3`) and Math (`3/3`), leading to its formal restriction to fast triage (`disqualified` from heavy code duels).

---

## Category 2 — Coding & Software Engineering Specialists

Evaluated via `proof_gemma4_coder_13areas.json`, `proof_reteste_18_titas_fable_dual.json`, `proof_duelo_codigo_8b_vs_9b.json`, `proof_duelo_opus_8b_vs_9b.json`, `BENCHMARK_CAMPEONATO_RESULTS.json`, and `quality_results*.jsonl`.

| Model | Arch / Params | Quant (Size) | Backend | `PP` (tok/s) | `TG` (tok/s) | Benchmark / Duel Scope | Exact Score / Outcome |
|---|---|---|---|---:|---:|---|---|
| **`gemma-4-12B-coder-fable5-composer2.5-v1`** | Gemma 4 Dense 12B (Teacher: Fable 5 Coder + Composer 2.5) | `Q4_K_M` (6.87 GB) | Xeon AVX2 (`lc_b10749`, `-t 14`, `-c 4096`) | 9.49 | 4.46 (boot 59s) | 13 Areas (39) + 10 Opus (`proof_gemma4_coder_13areas.json`) | **33/39 (84.62%)** (`8/13` perfect areas: Triage, Code `3/3`, RPA, Red-Team, Vision, Planning, Science, HW Gov) + **4/10 (40.0%) Opus** (`OPUS_04, 05, 07, 08`) |
| **`yuxinlu1-Gemma4-12B-Agentic-Fable5-Composer25`** | Gemma 4 Dense 12B | `Q4_K_M` (6.87 GB) | Dual Retest (`proof_reteste_18_titas_fable_dual.json`) | — | 3.14–4.04 (Normal) / 0.46–2.48 (Lambda) | Normal vs. Lambda-RLM Dual Retest (13 Areas + 10 Opus) | Normal: **24/39 + 3/10 Opus** (`05, 06, 08`) -> Lambda-RLM: **38/39 (97.44%, 12/13 perfect)** + **6/10 (60%) Opus** (`OPUS_04, 05, 06, 07, 08, 09`) |
| **`Qwen2.5-Coder-7B-Instruct`** | Qwen2.5 Dense 7.6B | `Q4_K_M` (4.36 GB) | Xeon AVX2 (`-t 14`, `-ngl 0`, `ctx 4096`) | 43.05 (156.0 GPU `pp512`) | 9.30 (16.32 GPU) | 9-Task Quality + **50-Task × 3 Reps (`150` runs)** | **9/9 (100%)** at **14.1 gen tok/correct**; Battery 50: **88.67% (`133/150`, IC95 [86%, 92%])**, `54/57` Code, `57/66` Math, `22/27` Extract, **18.2 gen tok/correct** in `8m01s` |
| **`Qwen2.5-Coder-1.5B-Instruct`** | Qwen2.5 Dense 1.5B | `Q4_K_M` (1.04 GB) | Xeon AVX2 (`-t 14`, `-ngl 0`) | 95.59 (`158.75` bench) | **25.54** (`23.25` bench) | Campeonato 10 Probes + `BENCHMARK_CHALLENGERS` | **100%** Coding (`2/2`), JSON (`2/2`), Tool (`2/2`), Instruction (`2/2`), `0/2` Math (`80%` overall); **fastest small coder (`25.54 tok/s`)** |
| **`RLM-Qwen3-8B-v0.1` (`8b-rlm`)** | Qwen3 Dense 8B | `Q4_K_M` (4.68 GB) | RX 580 Vulkan (`-ngl 33`) | — | 6.00–6.40 raw (`6.16–6.71` eff) | 10-Test Code Duel + 10-Test Opus Duel | Code Duel: **9/10 zero-shot -> 10/10 (100%)** (`202.06s`, repaired `C02`); Opus Duel: **2/10 zero-shot -> 3/10 (30%)** (`OPUS_04, 08, 10`) |
| **`Qwen3.8-9B-Heretic` (`9b-heretic`)** | Qwen3 Dense 9B | `IQ4_XS` (4.99 GB) | RX 580 Vulkan (`-ngl 30`) | — | 5.99–6.59 raw (`6.10–6.85` eff) | 10-Test Code Duel + 10-Test Opus Duel | Code Duel: **8/10 zero-shot -> 10/10 (100%)** (`266.40s`, repaired `C02, C09`); Opus Duel: **1/10 zero-shot -> 1/10 (10%)** (`OPUS_08`) |
| **`ProCreations-Dory-Beam-4B`** | `DoryForCausalLM` nGPT 4B (72 layers: 16 in + 40 rec ×2 loops + 16 out, 256K ctx) | `Q5_K_M` (3.42 GB) | Native PyTorch FP32 (`dory_ngpt_native_pytorch`) on Xeon CPU | — | 0.14–0.22 (FP32 CPU) | 13 Areas (39) + 10 Opus (`proof_reteste_18_titas_fable_dual.json`) | Normal: **29/39 + 1/10 Opus**; Lambda-RLM: **32/39 + 1/10 Opus** (`OPUS_06_median_two_sorted_arrays` zero-shot!) |
| **`NVIDIA-Nemotron-Labs-Dory1.0-4B`** | `DoryForCausalLM` nGPT Base 4B | `Q5_K_M` (3.42 GB) | Blocked in mainline `llama.cpp` | — | — | `benchmark_dory_dual_full.py` / `finish_nemotron_benchmark.py` | Status: `BLOQUEADO_ARQUITETURA_DORY` in mainline `llama.cpp` (preliminary 13-area run noted in script comments: `27/39` -> `33/39`, Opus pending native harness) |

#### 8B vs. 9B Code & Opus Duel Breakdown (`proof_duelo_codigo_8b_vs_9b.json` & `proof_duelo_opus_8b_vs_9b.json`)
- **Code Duel (10 Algorithmic Tests — AST/Pytest Verified):**
  - `8b-rlm`: Passed `C01` (Rotated Binary Search), `C03` (House Robber DP), `C04` (Coin Change Anti-Greedy `[1,3,4]->6`), `C05` (Levenshtein 2D DP), `C06` (LIS), `C07` (Interval Merge), `C08` (Valid Brackets), `C09` (Longest Unique Substring), `C10` (Directed Graph Cycle) **zero-shot (9/10)**, and self-repaired `C02` (Alphanumeric Palindrome) for **10/10 in 202.06s**.
  - `9b-heretic`: Required self-repair on both `C02` and `C09` (**8/10 -> 10/10 in 266.40s**, 31.8% slower total wall time).
- **Round 2 — Claude Opus Hard Duel (10 Extreme Algorithms):**
  - `8b-rlm` (**Winner: 3/10**): Zero-shot PASS on `OPUS_04` (2D Monotonic Stack Maximal Rectangle) and `OPUS_10` (DPLL CNF SAT Solver), plus RLM-repaired PASS on `OPUS_08` (Trapping Rain Water).
  - `9b-heretic` (**1/10**): Zero-shot PASS only on `OPUS_08`, failing `OPUS_04` and `OPUS_10` even after repair (`882.28s`).
- **Why Coding Specialists Stand Out:**
  - **`gemma-4-12B-coder-fable5-composer2.5-v1`** leads raw multi-area + Opus coding accuracy (**38/39** + **6/10 Opus** under Lambda-RLM), solving `OPUS_04, 05, 06, 07, 08, 09`, though at `3.1–4.5 tok/s` CPU speed it is strictly an L2/offline heavy-coder rather than real-time L1.
  - **`Qwen2.5-Coder-7B-Instruct`** is the **undisputed Pareto king of concise coding & reliability** (`14.1–18.2` generated tokens per correct answer—**13.8×–15.6× leaner** than reasoning models).
  - **`ProCreations-Dory-Beam-4B`** demonstrated remarkable algorithmic capability (`OPUS_06` Partitioned Median zero-shot, `32/39` areas) despite running unoptimized FP32 PyTorch at `0.14–0.22 tok/s` due to missing `llama.cpp` nGPT/Dory kernel support.

---

## Category 3 — Reasoning, Math, Logic & Quality Battery 50

Evaluated via `quality_results.jsonl`, `quality_results_fixed.jsonl`, `quality_results_recomputed_from_logs.json`, `qh_battery50_reps3_*.json*`, `proof_g9v3_english_benchmark.json`, `proof_g9v3_lambda_rlm_english.json`, `proof_comparativo_lambda_rlm_reversao.json`, and `proof_reteste_18_titas_fable_dual.json` (`Phi-4-reasoning-14B`).

### 3.1 Quality Battery 50 (`QH_REPS=3` = 150 Deterministic Executions per Model)
Deterministic evaluation across **50 tasks × 3 reps** (`Math`: 22/rep = 66; `Code`: 19/rep = 57; `Extract`: 9/rep = 27), with strict separation of `completion_tokens` vs `prefill_tokens` and truncation exclusion audit.

| Model | Arch / Params | Quant | Backend | Thinking | Reps Accuracy | Mean (`IC95`) | Truncated | `Math` (`66`) | `Code` (`57`) | `Extract` (`27`) | Gen tok / Correct | Total Time (150 runs) |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| **`Qwen3-8B` (ThinkON)** | Qwen3 Dense 8B | `Q4_K_M` | Xeon AVX2 (`-t 14`, `-ngl 0`, `ctx 4096`) | `default` (ON) | `[0.98, 0.98, 0.98]` (`sd=0.0`) | **98.00%** (`[98%, 98%]`) *(100% scorable)* | 3 (`c6` ×3) | **66/66 (100%)** | 54/57 (94.7%) | **27/27 (100%)** | 283.2 (`41,628` gen) | 5,632.4s (`93m52s`) |
| **`Qwen3-8B` (ThinkOFF)** | Qwen3 Dense 8B | `Q4_K_M` | Xeon AVX2 (`-t 14`, `-ngl 0`, `ctx 4096`) | `0` (`enable_thinking=false`) | `[0.90, 0.92, 0.90]` | **90.67%** (`[88%, 94%]`) | **0** | 52/66 (78.8%) | **57/57 (100%)** | **27/27 (100%)** | **16.4** (`2,234` gen) | 388.3s (task time) |
| **`DeepSeek-R1-Distill-Qwen-7B`** | Qwen2.5 Dense 7B (R1 Distill) | `Q4_K_M` | Xeon AVX2 (`-t 14`, `-ngl 0`, `ctx 4096`) | `default` (ON) | `[0.88, 0.94, 0.94]` (`sd=0.0346`) | **92.00%** (`[83%, 100%]`) | 0 | **66/66 (100%)** | 55/57 (96.5%) | 17/27 (63.0%) | 250.6 (`34,579` gen) | 4,274s (`71m14s`) |
| **`Qwen2.5-Coder-7B-Instruct`** | Qwen2.5 Dense 7.6B | `Q4_K_M` | Xeon AVX2 (`-t 14`, `-ngl 0`, `ctx 4096`) | Direct | `[0.88, 0.88, 0.90]` (`sd=0.0115`) | **88.67%** (`[86%, 92%]`) | 0 | 57/66 (86.4%) | 54/57 (94.7%) | 22/27 (81.5%) | **18.2** (`2,414` gen) | **481s (`8m01s`)** |
| **`LFM2.5-8B-A1B`** | LFM2.5 MoE 8B (1B active) | `Q4_K_M` | RX 580 Vulkan (`-ngl 45`, `-t 7`, `ctx 4096`) | Direct | `[0.64, 0.66, 0.62]` | 64.00% (`[59%, 69%]`) | 0 | 40/66 (60.6%) | 51/57 (89.5%) | 5/27 (18.5%) | 439.9 (`42,233` gen) | 1,972s (`32m52s`) |
| **`Qwen2.5-0.5B-Instruct`** | Qwen2.5 Dense 0.5B | `Q4_K_M` | Xeon AVX2 (`-t 14`, `-ngl 0`, `ctx 2048`) | Direct | `[0.60, 0.62, 0.62]` (`sd=0.0115`) | 61.33% (`[58.5%, 64.2%]`) | **0** | 21/66 (31.8%) | 49/57 (86.0%) | 22/27 (81.5%) | **32.5** (`2,994` gen) | **86.2s** |
| **`MiniCPM5-1B`** *(1 rep, 50 tasks)* | MiniCPM5 Dense 1B | `Q4_K_M` | Xeon AVX2 (`-t 14`, `-ngl 0`, `ctx 2048`) | `default` (ON) | `[0.46]` (`23/35` scorable = `66%`) | 46.0% raw / 66% scorable | **15 (30%)** | 11/15 scorable (73%) | 10/13 scorable (77%) | 2/7 scorable (29%) | 1,096 (`25,212` gen) | 841s (50 tasks) |

- **Critical Battery 50 Insight (`Qwen3-8B ThinkON vs. ThinkOFF`):** Turning thinking OFF reduced generation cost by **17.3×** (`283.2 -> 16.4` gen tok/correct, beating even `Coder-7B`'s `18.2`), **fixed `c6` code truncation** (`54/57 -> 57/57`), and maintained **27/27 Extract**, while dropping **Math from `66/66` to `52/66` (-14)**—proving `<think>` is structurally required for multi-step math, whereas `code` and `extract` perform better without reasoning overhead.

### 3.2 Recomputed 9-Task Quality Baseline (`quality_results.jsonl`, `quality_results_fixed.jsonl`, `quality_results_recomputed_from_logs.json`)
Log-verified token accounting (`completion_tokens` isolated from ~35 tok/task prefill, `ctx=4096`):

| Tag / Model | Quant | Device (`ngl`) | Score (Orig -> Fixed) | Math | Code | Extract | Total Time (s) | Old `tok/correct` | True `gen tok/correct` |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`Qwen25-Coder-7B-CPU`** | `Q4_K_M` | CPU (`0`) | **9/9 (100%)** | 5/5 | 3/3 | 1/1 | 22.3 | 50.8 | **14.1** (`127` gen) |
| **`MiniCPM5-2B-GPU`** | `Q4_K_M` | GPU (`45`) | **8/9** (`8/8` scorable, 1 trunc) | 5/5 | 3/3 | 0/1 | 31.9 -> 78.1 | 150.8 | **110.4** (`883` gen) |
| **`Phi4-mini-GPU`** | `Q4_K_M` | GPU (`45`) | 2/9 -> **5/9** | 2/5 | 2/3 | 1/1 | 10.0 -> **8.5** | 241.0 -> 92.0 | **111.0** (`222` gen orig) |
| **`Qwen3-1.7B-GPU`** | `Q4_K_M` | GPU (`45`) | **9/9 (100%)** | 5/5 | 3/3 | 1/1 | 69.3 | 311.9 | **276.6** (`2,489` gen) |
| **`R1-Distill-7B-CPU`** | `Q4_K_M` | CPU (`0`) | **9/9 (100%)** | 5/5 | 3/3 | 1/1 | 315.7 | 320.7 | **288.7** (`2,598` gen) |
| **`LFM25-8B-CPU-14t`** | `Q4_K_M` | CPU (`0`) | 7/9 | 4/5 | 2/3 | 1/1 | 101.1 | 434.3 | **333.6** (`2,335` gen) |
| **`LFM25-8B` (CPU / GPU Fix)** | `Q4_K_M` | CPU (`0`) / GPU (`45`) | 6/9 -> **8/9** | 4/5 | 3/3 | 1/1 | 124.2 -> 80.0 | 483.7 -> 369.0 | **368.0** (`CPU orig`) |
| **`Qwen3-8B-CPU`** | `Q4_K_M` | CPU (`0`) | **8/9** (`8/8` scorable, 1 trunc) | 5/5 | 2-3/3 | 1/1 | 392.1 -> 426.9 | 410.4 | **370.6** (`2,965` gen) |
| **`M5-1B-CPU` (v1 / v2)** | `Q4_K_M` | CPU (`0`) | 4/9 / 3/9 | 3/5 / 2/5 | 1/3 | 0/1 | 85.9 / 173.4 | 705.8 / 1,785.0 | **625.0** / **1,677.3** |
| **`Nemotron-1.5B-GPU`** | `Q4_K_M` | GPU (`45`) | 4/9 (Pruned: extreme verbosity) | 4/5 | 0/3 | 0/1 | 229.5 | 2,484.5 | **2,405.0** (`9,620` gen) |

### 3.3 G9v3-3B (English Native vs. Lambda-RLM), Phi-4-14B & Lambda-RLM Reversal Proofs

| Model | Arch / Params | Quant (Size) | Backend | Speed (`TG`) | 13 Areas (Baseline -> Lambda-RLM) | 10 Opus (Baseline -> Lambda-RLM) | Highlights & Standout Behavior |
|---|---|---|---|---:|---|---|---|
| **`ai9stars/G9v3-3B`** (`proof_g9v3_english_benchmark.json` & `proof_g9v3_lambda_rlm_english.json`) | Dense 3B | `Q4_K_M` (1.77 GB) | RX 580 Vulkan (`-ngl 99`, port `8081`) | **20.06** tok/s (13 areas) / **21.74** tok/s (Opus) bare-metal; `1.80` / `10.96` tok/s under Lambda-RLM | **27/39 (69.23%)** -> **38/39 (97.44%)** (`+11` areas rescued; **12/13** areas 3/3!) | **1/10 (10.0%)** -> **1/10 (10.0%)** (`OPUS_08_trapping_rain_water` zero-shot) | Bare-metal English: `3/3` in Code, Math, OS/RPA, Vision, HW Gov; Lambda-RLM rescued Triage, Memory, Metacognition, Red-Team, Vocal, Planning, Science, Discourse to `3/3` (only `02_code_engineering` was `2/3`). |
| **`unsloth-Phi-4-reasoning-14B`** (`proof_reteste_18_titas_fable_dual.json`, `run_phi4_14b_benchmark.py`) | Phi-4 Dense 14B Reasoning | `Q4_K_M` (8.43 GB) | Xeon AVX2 (`lc/bin`, `-t 12`, `-c 2048`, `-b 512`, `-ub 128`) | **1.83–2.50** tok/s (Opus telemetry) | **3/39 (7.7%)** -> **31/39 (79.5%)** (`+28` rescued!) | **0/10** -> **1/10** (`OPUS_08_trapping_rain_water`) | Classic reasoning verbosity bottleneck in baseline (`n_predict=512` exhausted inside `<think>`); Lambda-RLM unlocked `3/3` in Triage, RPA, Red-Team, Vocal, Vision, Science, HW Gov (`0/3` in Code Eng). |
| **`Qwen3-1.7B-Q6_K`** (`proof_comparativo_lambda_rlm_reversao.json`) | Qwen3 Dense 1.7B | `Q6_K` (1.56 GB) | Lambda-RLM Reversal Study | — | **22/39** -> **36/39 (92.3%)** (`+14`) | **0/10** -> **4/10 (40%)** (`2` zero-shot, `2` repaired) | Proves sub-2B Q6_K + Lambda-RLM achieves 40% Opus Hard. |
| **`DeepSeek-R1-Distill-Qwen-1.5B`** (`proof_comparativo_lambda_rlm_reversao.json`) | Qwen2.5 Dense 1.5B Reasoning | `Q4_K_M` (1.04 GB) | Lambda-RLM Reversal Study | — | **6/39** -> **25/39 (64.1%)** (`+19`) | **0/10** -> **2/10 (20%)** (`1` zero-shot, `1` repaired) | Rescued from `<think>` overflow on 13-area prompts. |
| **`IBM-Grok4-UltraFast-Coder-1B`** (`proof_comparativo_lambda_rlm_reversao.json` & `proof_reteste_18`) | Dense 1B Compact Coder | `Q4_K_M` (0.95 GB) | Lambda-RLM Reversal Study | — | **1/39** (`0/39` retest) -> **25/39** (`30/39` retest) | **0/10** -> **0/10** (`3/10` in retest: `OPUS_06, 07, 08`) | Zero-shot broken without structured scaffolding; Lambda-RLM turns a `1/39` failure into `25–30/39`. |

---

## Category 4 — High-Caliber, Titans & Challenger Models

Evaluated via `BENCHMARK_HIGH_CALIBER_RESULTS.json`, `BENCHMARK_CHALLENGERS_RESULTS.json`, `proof_novos_titans_pendentes.json` (`benchmark_titan_single.py`), and `iq3xxs_bench.json` (`test_27b_benchmark.py`, `test_iq3xxs_benchmark.py`).

### 4.1 High-Caliber Fleet (`BENCHMARK_HIGH_CALIBER_RESULTS.json` — Xeon AVX2, `-t 10`, `-ngl 0`)

| Model | Arch / Params | Quant | Disk Size | Load (s) | `PP` (tok/s) | `TG` (tok/s) | TTFT (ms) | Peak RAM (MB) | Golden Rule (`>=7.0`) | Operational Verdict |
|---|---|---|---|---:|---:|---:|---:|---:|:---:|---|
| **`Ring-mini 2.0`** | MoE 16.8B (1.4B active) | `Q4_K_M` | 9.23 GB | 39.89 | **30.61** | **20.82** | **1,045.36** | **5,193.98** | **PASS** | **L1 Speed King** — fits 100% in RAM, `20.82 tok/s`, ideal for terminal/RAG/fast loops |
| **`GPT-OSS 20B`** | Dense 20B | `Q4_K_M` | 10.82 GB | 50.76 | 18.05 | **13.10** | 4,765.71 | 10,076.76 | **PASS** | **L2 Balanced Brain** — dense 20B surpassing 13 tok/s on pure Xeon CPU |
| **`Qwen3.6-35B-A3B MoE + MTP`** | MoE 35B (3B active) + MTP Head | `UD-Q4_K_M` | 21.11 + 1.51 GB | **34.45** | 11.11 | **7.05** | 2,699.36 | 12,631.60 | **PASS (Warm)** | **L2 Deep Brain** — MTP speculative draft head yields **4.35× `TG` speedup** (`1.62 -> 7.05 tok/s`) and **8.6× faster TTFT** (`23.2s -> 2.7s`) when kept warm |
| **`Qwen3.6-35B-A3B MoE (Baseline)`** | MoE 35B (3B active), no MTP | `UD-Q4_K_M` | 21.11 GB | 70.82 | 1.29 | 1.62 | 23,236.49 | 11,502.75 | **FAIL** | Unviable without MTP / keep-alive |
| **`Agents-A1`** *(PRUNED)* | MoE / Dense 17B | `IQ4_XS` | 17.44 GB | 70.60 | 2.41 | **1.56** | 12,430.29 | 9,302.79 | **FAIL (BANNED)** | **Deleted from disk** — memory bandwidth crushes AVX2 (`1.56 tok/s`, `12.4s` TTFT) |

### 4.2 Standalone Challengers (`BENCHMARK_CHALLENGERS_RESULTS.json` — `llama-bench b10749`, Xeon AVX2, `-t 14`)

| Model | Arch / Params | Quant | Size | `PP` (`pp512`, tok/s) | `TG` (`tg128`, tok/s) | Verdict |
|---|---|---|---:|---:|---:|---|
| **`qwen2.5-coder-1.5b-instruct`** | Qwen2.5 Dense 1.5B | `Q4_K_M` | 1.04 GB | **158.75** | **23.25** | **APROVADO (`>= 7.0 tok/s`)** — L1 Code Fast-Path |
| **`MiniCPM5-2B`** | MiniCPM5 Dense 2.5B | `Q4_K_M` | 1.45 GB | 89.02 | **15.19** | **APROVADO (`>= 7.0 tok/s`)** — L0/L1 Universal Gateway |
| **`granite-4.2-3b`** | Granite 4.2 Dense 3.6B | `Q4_K_M` | 2.09 GB | 68.35 | **13.47** | **APROVADO (`>= 7.0 tok/s`)** — Configurable Reasoning L1 |

### 4.3 Standalone Titans (`proof_novos_titans_pendentes.json`, `benchmark_titan_single.py`, `iq3xxs_bench.json`)

| Model | Arch / Params | Quant (Size) | Backend | `PP` (tok/s) | `TG` (tok/s) | 13 Areas (39 Tests) | 10 Opus Hard | Elapsed / Notes |
|---|---|---|---|---:|---:|---:|---:|---|
| **`gemma-4-26B-A4B-it-Claude-Opus-Distill-v2`** | Gemma-4 MoE 26B (4B active, Opus Distill) | `Q4_K_M` (15.64 GB) | Xeon AVX2 (`lc/bin`, `-t 12`, `-c 3072`, `--no-repack`) | **27.34** | *`51291.02` (telemetry div-by-zero anomaly in JSON/log)* | **29/39 (74.36%)** (`7/13` perfect 3/3: Triage, Memory, Metacog, Vocal, Vision, Discourse, HW Gov) | **1/10 (10%)** (`OPUS_08` zero-shot; 9 SyntaxErrors on formatting) | `1,354.0s` (`benchmark_titan_1.log`). Strong non-code cognitive areas (`74.36%`), weak strict Python extraction. |
| **`Qwen_Qwen3-30B-A3B`** | Qwen3 MoE 30B (3B active) | `Q4_K_M` (17.35 GB) | Xeon AVX2 (`-t 12`) | **25.86** | **8.14** | 21/39 (53.85%) | **2/10 (20%)** (`OPUS_04, OPUS_05` zero-shot) | `1,235.62s`. Passes `7.0 tok/s` Golden Rule at 30B MoE scale! |
| **`Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled`** | MoE 35B (3B active, Claude 4.7 Opus Distill) | `Q4_K_M` (19.71 GB) | Xeon AVX2 (`-t 12`) | 18.16 | 3.72 | 14/39 (35.90%) | 0/10 (0%) | `4,373.49s` (`72.9 min`). Reasoning verbosity truncated/timed out code output at `3.72 tok/s`. |
| **`GPT-5.6-Sol`** *(oroboros-labs)* | Dense 8B/9B Sol Distill | `GGUF` (5.03 GB) | Xeon AVX2 | 20.84 | 7.55 | 7/39 (17.95%) | 0/10 (0%) | `SyntaxError` across 9/10 Opus tasks (`0/3` HW Gov, Vision, Science). |
| **`Qwen3.8-27B-UD-IQ3_XXS`** (`iq3xxs_bench.json`, `test_iq3xxs_benchmark.py`) | Dense 27B Unsloth Dynamic | `IQ3_XXS` | Xeon AVX2 (`ctx 2048`) | — | **1.68** (OFF, `-t 14`) / 1.48 (`draft-mtp=3`, `-t 12`) / 0.93 (`draft-mtp=4`, `-t 8`) | Speed/MTP Feasibility Probe | — | Dense 27B hits `1.68 tok/s` max; adding MTP draft hurt dense 27B (`1.48` / `0.93 tok/s`) due to memory bandwidth saturation. |
| **`Claude-Qwen3.5-V2`** *(mondk)* & **`Ornith-1.5-9B`** *(xoykor)* | 3.56 GB (`Q6_K`) / 6.64 GB (`Q5_K_M`) | `Q6_K` / `Q5_K_M` | Xeon AVX2 | — | — | **FAIL_BOOT** | **FAIL_BOOT** | Boot timeout or GGUF architecture incompatibility (`proof_novos_titans_pendentes.json`). |

---

## Key Empirical Takeaways Across Standalone Areas

1. **Speed vs. Conciseness Wins Agentic Loops:** `Qwen2.5-Coder-7B` (`9.30 tok/s` CPU, **14.1–18.2 gen tok/correct**) finishes 150 tasks in **8m01s**, whereas `R1-Distill-7B` (`9.02 tok/s`, **250.6 gen tok/correct**) takes **71m14s** for roughly overlapping accuracy (`88.7%` vs `92.0%`, within overlapping 95% CIs).
2. **Thinking Toggle Is Task-Specific (`Qwen3-8B`):** Keeping `<think>` ON yields **98.0% (`66/66` Math, `27/27` Extract, `sd=0`)**, while toggling `<think>` OFF cuts generation tokens by **17.3× (`16.4 tok/correct`)**, fixes `code` truncations (`57/57`), and preserves `27/27` Extract—losing accuracy exclusively in multi-step `Math` (`52/66`).
3. **Lambda-RLM Rescues Verbose Reasoning & Weak-Format Models:** `G9v3-3B` (`27/39 -> 38/39`), `Phi-4-reasoning-14B` (`3/39 -> 31/39`), `Gemma4-12B-Agentic` (`24/39 -> 38/39`, `3/10 -> 6/10` Opus), `Qwen3-1.7B` (`22/39 -> 36/39`, `0/10 -> 4/10` Opus), and `IBM-Grok4-1B` (`1/39 -> 25–30/39`) prove that formal-verifier feedback + prompt framing eliminates `<think>` exhaustion and formatting failures.
4. **MoE vs. Dense Scaling on Xeon AVX2:** Sparse MoE models with `1.4B–3B` active parameters (`Ring-mini 2.0` at `20.82 tok/s`, `Qwen3-30B-A3B` at `8.14 tok/s`, `Qwen3.6-35B-A3B + MTP` at `7.05 tok/s` warm) consistently clear the `7.0 tok/s` Golden Rule, while dense `17B–27B` models (`Agents-A1` at `1.56 tok/s`, `Qwen3.8-27B-IQ3_XXS` at `1.68 tok/s`) collapse under DDR4 memory-bandwidth saturation.
