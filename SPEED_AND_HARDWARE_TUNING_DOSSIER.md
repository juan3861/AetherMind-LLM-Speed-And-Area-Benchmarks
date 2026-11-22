# AetherMind Standalone Speed & Hardware Tuning Dossier

**Scope:** Standalone inference speed benchmarks, `llama-bench` hardware telemetry, speculative decoding (`MTP`, `PLD` n-gram), Flash Attention (`-fa`), `CPU_REPACK`, thread-affinity scaling, prompt-processing (`PP`) curves, and quantization memory-bandwidth analyses extracted from `F:\rotor-llm\` and `F:\data\`.  
*(Strictly separated from the multi-model cognitive & Opus tournaments in [`AetherMind-LLM-Benchmark-Lab`](https://github.com/juan3861/AetherMind-LLM-Benchmark-Lab).)*

---

## 0. Hardware Testbeds, Constraints & Measurement Methodology

### 0.1 Reference Hardware
| Component | Specification (Empirically Verified) | Engineering Implication |
|---|---|---|
| **CPU Host** | **Intel Xeon E5-2697 v3** (Haswell-EP, **14 Physical Cores / 28 Logical Threads**, 2.60 GHz, `SSE3/SSSE3/AVX/AVX2/F16C/FMA/BMI2/REPACK`) | Dual-regime bottleneck: prefill (`PP`) scales up to 20–28 threads; token generation (`TG`) is memory-bandwidth & HT-contention bound (peaks at `t=7`–`14`). |
| **System RAM** | **31.84 GiB (~32 GB) DDR4 Quad-Channel** | Hard ceiling for `CPU_REPACK` + mmap commit (`31.18 GB` commit on `Qwen3-30B-Q4_K_M` fails; `IQ3_M` without repack succeeds in `29.28 GB`). |
| **Discrete GPU** | **AMD Radeon RX 580 Series** (Polaris 20 / GCN4, **8192 MiB / 8 GB GDDR5 VRAM**, 7367 MiB free idle, Vulkan `1.3.260`, driver `26.5.2`, `warp size: 64`, `fp16: 0`, `int dot: 0`, `matrix cores: none`) | Fast prefill (`3.67×–4.51×` over CPU) and solid generation (`1.57×–4.40×` over CPU) when tensors fit, **but gated by Windows 256 MB PCIe BAR limit**. |
| **Inference Engines** | `llama.cpp` (`llama-bench.exe`, `llama-server.exe`, `llama-cli.exe`) builds `dfc29b64e (10749)` CPU AVX2 (`ggml-cpu-haswell.dll`) & `6a1a922d2 (10819)` Vulkan (`ggml-vulkan.dll`) | Builds `10749`+ introduce `--spec-type draft-mtp` and `CPU_REPACK` (`--no-repack` toggle). |

### 0.2 The 256 MB PCIe BAR (No-ReBAR) Vulkan Cliff
Empirical attempts to offload models with single contiguous tensors exceeding **256 MB** onto the RX 580 via Vulkan fail on X99/Xeon motherboards lacking Resizable BAR (`ReBAR` / Above 4G Decoding) under Windows WDDM:
- `Qwen2.5-7B-Instruct-Q4_K_M` (`server_vulkan_split.log`) → `alloc_tensor_range: failed to allocate Vulkan0 buffer of size 1044828160` (`VK_ERROR_OUT_OF_HOST_MEMORY`).
- `Qwen3.8-27B-UD-IQ3_XXS` (`server_27b.log`) → `failed to allocate Vulkan0 buffer of size 849838080` / `1053536000` (`ErrorOutOfHostMemory`).
- `Qwen 1.5B / Granite` hybrid offload tests (`RELATORIO_TECNICO_GPU_CPU_E_BENCHMARKS.md`) → failed on `311409152` B (`297 MB`) contiguous allocation.
- Models whose individual tensor buffers stay under the threshold (`MiniCPM5-1B/2B`, `Qwen2.5-1.5B`, `Qwen2.5-Coder-7B`, `DeepSeek-R1-Distill-7B`, `LFM2.5-8B-A1B`, `Qwen3.8-9B-IQ4_XS`, 14B `IQ3_M`/`Q3_K_M` in `lc_vulkan`) offload cleanly at `-ngl 45 / 99 / 999`.

### 0.3 Operational Laws & Measurement Integrity
1. **Golden Rule (`Regra de Ouro`):** Minimum acceptable throughput for local interactive/agentic loops = **`7.0 tok/s`** steady/cold generation (`INVENTARIO_E_BENCHMARKS_COMPLETO_DE_TODOS_OS_MODELOS.md`, `LLM_BENCHMARK_AND_PRUNING_REGISTRY.md` §0.2).
2. **Strict `PP` vs `TG` Separation:** Never report aggregated `tokens_total / wall_s` (which mixes fast prefill with slow generation, as proved in §6.21.2 and §6.23.1). All log summaries below separate weighted `PP` (`sum(prompt_tokens) / sum(prompt_ms)`) and weighted `TG` (`sum(eval_tokens) / sum(eval_ms)`), filtering out 1-token `0.00 ms` end-of-stream artifacts.
3. **Cold-Start vs Warm-RAM Regime:** On 20–35B MoE checkpoints, cold mmap loading penalizes TTFT heavily; keep-alive (`warm RAM`) is mandatory for speculative `MTP` wins.

---

## 1. Pure `llama-bench` Speed Rankings (GPU Vulkan vs CPU AVX2) & Log Telemetry

### 1.1 GPU Vulkan (`-ngl 45 / 99 / 999`) `llama-bench` & `llama-cli` Rankings
Sources: `raw_data/speed/pp_sweep.jsonl`, `raw_data/speed/arena_bench.log`, `raw_data/speed/fleet_benchmark_results.json`, `raw_data/speed/server_bench.jsonl`, `F:\rotor-llm\scratch\bench_7b_gpu.log`.

| Rank (TG) | Model | Params / Quant | Size | Config (`ngl` / `ctx` / test) | PP (`tok/s`) | TG (`tok/s`) | Source |
|---:|---|---|---:|---|---:|---:|---|
| 1 | **MiniCPM5-1B** | ~1B `Q4_K_M` | — | `ngl=999, t=14` (`pp512 / tg128`) | **1,111.39** *(pilot: 1,117.3)* | **51.57** *(pilot: 53.4)* | `pp_sweep.jsonl` |
| 2 | **Qwen2-VL-2B-Instruct** | `1.54 B` `Q4_K_M` | `934.69 MiB` | `ngl=45` (`pp512 / tg128`) | **675.18** | **43.67** | `arena_bench.log` |
| 3 | **Qwen2.5-1.5B-Instruct** | `1.5 B` `Q4_K_M` | — | `ngl=999, t=14` (`pp512 / tg128`) | **673.72** | **43.04** | `pp_sweep.jsonl` |
| 4 | **LFM2.5-8B-A1B (MoE)** | `8B (1B active)` `Q4_K_M` | — | `ngl=999, t=14` (`pp512 / tg128`) | **340.56** *(pp2048: 342.46)* | **31.31** | `pp_sweep.jsonl` |
| — | **LFM2.5-8B-A1B (server)** | `8B (1B active)` `Q4_K_M` | `5106.5 MiB` VRAM | `ngl=45, ctx=8192` (`p=38, n=128`) | 10.29 *(micro-prompt)* | **30.10** | `server_bench.jsonl` |
| 5 | **MiniCPM5-2B** | ~2B `Q4_K_M` | — | `ngl=999, t=14` (`pp512 / tg128`) | **428.06** | **30.31** | `pp_sweep.jsonl` |
| 6 | **Phi-4-mini-instruct** | `3.84 B` `Q4_K_M` | `2.31 GiB` | `ngl=45` (`pp512 / tg128`) | **290.91** | **29.05** | `arena_bench.log` |
| 7 | **Qwen3-VL-4B-Instruct** | `4.02 B` `Q4_K_M` | `2.32 GiB` | `ngl=45` (`pp512 / tg128`) | **245.33** | **23.92** | `arena_bench.log` |
| 8 | **Qwen2.5-VL-7B-Instruct** | `7.62 B` `Q4_K_M` | `4.36 GiB` | `ngl=45` (`pp512 / tg128`) | **157.39** | **23.29** | `arena_bench.log` |
| 9 | **DeepSeek-R1-Distill-Qwen-7B** | `7.62 B` `Q4_K_M` | `4.36 GiB` | `ngl=45` (`pp512 / tg128`) | **157.49** | **23.28** | `arena_bench.log` |
| — | **DeepSeek-R1-Distill-Qwen-7B** | `7.62 B` `Q4_K_M` | `4.36 GiB` | `ngl=999, t=14` (`pp512 / tg128`) | **157.60** | **23.11** | `pp_sweep.jsonl` |
| 10 | **Qwen2 7B (`bench_7b_gpu`)** | `7.62 B` `Q4_K_M` | `4.36 GiB` | `ngl=45` / `ngl=99` (`pp512 / tg128`) | **157.31 / 157.88** | **23.21 / 23.18** | `bench_7b_gpu.log` |
| 11 | **Qwen3-8B (server)** | `8B` `Q4_K_M` | `5734.8 MiB` VRAM | `ngl=45, ctx=8192` (`p=38, n=128`) | 34.29 *(micro-prompt)* | **19.92** | `server_bench.jsonl` |
| 12 | **Qwen2.5-Coder-7B-Instruct** | `7.62 B` `Q4_K_M` | — | `ngl=999, t=14` (`pp512 / tg128`) | **156.02** | **16.32** | `pp_sweep.jsonl` |
| 13 | **Qwen3.8-9B-Heretic-IQ4_XS** | `9.20 B` `IQ4_XS` | `4.99 GB` | `ngl=99, fa=1, t=6` (`pp64 / tg32`) | **132.02** | **14.64** | `fleet_benchmark_results.json` |
| 14 | **Qwen2.5-14B-della.Q3_K_M** | `14B` `Q3_K_M` | `6.83 GB` | `ngl=99, fa=1, t=6` (`pp64 / tg32`) | **57.60** | **10.33** | `fleet_benchmark_results.json` |
| 15 | **CoderO1-DeepSeekR1-Coder-14B** | `14B` `Q3_K_M` | `6.84 GB` | `ngl=99, fa=1, t=6` (`pp64 / tg32`) | **57.13** | **10.33** | `fleet_benchmark_results.json` |
| 16 | **UncensoredLM-R1-Distill-14B** | `14B` `IQ3_M` | `6.20 GB` | `ngl=99, fa=1, t=6` (`pp64 / tg32`) | **65.69** | **9.70** | `fleet_benchmark_results.json` |
| 17 | **DeepSeek-R1-Distill-Qwen-14B** | `14B` `IQ3_M` | `6.44 GB` | `ngl=99, fa=1, t=6` (`pp64 / tg32`) | **62.77** | **9.34** | `fleet_benchmark_results.json` |

> **GPU Vulkan Winner:** `MiniCPM5-1B-Q4_K_M` at **`1,111.39 tok/s` (`pp512`)** and **`51.57 tok/s` (`tg128`)**. Among 7–8B class models, `LFM2.5-8B-A1B` MoE hits **`31.31 tok/s` TG** (`342.46 t/s` `pp2048`), while dense 7B `Q4_K_M` peaks at **`23.29 tok/s`** and 14B `Q3_K_M`/`IQ3_M` still clears the 7.0 Golden Rule at **`9.34–10.33 tok/s`**.

---

### 1.2 CPU AVX2 (`-ngl 0`) `llama-bench` Rankings (Edge, Small & Mid Fleet)
Sources: `raw_data/speed/bench_cpu_small_compare.json`, `raw_data/speed/bench_cpu_r3.json`, `raw_data/speed/thread_sweep_gated_20261003.jsonl`, `raw_data/speed/pp_sweep.jsonl`, `raw_data/speed/BENCHMARK_FLEET_XEON_E5.json`, `F:\rotor-llm\scratch\mobilellm_bench2.log`.

| Rank (Best TG) | Model | Quant | Best TG (`tok/s`) | Optimal `t` (TG) | Best PP (`tok/s`) | PP Threads | Source |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | **MiniCPM4-0.5B** | `Q4_K_M` | **63.58** | `t=7` | **715.35** | `t=28` | `bench_cpu_small_compare.json` |
| 2 | **SmolLM2-360M-Instruct** | `Q4_K_M` | **50.41** | `t=7` | **323.26** | `t=28` | `bench_cpu_small_compare.json` |
| 3 | **Qwen2.5-0.5B-Instruct** | `Q4_K_M` | **48.06** | `t=7` | **254.69** | `t=28` | `bench_cpu_small_compare.json` |
| 4 | **Qwen3-0.6B** | `Q4_K_M` | **47.47** | `t=7` | **439.48** | `t=14` | `bench_cpu_small_compare.json` |
| 5 | **MiniCPM5-1B** | `Q4_K_M` | **43.12** | `t=7` | **374.34** | `t=20` | `thread_sweep_gated_20261003.jsonl` |
| 6 | **LFM2-1.2B** | `Q4_K_M` | **41.21** | `t=14` | **299.34** | `t=28` | `bench_cpu_small_compare.json` |
| 7 | **Llama-3.2-1B-Instruct** | `Q4_K_M` | **38.63** | `t=14` | **325.14** | `t=28` | `bench_cpu_small_compare.json` |
| 8 | **Qwen3.5-0.8B** | `Q4_K_M` | **31.53** | `t=7` | **241.66** | `t=14` | `bench_cpu_small_compare.json` |
| 9 | **DeepSeek-Coder-1.3B-Instruct** | `Q4_K_M` | **29.45** | `t=14` | **163.04** | `t=28` | `bench_cpu_small_compare.json` |
| 10 | **Gemma-3-1B-it** | `Q4_K_M` | **28.55** | `t=7` | **136.25** | `t=28` | `bench_cpu_small_compare.json` |
| 11 | **Qwen2.5-1.5B-Instruct** | `Q4_K_M` | **27.18** | `t=14` | **222.84** | `t=28` | `bench_cpu_small_compare.json` |
| 12 | **SmolLM2-1.7B-Instruct** | `Q4_K_M` | **26.22** | `t=14` | **167.48** | `t=28` | `bench_cpu_small_compare.json` |
| 13 | **Qwen3-1.7B** | `Q4_K_M` | **25.40** | `t=7` | **194.67** | `t=28` | `bench_cpu_small_compare.json` |
| 14 | **LFM2.5-8B-A1B (MoE)** | `Q4_K_M` | **24.11** | `t=10` | **129.36** | `t=20` | `thread_sweep_gated_20261003.jsonl` |
| 15 | **Falcon-H1-1.5B** | `Q4_K_M` | **21.18** | `t=14` | **198.02** | `t=28` | `bench_cpu_small_compare.json` |
| 16 | **MiniCPM5-2B** | `Q4_K_M` | **19.33** *(19.17 gated)* | `t=14` | **143.74** | `t=20` | `pp_sweep.jsonl` / `thread_sweep_gated` |
| 17 | **Qwen2.5-Coder-1.5B** (`n_gen=64`) | `Q4_K_M` (`1.04 GB`) | **19.04** | `t=14` | — | — | `BENCHMARK_FLEET_XEON_E5.json` |
| 18 | **Gemma-4-E2B-it** | `IQ4_XS` | **16.99** | `t=14` | **137.36** | `t=28` | `bench_cpu_small_compare.json` |
| 19 | **MobileLLM-R1.5-950M** (`llama4 ?B`) | `Q4_K_M` (`582.77 MiB`) | **14.96** | `t=7` | **112.38** | `t=7` | `mobilellm_bench2.log` |
| 20 | **Ministral-3-3B-Reasoning** (`n_gen=64`) | `Q4_K_M` (`2.00 GB`) | **14.68** | `t=14` | — | — | `BENCHMARK_FLEET_XEON_E5.json` |
| 21 | **Granite-4.0-micro** | `Q4_K_M` | **14.27** | `t=7` | **74.66** | `t=28` | `bench_cpu_small_compare.json` |
| 22 | **Phi-4-mini-instruct** (`n_gen=64`) | `Q4_K_M` (`2.32 GB`) | **13.28** | `t=14` | — | — | `BENCHMARK_FLEET_XEON_E5.json` |
| 23 | **Granite-4.2-3B** (`n_gen=64`) | `Q4_K_M` (`2.09 GB`) | **13.08** | `t=14` | — | — | `BENCHMARK_FLEET_XEON_E5.json` |
| 24 | **OpenReasoning-Nemotron-1.5B** (`r3`) | `Q4_K_M` | **12.40** | `t=7` | **101.55** | `t=14` | `bench_cpu_r3.json` |
| 25 | **Qwen2.5-Coder-7B-Instruct** | `Q4_K_M` | **9.11** *(9.02 gated)* | `t=14` | **51.25** | `t=20` | `pp_sweep.jsonl` / `thread_sweep_gated` |
| 26 | **DeepSeek-R1-Distill-Qwen-7B** | `Q4_K_M` | **8.51** *(8.50 @ t=14)* | `t=20` | **50.17** | `t=20` | `thread_sweep_gated_20261003.jsonl` |
| 27 | **Qwen3.8-9B-Heretic** | `IQ4_XS` (`4.98 GiB`) | **7.20** | `t=14 -fa 1` | **33.73** | `t=16 -fa 1` | `sweep_iq4_xs_focused.json` |
| 28 | **Qwen3.8-9B-Distill-Heretic** | `Q8_0` (`9.10 GiB`) | **4.36** | `t=14 -ub 512` | **18.68** | `t=14 -ctk/-ctv q8_0` | `sweep_q8_0.json` |
| — | **BitNet-b1.58-2B4T-i2_s** | `i2_s` | `ERR` | — | `ERR` | — | Failed to load in `lc_b10749` |
| — | **Qwen3.6-35B-A3B-UD** (`llama-bench`) | `Q4_K_M` (`21.11 GB`) | `TIMEOUT (180s)` | `t=14` | — | — | `BENCHMARK_FLEET_XEON_E5.json` |

> **CPU AVX2 Winner:** `MiniCPM4-0.5B-Q4_K_M` at **`63.58 tok/s` TG (`t=7`)** and **`715.35 tok/s` PP (`t=28`)**. In the sub-2B coding/agentic tier, `LFM2-1.2B` hits `41.21 t/s` (`t=14`), `DeepSeek-Coder-1.3B` hits `29.45 t/s` (`t=14`), and `LFM2.5-8B-A1B` (8B MoE) reaches `24.11 t/s` (`t=10`).

---

### 1.3 Parsed `F:\data\llama_bench_*.log` Telemetry (16 Server-Bench Logs)
All 16 logs ran under CPU AVX2 (`n_threads = 12`, `flash_attn = auto`, `CPU_Mapped` without `CPU_REPACK`; llama.cpp logs internal default buffer assignment as `offloaded N/N layers to GPU` when compiled CPU-only). Parsed stats are saved in `raw_data/speed/parsed_logs_telemetry.json`.

| Log File | Model & Quant | Arch | Size (BPW) | Config (`t` / `fa` / `layers`) | Weighted PP (`tok/s`) | PP Range (`n` reqs / tok) | Weighted TG (`tok/s`) | TG Range (`n` reqs / tok) | Status |
|---|---|---|---|---|---:|---|---:|---|---|
| `llama_bench_karpy_0_8b.log` | `NasledieLab-Qwen3.5-0.8B-Karpy-Q4_K_M` | `qwen35` | `494.32 MiB` (5.51) | `t=12, fa=auto, 25/25` | **167.18** | 134.71–210.12 (`59` / 7,696) | **25.00** | 16.96–30.30 (`59` / 9,140) | OK |
| `llama_bench_teichai_qwen3_30b_sonnet.log` | `Qwen3-30B-A3B-Thinking-2507-Claude-4.5-Sonnet-Distill-q4_k_m` | `qwen3moe` | `17.28 GiB` (4.86) | `t=12, fa=auto, 49/49` | **23.83** | 3.19–48.34 (`56` / 3,620) | **8.86** | 3.81–13.30 (`56` / 7,053) | OK |
| `llama_bench_unsloth_qwen3_30b_thinking.log` | `Qwen3-30B-A3B-Thinking-2507-Q4_K_M` | `qwen3moe` | `17.28 GiB` (4.86) | `t=12, fa=auto, 49/49` | **24.19** | 6.34–48.04 (`57` / 3,705) | **8.47** | 5.10–12.22 (`57` / 8,319) | OK |
| `llama_bench_jackrong_gemopus_4_26b_preview.log` | `Gemopus-4-26B-A4B-it-Preview-Q4_K_M` | `gemma4` | `15.63 GiB` (5.32) | `t=12, fa=auto, 31/31` | **23.84** | 7.92–37.24 (`58` / 3,778) | **7.98** | 5.18–12.19 (`58` / 7,584) | OK |
| `llama_bench_glyphsoftware_gemma_4_26b_opus.log` | `gemma-4-26b-a4b-opus-4.7-distilled.Q4_K_M` | `gemma4` | `15.63 GiB` (5.32) | `t=12, fa=auto, 31/31` | **26.69** | 8.78–40.89 (`58` / 4,133) | **7.86** | 6.22–12.23 (`58` / 8,006) | OK |
| `llama_bench_mudler_gemopus_4_26b_apex.log` | `gemopus-4-26B-A4B-APEX-Balanced` | `gemma4` | `18.15 GiB` (6.18) | `t=12, fa=auto, 31/31` | **30.04** | 8.00–35.19 (`58` / 4,015) | **7.76** | 5.52–13.06 (`58` / 7,649) | OK |
| `llama_bench_gpt_5_6_sol.log` | `gpt-5.6-sol-model` (`Q4_K_M`) | `qwen3` | `4.68 GiB` (4.90) | `t=12, fa=auto, 37/37` | **19.74** | 14.82–24.21 (`59` / 3,958) | **6.52** | 5.68–8.16 (`59` / 11,006) | OK |
| `llama_bench_qwen_qwen3_30b_iq3m.log` | `Qwen_Qwen3-30B-A3B-IQ3_M` | `qwen3moe` | `13.10 GiB` (3.69) | `t=12, fa=auto, 49/49` | **13.28** | 5.53–16.69 (`57` / 4,354) | **6.38** | 4.24–8.27 (`57` / 7,899) | OK |
| `llama_bench_unsloth_qwen3_5_35b.log` | `Qwen3.5-35B-A3B-Q4_K_M` | `qwen35moe` | `20.49 GiB` (5.08) | `t=12, fa=auto, 41/41` | **17.04** | 6.43–33.21 (`56` / 3,685) | **5.64** | 2.15–8.89 (`56` / 6,704) | OK |
| `llama_bench_ibm_granite_4_0_h_small.log` | `granite-4.0-h-small-Q4_K_M` | `granitehybrid` | `18.14 GiB` (4.84) | `t=12, fa=auto, 41/41` | **1.70** | 0.64–5.79 (`27` / 1,538) | **2.11** | 0.88–4.01 (`27` / 395) | OK (Slow) |
| `llama_bench_achilles_fable_coder_35b.log` | `fable-coder-35B-A3B-Q4_K_M` | `qwen35moe` | `20.21 GiB` (4.89) | `t=12` | — | — | — | — | `ERR`: missing `blk.40.ssm_conv1d.weight` |
| `llama_bench_jackrong_qwopus_3_6_35b_coder.log` | `Qwopus3.6-35B-A3B-Coder-MTP-Q4_K_M` | `qwen35moe` | `20.21 GiB` (4.89) | `t=12` | — | — | — | — | `ERR`: missing `blk.40.ssm_conv1d.weight` |
| `llama_bench_claude_qwen35_v2.log` | `Claude-Qwen3.5-V2-model.Q6_K` | `qwen35` | `3.31 GiB` (6.57) | `t=12` | — | — | — | — | `ERR`: missing `blk.32.ssm_conv1d.weight` |
| `llama_bench_ornith_1_5_9b.log` | `Ornith-1.5-9B.Q5_K_M` | `qwen35` | `6.18 GiB` (5.77) | `t=12` | — | — | — | — | `ERR`: missing `blk.32.ssm_conv1d.weight` |
| `llama_bench_qwen35_4b_opus_distill.log` | `Qwen3.5-4B-Claude-Opus-Distill.Q4_K_M` | `qwen35` | `2.58 GiB` (5.13) | `t=12` | — | — | — | — | `ERR`: missing `blk.32.ssm_conv1d.weight` |
| `llama_bench_gemma_4_assistant.log` | `gemma-4-26B-A4B-it-assistant.Q4_K_M` | `gemma4-assistant` | `295.34 MiB` (5.90) | `t=12` | — | — | — | — | `ERR`: unknown arch `gemma4-assistant` |

---

### 1.4 Parsed `F:\rotor-llm\scratch\bench_*.log` & `mobilellm_bench*.log` Telemetry (13 Logs)

| Log File | Model | Backend / Config | Size / Params | PP (`tok/s`) | TG (`tok/s`) | Notes |
|---|---|---|---|---:|---:|---|
| `bench_7b_gpu.log` | `qwen2 7B Q4_K_M` | Vulkan `ngl=45` / `ngl=99` | `4.36 GiB` / `7.62 B` | **157.31 / 157.88** (`pp512`) | **23.21 / 23.18** (`tg128`) | Stable across `ngl 45` and `99` |
| `bench_ring_mini_2_0.log` | `Ring-mini-2.0-Q4_K_M` | CPU `t=10` | `9.23 GB` | **30.61** (32 tok) | **21.26** (`20.82` client) | Warm High-Caliber Matrix |
| `bench_gpt_oss_20b.log` | `gpt-oss-20b-Q4_K_M` | CPU `t=10` | `10.82 GB` | **18.05** (86 tok) | **13.38** (`13.10` client) | Baseline High-Caliber Matrix |
| `bench_qwen35b_mtp.log` | `Qwen3.6-35B-A3B-UD-Q4_K_M + MTP` | CPU `t=10, draft=2` | `21.11 + 1.51 GB` | **11.11** (30 tok) | **7.20** (`7.05` client) | Warm RAM; draft acc `96.88%`, mean len `2.94` |
| `bench_qwen35b_baseline.log` | `Qwen3.6-35B-A3B-UD-Q4_K_M` | CPU `t=10` | `21.11 GB` | **1.29** (30 tok) | **1.66** (`1.62` client) | Baseline before MTP warm-up |
| `bench_ud_baseline.log` | `Qwen3.6-35B-A3B-UD-Q4_K_M` | CPU `t=10` | `21.11 GB` | **4.97** (30 tok) | **4.91** (`4.81` client) | Cold Official-vs-UD duel winner |
| `bench_official_baseline.log` | `Qwen3.6-35B-A3B-Q4_K_M` | CPU `t=10` | `19.02 GB` | **3.53** (30 tok) | **4.36** (`4.27` client) | Cold Official-vs-UD duel |
| `bench_official_mtp.log` | `Qwen3.6-35B-A3B-Q4_K_M + MTP` | CPU `t=10, draft=2` | `19.02 + 1.51 GB` | **0.98** (30 tok) | **3.03** (`2.97` client) | Cold-start penalty; draft acc `96.88%`, mean len `2.94` |
| `bench_ud_mtp.log` | `Qwen3.6-35B-A3B-UD-Q4_K_M + MTP` | CPU `t=10, draft=2` | `21.11 + 1.51 GB` | **0.54** (30 tok) | **2.24** (`2.19` client) | Cold-start TTFT `55.2s`; draft acc `96.88%`, mean len `2.94` |
| `bench_agents_a1.log` | `agents-a1-IQ4_XS` | CPU `t=10` | `17.44 GB` | **2.41** (30 tok) | **1.59** (`1.56` client) | Blacklisted & deleted |
| `mobilellm_bench2.log` | `llama4 ?B Q4_K_M` (`MobileLLM-R1.5`) | CPU `t=7` | `582.77 MiB` / `949.69 M` | **112.38** (`pp512`) | **14.96** (`tg128`) | Clean `llama-bench` |
| `mobilellm_bench.log` | `MobileLLM` (`BitNet/build/bin`) | CPU | — | — | — | `ERR`: missing `libomp.dll` |
| `bench_part2.log` | `Qwen3.8-9B-Heretic Q8_0` / `RLM-Qwen3-8B` | CPU `t=14, ctx=4096` | `9.10 GiB` / `4.68 GB` | — | **4.21** / **8.13** | Steady medians (cold `3.73` / `6.95`) |

---

### 1.5 GPU vs CPU Speedup Matrix (`pp_sweep.jsonl`, `t=14`, `-r 2`)
This 6-model × 2-device sweep (`LLM_BENCHMARK_AND_PRUNING_REGISTRY.md` §6.24.3) overturned the earlier 37-token micro-prompt fallacy by proving that the RX 580 delivers **`3.67×–4.51×` speedup in prefill (`pp512`)** (compute-bound, parallelizable) compared to **`1.57×–4.40×` in generation (`tg128`)** (memory-bandwidth bound).

| Model | Device | `pp64` | `pp512` | `pp2048` | `tg128` | GPU/CPU `pp512` Speedup | GPU/CPU `tg128` Speedup |
|---|---|---:|---:|---:|---:|---:|---:|
| **MiniCPM5-1B** | CPU (`lc_b10749`) | 244.48 | 266.83 | 188.57 | 12.44 | — | — |
| **MiniCPM5-1B** | GPU (`Vulkan`) | 656.07 | **1,111.39** | 917.05 | **51.57** | **4.17×** | **4.15×** |
| **MiniCPM5-2B** | CPU (`lc_b10749`) | 91.28 | 95.02 | 82.38 | 19.33 | — | — |
| **MiniCPM5-2B** | GPU (`Vulkan`) | 220.94 | **428.06** | 374.07 | **30.31** | **4.51×** | **1.57×** |
| **Qwen2.5-1.5B** | CPU (`lc_b10749`) | 157.78 | 168.83 | 146.66 | 22.40 | — | — |
| **Qwen2.5-1.5B** | GPU (`Vulkan`) | 336.70 | **673.72** | 603.30 | **43.04** | **3.99×** | **1.92×** |
| **LFM2.5-8B-A1B** | CPU (`lc_b10749`) | 47.95 | 92.27 | 94.66 | 11.13 | — | — |
| **LFM2.5-8B-A1B** | GPU (`Vulkan`) | 99.69 | **340.56** | **342.46** | **31.31** | **3.69×** | **2.81×** |
| **Qwen2.5-Coder-7B** | CPU (`lc_b10749`) | 44.11 | 42.57 | 40.87 | 9.11 | — | — |
| **Qwen2.5-Coder-7B** | GPU (`Vulkan`) | 116.88 | **156.02** | 145.99 | **16.32** | **3.67×** | **1.79×** |
| **R1-Distill-Qwen-7B** | CPU (`lc_b10749`) | 44.71 | 36.52 | 38.23 | 5.26 | — | — |
| **R1-Distill-Qwen-7B** | GPU (`Vulkan`) | 125.02 | **157.60** | 149.39 | **23.11** | **4.31×** | **4.40×** |

---

## 2. `gpt-oss-20b` Optimization Journey (Baseline → Threads → `CPU_REPACK` → PLD Tuned → `31.29 tok/s`)

Sources: `F:\rotor-llm\scratch\bench_gpt_oss_20b.log`, `raw_data/speed/proof_gpt20b_antidoom_live.json`, `proof_gpt20b_optimization_battle.json`, `proof_gpt20b_threads_benchmark.json`, `proof_gpt20b_aceleracao_total.json`, `proof_gpt20b_pld_tuned.json`, `proof_gpt20b_repack_paid.json`, `F:\data\repack_live.log`, `F:\data\server_pld_tuned.log`.

| Stage | Variant & Key Flags | `PP` (`tok/s`) | `TG` (`tok/s`) | Notes & Empirical Audit |
|---|---|---:|---:|---|
| **1. Baseline (`Q4_K_M`)** | `gpt-oss-20b-Q4_K_M.gguf` (`10.82 GB`), `t=10`, default | `18.05` | **`13.10`** *(13.38 engine)* | `50.8s` load, `TTFT 4,766 ms`, `RAM 10,076.8 MB` (`bench_gpt_oss_20b.log`) |
| **2. Antidoom Live (`IQ4_XS`)** | `gpt-oss-20b-antidoom.i1-IQ4_XS` (`12.1 GB` / `11.25 GiB`), baseline run | `26.36` | `9.48` | `120` tok in `17.73s` (`proof_gpt20b_antidoom_live.json`) |
| **3. Hyper-Optimized 8T (`Battle`)** | `t=8`, affinity `0x5555`, `Poll 100`, `Prio 2` | `19.76` | `9.64` | `140` tok in `19.76s` (`proof_gpt20b_optimization_battle.json`) |
| **4a. Thread Affinity Sweep: 8 Cores** | `t=8`, physical affinity `0x5555` | `24.02` | `10.15` | `140` tok in `19.45s` (`proof_gpt20b_threads_benchmark.json`) |
| **4b. Thread Affinity Sweep: 10 Cores** | `t=10`, physical affinity `0x15555` | `26.89` | **`10.47`** | **Best TG in thread sweep** (`140` tok in `18.43s`) |
| **4c. Thread Affinity Sweep: 12 Cores** | `t=12`, physical affinity `0x555555` | **`27.63`** | `9.71` | **Best PP in thread sweep**, TG dips due to memory contention (`19.39s`) |
| **5. Full Stack + PLD (`Aceleracao Total`)** | `spec=ngram-simple`, `draft=8`, `p-min=0.70`, `-fa on`, `t=8 (0x5555)`, `ctk/ctv q4_0`, `cache-reuse 256` | `27.00` | **`10.65`** | `160` tok in `17.70s`; `0` drafts accepted on open prose (`debug_server.log`) |
| **6. PLD Tuned (Code Gen)** | `ngram_n=3, ngram_m=16, draft=8, p-min=0.50`, `t=8`, `-fa on` | `22.36` | `8.73` | `200` tok Python Min-Heap; draft acc = **`10.96%` (`8/73`)** (`server_pld_tuned.log`) |
| **7. `CPU_REPACK` Enabled (`repack_paid`)** | `t=10 (0x15555)`, AVX2 `CPU_REPACK = 10,422.42 MiB`, `CPU_Mapped = 11,523.70 MiB`, `-fa on` | **`31.29`** | **`10.94`** *(JSON logged `31.29`)* | **Empirical Audit:** `repack_live.log` proves **PP = `31.29 tok/s`** (`117 tok / 3739.52 ms`, `+73.4%` vs baseline) and **TG = `10.94 tok/s`** (`150 tok / 13706.48 ms`, peak `antidoom` TG); `proof_gpt20b_repack_paid.json` mistakenly copied PP (`31.29`) into `generation_speed`. |

---

## 3. `MTP` Context Curve & Official vs Unsloth Dynamic (`UD`) Speedups (`Qwen3.5/3.6-35B-A3B` & `Qwen3.8-27B`)

### 3.1 Official vs Unsloth Dynamic (`UD`) Duel (`Qwen3.6-35B-A3B`, Cold Start & Warm RAM)
Sources: `raw_data/speed/BENCHMARK_OFFICIAL_VS_UD_RESULTS.json`, `F:\rotor-llm\scratch\_recovered_benchmark_matrix.txt`, `bench_*.log`.

| Configuration | State | Load (`s`) | TTFT (`ms`) | PP (`tok/s`) | TG (`tok/s`) | RAM Peak (`MB`) | Draft Acceptance |
|---|---|---:|---:|---:|---:|---:|---|
| `Qwen3.6-35B Official` (`19.02 GB`, Baseline) | Cold | 75.14 | 8,495.1 | 3.53 | 4.27 | 10,775.0 | — |
| `Qwen3.6-35B Official + MTP` (`draft_n=2`) | Cold | 61.04 | 30,735.2 | 0.98 | 2.97 | 11,892.8 | `96.88%` (`mean len 2.94`) |
| **`Qwen3.6-35B UD`** (`21.11 GB`, Baseline) | Cold | 95.11 | **6,031.6** | **4.97** | **4.81** | 11,422.5 | — |
| `Qwen3.6-35B UD + MTP` (`draft_n=2`) | Cold | 77.09 | 55,202.7 | 0.54 | 2.19 | 12,631.3 | `96.88%` (`mean len 2.94`) |
| `Qwen3.6-35B UD` (Baseline, High-Caliber Matrix) | Cold/Unwarmed | 70.80 | 23,236 | 1.29 | 1.62 | 11,502.8 | — |
| **`Qwen3.6-35B UD + MTP`** (`draft_n=2`, `t=10`) | **Warm RAM** | **34.50** | **2,699** | **11.11** | **7.05** *(7.20 eng.)* | 12,631.6 | **`96.88%` (`31/32`, len `2.94`)** |

- **Cold-Start Winner:** `UD-Q4_K_M` Baseline (**`4.81 tok/s` TG, `+12.6%` faster TG and `-29.0%` lower TTFT** than Official `Q4_K_M` at `4.27 tok/s`), resulting in the permanent deletion of the `19.02 GB` Official GGUF.
- **Warm-RAM MTP Acceleration:** With model pages warm in RAM (`keep-alive`), `UD + MTP` jumps from `1.62 t/s` to **`7.05 tok/s` (`4.35×` speedup)** and drops TTFT by `-88.4%` (`23.24s -> 2.70s`), crossing the `7.0 tok/s` Golden Rule.

### 3.2 `MTP` Draft Length & Thread Sweep: `Qwen3.6-35B-A3B-UD` (MoE) vs `Qwen3.8-27B` (Dense)
Sources: `raw_data/speed/relatorio_benchmark_mtp.json`, `raw_data/speed/iq3xxs_bench.json`, `F:\data\models\benchmark_live.log` (`--no-repack`, `ctx 2048`, 3 passes after warmup).

| Model | Arch / Size | Mode (`spec_type` / `draft_n` / `t`) | Avg TG (`tok/s`) | Max TG (`tok/s`) | Speedup vs Baseline | Verdict |
|---|---|---|---:|---:|---:|---|
| `Qwen3.6-35B-A3B-UD-Q4_K_M` | MoE (3B active) / `21.11 GB` | `OFF` (`n=0, t=14`) | 5.24 | 7.30 | 1.00× | Fails avg 7.0 floor |
| `Qwen3.6-35B-A3B-UD-Q4_K_M` | MoE | `draft-mtp` (`n=2, t=14`) | 5.62 | 9.83 | 1.07× | Pass peak, warm-up variance |
| `Qwen3.6-35B-A3B-UD-Q4_K_M` | MoE | `draft-mtp` (`n=3, t=14`) | 5.68 | 9.67 | 1.08× | Pass peak |
| `Qwen3.6-35B-A3B-UD-Q4_K_M` | MoE | `draft-mtp` (`n=4, t=14`) | 5.09 | 9.64 | 0.97× | Draft overhead at `t=14` |
| `Qwen3.6-35B-A3B-UD-Q4_K_M` | MoE | `draft-mtp` (`n=5, t=14`) | 4.97 | 8.87 | 0.95× | Over-drafting |
| `Qwen3.6-35B-A3B-UD-Q4_K_M` | MoE | `draft-mtp` (`n=6, t=14`) | 6.00 | 8.24 | 1.15× | Best `t=14` avg |
| **`Qwen3.6-35B-A3B-UD-Q4_K_M`** | **MoE** | **`draft-mtp` (`n=4, t=8`)** | **7.53** | **10.23** | **1.44×** *(peak 1.95×)* | **CHAMPION — Clears 7.0 Golden Rule** |
| **`Qwen3.8-27B-UD-IQ4_XS`** | Dense 27B | `OFF` (`n=0, t=14`) | **2.15** | **2.17** | 1.00× | Fastest 27B Dense config |
| `Qwen3.8-27B-UD-IQ4_XS` | Dense 27B | `draft-mtp` (`n=3..6, t=14`) | `2.01 -> 1.42` | `2.04 -> 1.52` | `0.93× -> 0.66×` | **MTP Regresses** |
| `Qwen3.8-27B-UD-IQ4_XS` | Dense 27B | `draft-mtp` (`n=4, t=12 / t=8`) | `1.70 / 1.31` | `1.74 / 1.41` | `0.79× / 0.61×` | **MTP Regresses** |
| **`Qwen3.8-27B-UD-Q3_K_XL`** | Dense 27B / `12.24 GB` | `OFF` (`n=0, t=14`) | **1.89** | **1.92** | 1.00× | Baseline |
| `Qwen3.8-27B-UD-Q3_K_XL` | Dense 27B | `draft-mtp` (`n=4 / n=5, t=14`) | `1.46 / 1.29` | `1.49 / 1.34` | `0.77× / 0.68×` | **MTP Regresses** |
| **`Qwen3.8-27B-UD-IQ3_XXS`** | Dense 27B | `OFF` (`n=0, t=14`) | **1.68** | **1.70** | 1.00× | Baseline (`iq3xxs_bench.json`) |
| `Qwen3.8-27B-UD-IQ3_XXS` | Dense 27B | `draft-mtp` (`n=3, t=12` / `n=4, t=8`) | `1.48 / 0.93` | `1.52 / 1.15` | `0.88× / 0.55×` | **MTP Regresses** |

> **Why MTP wins on `35B-A3B` MoE but loses on `27B` Dense:** On `35B-A3B` (only 3B active parameters per forward pass), verifying `n=1..4` speculative tokens in a single batched target pass is cheap relative to memory reads. On dense `27B` (all 27B parameters active per token on CPU), batched verification is compute-bound and costs more than sequential decoding.

### 3.3 `MTP` Inference Profile & Context Curve (`Qwen3.6-35B-A3B-UD-Q4_K_M`, `t=12`, Mask `0x5555550`, `KV=q8_0`)
Sources: `raw_data/speed/INFERENCE_PROFILE_BENCHMARK.json` & `raw_data/speed/MTP_CONTEXT_CURVE_BENCHMARK.json`.

#### Inference Profile (`INFERENCE_PROFILE_BENCHMARK.json`)
| Config | `spec_n` | Load (`s`) | `ctx_short` TG (`t/s`) | `ctx_short` PP (`t/s`) | `ctx_medium` TG (`t/s`) | `ctx_medium` PP (`t/s`) |
|---|---:|---:|---:|---:|---:|---:|
| `MTP_OFF` | 0 | 92.64 | 7.96 | 15.13 | 8.12 | 24.25 |
| `MTP_1` | 1 | 8.05 | 9.71 (`+22.0%`) | 13.52 | **10.30 (`+26.8%`)** | 20.30 |
| **`MTP_2`** | 2 | 8.58 | **10.78 (`+35.4%`)** | 15.43 | 9.99 (`+23.0%`) | 22.97 |
| `MTP_3` | 3 | 8.05 | 10.24 (`+28.6%`) | 15.20 | 10.20 (`+25.6%`) | 23.30 |

#### Context Scaling Curve (`MTP_CONTEXT_CURVE_BENCHMARK.json`)
| Config | `draft_n` | Load (`s`) | `ctx_short` (~150 tok) TG / Acc / RSS | `ctx_2k` (~2,483 tok) TG / Acc / RSS | `ctx_5k` (~4,289 tok) TG / Acc / RSS | Speedup (`short / 2k / 5k`) |
|---|---:|---:|---|---|---|---|
| `MTP_OFF` | 0 | 20.20 | `7.33 t/s` / — / `14.38 GB` | `7.50 t/s` / — / `19.16 GB` | `6.86 t/s` *(below 7.0)* / — / `19.60 GB` | `1.00× / 1.00× / 1.00×` |
| **`MTP_1`** | 1 | **8.09** | **`9.96 t/s`** / **`90.9%`** / `14.76 GB` | **`9.49 t/s`** / **`88.1%`** / `19.76 GB` | `8.21 t/s` / **`84.1%`** / `20.24 GB` | **`+35.9% / +26.5% / +19.7%`** |
| **`MTP_2`** | 2 | 12.61 | `9.56 t/s` *(rep2: 12.21)* / `80.4%` / `14.93 GB` | `9.19 t/s` / `69.5%` / `19.86 GB` | **`8.42 t/s`** / `68.9%` / `20.33 GB` | **`+30.4% / +22.5% / +22.7%`** |
| `MTP_3` | 3 | 14.12 | `9.59 t/s` / `62.1%` / `15.26 GB` | `9.02 t/s` / `59.85%` / `20.00 GB` | `7.84 t/s` / `59.7%` / `20.45 GB` | `+30.8% / +20.3% / +14.3%` |

> **Operational Takeaway:** `MTP_1` maximizes draft acceptance (`90.9% -> 84.1%`) and wins at short-to-2K contexts (`9.96` and `9.49 tok/s`), while `MTP_2` edges ahead at 5K context (`8.42 tok/s`), keeping the 35B MoE safely above the `7.0 tok/s` Golden Rule across the entire 0–5K curve.

---

## 4. Thread Scaling, Flash Attention (`-fa`), and `PP` Batching Sweeps

### 4.1 Thread Scaling Asymmetric Law (14C / 28T Xeon E5-2697 v3)
Sources: `raw_data/speed/thread_sweep_gated_20261003.jsonl`, `bench_cpu_small_compare.json`, `bench_cpu_r3.json`, `LLM_BENCHMARK_AND_PRUNING_REGISTRY.md` §6.25.2.

| Model Class | Model | `t=7` (`PP` / `TG`) | `t=10` (`PP` / `TG`) | `t=14` (`PP` / `TG`) | `t=20` or `t=28` (`PP` / `TG`) | Optimal `(PP, TG)` Pair |
|---|---|---:|---:|---:|---:|---|
| **0.5B Dense** | `MiniCPM4-0.5B` | `488.57` / **`63.58`** | — | `686.01` / `57.19` | `t=28`: **`715.35`** / `19.32` | **`(t=28, t=7)`** |
| **0.36B Dense** | `SmolLM2-360M` | `157.08` / **`50.41`** | — | `263.10` / `41.92` | `t=28`: **`323.26`** / `17.80` | **`(t=28, t=7)`** |
| **1B Dense** | `MiniCPM5-1B` | `261.44` / **`43.12`** | `296.70` / `40.82` | `315.15` / `41.30` | `t=20`: **`374.34`** / `29.59` | **`(t=20, t=7)`** |
| **1.2B Dense** | `LFM2-1.2B` | `178.87` / `38.03` | — | `245.61` / **`41.21`** | `t=28`: **`299.34`** / `18.59` | **`(t=28, t=14)`** |
| **2B Dense** | `MiniCPM5-2B` | `93.80` / `18.74` | `108.22` / `19.02` | `122.71` / **`19.17`** | `t=20`: **`143.74`** / `12.90` | **`(t=20, t=14)`** |
| **8B MoE** | `LFM2.5-8B-A1B` | `86.29` / `22.44` | `116.52` / **`24.11`** | `112.04` / `21.94` | `t=20`: **`129.36`** / `20.49` | **`(t=20, t=10)`** |
| **7B Dense** | `Qwen2.5-Coder-7B` | `31.78` / `7.94` | `43.39` / `8.93` | `48.58` / **`9.02`** | `t=20`: **`51.25`** / `8.81` | **`(t=20, t=14)`** |
| **7B Reasoner** | `R1-Distill-Qwen-7B` | `32.82` / `7.25` | `39.25` / `8.43` | `46.77` / `8.50` | `t=20`: **`50.17`** / **`8.51`** | **`(t=20, t=20)`** *(flat `14–20`)* |

- **Mechanism Proven:** Prefill (`pp512`) gains **`+43%` to `+61%`** from `t=7` to `t=20` across all 5 classes because parallel matmuls hide memory latency. Token generation (`tg128`) **collapses at `t=20/28` on small models** (`-31%` to `-70%`) due to HyperThreading scheduler contention, and **flattens on 7B** (`9.02 -> 8.81 t/s`) where DRAM bandwidth saturates first.
- **Host-Gate Audit (`§6.25.2.1.1`):** Replacing the flawed `bench_share` gate with `oversub <= 0.85` reclassified `13/20` cells as `QUIET` (`3` `MINOR_LOAD`, `4` `CONTAMINATED`), reproducing the exact same law on `QUIET`-only cells (`8B MoE` `+49.9%` PP, `7B dense` `+61.3%` PP, `7B reasoning` `+52.9%` PP).

### 4.2 Flash Attention (`-fa 0` vs `-fa 1`) Sweep (`fa_sweep_r1`, `fa_sweep_r5`, `fa_sweep_8192_gpu`, `parity_results`)
Sources: `raw_data/speed/fa_sweep_r1_20261005.jsonl`, `fa_sweep_r5_20261005.jsonl`, `fa_sweep_8192_gpu_20261005.jsonl`, `parity_results.jsonl`.

| Model | Device | `p=512` (`fa=0 -> fa=1`, `r5`) | Ratio (`r5`) | `p=2048` (`fa=0 -> fa=1`, `r5`) | Ratio (`r5`) | `p=8192` (`fa=0 -> fa=1`, `r3`) | Ratio (`8192`) |
|---|---|---|---:|---|---:|---|---:|
| `MiniCPM5-1B` | CPU | `322.75 -> 306.68` | `0.950×` | `257.41 -> 261.57` | `1.016×` | — | — |
| `MiniCPM5-1B` | GPU | `323.69 -> 379.52` | `1.172×` | `270.71 -> 284.06` | `1.049×` | **`173.04 -> 155.84`** | **`0.901×` (-10%)** |
| `MiniCPM5-2B` | CPU | `117.28 -> 133.12` | `1.135×` | `108.74 -> 109.60` | `1.008×` | — | — |
| `MiniCPM5-2B` | GPU | `122.03 -> 133.77` | `1.096×` | `106.71 -> 109.77` | `1.029×` | — | — |
| `Qwen2.5-1.5B` | CPU | `190.24 -> 199.16` | `1.047×` | `181.45 -> 171.32` | `0.944×` | — | — |
| `Qwen2.5-1.5B` | GPU | `187.48 -> 207.43` | `1.106×` | `178.67 -> 176.77` | `0.989×` | — | — |

- **Findings:**
  1. Single-run (`-r 1`) sweeps produced `0.808×–1.216×` false signals; `-r 5` proved `-fa` is **effectively neutral (`0.944×–1.049×`) at `p=2048`**.
  2. At **`p=8192` on RX 580 Vulkan**, `-fa 1` is **10% slower** (`155.84` vs `173.04 tok/s`), proving the Polaris Vulkan FA kernel does not recover the `O(n²)` attention drop (`270.7 -> 173.0 t/s` from `2048` to `8192`).
  3. **Accuracy Parity (`parity_results.jsonl`):** `MiniCPM5-1B` scored `4/9` (`44.4%`) on CPU `fa=auto`, GPU `fa=auto`, GPU `fa=off`, and both `thinkOFF` runs (`3/9` on `fa=on`), while `Qwen2.5-Coder-7B` scored `9/9` (`100%`) identically on CPU and GPU. `-fa` does not control output accuracy.

### 4.3 `PP` Batching / Prompt-Length Curves (`pp_sweep.jsonl`)
Across 5 of 6 models (`pp64`, `pp512`, `pp2048`), prefill throughput peaks at **`p=512`** and dips at `p=2048` as KV-cache traffic shifts the kernel from compute-bound toward memory-bandwidth-bound (e.g., `MiniCPM5-1B` GPU: `656.07 -> 1,111.39 -> 917.05 tok/s`; `Qwen2.5-1.5B` GPU: `336.70 -> 673.72 -> 603.30 tok/s`). Only `LFM2.5-8B-A1B` stays flat (`340.56 -> 342.46 tok/s`). Router `MODEL_TABLE` therefore uses `pp_by_prompt` curves rather than scalar extrapolation.

---

## 5. Fleet Memory, Quantization (`IQ3_M` vs `Q4_K_M` vs `IQ4_XS` vs `Q8_0`) & Bandwidth Analysis

### 5.1 `Qwen3-30B-A3B` MoE: `IQ3_M` vs `Q4_K_M` (`CPU_REPACK` RAM Cliff)
Sources: `raw_data/speed/proof_qwen3_moe_iq3_vs_q4km.json`, `F:\data\q4km_test.log`.

| Variant | File Size | `CPU_REPACK` Needed? | Extra Buffer Required | Total Commit vs 31.84 GiB Host | Load Time | Working Set | PP (`tok/s`) | TG (`tok/s`) | Pass Rate / Status |
|---|---|---|---|---|---|---:|---:|---:|---|
| **`Qwen3-30B-A3B-IQ3_M`** | `13.11 GB` (`14,076,541,600 B`) | **No** (`false`) | `0 B` | Fits natively | `90.8 s` | `29.28 GB` | **14.66** | **7.05** | **`3/3 (100%)` — CHAMPION** |
| `Qwen3-30B-A3B-Q4_K_M` | `17.35 GB` (`18,632,184,480 B`) | **Yes** (`true`) | **`13.83 GB` (`13,830,193,152 B`)** | **`31.18 GB`** -> Allocation Fails | `FAIL` | — | — | — | `BLOCKED_BY_RAM_REPACK_LIMIT` |

> **Architectural Verdict:** On a 32 GB RAM Xeon E5 host without a 30 GB+ pagefile, `IQ3_M` is mathematically and architecturally superior to `Q4_K_M` for 30B-A3B MoE: it avoids the `13.83 GB` `CPU_REPACK` buffer allocation failure and clears the `7.0 tok/s` Golden Rule (`7.05 tok/s`).

### 5.2 `Qwen3.8-9B-Heretic` Bandwidth Scaling: `Q8_0` vs `IQ4_XS` (`sweep_q8_0.json` & `sweep_iq4_xs_focused.json`)

| Quantization | Size (`BPW`) | Config | `pp512` (`tok/s`) | `tg128` (`tok/s`) | Golden Rule (`>= 7.0`) |
|---|---:|---|---:|---:|---|
| `Q8_0` | `9.10 GiB` | `-t 14` (baseline) | `12.16 ± 0.09` | `4.00 ± 0.01` | FAIL |
| `Q8_0` | `9.10 GiB` | `-t 20` / `-t 28` | `15.29` / `17.27` | `2.99` / `2.31` | FAIL (HT hurts TG) |
| `Q8_0` | `9.10 GiB` | `-t 14 -fa 1` | `12.25 ± 0.12` | `4.17 ± 0.06` | FAIL |
| `Q8_0` | `9.10 GiB` | `-t 14 -ctk q8_0 -ctv q8_0` | **`18.68 ± 0.39`** | `3.59 ± 0.64` | FAIL |
| `Q8_0` | `9.10 GiB` | `-t 14 -ub 512` | `12.43 ± 0.22` | **`4.36 ± 0.16`** | FAIL (`bench_part2`: `4.21`) |
| **`IQ4_XS`** | `4.98 GiB` (`4.25 bpw`) | `-t 14` (plain) | `31.88 ± 0.48` | `7.09 ± 0.06` | **PASS** |
| **`IQ4_XS`** | `4.98 GiB` (`4.25 bpw`) | **`-t 14 -fa 1`** | `31.69 ± 0.21` | **`7.20 ± 0.03`** | **PASS (Best CPU TG)** |
| `IQ4_XS` | `4.98 GiB` (`4.25 bpw`) | `-t 14 -ub 512` | `28.95 ± 3.79` | `5.73 ± 1.05` | FAIL (anomaly fixed by `-fa 1`: `7.05`) |
| `IQ4_XS` | `4.98 GiB` (`4.25 bpw`) | `-t 14 -fa 1 -ctk/-ctv q8_0` | `31.08 ± 0.18` | `7.11 ± 0.06` | **PASS** |
| `IQ4_XS` | `4.98 GiB` (`4.25 bpw`) | `-t 12 -fa 1` / **`-t 16 -fa 1`** | `32.33` / **`33.73`** | `7.08` / `7.12` | **PASS (Best CPU PP)** |
| **`IQ4_XS` (GPU)** | `4.99 GB` | Vulkan `-ngl 99 -fa 1 -t 6` (`pp64/tg32`) | **132.02** | **14.64** | **PASS (`2.03×` CPU TG)** |

> **Bandwidth Physics:** Dense CPU token generation scales linearly with inverse model byte size (`9.10 GiB -> 4.98 GiB` = `1.83×` smaller payload → `4.00 -> 7.09 tok/s` = **`1.77×` faster TG** and **`2.62×` faster PP**), turning an unusable `4.0 tok/s` checkpoint into a compliant `7.20 tok/s` CPU (and `14.64 tok/s` GPU) model.

### 5.3 Pruned / Unviable Checkpoints (Speed & Memory Blacklist)
1. **`Agents-A1-IQ4_XS`** (`17.44 GB` dense 17B): `1.56 tok/s` TG, `2.41 tok/s` PP, `12.43s` TTFT → **Deleted**.
2. **`Qwen3.6-35B-A3B Official Q4_K_M`** (`19.02 GB`): `4.27 tok/s` cold vs `4.81 tok/s` on `UD-Q4_K_M` → **Deleted**.
3. **`IBM Granite-4.0-h-small-Q4_K_M`** (`18.14 GiB`, `granitehybrid`): `2.11 tok/s` TG, `1.70 tok/s` PP (`llama_bench_ibm_granite_4_0_h_small.log`).
4. **`Qwen3.8-27B` Dense** (`IQ4_XS` `2.15 t/s`, `Q3_K_XL` `1.89 t/s`, `IQ3_XXS` `1.68 t/s`): CPU bandwidth bottleneck + Vulkan `256 MB` BAR `ErrorOutOfHostMemory`.

---

## 6. Repository Artifacts Index (Speed Partition)
- **`raw_data/speed/`** (31 files): Raw JSON/JSONL/TXT benchmark artifacts, `arena_bench.log`, `relatorio_benchmark_mtp.json`, `iq3xxs_bench.json`, `sweep_iq4_xs_focused.json`, `sweep_q8_0.json`, and `parsed_logs_telemetry.json` (parsed summary of all 16 `F:\data\llama_bench_*.log` + 13 `F:\rotor-llm\scratch\bench_*.log` / `mobilellm_bench*.log` + 4 tuning logs).
- **`scripts/speed/`** (17 files): All standalone speed, `MTP`, `PP`, `FA`, thread-sweep, and `gpt-oss-20b` scripts & `.bat`/`.html` launchers.
- **`registry_docs/`** (4 files): Canonical rotor-llm registry and hardware audit documents (`LLM_BENCHMARK_AND_PRUNING_REGISTRY.md`, `INVENTARIO_E_BENCHMARKS_COMPLETO_DE_TODOS_OS_MODELOS.md`, `RELATORIO_TECNICO_GPU_CPU_E_BENCHMARKS.md`, `ROTOR_FLEET_STATE.md`).
