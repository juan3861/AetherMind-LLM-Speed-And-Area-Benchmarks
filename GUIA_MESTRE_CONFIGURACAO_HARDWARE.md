# 🛠️ GUIA MESTRE DE CONFIGURAÇÃO DE HARDWARE — AetherMind Local Lab

**Matriz Equilibrada de Máxima Velocidade & Precisão para LLMs Pequenas, Médias e Grandes (`0.36B` a `35B+`)**  
**Hardware Auditado:** Intel Xeon E5-2697 v3 (`14C / 28T`, Haswell-EP AVX2) + `31.84 GiB` DDR4 Quad-Channel + AMD Radeon RX 580 (`8 GB` GDDR5, Vulkan `1.3.260`, Windows)  
**Motores:** `llama.cpp` (`b10749` AVX2, `b10819` Vulkan, `b9245` Vulkan)

> **Propósito deste Guia:** Consolidar em um único manual prático todas as configurações físicas descobertas nos benchmarks, gates de qualidade (`KV_FINAL_VALIDATION_GATE.json`, `KV_QUALITY_COMPARISON_Q8_VS_F16.json`), perfis de inferência ([`inference_profile.py`](raw_data/hardware_configs/inference_profile.py)), scripts de afinidade ([`affinity_tools.py`](raw_data/hardware_configs/affinity_tools.py)) e launchers de produção.

---

## 1. Anatomia Física & Leis Invioláveis do Hardware

| Subsistema | Regra Física Descoberta | Impacto Prático |
| :--- | :--- | :--- |
| **CPU (`Xeon E5-2697 v3`)** | **14 Núcleos Físicos / 28 Threads.** HyperThreading ajuda na leitura (`PP` até `t=20–28`), mas **destrói a geração (`TG` cai `-31%` a `-78%` acima de `t=14`)** por contenção na banda DDR4. | Use sempre **`-t 7` a `-t 12`** (ou `-tb 14` no batch) com máscara de afinidade em núcleos físicos pares. |
| **Máscaras de Afinidade** | Calculadas em [`affinity_tools.py`](raw_data/hardware_configs/affinity_tools.py):<br>• **`0x5555550`** = **12 núcleos físicos** (isola os 2 primeiros cores `[0, 2]` para o Windows)<br>• **`0x5555555`** = **14 núcleos físicos** (todos os cores físicos, 0 HT)<br>• **`0x15555`** = **10 núcleos físicos** (ideal para `gpt-oss-20b`) | **`0x5555550`** é o padrão ouro para modelos grandes em CPU evitando engasgos do sistema operacional; **`0x5555555`** com `-t 7 -tb 14` maximiza GPU híbrida/prefill. |
| **GPU (`AMD RX 580 8GB`)** | No Windows com placa-mãe Xeon sem ReBAR, o driver fixa a janela Host-Visible em **256 MB**, gerando `VK_ERROR_OUT_OF_HOST_MEMORY` em modelos maiores. | Definir **sempre** no ambiente antes de subir o servidor Vulkan:<br>`set GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1`<br>`set GGML_VK_ALLOW_SYSMEM_FALLBACK=1` |
| **RAM (`31.84 GiB DDR4`)** | **`--repack`** realinha tensores em 256-bit SIMD AVX2 (acelera até `+73%` em modelos de `~11–12 GB`), porém consome buffer extra massivo em modelos `>17 GB`. | • Até `~12 GB` (ex: `20B IQ4_XS`): **`--repack`**<br>• Acima de `~15 GB` (ex: `30B`, `35B`): **`--no-repack`** obrigatório para não estourar os 31.84 GiB! |
| **KV Cache (`f16` vs `q8_0`)** | Provado em [`KV_QUALITY_COMPARISON_Q8_VS_F16.json`](raw_data/hardware_configs/KV_QUALITY_COMPARISON_Q8_VS_F16.json) e [`KV_FINAL_VALIDATION_GATE.json`](raw_data/hardware_configs/KV_FINAL_VALIDATION_GATE.json): **`q8_0` no KV degrada código Python (`3/5` vs `4/5`) e derruba aceitação MTP (`70.6%` vs `93.3%`)**. | • **Padrão Ouro (Precisão + Velocidade):** **`-ctk f16 -ctv f16`** (ou omitir `-ctk/v`)<br>• **Assimetria Haswell CPU MoE:** **`-ctk q8_0 -ctv f16 -fa 1`** (`+163%` no `Ring-mini 2.0`, mantendo `Value` em `f16`!)<br>• **Vulkan RX 580:** Se usar `-ctk q8_0`, **`-fa 1` é obrigatório** (com `-fa 0` o servidor fecha com `exit 1`). |

