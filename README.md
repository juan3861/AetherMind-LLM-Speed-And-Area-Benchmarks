# AetherMind — Benchmarks de Velocidade Pura, Tuning de Hardware & Destaques por Área

**Repositório dedicado exclusivamente a telemetria de velocidade de inferência (`tok/s`, `PP`, `TG`, `TTFT`), estudos de otimização do motor `llama.cpp` (`MTP`, `PLD`, `CPU_REPACK`, `-fa`, Thread Affinity, Vulkan vs. AVX2) e destaques isolados por área**, extraído integralmente de `F:\rotor-llm\` e `F:\data\`.

> **Separação Clara dos Repositórios:**
> - **Este Repositório ([`AetherMind-LLM-Speed-And-Area-Benchmarks`](https://github.com/juan3861/AetherMind-LLM-Speed-And-Area-Benchmarks)):** Focado em **velocidade pura (`llama-bench`, `llama-server`)**, **tuning de hardware/engine** e **modelos testados isoladamente por área ou triagem de velocidade**.
> - **Repositório de Torneios Cognitivos ([`AetherMind-LLM-Benchmark-Lab`](https://github.com/juan3861/AetherMind-LLM-Benchmark-Lab)):** Focado nos **torneios multi-modelo completos (100M a 35B+)** avaliados nas **13 Áreas Cognitivas (39 provas)** e **10 Desafios Opus Hard** com `Lambda-RLM`.

---

## 1. Hardware de Referência (Testbed Bare-Metal)

| Componente | Especificação Verificada | Impacto na Velocidade |
| :--- | :--- | :--- |
| **CPU Host** | **Intel Xeon E5-2697 v3** (Haswell-EP, **14 Núcleos Físicos / 28 Threads**, 2.60 GHz, `AVX2/FMA/F16C/BMI2`) | Prefill (`PP`) escala até `20–28` threads; Geração (`TG`) satura banda DDR4 e degrada com HyperThreading acima de `7–14` threads. |
| **Memória RAM** | **31.84 GiB (~32 GB) DDR4 Quad-Channel** | Teto físico para `CPU_REPACK` + `mmap` (`Qwen3-30B-Q4_K_M` estoura `31.18 GB`; `IQ3_M` roda limpo em `29.28 GB`). |
| **GPU Discreta** | **AMD Radeon RX 580 Series** (Polaris 20, **8 GB GDDR5**, Vulkan `1.3.260`, Adrenalin `26.5.2`) | Até **4.5× mais rápida** em `PP` e **4.4× em `TG`** que a CPU quando cabe na VRAM; limitada no Windows pela janela **PCIe BAR de 256 MB** (sem ReBAR). |
| **Motores** | `llama.cpp` (`b10749` AVX2, `b10819` Vulkan, `llama-bench.exe`, `llama-server.exe`) | **Regra de Ouro:** loops agênticos locais exigem **`>= 7.0 tok/s`** de geração sustentada (`TG`). |

---

## 2. Tabela Mestra de Velocidade — GPU Vulkan (AMD RX 580 8GB)

Medições empíricas via `llama-bench` (`pp512` / `tg128`) e `llama-server` (`ctx=8192`) com offload Vulkan:

| Modelo | Quant | Tamanho | Config | Prompt (`PP`) | Geração (`TG`) | Fonte Bruta |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`MiniCPM5-1B`** | `Q4_K_M` | ~0.75 GB | `ngl=999, t=14` | **1,111.39 tok/s** | **51.57 tok/s** | [`pp_sweep.jsonl`](raw_data/speed_llama_bench/pp_sweep.jsonl) |
| **`Qwen2-VL-2B-Instruct`** | `Q4_K_M` | 934.7 MiB | `ngl=45` | **675.18 tok/s** | **43.67 tok/s** | [`arena_bench.log`](raw_data/speed_llama_bench/arena_bench.log) |
| **`LFM2.5-8B-A1B` (MoE)** | `Q4_K_M` | ~4.6 GB | `ngl=999 / ctx=8192` | **342.46 tok/s** | **30.10–31.31 tok/s** | [`pp_sweep.jsonl`](raw_data/speed_llama_bench/pp_sweep.jsonl) · [`server_bench.jsonl`](raw_data/speed_server_mtp_pld/server_bench.jsonl) |
| **`Phi-4-mini-instruct`** | `Q4_K_M` | 2.31 GiB | `ngl=45` | **290.91 tok/s** | **29.05 tok/s** | [`arena_bench.log`](raw_data/speed_llama_bench/arena_bench.log) |
| **`Qwen3-VL-4B-Instruct`** | `Q4_K_M` | 2.32 GiB | `ngl=45` | **245.33 tok/s** | **23.92 tok/s** | [`arena_bench.log`](raw_data/speed_llama_bench/arena_bench.log) |
| **`Qwen2.5-VL-7B-Instruct`** | `Q4_K_M` | 4.36 GiB | `ngl=45` | **157.39 tok/s** | **23.29 tok/s** | [`arena_bench.log`](raw_data/speed_llama_bench/arena_bench.log) |
| **`DeepSeek-R1-Distill-Qwen-7B`** | `Q4_K_M` | 4.36 GiB | `ngl=45` | **157.49 tok/s** | **23.28 tok/s** | [`arena_bench.log`](raw_data/speed_llama_bench/arena_bench.log) |
| **`Qwen2.5-7B-Instruct`** | `Q4_K_M` | 4.36 GiB | `ngl=45 / 99` | **157.88 tok/s** | **23.18–23.21 tok/s** | [`bench_7b_gpu.log`](raw_data/speed_llama_bench/bench_7b_gpu.log) |
| **`Qwen3-8B`** | `Q4_K_M` | ~4.9 GB | `ngl=45, ctx=8192` | 34.29 tok/s *(p=38)* | **19.92 tok/s** | [`server_bench.jsonl`](raw_data/speed_server_mtp_pld/server_bench.jsonl) |
| **`Qwen3.8-9B-Distill-Heretic`** | `IQ4_XS` | 4.99 GB | `ngl=99, -fa 1` | — | **14.17–14.64 tok/s** | [`sweep_iq4_xs_focused.json`](raw_data/speed_llama_bench/sweep_iq4_xs_focused.json) |

---

## 3. Tabela Mestra de Velocidade — CPU Pura AVX2 (Xeon E5-2697 v3)

### 3A. Modelos Leves & Edge (`0.36B – 4B`) — Varredura `7T / 14T / 28T`

| Modelo | Quant | Melhor `TG` (CPU) | Melhor `PP` (CPU) | Comportamento HT (`28T`) | Fonte Bruta |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`MiniCPM4-0.5B`** | `Q4_K_M` | **63.58 tok/s** (`7T`) | **715.35 tok/s** (`28T`) | Cai p/ `19.32 t/s` (`-70%`) | [`bench_cpu_small_compare.json`](raw_data/speed_llama_bench/bench_cpu_small_compare.json) |
| **`SmolLM2-360M-Instruct`** | `Q4_K_M` | **56.19 tok/s** (`7T`) | **323.26 tok/s** (`28T`) | Cai p/ `17.80–18.44 t/s` | [`bench_cpu_small_compare_round1.json`](raw_data/speed_llama_bench/bench_cpu_small_compare_round1.json) |
| **`Qwen2.5-0.5B-Instruct`** | `Q4_K_M` | **49.52 tok/s** (`7T`) | **297.66 tok/s** (`14T`) | Cai p/ `15.25–23.46 t/s` | [`bench_cpu_small_compare_round1.json`](raw_data/speed_llama_bench/bench_cpu_small_compare_round1.json) |
| **`Qwen3-0.6B`** | `Q4_K_M` | **47.47 tok/s** (`7T`) | **439.48 tok/s** (`14T`) | Cai p/ `10.38 t/s` (`-78%`) | [`bench_cpu_small_compare.json`](raw_data/speed_llama_bench/bench_cpu_small_compare.json) |
| **`LFM2-1.2B`** | `Q4_K_M` | **41.21 tok/s** (`14T`) | **299.34 tok/s** (`28T`) | Cai p/ `18.59 t/s` | [`bench_cpu_small_compare.json`](raw_data/speed_llama_bench/bench_cpu_small_compare.json) |
| **`Llama-3.2-1B-Instruct`** | `Q4_K_M` | **38.63 tok/s** (`14T`) | **325.14 tok/s** (`28T`) | Cai p/ `19.43 t/s` | [`bench_cpu_small_compare.json`](raw_data/speed_llama_bench/bench_cpu_small_compare.json) |
| **`deepseek-coder-1.3b-instruct`** | `Q4_K_M` | **31.86 tok/s** (`7T`) | **163.04 tok/s** (`28T`) | Cai p/ `12.36 t/s` | [`bench_cpu_small_compare_round2.json`](raw_data/speed_llama_bench/bench_cpu_small_compare_round2.json) |
| **`Qwen3.5-0.8B`** | `Q4_K_M` | **31.53 tok/s** (`7T`) | **241.66 tok/s** (`14T`) | Cai p/ `9.06 t/s` | [`bench_cpu_small_compare.json`](raw_data/speed_llama_bench/bench_cpu_small_compare.json) |
| **`gemma-3-1b-it`** | `Q4_K_M` | **28.55 tok/s** (`7T`) | **136.25 tok/s** (`28T`) | Cai p/ `6.08 t/s` | [`bench_cpu_small_compare.json`](raw_data/speed_llama_bench/bench_cpu_small_compare.json) |
| **`Qwen2.5-1.5B-Instruct`** | `Q4_K_M` | **27.18 tok/s** (`14T`) | **222.84 tok/s** (`28T`) | Cai p/ `9.24 t/s` | [`bench_cpu_small_compare.json`](raw_data/speed_llama_bench/bench_cpu_small_compare.json) |
| **`SmolLM2-1.7B-Instruct`** | `Q4_K_M` | **26.22 tok/s** (`14T`) | **167.48 tok/s** (`28T`) | Cai p/ `9.15 t/s` | [`bench_cpu_small_compare.json`](raw_data/speed_llama_bench/bench_cpu_small_compare.json) |
| **`Qwen2.5-Coder-1.5B-Instruct`** | `Q4_K_M` | **25.54 tok/s** *(steady)* | **158.75 tok/s** | Aprovado `>= 7.0 tok/s` | [`BENCHMARK_CHALLENGERS_RESULTS.json`](raw_data/triage_and_fleet/BENCHMARK_CHALLENGERS_RESULTS.json) |
| **`Qwen3-1.7B`** | `Q4_K_M` | **25.40 tok/s** (`7T`) | **194.67 tok/s** (`28T`) | Cai p/ `8.67 t/s` | [`bench_cpu_small_compare.json`](raw_data/speed_llama_bench/bench_cpu_small_compare.json) |
| **`MiniCPM5-1B`** | `Q4_K_M` | **23.46 tok/s** (`7T`) | **220.40 tok/s** (`14T`) | — | [`bench_cpu_r3.json`](raw_data/speed_llama_bench/bench_cpu_r3.json) |
| **`Falcon-H1-1.5B`** | `Q4_K_M` | **21.18 tok/s** (`14T`) | **198.02 tok/s** (`28T`) | Cai p/ `8.47 t/s` | [`bench_cpu_small_compare.json`](raw_data/speed_llama_bench/bench_cpu_small_compare.json) |
| **`gemma-4-E2B-it`** | `IQ4_XS` | **17.84 tok/s** (`7T`) | **137.36 tok/s** (`28T`) | Cai p/ `6.53 t/s` | [`bench_cpu_small_compare_round1.json`](raw_data/speed_llama_bench/bench_cpu_small_compare_round1.json) |
| **`MiniCPM5-2B`** | `Q4_K_M` | **17.43 tok/s** *(steady)* | **89.02 tok/s** | Cai p/ `3.98 t/s` (`14T r3`) | [`bench_cpu_r3.json`](raw_data/speed_llama_bench/bench_cpu_r3.json) · [`wait_and_benchmark.log`](raw_data/triage_and_fleet/wait_and_benchmark.log) |
| **`MobileLLM-R1.5 (Llama4 949M)`** | `Q4_K_M` | **14.96 tok/s** (`7T`) | **112.38 tok/s** (`7T`) | `582.77 MiB` | [`mobilellm_bench2.log`](raw_data/speed_llama_bench/mobilellm_bench2.log) |
| **`granite-4.0-micro`** | `Q4_K_M` | **14.27 tok/s** (`7T`) | **74.66 tok/s** (`28T`) | Cai p/ `5.17 t/s` | [`bench_cpu_small_compare.json`](raw_data/speed_llama_bench/bench_cpu_small_compare.json) |
| **`granite-4.2-3b`** | `Q4_K_M` | **13.47 tok/s** | **68.35 tok/s** | Aprovado `>= 7.0 tok/s` | [`BENCHMARK_CHALLENGERS_RESULTS.json`](raw_data/triage_and_fleet/BENCHMARK_CHALLENGERS_RESULTS.json) |
| **`OpenReasoning-Nemotron-1.5B`** | `Q4_K_M` | **12.40 tok/s** (`7T`) | **101.55 tok/s** (`14T`) | `10.53 t/s` (`14T`) | [`bench_cpu_r3.json`](raw_data/speed_llama_bench/bench_cpu_r3.json) |

### 3B. Triagem Fase A (`llama-server` End-to-End) & Modelos Pesados (`8B – 35B+`)

| Modelo | Escala / Quant | Tamanho | `PP` / `TTFT` | `TG` (Velocidade) | Veredito / Observação | Fonte Bruta |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **`Ring-mini 2.0`** | 16.8B MoE `Q4_K_M` | 9.23 GB | `30.61 t/s` (`1045 ms`) | **20.82–25.57 tok/s** | 🏆 **Rei High-Caliber L1** (100% RAM) | [`BENCHMARK_HIGH_CALIBER_RESULTS.json`](raw_data/speed_server_mtp_pld/BENCHMARK_HIGH_CALIBER_RESULTS.json) · [`triagem_fase_a_ring-mini-2_0`](raw_data/triage_and_fleet/triagem_fase_a_ring-mini-2_0_20260911_221054.json) |
| **`LFM2.5-8B-A1B` (CPU)** | 8B MoE `Q4_K_M` | ~4.6 GB | `129.36 t/s` (`t=20`) | **24.11 tok/s** (`t=10`) | `15.87 t/s` em `ctx=8192` | [`thread_sweep_gated_20261003.jsonl`](raw_data/speed_llama_bench/thread_sweep_gated_20261003.jsonl) |
| **`Ministral-3-3B`** | 3B `Q4_K_M` | 2.00 GB | `TTFT 663.4 ms` | **15.34 tok/s** | `12/15` casos Triagem A | [`triagem_fase_a_ministral-3-3b`](raw_data/triage_and_fleet/triagem_fase_a_ministral-3-3b_20260912_003732.json) |
| **`Phi-4-mini`** | 3.8B `Q4_K_M` | 2.32 GB | `TTFT 844.3 ms` | **14.99 tok/s** | Triagem Fase A (CPU) | [`triagem_fase_a_phi-4-mini`](raw_data/triage_and_fleet/triagem_fase_a_phi-4-mini_20260912_003541.json) |
| **`GPT-OSS 20B`** | 20B `Q4_K_M` | 10.82 GB | `18.05 t/s` (`4766 ms`) | **13.10 tok/s** | Passa Regra de Ouro (`>7.0`) | [`BENCHMARK_HIGH_CALIBER_RESULTS.json`](raw_data/speed_server_mtp_pld/BENCHMARK_HIGH_CALIBER_RESULTS.json) |
| **`gpt-oss-20b-antidoom`** | 20B `IQ4_XS` | 11.25 GiB | **31.29 tok/s** (`+73%`) | **10.94 tok/s** | Com `CPU_REPACK` ativo | [`proof_gpt20b_repack_paid.json`](raw_data/speed_server_mtp_pld/proof_gpt20b_repack_paid.json) |
| **`granite-3.1-2b`** | 2B `Q4_K_M` | ~1.5 GB | `TTFT 5071.8 ms` | **10.48 tok/s** | `3/3` casos Triagem A | [`triagem_fase_a_granite-3_1-2b`](raw_data/triage_and_fleet/triagem_fase_a_granite-3_1-2b_20260911_195507.json) |
| **`qwen3.5-4b`** | 4B `Q4_K_M` | ~2.7 GB | `TTFT 1773.7 ms` | **9.42 tok/s** | Triagem Fase A | [`triagem_fase_a_qwen3_5-4b`](raw_data/triage_and_fleet/triagem_fase_a_qwen3_5-4b_20260912_002847.json) |
| **`Qwen3.6-35B-A3B-UD + MTP`** | 35B MoE `Q4_K_M` | 21.1 + 1.5 GB | `11.11 t/s` (`2699 ms`) | **7.05 – 10.78 tok/s** | **MTP** (`+35%` a `4.35×` ganho) | [`INFERENCE_PROFILE_BENCHMARK.json`](raw_data/speed_server_mtp_pld/INFERENCE_PROFILE_BENCHMARK.json) · [`MTP_CONTEXT_CURVE_BENCHMARK.json`](raw_data/speed_server_mtp_pld/MTP_CONTEXT_CURVE_BENCHMARK.json) |
| **`Qwen3-30B-A3B`** | 30B MoE `IQ3_M` | 13.11 GB | `14.66 tok/s` | **7.05 tok/s** | `29.28 GB` RAM (`Q4_K_M` estoura RAM) | [`proof_qwen3_moe_iq3_vs_q4km.json`](raw_data/speed_server_mtp_pld/proof_qwen3_moe_iq3_vs_q4km.json) |
| **`Agents-A1`** | MoE `IQ4_XS` | 17.44 GB | `2.41 tok/s` (`12.4 s`) | **1.56 tok/s** | ❌ Reprovado (`< 7.0 tok/s`) | [`BENCHMARK_HIGH_CALIBER_RESULTS.json`](raw_data/speed_server_mtp_pld/BENCHMARK_HIGH_CALIBER_RESULTS.json) |

---

## 4. Índice de Navegação Limpo

| Arquivo / Pasta | O que Contém |
| :--- | :--- |
| **[`SPEED_AND_HARDWARE_TUNING_DOSSIER.md`](SPEED_AND_HARDWARE_TUNING_DOSSIER.md)** | Dossiê técnico completo de hardware (`PCIe BAR`, `Thread Scaling`, `MTP`, `CPU_REPACK`, `PLD`, `-fa`, `ShadowRouter 3ms`) e todas as tabelas detalhadas por modelo. |
| **[`STANDALONE_AREA_HIGHLIGHTS_CATALOG.md`](STANDALONE_AREA_HIGHLIGHTS_CATALOG.md)** | Catálogo de destaques isolados por área (`Coding`, `Battery 50 ThinkON/OFF`, `Campeonatos`, `Titans`). |
| **[`raw_data/speed_llama_bench/`](raw_data/speed_llama_bench/)** | Logs e JSONs puros do `llama-bench` (`arena_bench.log`, `bench_7b_gpu.log`, `bench_cpu_small_compare*.json`, `bench_cpu_r3.json`, `mobilellm_bench2.log`, `diag_speed.log`, sweeps). |
| **[`raw_data/speed_server_mtp_pld/`](raw_data/speed_server_mtp_pld/)** | Telemetria de servidor HTTP, curvas `MTP`, duelos `Official vs. UD`, `gpt-oss-20b` (`CPU_REPACK`/`PLD`), `Qwen3-30B`, e piloto `ShadowRouter`. |
| **[`raw_data/triage_and_fleet/`](raw_data/triage_and_fleet/)** | Relatórios `triagem_fase_a_*.json`, stress test `megazord_maximum_stress`, `CHALLENGERS` e logs de frota. |
| **[`raw_data/areas/`](raw_data/areas/)** | Provas isoladas por área, `QUALITY_RANKING_FINAL.txt`, `PARIDADE_REPORT_FINAL.txt`, Battery 50 e logs `campeonato_*.log`. |
| **[`registry_docs/`](registry_docs/)** | 4 documentos canônicos históricos do laboratório (`LLM_BENCHMARK_AND_PRUNING_REGISTRY.md`, `ROTOR_FLEET_STATE.md`, etc.). |
| **[`scripts/`](scripts/)** | Scripts Python e `.bat` reprodutíveis de velocidade (`scripts/speed/`) e avaliações isoladas (`scripts/areas/`). |

---

## ⚡ Estudo A/B de Otimização de Hardware nos Campeões (`K2-Horizon-0.9B [Q6_K]` & `3.7B [Q5_K_M]`)

Comparativo empírico controlado ([`proof_ab_tuning_winners.json`](raw_data/speed_server_mtp_pld/proof_ab_tuning_winners.json) · [`ab_tuning_winners.log`](raw_data/speed_server_mtp_pld/ab_tuning_winners.log)) medindo latência fria, reuse de prefixo (`--cache-reuse 256`), threads assimétricos (`-t 7 -tb 14 -C 0x5555555`), KV cache `q8_0`, `-fa` e `ngram-cache` mantendo validação cognitiva simultânea:

### 1. `K2-Horizon-0.9B [Q6_K]` (846.4 MB)
| Perfil | Flags Principais | Prompt Frio (`PP`) | Reuse Prefixo | `TG` Global | Áreas | Opus |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`A1_baseline_gpu`** | `-ngl 99 -t 8 -fa 1` | 2,432.4 ms (`171.85 t/s`) | 425.1 ms (`89.4 t/s`) | **29.81 tok/s** | 9/13 | 2/4 |
| **`A2_tuned_gpu_kv_reuse`** | `-t 7 -tb 14 -C 0x5555555 -ctk/v q8_0 --cache-reuse 256 --prio 2 --poll 100` | **2,049.4 ms (`203.96 t/s`, +18.7%)** | **334.2 ms (-21.4%)** | 26.84 tok/s | **10/13** | **3/4** |
| **`A3_tuned_cpu_zero_vram`** | `--device none -t 7 -tb 14 -C 0x5555555 -ctk/v q8_0 --cache-reuse 256` | 2,062.8 ms (`202.64 t/s`) | **328.0 ms (-22.8%)** | 26.21 tok/s | **10/13** | **3/4** |
| **`A4_tuned_cpu_ngram`** | `A3` + `--spec-type ngram-cache --spec-draft-n-max 8` | 2,254.8 ms (`185.39 t/s`) | 380.3 ms (`99.9 t/s`) | 20.62 tok/s | **11/13** | **3/4** |

### 2. `K2-Horizon-3.7B [Q5_K_M]` (3,475.0 MB)
| Perfil | Flags Principais | Prompt Frio (`PP`) | Reuse Prefixo | `TG` Global | Áreas | Opus |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`B1_baseline_gpu`** | `-ngl 99 -t 8 -fa 1` | 2,420.4 ms (`148.74 t/s`) | **215.1 ms (`144.15 t/s`)** | **19.93 tok/s** | **13/13** | **2/2** |
| **`B2_tuned_gpu_fa0`** | `-fa 0` + `-ctk/v q8_0` | ❌ *Exit code 1* | — | — | — | — |
| **`B3_tuned_gpu_fa1`** | `-fa 1 -t 7 -tb 14 -C 0x5555555 -ctk/v q8_0 --cache-reuse 256 --prio 2 --poll 100` | **1,830.9 ms (`196.62 t/s`, +32.2%)** | 721.9 ms (`42.9 t/s`) | 17.34 tok/s | **13/13** | **2/2** |
| **`B4_tuned_gpu_ngram`** | `B3` + `--spec-type ngram-cache` | ❌ *Exit code 1* | — | — | — | — |

### Principais Descobertas Empíricas de Engenharia:
1. **Prefill Assimétrico (`-t 7 -tb 14 -C 0x5555555`) acelera ingestão em +18.7% a +32.2%:** No `3.7B`, o tempo de prompt frio caiu de **2.42s para 1.83s** (`148.74 -> 196.62 t/s`).
2. **Regra do KV Cache Quantizado (`-ctk/v q8_0`):** No backend Vulkan (RX 580), `-ctk/v q8_0` exige `-fa 1` (Flash Attention ligado); com `-fa 0` o servidor recusa iniciar (`exit 1`). Em `f16` padrão (`B1`), o reuse de prefixo em GPU é mais rápido (`215ms` vs `721ms`) e o `TG` de geração pura é `+14.9%` maior (`19.93` vs `17.34 t/s`) — logo **`-ctk/v q8_0` só compensa quando for preciso economizar VRAM**, enquanto **`-t 7 -tb 14 -C 0x5555555` com KV padrão (`f16`) combina o melhor prefill com o maior TG**.
3. **N-Gram Cache (`--spec-type ngram-cache`):** Em CPU pura no `0.9B`, reduziu o `TG` (`26.2 -> 20.6 t/s`) pelo custo de verificação, e na GPU Vulkan com `3.7B` falhou ao subir (`exit 1`).
4. **CPU Zero-VRAM (`A3`) viável para sub-1B:** O `0.9B` em CPU pura com afinidade física roda a **26.21 tok/s** com **328 ms** de latência reuse e `10/13` + `3/4` Opus, consumindo **0 MB de VRAM**.
