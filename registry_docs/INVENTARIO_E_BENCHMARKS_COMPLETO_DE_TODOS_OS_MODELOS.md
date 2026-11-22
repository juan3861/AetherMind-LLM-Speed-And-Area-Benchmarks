# INVENTÁRIO CANÔNICO E BENCHMARKS COMPLETOS DE TODOS OS MODELOS (ROTOR-LLM / MEGAZORD)
# COMPREHENSIVE CANONICAL MODEL INVENTORY & BENCHMARK REGISTRY FOR ALL LLMs

> **AVISO PARA QUALQUER IA / AGENTE (Antigravity, WorkBuddy AI, Traycer, etc.):**  
> ESTE É O ARQUIVO CENTRAL DE MEMÓRIA PERMANENTE SOBRE MODELOS DE LLM TESTADOS NO PROJETO ROTOR-LLM / MEGAZORD.  
> **NUNCA BAIXE NEM EXECUTE MODELOS MARCADOS COMO DELETADOS / REPROVADOS.**  
> **CONSULTE ESTA TABELA ANTES DE QUALQUER EXPERIMENTO DE ROTEAMENTO OU DOWNLOAD.**  
>
> **Líder & Arquiteto:** Mestre Ruan  
> **Hardware de Referência:** Intel Xeon E5-2697 v3 (14C/28T AVX2) | 32 GB RAM DDR4 | AMD Radeon RX 580 8GB  
> **Diretório Canônico de Modelos:** `F:\data\models\`  
> **Regra de Ouro Inegociável:** Throughput mínimo de geração = **7.0 tok/s**. Modelos abaixo de 7.0 tok/s são considerados densos demais para loops agênticos locais e **DEVEM SER PODADOS/DELETADOS DO DISCO**.

---

## 1. TABELA MESTRE COMPARATIVA FORENSE (TODOS OS MODELOS)

| Modelo | Arquitetura / Quant | Tamanho Físico | Geração (tok/s) | TTFT (1º token) | RAM Peak | Status & Veredito Final | Papel no Megazord |
|---|---|---|---|---|---|---|---|
| **Ring-mini 2.0** | MoE 16.8B (1.4B ativos) Q4_K_M | 9.23 GB | **20.82 tok/s** | **1.04 s** | 5.19 GB | 🟢 **APROVADO & MANTIDO** | **L1: Reflexo, Terminal, RAG, Geral** (20+ tok/s) |
| **GPT-OSS 20B** | Dense 20B Q4_K_M | 10.83 GB | **13.10 tok/s** | **4.76 s** | 10.07 GB | 🟢 **APROVADO & MANTIDO** | **L2: Raciocínio Balanceado / Alta Qualidade** |
| **Qwen3.6-35B-A3B MoE (UD)** | MoE 35B (3B ativos) UD-Q4_K_M + MTP | 21.11 GB + 1.51 GB | **7.05 a 10.23 tok/s** | **2.69 s** | 12.63 GB | 🟢 **APROVADO & MANTIDO** (com MTP) | **L2: Cérebro Profundo (Deep Brain)** |
| **Ministral-3-3B-Reasoning** | Dense 3.3B Q4_K_M | 2.00 GB | **15.34 tok/s** | ~1.2 s | 2.8 GB | 🟢 **APROVADO & MANTIDO** | **L1: Matemática Simbólica (80% AIME)** |
| **Granite-3.1-2B-Instruct** | Dense 2.5B Q4_K_M | 1.44 GB | **17.50 tok/s** | ~0.9 s | 2.1 GB | 🟢 **APROVADO & MANTIDO** | **L1: Extração JSON / Tools Estritas (100%)** |
| **MiniCPM5-2B** | Dense 2.5B Q4_K_M | 1.45 GB | **15.19 tok/s** | Prompt: 89.0 tok/s | 2.2 GB | 🟢 **APROVADO & MANTIDO** | **L0/L1: Gateway Rápido / Agentic Tool-Use (131K)** |
| **granite-4.2-3b** | Dense 3.6B Q4_K_M | 2.09 GB | **13.47 tok/s** | Prompt: 68.3 tok/s | 2.9 GB | 🟢 **APROVADO & MANTIDO** | **L1: Raciocínio Configurável (Thinking/Low-Effort)** |
| **qwen2.5-coder-1.5b** | Dense 1.5B Q4_K_M | 1.04 GB | **23.25 tok/s** | Prompt: 158.7 tok/s | 1.6 GB | 🟢 **APROVADO & MANTIDO** | **L1: Code Fast-Path (Sintaxe/Regex/Patch)** |
| **Qwen3.5-4B** | Dense 4B Q4_K_M | 2.55 GB | **9.25 tok/s** | ~1.8 s | 3.4 GB | 🟢 **APROVADO & MANTIDO** | **L1: Código Algorítmico Inicial** (escala p/ L2) |
| **NVIDIA-Nemotron-3-Nano-4B** | Dense 4B Q4_K_M | 2.64 GB | ~10-12 tok/s | ~1.5 s | 3.2 GB | 🟢 **APROVADO & MANTIDO** | **L3: Crítico Independente / Auditor de Conflito** |
| **bge-reranker-v2-m3** | Cross-Encoder Q4_K_M | 0.41 GB | N/A | N/A | < 1 GB | 🟢 **APROVADO & MANTIDO** | **Infra: Reranker de RAG Local** |
| **embeddinggemma-300M** | Embedding Model Q8_0 | 0.31 GB | N/A | N/A | < 0.5 GB | 🟢 **APROVADO & MANTIDO** | **Infra: Vetorização de Documentos** |
| **ggml-large-v3-turbo** | Whisper Speech-to-Text | 0.81 GB | N/A | N/A | < 1.5 GB | 🟢 **APROVADO & MANTIDO** | **Infra: Transcrição de Áudio** |
| **Agents-A1** | Dense 17B IQ4_XS | 17.44 GB | **1.56 tok/s** ❌ | **12.43 s** ❌ | 9.30 GB | 🔴 **ELIMINADO / DELETADO DO DISCO** | **PROIBIDO RE-BAIXAR**. Inviável no Xeon (1.56 tok/s). |
| **Qwen3.6-35B-A3B (Official)** | MoE 35B Q4_K_M | 19.02 GB | **4.27 tok/s** ❌ | **8.50 s** | 10.78 GB | 🔴 **ELIMINADO / DELETADO DO DISCO** | **DUPLICATA INFERIOR**. Perdeu duelo contra UD (19 GB liberados). |
| **Phi-4-mini-instruct** | Dense 3.8B Q4_K_M | 2.32 GB | ~11-13 tok/s | ~1.9 s | 3.1 GB | 🟡 **ARQUIVADO / SEM PAPEL** | Perdeu para Ministral-3B em AIME (40% vs 80%). |
| **Qwen2.5-7B-Instruct** | Dense 7.6B Q4_K_M | 4.36 GB | **8.49 tok/s** | ~2.1 s | 4.1 GB | 🟡 **ISOLADO (Porta 8080)** | Redundante com Ring-mini 2.0 (20 tok/s). Fora do Megazord final. |
| **mistral-7b-instruct-v0.2** | Dense 7B Q4_K_M | 4.07 GB | ~7-9 tok/s | ~2.5 s | 4.5 GB | 🟡 **ARQUIVADO** | Sem benchmark vencedor. Substituído por GPT-OSS 20B e Ring-mini. |
| **InternVL2_5-4B + mmproj** | Vision Multimodal Q4_K_M | 2.28 GB total | ~8-10 tok/s | ~3.0 s | 3.5 GB | 🟡 **ARQUIVADO** | Visão multimodal sem pipeline ativo no momento. |
| **ai9stars_G9v3-3B** | Dense 3B Q4_K_M | 1.77 GB | Não auditado | N/A | N/A | 🟡 **ARQUIVADO** | Sem papel arquitetural no Megazord. |

---

## 2. CAMPEONATO ATUAL: NOVOS DESAFIANTES (EM ANDAMENTO)

### A. Baixados e Prontos em `F:\data\models\` para Benchmark Forense (Antigravity):
1. **`MiniCPM5-2B-Q4_K_M.gguf` (1.45 GB)**
   - **Origem:** `openbmb/MiniCPM5-2B-GGUF`
   - **Competência Avaliada:** Roteador ultrarrápido universal (L0/L1), 131K context nativo, tool-calling e agentic workflows.
   - **Objetivo:** Enfrentar `Granite-4.2-3B` e testar se pode substituir o `Ring-mini` ou `Granite-3.1` como gateway de baixo custo computacional.
2. **`granite-4.2-3b-Q4_K_M.gguf` (2.09 GB)**
   - **Origem:** `ibm-granite/granite-4.2-3b-GGUF`
   - **Competência Avaliada:** 128K nativo (expansível a 512K), 3 modos dinâmicos (`thinking`, `low_effort`, `non-thinking`), AIME25 78.33.
   - **Objetivo:** Duelo direto contra `MiniCPM5-2B` pelo posto de "pequeno cérebro generalista / agente".
3. **`qwen2.5-coder-1.5b-instruct-q4_k_m.gguf` (1.04 GB)**
   - **Origem:** `Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF`
   - **Competência Avaliada:** Especialista de código ultraleve (`code_fast_path` para regex, syntax, stack trace, patch).
   - **Objetivo:** Se não superar `Granite-3.1-2B` em latência × acurácia de código, será eliminado sem piedade.

### B. Desafiantes em Processamento Paralelo (WorkBuddy AI):
1. **`Qwen3.8-9B-Distill-Heretic-Uncensored-Q8_0.gguf` (~9.12 GB)**
2. **`RLM-Qwen3-8B-v0.1-Q4_K_M.gguf` (~4.68 GB)**
3. **`Qwen3-4B-Instruct-2507-RLM-SFT-v3-per-root-turn`** (safetensors via Git LFS para conversão GGUF)

---

## 3. HISTÓRICO DE PODAS & MODELOS BANIDOS (POR QUE FORAM DELETADOS)

### ❌ `Agents-A1-IQ4_XS.gguf` (17.44 GB) — BANIDO PERMANENTEMENTE
- **Data do Benchmark:** 16 de Setembro de 2026
- **Resultado:** Throughput de **1.56 tok/s** e TTFT de **12.43 segundos**.
- **Diagnóstico:** A densidade da rede esmaga a CPU Haswell AVX2. Qualquer loop de agente entra em timeout.
- **Ação Executada:** Arquivo DELETADO fisicamente do disco F:. Liberados 17.44 GB.
- **Ordem Expressa:** NENHUMA IA DEVE TENTAR BAIXAR ESTE MODELO NOVAMENTE.

### ❌ `Qwen3.6-35B-A3B-Q4_K_M.gguf` (Versão Oficial ggml-org, 19.02 GB) — DELETADO
- **Data do Duelo:** 18 de Setembro de 2026 (confirmado e deletado em 21 de Setembro de 2026).
- **Resultado do Duelo Head-to-Head:**
  - `UD-Q4_K_M` (21.11 GB): **4.81 tok/s** (cold) / TTFT 6.03s.
  - `Official Q4_K_M` (19.02 GB): **4.27 tok/s** (cold) / TTFT 8.50s.
- **Diagnóstico:** A quantização Unsloth Dynamic (`UD`) superou a versão oficial em 13% de throughput e 29% menor tempo para o primeiro token. Manter ambos era desperdício de 19 GB de SSD.
- **Ação Executada:** Arquivo oficial DELETADO fisicamente. Liberados 19.02 GB (espaço livre subiu para 37.5 GB).

---

## 4. TOPOLOGIA DA ARQUITETURA COGNITIVA MEGAZORD (FINAL FORM)

```text
                                MEGAZORD GATEWAY (:3700)
                                           │
                        ┌──────────────────┴──────────────────┐
                        │                                     │
                 L0 DETERMINÍSTICO                     L1 ESPECIALISTAS RÁPIDOS
                 Ferramentas / Python / Shell          ├─ Ring-mini 2.0 (20.8 tok/s) -> Geral/Terminal/RAG
                                                       ├─ Ministral-3-3B (15.3 tok/s) -> Matemática
                                                       ├─ Granite-3.1-2B (17.5 tok/s) -> Tools / Schemas
                                                       └─ Candidato Vencedor (MiniCPM5 ou Granite 4.2)
                                                              │
                                            (se falha / complexidade alta)
                                                              │
                                                              ▼
                                                       L2 CÉREBRO PROFUNDO
                                                       ├─ GPT-OSS 20B (13.1 tok/s) -> Raciocínio Geral
                                                       └─ Qwen 35B-A3B + MTP (7-10 tok/s) -> Resolução Pesada
                                                              │
                                            (se divergência / ambiguidade)
                                                              │
                                                              ▼
                                                       L3 CRÍTICO INDEPENDENTE
                                                       └─ Nemotron-3-Nano-4B -> Auditoria e Veredito Final
```

---

## 5. DIRETRIZES DE OPERAÇÃO MULTI-AGENTE (ANTIGRAVITY + WORKBUDDY + TRAYCER)

1. **Memória Compartilhada:** Sempre sincronizar este arquivo e `TRI_AGENT_PROJECT_HUB.md`.
2. **Sem Redundância de Trabalho:** Antigravity baixou MiniCPM5, Granite 4.2 e Qwen2.5-Coder; WorkBuddy está trabalhando no Qwen3.8-Heretic e RLM-8B. Não sobrescrever arquivos nem matar processos do parceiro.
3. **Auditoria Rigorosa:** Todo resultado de benchmark deve registrar: TTFT, tok/s de geração, RAM Peak, acurácia e veredito formal.