---

## 2. Matriz Equilibrada por Modo de Execução (`GPU` · `Híbrido` · `CPU Pura`)

### 🟢 MODO 1 — GPU Pura Vulkan (Máxima Velocidade: `0.36B – 9B`)
*Ideal quando o modelo + KV Cache cabem nos ~7.3 GB úteis de VRAM da RX 580.*

**Variáveis obrigatórias:**
```bat
set GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1
set GGML_VK_ALLOW_SYSMEM_FALLBACK=1
```

| Faixa / Modelo | Quant | Flags Ideais (`llama-server`) | `PP` Esperado | `TG` Esperado | Precisão / Notas |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **Sub-1B (`K2-Horizon-0.9B`)** | `Q6_K` | `-ngl 99 --fit off -fa 1 -t 7 -tb 14 -C 0x5555555 -ctk q8_0 -ctv q8_0 --cache-reuse 256 --prio 2 --poll 100` | **204 tok/s** | **26.8–34.3 tok/s** | `10/13` Áreas + `3–4/10` Opus; reuse `334 ms`. |
| **1B–2B (`MiniCPM5-1B`, `Qwen2-VL-2B`)** | `Q4_K_M` | `-ngl 99 --fit off -fa 1 -t 7 -tb 14 -C 0x5555555 --cache-reuse 256` | **675–1,111 tok/s** | **43.7–51.6 tok/s** | Campeões absolutos de velocidade em GPU. |
| **Campeão 3B–4B (`K2-Horizon-3.7B`)** 🏆 | `Q5_K_M` / `Q6_K` | `-ngl 99 --fit off -fa 1 -t 7 -tb 14 -C 0x5555555 --cache-reuse 256 --prio 2 --poll 100` *(KV `f16`)* | **196–203 tok/s** | **19.3–20.0 tok/s** | **Melhor equilíbrio do laboratório:** `37/39` (`94.9%`) + `3/10` Opus; reuse `217–238 ms`. |
| **Visão / Código 4B (`Phi-4-mini`, `Qwen3-VL-4B`)** | `Q4_K_M` | `-ngl 45 --fit off -fa 1 -t 7 -tb 14 -C 0x5555555 --cache-reuse 256` | **245–291 tok/s** | **23.9–29.1 tok/s** | Roda 100% em VRAM com folga. |
| **7B–8B (`Qwen2.5-7B`, `DeepSeek-R1-7B`, `LFM2.5-8B`)** | `Q4_K_M` | `-ngl 45` (ou `-ngl 24` p/ folga) `--fit off -fa 1 -t 8 -c 4096 --no-repack` | **157–342 tok/s** | **23.2–31.3 tok/s** | Com `GGML_VK_*` ativado evita `OutOfHostMemory`. |
| **9B Uncensored (`Qwen3.8-9B-Heretic`)** | `IQ4_XS` | `-ngl 99 --fit off -fa 1 -t 8 -c 4096` | — | **14.2–14.6 tok/s** | `9/10` Campeonato + `33/39` (13 Áreas). |

> ⚠️ **Regra de `-fa` na RX 580 para contexto longo (`8192`):** Até `2048–4096` tokens, `-fa 1` é neutro/benéfico; em prompts de **`8192` tokens na GPU**, `-fa 0` é **11% mais rápido** (`173.04` vs `155.84 tok/s`, ver [`fa_sweep_8192_gpu_20261005.jsonl`](raw_data/speed_llama_bench/fa_sweep_8192_gpu_20261005.jsonl)).

---

### 🟡 MODO 2 — Híbrido GPU RX 580 + CPU Xeon (Modelos Densos `7B Q5/Q6` e `27B`)
*Ideal quando o modelo excede 6 GB e não cabe inteiro na VRAM + KV Cache.*

| Modelo | Quant / Peso | Divisão (`-ngl`) & Flags | `PP` Esperado | `TG` Esperado | Observação Prática |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **`K2-Horizon-7B`** | `Q5_K_M` (6.02 GB) / `Q6_K` (6.89 GB) | `-ngl 24` (`Q5_K_M`) ou `-ngl 20` (`Q6_K`) `--fit off -fa 1 -t 8 -c 4096` | **16.9–19.8 tok/s** | **5.9–6.7 tok/s** | Precisa timeout `>= 360s` em cadeias `<think>` longas; `3.7B [Q6_K]` entrega mesma nota 3.3× mais rápido. |
| **`Qwen3.8-27B-UD`** | `IQ3_XXS` (10.18 GB) | `GGML_VK_*` + `-ngl 30 --threads 8 --ctx-size 4096 --no-repack` | **15.4 tok/s** (`2.16×` CPU) | — | Offload de 30 camadas para a RX 580 dobra a leitura de prompt no 27B ([`INICIAR_QWEN_27B_HIBRIDO_SERVER.cmd`](raw_data/hardware_configs/INICIAR_QWEN_27B_HIBRIDO_SERVER.cmd)). |

---

### 🔵 MODO 3 — CPU Pura AVX2 (`Xeon E5-2697 v3` — Zero VRAM / GPU Livre)
*Ideal para deixar a RX 580 100% livre (ComfyUI/DirectML/vídeo) ou rodar MoEs gigantes de `16B` a `35B` em 32 GB RAM.*

| Modelo / Faixa | Quant | Flags Ideais (`llama-server` AVX2) | `PP` Esperado | `TG` Esperado | Fonte / Prova |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **Micro (`MiniCPM4-0.5B`, `SmolLM2-360M`, `Qwen3-0.6B`)** | `Q4_K_M` | `--device none -ngl 0 -t 7 -C 0x5555555 -fa 1` | **252–489 tok/s** | **47.5–63.6 tok/s** | NUNCA usar `-t 28` em TG (derruba `63.6` -> `19.3 t/s`). |
| **Leves (`K2-Horizon-0.9B`, `LFM2-1.2B`, `Llama-3.2-1B`)** | `Q4_K_M` / `Q6_K` | `--device none -ngl 0 -t 7 -tb 14 -C 0x5555555 -ctk q8_0 -ctv q8_0 --cache-reuse 256 --prio 2 --poll 100` | **202–246 tok/s** | **26.2–41.2 tok/s** | `0.9B [Q6_K]` faz `10/13` + `3/4` Opus com `328 ms` reuse e **0 MB VRAM**. |
| **Compactos (`Ministral-3-3B`, `Phi-4-mini`)** | `Q4_K_M` | `--device none -t 12 -C 0x5555550 -ctk f16 -ctv f16 -fa 1 --prio -1 --no-repack` | **70–102 tok/s** | **14.9–17.7 tok/s** | `-fa 1` obrigatório no Haswell (`+641%` no Ministral-3B). |
| **MoE 8B (`LFM2.5-8B-A1B`)** | `Q4_K_M` | `--device none -t 10 -tb 20 -C 0x5555550 -fa 1` | **129.4 tok/s** | **24.1 tok/s** | `15.87 tok/s` sustentado em `ctx=8192`. |
| **MoE 16.8B (`Ring-mini-2.0`)** 🏆 | `Q4_K_M` (9.23 GB) | `--device none -t 12 -C 0x5555550 -ctk q8_0 -ctv f16 -fa 1 --no-repack` | **30.6+ tok/s** | **20.8–28.8 tok/s** | **Assimetria `-ctk q8_0 -ctv f16 -fa 1`:** `+163%` vs `10.95 t/s` baseline! |
| **Denso 20B (`gpt-oss-20b-antidoom`)** 🏆 | `IQ4_XS` (11.25 GiB) | `--repack -t 10 -C 0x15555 --poll 100 --prio 2 -fa on --cache-reuse 256 -b 512 -ub 64 --skip-chat-parsing --min-p 0.05 --dynatemp-range 0.4 --dry-multiplier 0.8` | **31.29 tok/s** (`+73%`) | **10.9–13.1 tok/s** | `--repack` + micro-batch `-b 512 -ub 64` alinhado à L2 cache. |
| **MoE 30B (`Qwen3-30B-A3B`)** | `IQ3_M` (13.11 GB) | `--no-repack -t 12 -C 0x5555550 -fa 1` *(usar `IQ3_M`, nunca `Q4_K_M`)* | **14.66 tok/s** | **7.05 tok/s** | `Q4_K_M` estoura RAM (`31.18 GB`); `IQ3_M` cabe em `29.28 GB`. |
| **MoE 35B (`Qwen3.6-35B-A3B-UD + MTP`)** 🏆 | `UD-Q4_K_M` (21.11 GB) | `--no-repack -t 12 -C 0x5555550 --spec-type draft-mtp --spec-draft-n-max 2 -ctk f16 -ctv f16` *(ou `q8_0` p/ economizar RAM)* + **KEEP-ALIVE OBRIGATÓRIO** | **11.1–24.6 tok/s** | **7.1–12.2 tok/s** | `f16` dá **`93.3%` aceitação MTP** e passa no teste de código (`4/5`); **NUNCA descarregar entre chamadas** (cold start MTP cai para `2.19 t/s`). |

---

## 3. Comandos Prontos de Produção (Copy-Paste)

### 🥇 Perfil 1: Melhor Modelo Diário Equilibrado (`K2-Horizon-3.7B [Q6_K]` — GPU Vulkan)
```powershell
$env:GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM = "1"
$env:GGML_VK_ALLOW_SYSMEM_FALLBACK = "1"
F:\AetherMind_LLM\bin\llama-server.exe -m F:\models\desafiantes_3b_4b\K2-Horizon-4B-Q6_K.gguf `
  --host 127.0.0.1 --port 8080 -ngl 99 --fit off -c 4096 -cb -np 1 `
  -t 7 -tb 14 -C 0x5555555 -fa 1 --cache-reuse 256 `
  --prio 2 --prio-batch 2 --poll 100 --poll-batch 1 --skip-chat-parsing
```

### 🥈 Perfil 2: Sub-1B Zero-VRAM Ultra-Rápido (`K2-Horizon-0.9B [Q6_K]` — CPU Pura)
```powershell
F:\AetherMind_LLM\bin\llama-server.exe -m F:\models\ab_tuning\K2-Horizon-1B-Q6_K.gguf `
  --device none -ngl 0 --fit off --host 127.0.0.1 --port 8080 -c 4096 -cb -np 1 `
  -t 7 -tb 14 -C 0x5555555 -fa 1 -ctk q8_0 -ctv q8_0 --cache-reuse 256 `
  --prio 2 --prio-batch 2 --poll 100 --poll-batch 1
```

### 🥉 Perfil 3: Cérebro Pesado 35B MoE + MTP Máxima Precisão (`Qwen3.6-35B-A3B-UD` — CPU RAM Quente)
```powershell
F:\tools\lc_b10749\llama-server.exe -m F:\data\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf `
  --host 127.0.0.1 --port 8080 --threads 12 -C 0x5555550 --ctx-size 4096 -np 1 `
  --no-repack -fa 1 -ctk f16 -ctv f16 --spec-type draft-mtp --spec-draft-n-max 2 `
  -b 512 -ub 64 --skip-chat-parsing
```

---

## 4. Provas Brutas Vinculadas
- [`KV_FINAL_VALIDATION_GATE.json`](raw_data/hardware_configs/KV_FINAL_VALIDATION_GATE.json) — Prova fatorial `A/B/C/D` (`f16 + MTP` = `4/5` qualidade vs `3/5` em `q8_0`)
- [`KV_QUALITY_COMPARISON_Q8_VS_F16.json`](raw_data/hardware_configs/KV_QUALITY_COMPARISON_Q8_VS_F16.json) — `93.26%` vs `70.62%` aceitação MTP (`f16` vs `q8_0`)
- [`SMOKE_TEST_PERF_V1.json`](raw_data/hardware_configs/SMOKE_TEST_PERF_V1.json) — Validação física `0x5555550` (`12` cores) no `Qwen3.6-35B`
- [`inference_profile.py`](raw_data/hardware_configs/inference_profile.py) — Registry com `Ring-mini-2.0` (`-ctk q8_0 -ctv f16 -fa 1`), `Ministral-3-3B` e `Phi-4-mini`
- [`affinity_tools.py`](raw_data/hardware_configs/affinity_tools.py) — Cálculo dinâmico de máscaras (`0x5555550` / `0x5555555`)
- [`proof_ab_tuning_winners.json`](raw_data/speed_server_mtp_pld/proof_ab_tuning_winners.json) — Provas A/B Round 1 & Round 2 nos campeões `K2-Horizon`

---

## 🧪 Prova Real Supervisionada: O Melhor de Cada Categoria (3 Perguntas Objetivas — Baseline vs. Guia Mestre)

Teste executado ponta a ponta em [`proof_real_categories_gains.json`](raw_data/speed_server_mtp_pld/proof_real_categories_gains.json) ([`proof_real_categories_gains.log`](raw_data/speed_server_mtp_pld/proof_real_categories_gains.log)) validando **Código Python executável**, **Matemática** e **JSON estrito em Português**, com supervisão ativa de crashes, timeouts e boot:

| Categoria / Campeão | Baseline (Boot / PP / TG / Acertos) | Otimizado Guia Mestre (Boot / PP / TG / Acertos) | Ganho & Diagnóstico Supervisionado |
| :--- | :---: | :---: | :--- |
| **1. Sub-1B (`MiniCPM5-1B-Opus [Q6_K]`)** | 8.08s / 374.1 / 44.50 t/s / **3/3** | **2.52s** / 355.9 / **44.71 t/s** / **3/3** | **Boot -68.8%**, zero erros. |
| **2. 1.5B Fast-Code (`Qwen2.5-Coder-1.5B`)** | 7.61s / 207.5 / 38.63 t/s / **3/3** | **3.58s** / 204.1 / **38.66 t/s** / **3/3** | **Boot -53.0%**, `2.22s` total p/ 3 provas. |
| **3. 3B–4B Pareto (`K2-Horizon-3.7B [Q6_K]`)** | 24.81s / 100.9 / 19.70 t/s / **3/3** | **8.63s** / 96.1 / 19.68 t/s / **3/3** | **Boot -65.2%**, 100% precisão mantida. |
| **4. 8B Generalista (`RLM-Qwen3-8B-v0.1`)** | 31.01s / 59.0 / 13.65 t/s / **3/3** | **10.15s** / **60.6** / **14.26 t/s** / **3/3** | **Boot -67.3%**, **+4.5% TG**, menor latência (`15.22s`). |
| **5. 14B Híbrido (`DeepSeek-R1-14B [IQ3_M]`)** | 36.63s / *Timeout 120s* / 0/3 | **11.63s** / *Timeout 120s* / 0/3 | ⚠️ **Bug detectado:** Boot caiu `-68.2%`, mas `-ngl 18` com `IQ3_M` na Vulkan estoura `120s` na geração. |
| **6. 16.8B MoE (`Ring-mini-2.0 [Q4_K_M]`)** | ❌ `CRASH_EXIT_1` (`q8_0/q8_0 -fa 0`) | **4.54s / 94.99 / 23.29 t/s / 3/3** | 🏆 **Destravamento Total:** `-ctk q8_0 -ctv f16 -fa 1 -t 12 -C 0x5555550` subiu em `4.5s` a **23.29 tok/s**! |
| **7. 20B Heavy (`GPT-OSS-20B-Antidoom`)** | 165.48s / 29.2 / **12.84 t/s** / **3/3** | ❌ `BOOT_TIMEOUT_180S` (`--repack`) | ⚠️ **Bug detectado:** `--repack` em `11.27 GB` leva `>180s` (~4–5 min) só para repacking no boot; **`--no-repack`** roda liso a `12.84 t/s`. |
