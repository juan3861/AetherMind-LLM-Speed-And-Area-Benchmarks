# LLM BENCHMARK AND PRUNING REGISTRY — rotor-llm

> **NOTA DE SOBRESCRITA (02/10/2026).** Este arquivo foi sobrescrito **DUAS VEZES** por
> anexos de revisão externa. Na primeira vez não estava sob controle de versão e as
> seções 1-6.20 foram perdidas do disco; na segunda (02/10 18:01) o disco voltou a
> conter só o texto da revisão (59 linhas) enquanto o HEAD tinha 497 — recuperado por
> `git checkout`. **O arquivo agora está versionado e é a fonte de verdade.**
>
> **RECUPERAÇÃO DOCUMENTADA (§0).** Boa parte das seções 1-6.20 foi recuperada de fontes
> primárias que sobreviveram: o transcript da sessão de benchmark
> (`transcript_full.txt`, 1,4 MB, 03-22/09), os JSONs de resultado na raiz do repo
> (`BENCHMARK_*_RESULTS.json`), e os logs de campeonato em `scratch/campeonato_*.log`.
> O que foi recuperado está em **§0 RECUPERAÇÃO**; o que continua perdido está listado lá.

**Hardware de referência:** AMD Radeon RX 580 (8 GB VRAM, Polaris/GCN4), Intel Xeon
E5-2697 v3 (**14 núcleos físicos / 28 lógicos**, confirmado por portão de host em
02/10 13:27), 31,84 GB RAM **DDR4** quad-channel.

> **Correção 02/10 (revisão #2):** o cabeçalho dizia "DDR3". O Xeon **E5-2697 v3**
> (Haswell-EP) usa controlador de memória **DDR4**. Era erro de transcrição na
> reconstrução; restaurado para DDR4, como estava no original.

---

## 0 RECUPERAÇÃO DO ARQUIVO ORIGINAL (seções 1-6.20)

A revisão #2 notou corretamente que a perda foi maior que o descrito na primeira nota:
o original tinha **da seção 1 até a 6.20**, e a reconstrução cobria só 6.19-6.22 e fora
de ordem. O conteúdo perdido é justamente o que existe **para impedir que agentes
futuros repitam testes caros**: a Regra de Ouro, o registro forense do Agents-A1
("não baixar de novo"), o duelo MTP, o campeonato, a campanha do Heretic, o route
controller, o hard lock e o histórico do Adrenalin.

### 0.1 Fontes primárias que sobreviveram (verificadas em 02/10 18:05)

| Fonte | O que contém | Estado |
|---|---|---|
| `~/WorkBuddy AI/.../transcript_full.txt` | matriz de benchmark 03-22/09, duelo MTP, Agents-A1, Regra de Ouro | **1,4 MB, íntegro** |
| `BENCHMARK_HIGH_CALIBER_RESULTS.json` | 5 modelos, gen/prompt t/s, TTFT, RAM | íntegro |
| `BENCHMARK_OFFICIAL_VS_UD_RESULTS.json` | duelo Official vs UD ± MTP Head | íntegro |
| `scratch/championship_full_run.log` | campeonato 4 modelos pequenos, tabela + dimensões | íntegro |
| `scratch/campeonato_*.log` (9 arquivos) | rodadas granulares do campeonato | íntegro |
| `BENCHMARK_CAMPEONATO_RESULTS*.json` | 4 rodadas + backups | íntegro |
| `BENCHMARK_CHALLENGERS_RESULTS.json` | desafiante MiniCPM5-2B / granite-4.2 / coder-1.5B | íntegro |
| `scratch/REGISTRY_overwritten_by_review.md` | **só** o texto da revisão #1 | (não é o original) |

### 0.2 REGRA DE OURO (recuperada do transcript, 21/09)

**Limiar de aprovação de velocidade: 7,0 tok/s em cold start**, exigido pela "Regra de
Ouro do Mestre Ruan". Todo veredito de velocidade do campeonato aplica este piso.
Recuperado verbatim do transcript:

> *"Nenhuma das 4 configurações atingiu o limiar de **7 tok/s** exigido pela Regra de
> Ouro do Mestre Ruan em cold start."*

**Corolário operacional (também recuperado):** *"O Qwen 35B MoE deve operar SEMPRE com
keep-alive habilitado (não descarregar o modelo entre chamadas) para manter o MTP
eficaz. Sem keep-alive, o MTP é prejudicial em cold start."*

### 0.3 DUELO MTP — Official vs UD, com e sem MTP Head (17/09)

Fonte: `BENCHMARK_OFFICIAL_VS_UD_RESULTS.json` + veredito no transcript.

| Config | load (s) | TTFT (ms) | gen (t/s) | RAM pico (MB) |
|---|---:|---:|---:|---:|
| Official Baseline | 75,14 | 8.495 | 4,27 | 10.775 |
| Official + MTP Head | 61,04 | 30.735 | 2,97 | 11.893 |
| **UD Baseline** | 95,11 | **6.032** | **4,81** | 11.423 |
| UD + MTP Head | 77,09 | 55.203 | 2,19 | 12.631 |

**Veredito recuperado:**
- **Vencedor do duelo: UD Baseline** — 4,81 t/s, +13% de throughput e −29% de TTFT sobre
  a variante Official.
- **Por que o MTP regrediu aqui?** Na sessão anterior (16/09) o modelo estava em RAM
  quente após os benchmarks de Ring-mini e GPT-OSS-20B, o que favorecia o MTP (7-10 t/s).
  No teste **frio e sequencial**, o overhead de carregar o cabeçalho draft penalizou
  (TTFT de 55,2 s no UD+MTP).
- **Ambas as configurações com MTP em cold start ficam ABAIXO de 7 t/s** → falham a
  Regra de Ouro em cold start isolado.

**Recomendação operacional (recuperada):**

| Cenário | Configuração |
|---|---|
| Servidor já aquecido (keep-alive ativo) | UD + MTP (`--spec-draft-n-max 2`) — pode atingir 7-10 t/s |
| Cold start / primeiro uso | UD Baseline (4,81 t/s) |
| Produção interativa sem latência | Ring-mini 2.0 (20,82 t/s) ou GPT-OSS 20B (13,10 t/s) |

### 0.4 Matriz de benchmark multi-modelo (16/09) — "High Caliber"

Fonte: `BENCHMARK_HIGH_CALIBER_RESULTS.json`. Host: Xeon E5-2697 v3 14C/28T, 32 GB.
Threads=10 (configuração da época — **anterior** à correção para 14, ver §6.21.3).

| Modelo | Tamanho | load (s) | prompt t/s | gen t/s | TTFT (ms) | RAM pico (MB) |
|---|---:|---:|---:|---:|---:|---:|
| Ring-mini 2.0 Q4_K_M | 9,23 GB | 39,9 | 30,61 | **20,82** | 1.045 | 5.194 |
| GPT-OSS 20B Q4_K_M | 10,82 GB | 50,8 | 18,05 | 13,10 | 4.766 | 10.077 |
| Qwen3.6-35B-A3B MoE baseline | 21,11 GB | 70,8 | 1,29 | 1,62 | 23.236 | 11.503 |
| Qwen3.6-35B-A3B MoE + MTP | 21,11+1,51 GB | 34,5 | 11,11 | **7,05** | 2.699 | 12.632 |
| **Agents-A1 IQ4_XS** | 17,44 GB | 70,6 | 2,41 | 1,56 | 12.430 | 9.303 |

### 0.5 🔒 REGISTRO FORENSE — AGENTS-A1 ("não baixar de novo")

O `Agents-A1-IQ4_XS.gguf` (**17,44 GB**, MoE "Agentic Specialist") é **inviável nesta
máquina e não deve ser baixado novamente**. Medição de 16/09:

- **1,56 t/s de geração**, 2,41 t/s de prefill — **abaixo do piso de 7 t/s da Regra de
  Ouro**, e por ampla margem.
- TTFT de **12,4 s**; RAM pico de **9,3 GB** — não cabe com o resto da stack.
- Custo: 17,44 GB de download, 70,6 s de load, para o pior resultado da matriz.

**AÇÃO PARA AGENTES FUTUROS: NÃO BAIXAR O Agents-A1 DE NOVO.** Ele foi medido em
16/09/2026 e é um beco sem saída comprovado. Se o nome reaparecer em alguma lista de
candidatos, **esta seção é a resposta** — não repita o teste.

### 0.6 CAMPEONATO DE MODELOS PEQUENOS (22-23/09, Fase 1.4)

Fonte: `scratch/championship_full_run.log` (22/09) e `campeonato_*.log` (23/09).
Config: **CPU pura | 14 threads | ctx 4096 | temp 0.0 | porta 11499**.
Denominador = **sondas pontuáveis** (truncadas saem, ver §6.22.2).

| Modelo | steady (t/s) | cold (t/s) | TTFT (ms) | RAM pico | semEsc% | estab% | Regra |
|---|---:|---:|---:|---:|---:|---:|---|
| **MiniCPM5-2B** Q4_K_M | **20,24** | 20,87 | 312 | 2.037 | **100** | **100** | PASS |
| Granite 4.2-3B Q4_K_M | 14,55 | 14,60 | 858 | 2.489 | 80 | 80 | PASS |
| Qwen2.5-Coder-1.5B Instruct | **23,03** | 25,13 | 449 | 1.175 | 80 | 80 | PASS |
| Granite-3.1-2B Instruct (incumbente) | 15,52 | 14,63 | 996 | 1.979 | 80 | 80 | PASS |

**Dimensões funcionais (1ª tentativa, denominador = sondas pontuáveis):**

| Modelo | coding | instruction | json | math | tool | finish_mode |
|---|---|---|---|---|---|---|
| MiniCPM5-2B | 100% (2/2) | 100% (1/1) | 100% (1/1) | 100% (2/2) | 100% (2/2) | reasoning (reasoning_obs=2275) |
| Granite 4.2-3B | 100% (2/2) | 100% (2/2) | 100% (2/2) | **0% (0/2)** | 100% (2/2) | direct |
| Qwen2.5-Coder-1.5B | 100% (2/2) | 100% (2/2) | 100% (2/2) | **0% (0/2)** | 100% (2/2) | direct |
| Granite-3.1-2B | 100% (2/2) | 100% (2/2) | 50% (1/2) | 50% (1/2) | 100% (2/2) | direct |

**Falhas detalhadas (evidência negativa preservada, como o arquivo manda):**

| Modelo | Sonda | Motivo |
|---|---|---|
| minicpm5_2b | json_flat | `[UNUSABLE_TRUNCATED]` teto final=2048 |
| minicpm5_2b | instr_bullets | `[UNUSABLE_TRUNCATED]` teto final=2048 |
| granite42_3b | math_discount | `NUMERO=64.0; esperado=68.0` |
| granite42_3b | math_trap | `NUMERO=100.0; esperado=5.0` |
| qwen25coder15b | math_discount | `NUMERO=76.0; esperado=68.0` |
| qwen25coder15b | math_trap | `NUMERO=100.0; esperado=5.0` |
| granite31_2b | json_nested | `SOMA_ERRADA:32` |
| granite31_2b | math_trap | `NUMERO=100.0; esperado=5.0` |

**Leitura do campeonato:** `math_trap` (o problema do tipo "5 máquinas fazem 5 peças em
5 min; 100 máquinas fazem 100 peças em quanto tempo?") derruba **os três** modelos
pequenos não-reasoning — todos respondem 100. É uma sonda **discriminante** e deve ser
mantida. O MiniCPM5-2B, que roda em modo reasoning, é o único que escapa.

### 0.7 Campanha do HERETIC (23-25/09)

O `Qwen3.8-9B-Heretic-IQ4_XS` (5,36 GB) foi avaliado em 3 rodadas:
`campeonato_qwen38_9b_heretic.log` (Q4_K_M), `..._iq4xs.log` (IQ4_XS, CPU) e
`..._iq4xs_gpu.log` (IQ4_XS, GPU). Resultados consolidados em
`BENCHMARK_CAMPEONATO_PART3_IQ4XS.json` e `PART4_GPU.json`.

**O que a campanha estabeleceu:** o par CPU/GPU do mesmo peso IQ4_XS permite comparar
device pelo mesmo método de §6.22. **Pendente de re-consolidação após o fix de
`completion_tokens`** — os tok/acerto desta campanha sofrem do mesmo viés.

### 0.8 O que continua PERDIDO (não recuperado)

Itens que a revisão #2 listou como perdidos e para os quais **não achei fonte primária**:

- **Route controller** — a lógica de roteamento está viva em `agi/router.py`
  (`MODEL_TABLE`, `suggest_model`) mas o **registro narrativo** da sua construção não.
- **Hard lock** — o mecanismo de trava está no código; o registro da decisão de design, não.
- **Histórico do Adrenalin** — não encontrei menção em nenhuma fonte sobrevivente.
- **Seções 1-6.13 originais** — só os pedaços citados por 6.14-6.20 sobrevivem.

**Se o usuário tiver o anexo original da conversa, ele deve ser colado aqui.** Enquanto
isso, o que está em §0 é o que a evidência primária sustenta — não invenção.

---

## 6.21 CORREÇÕES E INVALIDAÇÕES — revisão externa de 02/10/2026

Uma revisão externa (anexo) apontou inconsistências. **Duas eram erros reais meus, uma
era um erro meu de cálculo, e três eram contradições internas do próprio registro.**
Registro abaixo o que foi invalidado, para que nenhuma conclusão posterior se apoie nisso.

### 6.21.1 INVALIDADO: "MiniCPM5-1B é 0/9 na GPU" — o servidor nunca subiu

**A objeção externa estava certa.** Investigado no log: **não existe** `srv_MiniCPM5-1B.log`.
O servidor Vulkan nunca carregou o modelo, e o harness então rodou as 9 tarefas contra
um socket morto. A prova está no JSON:

- **0 tokens gerados em TODAS as 9 tarefas**, `answer_head` vazio em todas;
- cinco tarefas retornaram em **0,0 s** — fisicamente impossível para inferência;
- `18,7 s` de total = soma dos **timeouts de conexão**, não de computação.

E a causa-raiz foi encontrada no log (`srv_MiniCPM5-1B-CPU.log`, 13 linhas):

```
E llama_init_from_model: failed to initialize the context:
                         vk::Device::createCommandPool: ErrorDeviceLost
E cmn  common_init_: failed to create context with model 'MiniCPM5-1B-Q4_K_M.gguf'
E srv  llama_server: exiting due to model loading error
```

O processo **saiu antes de abrir o socket**. `ErrorDeviceLost` = o device Vulkan morreu na
criação do contexto. **Re-testado em 02/10 pós-reboot: carrega perfeitamente em CPU puro e em
GPU full-offload (`ngl 999`).** Era **fadiga de driver**, não incompatibilidade de modelo.

**Conclusão anterior ("o mais rápido em tok/s é o pior em acerto") era lixo e é RETIRADA.**

**Causa-raiz do silêncio:** o harness tratava exceção de requisição como resposta vazia
(`ans, tim = "", {}`), indistinguível de "o modelo respondeu vazio". Só o campo `tok=0` no
JSON delatava. **Corrigido:** requisição que falha agora marca `backend_error=True` e a
bateria é **ABORTADA**, não pontuada. Medir contra servidor morto nunca mais produz ranking.
**Regra nova:** antes de aceitar qualquer `0/N`, `grep` o log do servidor por `listening on`.

### 6.21.2 CORRIGIDO: velocidade CPU do Coder-7B — a minha agregação estava errada

A revisão derivou ~20 tok/s de `459 tok / 22,3 s` e concluiu que "parece ter rodado na GPU
com rótulo de CPU". **O dispositivo estava certo (CPU, `n_threads=14`, zero linhas Vulkan),
mas o número de 20 tok/s era um artefato do meu próprio regex de análise**, que casava
`prompt eval time` dentro do padrão de `eval time` e contava o prefill duas vezes.

Separação correta (por linha, `prompt eval` excluído), **medida de novo em 02/10 17:35**:

| Modelo | PREFILL | GERAÇÃO | tokens gerados | tempo gerando |
|---|---|---:|---:|---:|
| Qwen2.5-Coder-7B (fresh) | 43,05 t/s | **9,30 t/s** | 128 | 13,76 s |
| Qwen2.5-Coder-7B (original) | 39,93 t/s | **8,52 t/s** | 127 | 14,91 s |
| R1-Distill-7B (fresh) | 40,84 t/s | **9,02 t/s** | 2.261 | 250,62 s |
| R1-Distill-7B (original) | 39,23 t/s | **8,41 t/s** | 2.598 | 308,07 s |

**Paridade confirmada de forma independente: 9,30 vs 9,02 t/s.** A divergência de 2× apontada
pela revisão **não existe** — era erro meu de medição, exatamente como ela suspeitou, embora
por uma causa diferente da que propôs. **Pergunta "o Coder-7B rodou mesmo em CPU?" →
RESPOSTA: SIM**, re-medido, com `device=CPU` gravado no registro, binário sem Vulkan,
`n_threads=14`, zero linhas de device no log.

**O que realmente difere é a VERBOSIDADE, não a velocidade:**

| Tarefa | Coder-7B | R1-7B | razão |
|---|---:|---:|---:|
| m2 (15% de 240) | **24 tok** | 168 tok | 7,0× |
| c1 (soma_quadrados) | 62 tok | 533 tok | 8,6× |
| c3 (fatorial) | 56 tok | 470 tok | 8,4× |
| **total 9 tarefas** | **457 tok** | **2.886 tok** | **6,3×** |

**REGRA PERMANENTE:** nunca reportar tok/s agregado como `tokens_total / segundos_total`.
Esse número mistura prefill barato (~40-43 t/s) com geração cara (~9 t/s) e é sempre enganoso.
Reportar **prefill t/s** e **geração t/s** separados, sempre. O harness já grava
`device`, `threads`, `fa` e o nome do binário em cada registro.

### 6.21.3 ⚠️ RETIFICADO em 02/10: contagem de threads — topologia ≠ ótimo

A seção 6.14 citava "7C/14T" e 7 threads vencendo; a 6.19 passou a usar 14 threads
descrevendo 14 físicos. Contradição real. **Portão de host executado em 02/10 13:27:**

```
CPU                 : Intel Xeon E5-2697 v3 @ 2.60GHz
Núcleos físicos     : 14
Processadores lógicos: 28
LoadPercentage      : 10
RAM livre           : 11,94 GB / 31,84 GB
```

A topologia é 14C/28T e o "7C/14T" da 6.14 era um estado anterior do host (power plan /
BIOS). **Regra permanente mantida: rodar o portão de host e LER a topologia antes de cada
bateria — nunca herdar o número de uma seção antiga.**

> **⛔ RETIFICAÇÃO (02/10, revisão #2 + §6.26):** a frase original continuava
> "...→ **14 threads é o valor correto**". Essa conclusão **não se sustenta**: o portão de
> host valida a **MÁQUINA**, não o **ÓTIMO**. As varreduras desta mesma seção acharam
> 7 threads ótimo para modelos ≤1B, e a re-medição da §6.25.2 acha **t=7 ótimo de geração
> e t=20 ótimo de prefill nas três classes ≤8B** — em nenhuma classe 14 é ótimo.
> **A topologia 14C/28T está certa; "14 threads é o correto" está errado.**

### 6.21.4 PARCIALMENTE RESOLVIDO: a contradição de VRAM (4 GB vs 8 GB)

A revisão está certa de que o registro se contradizia: "4 GB" em uma seção, 8192 MiB em
outra, teto de 6,4 GB em outra. **O valor físico é 8 GB** (RX 580). A explicação anterior
("9B streamando por PCIe") é **implausível**: 5,36 GB caem inteiros em 8 GB.

**Confirmado por medição direta em 02/10 (§6.22.4):**
```
$ llama-server.exe --list-devices
Available devices:
  Vulkan0: Radeon RX 580 Series (8192 MiB, 7367 MiB free)
$ vulkaninfo --summary
  deviceName = Radeon RX 580 Series | deviceID = 0x67df | driverID = AMD proprietary
  driverInfo = 26.5.2 | apiVersion = 1.3.260 | deviceType = DISCRETE_GPU
```
**8.192 MiB, dos quais 7.367 MiB livres com a GPU ociosa.** Não existe "4 GB". O texto
"4 GB" era **erro de transcrição** e está retirado.

**A hipótese do KV cache (da revisão) segue sendo a mais coerente** — mas ainda não medida.
O que já se sabe: com `-c 4096`, `n_ctx_slot = 4096`, `kv_unified='false'` (lido dos logs).
**STATUS: pendente** — varrer `-c` (2048/4096/8192) medindo VRAM para fechar.
Ver item 6.21.7.

### 6.21.5 NÃO RESOLVIDO: 9 tarefas medem competência básica, não raciocínio

A revisão tem razão: 17×23 todo modelo acerta, e a diferença entre 8/9 e 9/9 é **uma única
tarefa** — ruído. Além disso **corrigi o verificador durante a mesma sessão**, o que cria
risco de ajustar o instrumento aos modelos (documentado na 6.20 e na skill).

**STATUS: pendente.** Plano no item 6.21.7: bateria de 50-100 tarefas com subconjunto
difícil separado e **intervalo de confiança**, não contagem seca.

### 6.21.6 NÃO RESOLVIDO: Qwen2.5-VL-7B "derrotado" só em velocidade

A revisão está certa: ele foi derrotado em **prefill e VRAM**, nunca em **qualidade de
visão**. "Derrotado" sem qualificador é uma afirmação que os dados não sustentam.

**Nota descoberta em 02/10:** os pesos do `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` (4.683 MB) e
do `mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf` (853 MB) **estão completos em disco** — os
`.part*` ao lado eram downloads abandonados que já tinham a versão final e foram removidos
(7,85 GB liberados, §6.22.5). **A bateria de visão é executável já.**

**STATUS: pendente de bateria de visão.**

### 6.21.7 Plano de medição (o que a revisão propôs e eu adoto)

1. ✅ **Paridade GPU×CPU** com MiniCPM5-1B e Coder-7B, mesmo harness, `-fa` on/off → **FEITO, §6.22**
   (e revelou um bug de instrumento maior que a própria objeção).
2. **Bateria de 50-100 tarefas**, subconjunto difícil separado (código com casos de borda,
   raciocínio multi-passo, cadeias de ferramentas), reportando **acertos com intervalo**.
3. **VRAM vs contexto:** varrer `-c` no 9B/8B com medidor de VRAM para resolver 6.21.4.
4. **Bateria de visão** para separar velocidade de qualidade (6.21.6).
5. Só então corrigir `MODEL_TABLE` com base nos itens 1-4.

### 6.21.8 CONFIRMADO PELA REVISÃO (pontos que ela aceitou e eu mantenho)

- **Prefill decide se agente funciona**, mais que tok/s de geração. O 35B faz 11 t/s de
  prompt (4k tokens ≈ 6 min); o 7B na GPU faz ~157 t/s (10k de contexto ≈ 64 s por passo).
  **Loops de agente exigem contexto curto e poucos trechos recuperados.**
  → **Agora QUANTIFICADO em §6.22.3: a RX 580 só entrega 1,51× em prefill contra 2,45× em geração.**
- **Raciocínio profundo é limitado pelos pesos.** O 35B-A3B é a única classe ~30B viável
  nesta máquina, e rende 7-10 t/s só quando quente.
- **A metodologia é a melhor parte do projeto**: portão de host, truncamento fora do
  denominador, checkpoint por tarefa, SHA via pointer LFS.

**Correções que a revisão trouxe sobre a própria posição anterior** (aceitas):
subestimou a velocidade do 7-8B na RX 580 (usou ~7 t/s de fonte de comunidade em vez dos
23 t/s medidos); disse que MoE de ~30B "não cabe" (o Qwen3.6-35B-A3B rodou com 12,6 GB de
RSS — o mmap só puxa experts ativos, 4,8 t/s frio e 7-10 quente com MTP); e propôs
"um modelo por vez + fila noturna" quando o MoE leve em CPU roda **em paralelo** à GPU.

---

## 6.22 TESTE DE PARIDADE GPU×CPU + O BUG DE INSTRUMENTO QUE ELE REVELOU (02/10/2026)

O item 1 do plano da revisão foi executado: **mesmo peso, mesmo quant, mesma temperatura,
mesmo harness, variando só device e `-fa`**. A objeção 2 perguntava se o "0/9 na GPU" do
MiniCPM5-1B era **problema do modelo ou do backend**. A resposta é: **nem um nem outro —
era um TERCEIRO problema, e ele está no meu instrumento.**

Para permitir o teste, o harness ganhou: suporte a `-fa` (valores `on|off|auto` — **não**
`1|0`, verificado com `--help`), campo `device` explícito (nunca inferido de `ngl`), e
gravação de `device`/`threads`/`fa`/`server` em cada registro.

### 6.22.1 A paridade existe — o eixo device é irrelevante neste modelo

| Célula | Device | `-fa` | `ngl` | Acertos | gen/acerto | tempo |
|---|---|---|---:|---:|---:|---:|
| `MiniCPM5-1B_CPU_faauto` | CPU | auto | 0 | **4/9 (44%)** | 1.480 | 151,6 s |
| `MiniCPM5-1B_GPU_faauto` | GPU | auto | 999 | **4/9 (44%)** | 1.667 | 130,7 s |
| `MiniCPM5-1B_GPU_faon` | GPU | **on** | 999 | **3/9 (33%)** | 1.792 | 105,5 s |
| `MiniCPM5-1B_GPU_faoff` | GPU | **off** | 999 | **4/9 (44%)** | 1.170 | 124,9 s |
| `MiniCPM5-1B_CPU_thinkOFF` | CPU | auto | 0 | **4/9 (44%)** | 58 | 6,0 s |
| `MiniCPM5-1B_GPU_thinkOFF` | GPU | auto | 999 | **4/9 (44%)** | 58 | 5,5 s |

> **CORREÇÃO 02/10 (revisão #2).** Esta tabela dizia **4/4** nas duas linhas de
> `thinkOFF`. **Está errado: é 4/9 (44%).** O número "4/4" veio do *subconjunto
> pontuável* (4 acertos em 4 tarefas não truncadas) e, apresentado sem o denominador
> completo, fazia o modelo parecer perfeito. Não é. O MiniCPM5-1B com thinking
> desligado **acerta 4 das 9 tarefas** — as outras 5 são **erros genuínos**, não
> truncamentos (com thinking off não houve truncamento nenhum). Isto é exatamente o
> erro que a §6.22.2 mandava não cometer: confundir "pontuável" com "total".

**Paridade CPU×GPU é EXATA com thinking desligado: mesma pontuação (4/9), mesmos 556
tokens gerados, 6,0 s vs 5,5 s.** GPU e CPU produzem a mesma resposta porque é o mesmo
modelo — como esperado.

**Sobre `-fa` (correção de enquadramento — revisão #2):** a frase anterior dizia que a
hipótese do `-fa` foi "**refutada**". Isso é um **erro de categoria**: `-fa` afeta
**velocidade e memória**, não acurácia. Comparar acertos com n=9 para julgar `-fa` mede
a métrica errada. O correto é: **"não testado na métrica certa"** — o teste válido é
prefill (`pp`) com `-fa` on/off em prompt longo, que segue **pendente** (§6.25).
Os 3/9 (on) vs 4/9 (off/auto) desta tabela são **ruído de amostragem com n=9**, não
evidência sobre `-fa` em nenhuma direção.

### 6.22.2 ⚠️ BUG DE INSTRUMENTO (o mais grave até agora): truncamento contado como erro

Durante o teste a assinatura ficou visível: **4 tarefas gastaram exatamente ~1233-1270 tokens
em ~23-31 s e devolveram `content` VAZIO**. O verificador via "nenhum número na resposta" e
contava **ERRO**. Não era erro: era **TRUNCAMENTO**.

**Causa-raiz provada lendo o template do GGUF.** O `tokenizer.chat_template` do MiniCPM5-1B
contém:

```jinja
{%- if add_generation_prompt %}
    {{- '<|im_start|>assistant\n' }}
    {%- if enable_thinking is defined %}
        {%- if enable_thinking is false %}
            {{- '<think>\n\n</think>\n\n' }}
        {%- elif enable_thinking is true %}
            {{- '<think>\n' }}
        {%- endif %}
    {%- endif %}
{%- endif %}
```

Com thinking ligado, o modelo gasta o orçamento inteiro dentro de `<think>`, estoura
`max_tokens`, `finish_reason=length`, e o campo `content` volta **vazio** — o reasoning vai
para `reasoning_content`, que o harness nem lia.

**Correções aplicadas:**
1. `max_tokens` parametrizável (`QH_MAXTOK`).
2. Toggle de thinking (`QH_THINK=0` → `chat_template_kwargs={"enable_thinking": false}`);
   só enviado quando pedido, porque kwarg que o template não declara derruba a requisição.
3. Leitura de `reasoning_content` / `finish_reason`.
4. `truncated=True` quando `finish_reason=length` ou contagem no teto com `content` vazio.
5. **Truncamento sai do DENOMINADOR** e é contado separado (`truncados`, `pontuaveis`,
   `acuracia_bruta`), exatamente como o skill de forense já mandava (§4). Imprime `TRUN` no log.

**Deteccão retroativa nos dados antigos** (`scripts/report_quality.py`): resposta vazia +
tokens ≥ teto − 8 = truncado. Resultado — o estrago era maior que o MiniCPM5-1B:

| Modelo | Truncados | Pontuável | Acerto REAL | Reportado antes |
|---|---:|---|---:|---:|
| MiniCPM5-1B GPU auto | **5/9** | 4/4 | **100%** | 4/9 (44%) |
| MiniCPM5-1B CPU auto | 4/9 | 4/5 | **80%** | 4/9 (44%) |
| MiniCPM5-1B GPU fa=on | 4/9 | 3/5 | 60% | 3/9 (33%) |
| M5-1B-CPU-v2 | 3/9 | 3/6 | 50% | 3/9 (33%) |
| MiniCPM5-1B GPU fa=off | 3/9 | 4/6 | 67% | 4/9 (44%) |
| **MiniCPM5-2B** | 1/9 | 8/8 | **100%** | 8/9 (89%) |
| **Qwen3-8B** | 1/9 | 8/8 | **100%** | 8/9 (89%) |

**Três conclusões que mudam o ranking:**
1. O MiniCPM5-1B acertou **100% do que conseguiu de fato responder** — mas só conseguiu
   responder 4 de 9 com thinking ligado. **O problema dele é verbosidade patológica de
   reasoning, não incapacidade.** Com thinking off: 556 tokens em 5,5 s (26× menos tokens).
2. **MiniCPM5-2B e Qwen3-8B são 8/8 pontuáveis + 1 truncado** — não 9/9, e não 8/9.
   **Correção 02/10 (revisão #2):** a frase anterior dizia "9/9 pontuáveis", o que é
   impreciso. O correto é: cada um tem **8 acertos em 8 tarefas pontuáveis**, e **1
   tarefa truncada** (`e1` e `c2` respectivamente) que **sai do denominador**. Ou seja
   `pontuaveis=8`, `truncados=1`, `acuracia=8/8=100%`, `acuracia_bruta=8/9=89%`. Chamar
   de "9/9" infla o denominador com uma tarefa que o modelo não respondeu.
3. Com thinking desligado os erros do MiniCPM5-1B mudam de natureza e ficam **informativos**:
   `m2` devolve `0.15` (a taxa) em vez de `36`; `m3` devolve `120` (a distância) em vez de
   `80`; `m4` devolve `6` (operário-dia) em vez de `2`. Ele **calcula certo e responde a
   pergunta errada** — não é o mesmo modo de falha de antes.

**REGRA PERMANENTE:** um `content` vazio com tokens no teto é SEMPRE truncamento, nunca erro
do modelo. Contar truncamento como erro pune verbosidade como se fosse incapacidade, e pune
mais os modelos de reasoning.

### 6.22.3 ~~🔴 ACHADO PRINCIPAL: a RX 580 é muito pior em PREFILL que em geração~~

> ⛔ **SEÇÃO RETRATADA EM 02/10 (revisão #2) — NÃO USAR ESTA CONCLUSÃO.**
> O achado abaixo foi medido com **330 tokens de prefill no total das 9 tarefas = ~37
> tokens por prompt**. A essa escala a taxa de prefill é **warm-up**, não throughput, e
> o número **não é transferível** para contextos de 1-4k.
> **A conclusão INVERTE quando medida corretamente (§6.24.2):** no Coder-7B, `pp512`
> GPU/CPU = **156,0 / 42,6 = 3,67×** enquanto a geração é **1,79×** (16,32/9,11).
> **O prefill escala MAIS que a geração, não menos.** O "34× subutilizado" também não
> sai dos números (105/65 = 1,6×). Ver §6.24 para a medição correta e §6.25.5 para o erro.
> O texto abaixo fica **como registro do erro**, não como conclusão válida.

Medido no par Coder-7B, mesmos pesos, mesmos prompts, 9 tarefas, `ngl 999` vs `ngl 0`:

| | CPU (`lc_b10749`) | GPU (`lc_vulkan`) | speedup |
|---|---:|---:|---:|
| **prefill** | 43,0 t/s | **65,2 t/s** | **1,51×** |
| **geração** | 9,3 t/s | **22,8 t/s** | **2,45×** |
| prefill (s) | 7,67 s | 5,06 s | |
| geração (s) | 13,76 s | 5,49 s | |
| **total 9 tarefas** | **21,4 s** | **10,6 s** | 2,03× |
| acertos / tokens | 9/9, 458 tok | 9/9, 455 tok | idêntico |

**A GPU entrega 2,45× na geração mas só 1,51× no prefill.** Isto contradiz a intuição
comum de que a GPU é "uniformemente mais rápida" e tem consequência direta para agente:

- No Coder-7B, **o prefill é 35,8% do tempo total** (7,67 s de 21,4 s). É a fração mais
  caro-inelástica: 1/3 do tempo do agente roda a 43-65 t/s enquanto o modelo consegue gerar
  a 22,8 t/s. **O prefill está ~34× abaixo do que o hardware suportaria se escalasse como
  a geração** (se fosse 2,45× também, 43,0 → 105 t/s, não 65,2).
- Para o R1-Distill-7B o prefill é só 2,7% (7,05 s de 257,7 s) porque ele gera 2261 tokens
  de uma vez. **Ou seja: quanto mais conciso o modelo, mais o prefill domina a latência — e
  é justamente o modelo conciso que serve para agente.**
- Consequência prática: **para agente, o gargalo não é "tok/s de geração" — é o prefill
  por passo de recuperação.** Reduzir contexto e número de trechos recuperados vale mais que
  escolher um modelo com 2 t/s a mais de geração. Isto confirma e *quantifica* o ponto do
  §6.21.8 ("prefill decide se agente funciona").

**Hipótese a testar (§6.21.7 item 3):** o build Vulkan do Polaris pode estar subutilizando o
prefill por falta de *batched prefill* / `-b`, ou porque o `-fa auto` caiu em off neste modelo.
Vale varrer `-b`, `-ub` e `-fa on` **medindo prefill separado** — não agregado, que foi
exatamente o erro do §6.21.2.

### 6.22.4 Metodologia do teste (reprodutível)

Runner: `scratch/parity_fa_test.py`; grid declarado
em `GRID` (modelo, device, ngl, fa, binário, ctx, threads). Resultado bruto appendado em
`scratch/parity_results.jsonl`; logs do servidor por célula em `scratch/srv_<tag>.log`.
Relatório consolidado: `python scripts/report_quality.py` (ranking + auditoria de truncamento
+ matriz de paridade) → `scratch/QUALITY_RANKING_FINAL.txt`.

Binários usados:
- `F:\tools\lc_vulkan\llama-server.exe` — stub de 9 KB que carrega `ggml-vulkan.dll` (55 MB).
- `F:\tools\lc_b10749\llama-server.exe` — CPU puro, **sem** Vulkan (0 DLLs de device).
- `--list-devices` no `lc_vulkan` confirma: `Vulkan0: Radeon RX 580 Series (8192 MiB, 7367 MiB free)`.

⚠️ Cuidado: `lc_vulkan\llama-server.exe` tem 9 KB porque é um *launcher*; o executável real de
12 MB está em `lc_vulkan_b9245`. Ambos reportam o mesmo `Vulkan0`. Não confundir tamanho de
arquivo com ausência de Vulkan — o teste decisivo é `--list-devices`.


### 6.22.5 Limpeza: 7,85 GB de downloads abandonados (02/10)

`E://models//gguf//cpu_bench` continha **63 arquivos `.part*` (7,85 GB)** de downloads
multi-parte **já concluídos** — os arquivos finais existiam ao lado. Verificado antes de
apagar: cada `.part` tinha contraparte completa e não-vazia.

| Base | `.part` | GB | Arquivo final |
|---|---:|---:|---|
| `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` | 15 | 4,39 | OK 4.683 MB |
| `ggml-large-v3-turbo.bin` | 16 | 1,62 | OK 1.625 MB |
| `Qwen2-VL-2B-Instruct-Q4_K_M.gguf` | 16 | 0,99 | OK 986 MB |
| `mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf` | 16 | 0,85 | OK 853 MB |

Removido com verificação de contraparte (o script aborta se algum final faltar).
**E: 173 GB livres.** Isto desbloqueia a bateria de visão (6.21.6) — os pesos do VL-7B e
o `mmproj` estão íntegros em disco.

---

## 6.23 CORREÇÃO DE CONTAGEM: `completion_tokens` vs `tokens` somado (02/10/2026)

**Segunda revisão externa.** A revisão #2 achou um erro de contagem que atravessa **todo
o ranking** e que eu não tinha pego. Ela está certa, e a correção **inverte a narrativa**
do §6.21.2.

### 6.23.1 O bug: o campo `tokens` do harness somava prompt + geração

O harness gravava `tok = predicted_n + prompt_n`. Como o **prompt é constante por
tarefa** (~37 tokens na bateria de 9), isso **inflava `tokens_por_acerto` em todas as
linhas**, com um viés proporcionalmente maior para os modelos **concisos**.

Verificação contra os logs do servidor (o teste decisivo: `prefill + geração` bate com
o campo `tokens` em todos os registros):

| Execução | prefill + geração | `tokens` relatado | bate? |
|---|---:|---:|---|
| Coder, original | 330 + 127 | 457 | ✅ |
| Coder, nova | 330 + 128 | 458 | ✅ |
| Coder, GPU | 330 + 125 | 455 | ✅ |
| R1, original | 288 + 2.598 | 2.886 | ✅ |
| R1, nova | 288 + 2.261 | 2.549 | ✅ |
| MiniCPM5-1B, GPU auto | 336 + 6.655 | 6.991 | ✅ |

O "1233-1270 tokens no teto" do MiniCPM (que eu tratei como sinal de truncamento) é
**exatamente isto**: 1.200 de teto + 33-70 de prompt.

**Consequência dupla:**
1. **A objeção ORIGINAL da revisão #1 estava errada.** Ela derivou ~20 tok/s de
   `457 tok / 22,3 s` assumindo que `tokens` era só geração. A premissa era falsa.
   (O dispositivo — CPU — estava certo; o método de derivação, não.)
2. **O `tok/acerto` estava inflado em todas as linhas.** O Coder tem **~14-15 tokens
   GERADOS por acerto** (127/9), não 51. O R1 tem **~285**, não 321.

### 6.23.2 Impacto no ranking — a verbosidade estava subestimada em ~3×

| | relatado antes | correto (só geração) | erro |
|---|---:|---:|---:|
| Coder-7B gen/acerto | 51 | **15** | 3,4× inflado |
| R1-Distill-7B gen/acerto | 321 | **285** | 1,13× inflado |
| **razão de verbosidade Coder:R1** | **6,3×** | **19,1×** | subestimada 3× |
| Phi-4-mini | 241 | 27 | 8,9× inflado |
| Nemotron-1.5B | 2.484 | 2.404 | 1,03× inflado |

**A ordem do ranking se MANTÉM** (o viés é aditivo, não multiplicativo), mas a
**vantagem dos modelos concisos estava gravemente subestimada**. O MiniCPM5-1B com
thinking desligado cai de 139 para 58 gen/acerto — ele é **ainda mais eficiente** do que
eu dizia, e o problema dele é **100% verbosidade de reasoning**, não qualidade.

### 6.23.3 Correção aplicada

**Harness (`agi/quality_harness.py`):**
- `completion_tokens` (= `predicted_n`) e `prefill_tokens` (= `prompt_n`) agora são
  gravados **separados** por tarefa e no registro final.
- `tokens_por_acerto` usa **só geração**.
- `tokens_por_acerto_legado` fica gravado para auditoria, mas **nunca** para ranking.
- `prefill_por_tarefa` expõe o custo de contexto separado.

**Relatório (`scripts/report_quality.py`):**
- Deriva geração retroativa: registro novo usa o campo; registro legado subtrai
  `PREFILL_ESTIMATE=36` × n_tarefas (mediana verificada de 32-37 nos logs).
- Matriz de paridade passa a mostrar `gen/acerto` + `prefil/t` e **avisa explicitamente**
  que o prefill ali mede lotes de ~37 tokens e **não pode ser extrapolado** para 1-4k.

**REGRA PERMANENTE (nova):** **`tokens` soma prefill+geracao e nunca deve ser usado
para medir trabalho do modelo.** Só `completion_tokens` mede trabalho. Qualquer métrica
de "tokens por X" que use o total é **inválida por construção**, e o erro é maior
justamente para os modelos que mais importam (os concisos, que servem para agente).

---

## 6.24 PREFILL É FUNÇÃO DO TAMANHO DO PROMPT (02/10/2026)

**A revisão #2 também refutou o "achado principal" do §6.22.3 — e estava certa.**

### 6.24.1 Por que o §6.22.3 estava errado

O §6.22.3 concluiu que "a RX 580 só entrega 1,51× em prefill contra 2,45× em geração",
medindo **330 tokens de prefill no total das 9 tarefas = ~37 tokens por prompt**. Três
erros de raciocínio se acumularam:

1. **Amostra minúscula.** Prefill medido em lotes de 37 tokens diz **pouco** sobre
   contextos de 1-4k, que é o que um agente realmente usa.
2. **A própria arena contradizia.** O `arena_bench.log` mediu **157,9 t/s de pp512**
   para o Coder-7B **na GPU** contra ~43 na CPU → **3,7×, mais que os 2,45× da geração**.
   O achado **inverte**, não confirma.
3. **O "34× subutilizado" não sai dos números** — 105 contra 65 dá 1,6×. Inventei uma
   cifra que a medição não sustenta.

**Consequência prática:** o `MODEL_TABLE` guardava `pp=65` para o Coder-7B GPU, o que
faz o roteador **superestimar o prefill de prompts longos em ~2,4×**.

### 6.24.2 Medição correta: `llama-bench -p 64,512,2048` (CPU + GPU)

Runner: `scratch/pp_sweep.py` → `scratch/pp_sweep.jsonl`. Só prefill (`-n 0`) para
isolar a curva, mais `-n 128` para o fluxo completo. `-r 2`.

**MiniCPM5-1B (piloto, decisivo):**

| Prompt | CPU (`lc_b10749`) | GPU (`lc_vulkan`) | speedup |
|---:|---:|---:|---:|
| 64 | 350,7 t/s | 667,4 t/s | 1,90× |
| **512** | **347,4 t/s** | **1.117,3 t/s** | **3,22×** |
| 2.048 | 290,8 t/s | 918,8 t/s | 3,16× |
| geração (`-n 128`) | 41,3 t/s | 53,4 t/s | 1,29× |

**O achado do §6.22.3 INVERTE.** No prompt de 512 tokens a GPU entrega **3,22×** no
prefill, enquanto a geração entrega apenas **1,29×** no mesmo modelo. **A GPU ajuda
MAIS no prefill, não menos.** Isto reabilita o caso de uso "agente com contexto longo na
GPU" que o §6.22.3 tinha desencorajado — e o mecanismo é claro: prefill é *compute-bound
e paralelizável* (a GPU brilha), enquanto geração é *memory-bandwidth-bound e serial*
(a RX 580 não tem banda para se destacar tanto).

### 6.24.3 Varredura completa — 6 modelos × 2 devices (02/10, `scratch/pp_sweep.jsonl`)

`llama-bench -p 64,512,2048 -n 0,128 -r 2`, `-t 14`. Binários: `lc_b10749` (CPU puro,
sem Vulkan) e `lc_vulkan` (`ngl 999`, Vulkan confirmado por `--list-devices`).

| Modelo | Device | pp64 | **pp512** | pp2048 | tg128 | **× pp512** | **× tg** |
|---|---|---:|---:|---:|---:|---:|---:|
| LFM2.5-8B-A1B | CPU | 47,9 | 92,3 | 94,7 | 11,13 | | |
| LFM2.5-8B-A1B | GPU | 99,7 | **340,6** | 342,5 | 31,31 | **3,69×** | 2,81× |
| MiniCPM5-1B | CPU | 244,5 | 266,8 | 188,6 | 12,44 | | |
| MiniCPM5-1B | GPU | 656,1 | **1.111,4** | 917,0 | 51,57 | **4,17×** | 4,15× |
| MiniCPM5-2B | CPU | 91,3 | 95,0 | 82,4 | 19,33 | | |
| MiniCPM5-2B | GPU | 220,9 | **428,1** | 374,1 | 30,31 | **4,51×** | 1,57× |
| Qwen2.5-1.5B | CPU | 157,8 | 168,8 | 146,7 | 22,40 | | |
| Qwen2.5-1.5B | GPU | 336,7 | **673,7** | 603,3 | 43,04 | **3,99×** | 1,92× |
| Qwen2.5-Coder-7B | CPU | 44,1 | 42,6 | 40,9 | 9,11 | | |
| Qwen2.5-Coder-7B | GPU | 116,9 | **156,0** | 146,0 | 16,32 | **3,67×** | 1,79× |
| R1-Distill-7B | CPU | 44,7 | 36,5 | 38,2 | 5,26 | | |
| R1-Distill-7B | GPU | 125,0 | **157,6** | 149,4 | 23,11 | **4,31×** | 4,40× |

**O achado do §6.22.3 está refutado em 6 de 6 modelos.** O speedup de prefill na GPU
(3,67×–4,51×) é **igual ou maior** que o de geração em **todos** os casos. O padrão
mecanístico é claro e consistente:

- **Prefill é compute-bound** → a GPU paraleliza bem → o ganho é **grande e estável**
  (3,7×–4,5× em todos os modelos, quase independente do tamanho).
- **Geração é memory-bandwidth-bound** → a RX 580 (Polaris, ~256 GB/s) é apenas
  ~2-4× a banda útil da CPU → o ganho é **menor e errático** (1,6×–4,4×).
- Os dois modelos em que a geração empata (MiniCPM5-1B, R1) são justamente os que
  **já são rápidos o bastante** para saturar o caminho de memória.

**Observação de forma da curva:** o prefill **não** é monótono — em quase todos os
modelos `pp512 > pp2048` (ex.: MiniCPM5-1B 1.111 → 917). Isso é esperado: em 2.048
tokens o KV cache e a pressão de memória crescem, e a curva passa a ser limitada por
banda, não por compute. **Por isso `pp` como escalar é duplamente errado: além de
depender do device, depende do tamanho do prompt de forma não-linear.**

### 6.24.4 Correção do MODEL_TABLE

`pp` deixa de ser um escalar e passa a ser uma **curva**: `pp_by_prompt = {"64": …,
"512": …, "2048": …}` por modelo+device, derivada do sweep da §6.24.3. O roteador escolhe
o ponto da curva pelo tamanho estimado do prompt, em vez de extrapolar um número medido
em 37 tokens — que era a origem do erro de 2,4×.

Implementado em `agi/router.py`. O escalar `pp` é mantido igual ao valor de **p=512** (o
mais próximo de um prompt de agente) para não quebrar consumidores legados, mas
`pp_by_prompt` é a fonte de verdade. Travado por 3 asserções novas na suíte
(`agi/test_agi_layer1.py`): as duas entradas do Coder-7B precisam ter a curva e o valor
de p=512 correto, senão o teste falha.

## 6.25 ERROS MENORES DA §6.22 CORRIGIDOS (02/10/2026 — revisão #2)

A revisão #2 listou sete erros menores no texto novo. Todos procedem. Registro cada um
com a correção, porque a §6.22 é a seção mais citada e não pode carregar erro.

### 6.25.1 Truncamento NÃO é `-fa` — e `-fa` não é questão de acurácia

Já corrigido na tabela da §6.22.1: **"refutada" é erro de categoria**. `-fa` (flash
attention) afeta **velocidade e memória**, não acurácia. Comparar acertos com n=9 para
julgar `-fa` mede a métrica errada. O correto é **"não testado na métrica certa"**.

**Instrumento pronto, execução FEITA em 05/10 — e o resultado é INCONCLUSIVO.**
`scratch/fa_sweep.py` mediu a métrica certa: `pp` em 512 **e** 2048, com `-fa 0` e `-fa 1`,
CPU e GPU, em 3 modelos. O motivo de medir **também em 2048**: o custo de atenção é O(n²) no
comprimento do contexto, então se `-fa` ajudasse em algum lugar seria onde a atenção domina.

| modelo | dev | p=512 | p=2048 |
|---|---|---|---|
| MiniCPM5-1B | cpu | 311,2 → 296,2 (**0,952×**) | 235,4 → 254,3 (**1,080×**) |
| MiniCPM5-1B | gpu | 299,3 → 278,6 (0,931×) | 252,8 → 264,6 (1,047×) |
| MiniCPM5-2B | cpu | 102,5 → 120,2 (**1,173×**) | 95,6 → 91,6 (**0,958×**) |
| MiniCPM5-2B | gpu | 97,8 → 119,0 (**1,216×**) | 99,4 → 100,4 (1,010×) |
| Qwen2.5-1.5B | cpu | 176,7 → 142,7 (**0,808×**) | 131,6 → 130,6 (0,993×) |
| Qwen2.5-1.5B | gpu | 132,9 → 144,9 (**1,090×**) | 125,6 → 124,7 (0,993×) |

**O padrão do 1B (ajuda em 2048, atrapalha em 512) NÃO se repete nos outros dois.** O 2B faz o
**oposto** (ajuda em 512, atrapalha em 2048). O Qwen dá **0,808×** em 512 na CPU e **1,090×** na
GPU — mesmo prompt, mesmo modelo, sinais trocados.

**A causa é o próprio instrumento: `-r 1`.** Cada célula foi medida **uma vez**. A faixa de
variação observada (0,81× a 1,22×) é da ordem do ruído desta máquina — o mesmo defeito de
**n=1** que a bateria de qualidade acabou de corrigir com `QH_REPS`.

**CONCLUSÃO HONESTA: a pergunta do `-fa` continua ABERTA.** O que dá para afirmar é mais
estreito do que qualquer das duas hipóteses anteriores:

- ❌ "`-fa` não ajuda" (afirmação original do registro) — **não sustentada**, mas por medir `tg`.
- ❌ "`-fa` ajuda em contexto longo" (hipótese da revisão) — **também não sustentada** pelos
  dados atuais: o 2B contradiz.
- ✅ O que os dados sustentam: **com uma medição por célula, o efeito de `-fa` é
  indistinguível de ruído nestes 3 modelos.** É preciso `-r ≥ 5` antes de qualquer conclusão.

**Correção aplicada:** `fa_sweep.py` passou de `-r 1` para `-r 5`. **Re-execução FEITA em
05/10 — e ela dissolveu o "sinal".**

| modelo | dev | p=512 (r1 → r5) | p=2048 (r1 → r5) |
|---|---|---|---|
| MiniCPM5-1B | cpu | 0,952× → 0,950× | 1,080× → **1,016×** |
| MiniCPM5-1B | gpu | 0,931× → **1,172×** | 1,047× → 1,049× |
| MiniCPM5-2B | cpu | 1,173× → 1,135× | 0,958× → **1,008×** |
| MiniCPM5-2B | gpu | 1,216× → 1,096× | 1,010× → 1,029× |
| Qwen2.5-1.5B | cpu | **0,808×** → **1,047×** | 0,993× → 0,944× |
| Qwen2.5-1.5B | gpu | 1,090× → 1,106× | 0,993× → 0,989× |

**O outlier que sustentava a leitura "`-fa` atrapalha" era ruído.** O Qwen em 512/CPU media
**0,808×** com `-r 1` e **1,047×** com `-r 5` — praticamente neutro. O mesmo vale para o
MiniCPM5-1B em GPU/512 (0,931× → 1,172×) e para o 2B em 2048/CPU (0,958× → 1,008×).

**CONCLUSÃO (agora sim sustentada):** nestes 3 modelos e nestes comprimentos, **`-fa` é
aproximadamente NEUTRO no prefill** — os valores de `-r 5` em 2048 agrupam-se em torno de 1,0
(0,944–1,049), sem o ganho predito pela hipótese do O(n²).

**Ressalva importante:** **2048 tokens pode ser curto demais** para o termo O(n²) dominar. O
teste decisivo seria em 8192+, que não foi medido. Então o veredito é "neutro até 2048", não
"neutro em geral".

### 6.25.1.1 O teste em 8192 — e ele também não salva o `-fa` (05/10)

Feito: MiniCPM5-1B, GPU, `p=8192`, `-r 3`.

```
fa=0  pp8192 = 173,04 t/s
fa=1  pp8192 = 155,84 t/s     ->  0,901x
```

**Em 8192 o `-fa` é ~10% MAIS LENTO.** A hipótese predizia o contrário — era exatamente aqui que
o termo O(n²) deveria dominar e o `-fa` deveria ajudar. Não ajuda.

**Mas o custo O(n²) É real e visível:** o mesmo modelo em GPU cai de **~253 t/s em 2048** para
**173 t/s em 8192** (0,68× para 4× os tokens). Ou seja, o efeito existe — **o `-fa` é que não o
recupera** nesta configuração (kernel Vulkan provavelmente menos otimizado que o caminho padrão).

**VEREDITO FINAL, agora com três comprimentos medidos:** `-fa` é **neutro a levemente
prejudicial** no prefill, de 512 a 8192, nos modelos testados. Nem a hipótese original ("não
ajuda", medida em `tg`) nem a da revisão ("ajuda em contexto longo") se sustentam — por motivos
diferentes.

**O que fica registrado como fato:** o custo de atenção cresce com o contexto (253 → 173 t/s de
2048 para 8192), e **ligar `-fa` não o reduz** aqui.

**O que fica fechado:** a afirmação original do registro ("`-fa` não ajuda", baseada em `tg`)
continua **mal-fundamentada** — mas a hipótese que a substituiria ("ajuda em contexto longo")
**também não se confirmou** onde foi testada. Duas hipóteses erradas não fazem uma certa.

**Lição (a mesma de §6.27.1 e §6.28):** um instrumento com n=1 produz números plausíveis em
qualquer direção. Foi preciso **três modelos** para o ruído ficar visível — com um modelo só eu
teria "confirmado" a hipótese que quisesse, e teria ficado satisfeito.

### 6.25.2 Threads: "14 é o correto" era dedução de topologia, não medição

A §6.21.3 afirmou "14 threads é o valor correto" deduzindo do portão de host (14C/28T).
**O portão valida a MÁQUINA, não o ÓTIMO.** As varreduras 6.12/6.13 do próprio arquivo
acharam **7 threads ótimo para modelos ≤1B**.

**Hipótese mecanística (a testar):** hyperthreads **ajudam o prefill** (memory-bound,
mais MLP em voo) e **atrapalham a geração** (compute-bound, contenção no scheduler).
Se for isso, não existe um único "ótimo" — existe um par (ótimo_pp, ótimo_tg).

**Medição:** `scratch/thread_sweep_gated.py` (sonda de host **concorrente**), `-t 7,10,14,20`,
`-p 512` e `-n 128`, binário CPU puro, regime **pré-voo `QUIET`** (9,4% de 28 CPUs).

### 6.25.2.1 Resultado — 5 classes completas (03/10)

| classe | t=7 | t=10 | t=14 | t=20 | ótimo **tg** | ótimo **pp** |
|---|---:|---:|---:|---:|---|---|
| **1B** pp512 | 261,4 | 296,7 | 315,2 | **374,3** | **t=7** (43,1) | t=20 |
| **1B** tg128 | **43,1** | 40,8 | 41,3 | 29,6 | | |
| **2B** pp512 | 93,8 | 108,2 | 122,7 | **143,7** | **t=14** (19,2) | t=20 |
| **2B** tg128 | 18,7 | 19,0 | **19,2** | 12,9 | | |
| **8B MoE** pp512 | 86,3 | **116,5** | 112,0 | 129,4 | **t=10** (24,1) | t=20 |
| **8B MoE** tg128 | 22,4 | **24,1** | 21,9 | 20,5 | | |
| **7B denso** pp512 | 31,8 | 43,4 | 48,6 | **51,3** | **t=14** (9,02) | t=20 |
| **7B denso** tg128 | 7,94 | 8,93 | **9,02** | 8,81 | | |
| **7B reasoning** pp512 | 32,8 | 39,3 | 46,8 | **50,2** | **t=20** (8,51) | t=20 |
| **7B reasoning** tg128 | 7,25 | 8,43 | 8,50 | **8,51** | | |

**A hipótese está CONFIRMADA nas cinco classes:**

1. **O prefill sobe com threads em TODAS as cinco** — t=20 é o melhor de pp nas cinco. Faz
   sentido: prefill é *memory-bound* e mais threads em voo escondem a latência de memória.
   O ganho é grande: 1B **+43%**, 2B **+53%**, 7B denso **+61%**, 7B reasoning **+53%**.
2. **A geração cai no t=20 — mas só nos modelos pequenos.** 1B: 43,1→29,6 (**−31%**);
   2B: 19,2→12,9 (**−33%**); 8B MoE: 24,1→20,5 (−8%); **7B denso: 9,02→8,81 (−2%)**;
   **7B reasoning: 8,50→8,51 (plano)**.
3. **Não existe um único "ótimo"** — existe o par (ótimo_pp, ótimo_tg). Em **nenhuma** classe
   o ótimo é 14.

**Por que o colapso da geração some nos 7B (refinamento do mecanismo):** nos modelos pequenos
o trabalho por token é pequeno, então a **contenção de escalonador** (hyperthreads disputando
o mesmo núcleo físico) domina e o t=20 machuca. Nos 7B o gargalo passa a ser **banda de
memória**: as threads extras ficam *esperando memória* de qualquer jeito, então não ajudam
(o tg fica plano) mas também não atrapalham tanto. **O efeito de threads na geração é,
portanto, função do tamanho do modelo — não uma constante.** Isso explica por que uma única
"contagem ótima de threads" nunca poderia servir para todas as classes.

**Reforço do argumento:** as células de t=20 rodaram sob **mais** carga que as de t=7 (o próprio
host acumulou trabalho), e **mesmo assim** o pp de t=20 foi o maior em todas as cinco classes.
O efeito de threads no prefill é forte o bastante para aparecer apesar do confundidor.

### 6.25.2.1.1 AUDITORIA dos rótulos de regime — 9 de 20 estavam errados (05/10)

A tabela acima foi produzida com o gate **antigo** (`bench_share`). Depois de corrigir o gate
para `oversub` (§6.26.1), os rótulos gravados no JSONL ficaram **obsoletos**. Eu re-auditei as
20 células aplicando o gate correto sobre os campos brutos já gravados:

| veredito | gate antigo (`bench_share`) | gate correto (`oversub`) |
|---|---:|---:|
| `QUIET` | 4 | **13** |
| `MINOR_LOAD` | 4 | 3 |
| `CONTAMINATED` | **12** | **4** |

**O gate antigo marcou 8 células como contaminadas que eram limpas** — e, na direção oposta,
deixou passar como limpa a maior parte do 1B, cujas células de t=10/14/20 **eram** as
contaminadas de verdade. O erro não era aleatório: `bench_share` bruto num host de 28 vCPUs
mede "quantos núcleos de *qualquer coisa* estão ocupados", não se o bench está faminto — a falácia
que motivou a troca (§6.26.1).

**O resultado NÃO foi descartado — só os rótulos estavam errados.** A re-análise só com as células
`QUIET` **reproduz a conclusão**, e mais limpa:

| classe | threads (só `QUIET`) | pp512 | ganho pp | tg128 |
|---|---|---:|---:|---|
| **8B MoE** | 7, 10, 14, 20 | 86 → 129 | **+49,9%** | 22,4 → 24,1 → 21,9 → 20,5 (cai em t=20) |
| **7B denso** | 7, 10, 14, 20 | 32 → 51 | **+61,3%** | 7,9 → 8,9 → 9,0 → 8,8 (plano) |
| **7B reasoning** | 7, 10, 14, 20 | 33 → 50 | **+52,9%** | 7,2 → 8,4 → 8,5 → 8,5 (plano) |
| **1B** | 7 apenas | 261 | — | 43,1 |

O mecanismo do §6.25.2.1 se sustenta: **prefill sobe com threads em toda classe; a geração só
degrada no t=20 dos modelos menores** (8B MoE −15% aqui, contra −8% na tabela antiga; os 7B
seguem planos). O `1B` fica com **uma única** célula limpa — o que *reforça* o item 2 da
conclusão: é justamente o modelo pequeno que se degrada, e é justamente ele que não sobrevive
ao regime limpo.

**Regra que isto grava (nova):** *um artefato com veredito de regime gravado pode envelhecer
quando o gate muda.* Todo JSONL deve guardar os **campos brutos** (`busy_pct`, `logical_cpus`),
não só o veredito — foi isso que permitiu re-auditar sem re-rodar. Nunca re-gravar o veredito
no artefato original; re-derivar numa seção nova.

### 6.25.2.2 O travamento de 5h44m — e o que ele ensinou

Na primeira tentativa, as classes de 7B **não rodaram**: o driver travou no primeiro
`llama-bench` do 7B denso e ficou **5h44m sem escrever nada** (último mtime 14:19, nenhum
processo `llama-bench` ativo, nenhum consumo de CPU).

**Causa confirmada:** `TEMP`/`TMP` apontavam para **F: com ~0,1 GB livres**, e o modelo de 7B
tem 4,68 GB — carregar modelo num disco cheio é onde o `llama-bench` trava. **Depois de mover
`TEMP`/`TMP` para `E:\rotor_tmp` (181 GB livres), o mesmo 7B carregou e mediu normalmente**
(`pp512 = 30,78 t/s`). As 8 células saíram.

**Isto é uma instância concreta da regra do §6.26:** o travamento não produziu erro, produziu
**silêncio** — o log simplesmente parou. Um observador menos atento concluiria "terminou"
olhando o arquivo. **Detecção:** comparar o **mtime do log** com o relógio, e verificar se há
processo de bench ativo. Nenhum dos dois é automático — vale embutir no harness.

### 6.25.2.3 Conclusão que já está travada

Existe um **par** (ótimo_pp, ótimo_tg) por classe, e **não** um único ótimo — isso se sustenta
em **5 classes com 20 células**. **"14 é o correto" não se reproduz em nenhuma classe.** O
efeito de threads na geração **depende do tamanho do modelo** (§6.25.2.1, item 3).

Os valores absolutos continuam **não citáveis** como constantes de produção enquanto o host não
estiver com `oversub ≤ 0,85` de forma estável (algumas células chegaram a `oversub 1,77`).

### 6.25.3 Controle do R1: 9/9 → 8/9 em config "idêntica" **é** o achado

O R1-Distill-7B fez **9/9** na bateria original e **8/9** na re-execução, com **13% menos
tokens**, na mesma configuração. Eu tratei isso como "confirmação" (as velocidades batiam).

**A revisão está certa: é o oposto.** Uma diferença de resultado **em configuração
idêntica** é a prova de que **n=9 não tem poder de ranquear modelos separados por uma
única tarefa**. O que confirmei foi a **paridade de velocidade** — que é legítima. O que
não posso afirmar é ordenação por acerto com essa amostra.

**Correção:** a bateria de 50-100 tarefas (`§6.21.7` item 2) passa a exigir **≥3
repetições** por célula e **intervalo de confiança**; sem isso, diferenças de 1 tarefa
não são reportáveis como diferença.

### 6.25.4 Células GPU: o log PRECISA provar o offload — e não provava

**A revisão pediu:** "Confirme `offloaded N/N layers to GPU` em cada log de célula GPU."

**Investigação (02/10 21:20) — a resposta é sutil e importante:** os logs de GPU **não
tinham nenhuma linha de device**, o que parecia indicar fallback para CPU. **Não era.**
O `llama-server` sai com `verbosity = 3` por padrão, e nesse nível ele **suprime** as
linhas `offloaded N/N layers to GPU` e `using device Vulkan0`. **O log é silencioso por
configuração**, não por ausência de GPU.

**Prova de que a GPU estava ativa** (medido 21:22, mesma invocação do harness):

| Caminho | `-lv` | linhas de offload no log | prefill p=501 |
|---|---:|---|---:|
| harness (default) | 3 | **nenhuma** | **844 t/s** |
| diagnóstico | 4 | `offloaded 25/25 layers to GPU` | ~830 t/s |
| CPU puro (`ngl 0`) | 4 | `offloaded 0/25` | **180 t/s** |

**844 t/s é impossível em CPU** — a CPU faz 180. A GPU sempre esteve ativa.

**REGRA PERMANENTE:** `llama-server` roda com `-lv 4` **em todo teste com GPU**, senão o
log não serve como evidência. "Sem linha de offload no log" **só** é evidência de
fallback quando o log foi emitido com `-lv 4`. Sem esse cuidado, o investigador (eu)
comete o erro inverso: declara CPU onde havia GPU.

### 6.25.5 O erro mais grave desta rodada: prefill medido em lotes de 37 tokens

O §6.22.3 comparou prefill CPU vs GPU **somando 330 tokens de 9 tarefas**. Duas falhas:

1. **37 tokens por prompt é warm-up, não prefill.** A essa escala a taxa é dominada por
   overhead fixo de lançamento de kernel, e não mede throughput.
2. **Achado invertido.** Ver §6.24.2: no Coder-7B, `pp512` na GPU é **156,0 t/s** contra
   **42,6** na CPU = **3,67×**; a geração no mesmo par é **1,79×** (16,32 vs 9,11). O
   prefill escala **mais** que a geração — o oposto do que o §6.22.3 concluiu.

---

> **AVISO (atualizado 02/10, revisão #2):** três correções se aplicam a esta tabela.
> 1. A linha `MiniCPM5-1B` (0/9) foi **INVALIDADA** — ver 6.21.1.
> 2. MiniCPM5-2B e Qwen3-8B são **8/8 pontuáveis + 1 truncado** — **não** "9/9" (o
>    denominador não inclui a tarefa truncada). Ver §6.22.2.
> 3. **A coluna `tok/acerto` está INFLADA em TODAS as linhas** — ela somava
>    prefill+geração. Os valores corretos (só geração) estão em **§6.23**. Ex.:
>    Coder-7B é **15 gen/acerto**, não 51; a razão de verbosidade Coder:R1 é **19×**,
>    não 6,3×. **A ordem do ranking sobrevive; a magnitude não.**
> O `tok/acerto` **não depende do dispositivo** — essa parte segue válida.

Métrica: **tokens GERADOS por acerto** (menor = melhor) — corrigido em §6.23 para excluir
o prefill. Verificação **determinística** — matemática exata, código extraído e EXECUTADO
com casos de teste, JSON comparado campo a campo. Nenhum juiz LLM.

### Os dois bugs do instrumento (corrigidos e re-medidos)

1. **`_v_math` só buscava dígitos, nunca avaliava a expressão.** Modelo que respondia
   `17 * 23` (a expressão CORRETA) era marcado ERRADO. Fix: avaliador AST com whitelist
   (nunca `eval`), aceitando valor literal **ou** expressão que o computa; rejeita qualquer
   identificador ou chamada de função (só aritmética pura).
2. **`e1` exigia as chaves `nome`/`idade` que o enunciado não nomeava.** Modelos respondiam
   `{"name","age"}` — correto em inglês — e contava erro. Fix: nomear as chaves no enunciado.

**Efeito medido da correção (mesmo modelo, mesmo hardware):**

| Modelo | antes | depois | tok/acerto |
|---|---|---|---|
| Phi-4-mini | 2/9 | **5/9 (+3)** | 241 → **92** |
| LFM2.5-8B (GPU) | 6/9 | **8/9 (+2)** | 484 → **369** |
| MiniCPM5-2B | 8/9 | 8/9 | 151 → 325 (ver nota) |
| Qwen3-8B | 8/9 | 8/9 | 410 → 472 |

**Falha de método confessada:** editei o harness **com a bateria rodando**. Os modelos
seguintes importaram o arquivo editado e a bateria passou a ter **duas versões de
verificador** nos mesmos resultados. Detecção: auditar a string `why` de cada linha
(marcadores novos `expressao avaliada` / `campos conferem` vs antigos `campo 'nome' ausente`).
Correção: arquivei o conjunto antigo, re-rodei os 4 afetados em arquivo separado
(`QH_OUT=quality_results_fixed.jsonl`) e só então consolidei.

### RANKING (consolidado, verificador corrigido)

| # | Modelo | Acertos | tok/acerto | Verbo | math | code | ext | Device |
|---|--------|:---:|---:|---:|:---:|:---:|:---:|:---:|
| 1 | **Qwen2.5-Coder-7B** | **9/9** | **51** | 457 tok | 5/5 | 3/3 | 1/1 | CPU |
| 2 | Phi-4-mini | 5/9 | 92 | 460 tok | 2/5 | 2/3 | 1/1 | GPU |
| 3 | **Qwen3-1.7B** | **9/9** | 312 | — | 5/5 | 3/3 | 1/1 | GPU |
| 4 | **R1-Distill-7B** | **9/9** | 321 | 2.886 tok | 5/5 | 3/3 | 1/1 | CPU |
| 5 | MiniCPM5-2B | 8/9 | 325 | — | 5/5 | 3/3 | 0/1 | GPU |
| 6 | LFM2.5-8B-A1B | 8/9 | 369 | — | 4/5 | 3/3 | 1/1 | GPU |
| 7 | Qwen3-8B | 8/9 | 472 | 3.283 tok | 5/5 | 2/3 | 1/1 | CPU |
| 8 | MiniCPM5-1B (CPU) | 4/9 | 706 | 2.823 tok | 3/5 | 1/3 | 0/1 | CPU |
| 9 | MiniCPM5-1B (CPU v2) | 3/9 | 1.785 | 5.355 tok | 2/5 | 1/3 | 0/1 | CPU |
| 10 | Nemotron-1.5B | 4/9 | 2.484 | 9.938 tok | 4/5 | 0/3 | 0/1 | GPU |
| 11 | ~~MiniCPM5-1B (GPU)~~ | ~~0/9~~ | — | — | — | — | — | **INVALIDADO 6.21.1** |

### Achado principal

**Qwen2.5-Coder-7B: 9/9 a 51 tok/acerto.** Ganha em **todas** as categorias (não só código),
roda em CPU, e é **conciso por hábito** (m2 = 24 tokens, contra 168 do R1 e 1.221 do Nemotron).
A ~9,16 t/s de geração, mas como gasta 6,3× menos tokens, termina a bateria em 22 s contra
316 s do R1. **Concisão vale mais que velocidade bruta em geração.**

### Veredictos

1. **Qwen2.5-Coder-7B é o oráculo.** 9/9 a 51 tok/acerto, 6× mais eficiente que o
   Qwen3-1.7B. Modelo afinado em código **não** sacrifica aritmética.
2. **Qwen3-1.7B é o melhor generalista pequeno:** 9/9 a 312 tok/acerto **na GPU** — libera
   a CPU para o slot pesado.
3. **R1-Distill-7B também faz 9/9**, confirmando-o como denso confiável para `pesado`, mas
   paga 6,3× em tokens para o mesmo acerto. Serve para raciocínio longo, não para volume.
4. **MiniCPM5-2B (8/9) vs o irmão de 1B (3-4/9):** o dobro de parâmetros é a diferença
   entre utilizável e inútil. A falha do 2B (`e1`) é **real** — divagou 1.247 tokens sem
   produzir JSON.
5. **LFM2.5-8B-A1B: 8/9 a 369 tok/acerto.** Confirma o MoE na GPU; seu único erro (m2) é de
   **formato** (respondeu `240 * 0.15` em vez do valor), não de raciocínio.
6. **Phi-4-mini: o mais rápido por bateria (8,5 s), mas 5/9.** Acerta o formato e erra o
   cálculo. Ótimo para `reflexo`, inadequado como oráculo.
7. **Nemotron-1.5B: pior custo-benefício.** 4/9 a **2.484 tok/acerto** — ~1.220 tokens por
   tarefa em modo reasoning sem converter. **Podar da rotação.**

### Nota de honestidade sobre o MiniCPM5-2B

O tok/acerto dele **subiu** de 151 para 325 com o verificador corrigido. Não é regressão: na
passada antiga o `e1` falhava rápido (`campo ausente`, 152 tok) e agora o modelo **realmente
divaga** até 1.247 tokens antes de falhar. O instrumento velho **escondia** o defeito medindo-o
como erro barato. O ranking corrigido é pior **e mais verdadeiro**.

---


## 6.26 🔴 O NULO NÃO É ESTACIONÁRIO — o host estava saturado (02/10/2026, RETIFICADO 03/10)

> **⛔ RETIFICAÇÃO (03/10):** a manchete original dizia "153% de 16 CPUs". **Os dois números
> estavam errados.** `os.cpu_count()` = **28**, não 16 — meu `regime_probe.py` fixava
> `LOGICAL_CPUS = 16`, e isso inflou `busy_pct` em 28/16 = 1,75×. O valor correto daquela
> medição é **87,6% de 28 CPUs** (24,5 núcleos ocupados de 28).
>
> **O sinal de que eu estava errado estava na própria saída e eu não vi:** `busy_pct > 100%`
> é **fisicamente impossível** — 28 CPUs 100% ocupadas dá exatamente 100%. Um valor de 153%
> só podia significar denominador errado. O `verdict()` agora tem uma guarda que devolve
> `BUG_INSTRUMENTO` nesse caso.
>
> **O achado sobrevive, a atribuição muda.** O que continua medido e verdadeiro:
> o `bench_share` era **73,9%** (métrica independente do denominador), e a **mesma célula
> mediu 4,36× diferente entre duas passadas**. A causa passa a ser descrita como
> *sobrecarga do host* (24,5 núcleos de demanda sobre 14 físicos = **1,75× oversubscrito**),
> não como "153% de 16".

**Este é o achado mais importante da rodada 5, e ele contamina retroativamente todas as
medições de thread desta máquina.** Descobri por acidente: ao re-executar o thread_sweep,
a **mesma célula** que já tinha dado 133,27 t/s agora dava **30,58 t/s**.

### 6.26.1 O sintoma

| Célula (idêntica) | Passada A | Passada B | Razão |
|---|---:|---:|---:|
| MiniCPM5-1B, `-t 7`, `pp512` | **133,27 t/s** | **30,58 t/s** | **4,36×** |
| MiniCPM5-1B, `-t 7`, `tg128` | 20,18 t/s | 7,43 t/s | 2,72× |

Mesmo binário (`lc_b10749`), mesmo modelo, mesmo `-r 2`, mesma máquina, mesmo dia. **Uma
diferença de 4,36× não é ruído de medição — é outra distribuição.** O erro natural teria
sido concluir "o t=7 é instável" ou até "o modelo piorou". Nenhuma das duas é verdade.

### 6.26.2 A causa, medida (não inferida)

Sondei o host **durante** a varredura, com `GetProcessTimes` por processo (delta de 5 s):

```
total de CPU consumida = 122,67 cpu-s em 5,0 s de parede
                       = 24,5 núcleos ocupados  =  87,6% de 28 CPUs lógicas
                       = 1,75× os 14 núcleos FÍSICOS          <-- a métrica que importa
llama-bench levou apenas  90,67 cpu-s  =  73,9% do total
contaminantes: firefox 13,8 | chrome 9,4 | GoogleDriveFS 6,1
               voicemeeter 1,0 | FAHWindow64 (Folding@Home) 0,5
```

**O host tinha 24,5 núcleos de demanda sobre 14 núcleos físicos = 1,75× superassinado.** Os
~10 núcleos de excesso são *hyperthreads disputando o mesmo núcleo físico*, e é aí que as
threads do benchmark param. O `llama-bench` recebia **73,9%** da CPU que consumia — um quarto
do trabalho de cada thread era roubado pelo escalonador.

Isso explica a razão de 4,36× sem invocar nada sobre o modelo: **t=7 num host com folga
consegue 7 threads reais; t=7 num host 1,75× superassinado consegue ~3,4 threads reais.**

> **Por que a métrica mudou de `busy_pct` para `oversub`:** `busy_pct = 87,6%` soa "quase
> saturado, mas ainda tem folga" — e sugere que estaria tudo bem. `oversub = 1,75` mostra a
> verdade: **os núcleos físicos estão saturados há um fator de 1,75**. Numa máquina com SMT,
> `busy_pct` esconde a contenção porque dilui a demanda pelos núcleos lógicos que não existem
> fisicamente. **Sempre normalize por núcleos FÍSICOS.**

### 6.26.3 Por que isso é pior que um bug de código

Um bug de código falha igual toda vez. **Um nulo não estacionário produz resultados que
parecem válidos nas duas pontas.** A passada A (133 t/s) e a passada B (30 t/s) ambas têm
formato de array JSON bem-formado, ambas passam o parser, ambas têm números plausíveis. Um
leitor futuro escolheria uma das duas — provavelmente a que está no arquivo, sem saber que
havia 4× de diferença entre duas execuções do mesmo comando.

**A regra que eu deveria ter seguido e não segui:** *sempre registrar o estado do host
por amostra*. Não inferir de "a máquina parecia ociosa" — **medir**.

### 6.26.4 Correção aplicada: sonda de regime

Criado `scratch/regime_probe.py`. **Critério primário: `oversub = núcleos_ocupados ÷ 14
FÍSICOS`** (`bench_share` fica registrado apenas como informação):

| Regime | Critério (`oversub`) | Ação |
|---|---|---|
| `QUIET` | `≤ 0,85` (host deixa ≥15% dos físicos livres) | medir; número é citável |
| `MINOR_LOAD` | `≤ 1,15` | medir; anotar a carga |
| `CONTAMINATED` | `> 1,15` (físicos saturados, hyperthreads disputando) | **não medir** |


E `scratch/thread_sweep_gated.py`, que **recusa rodar** em regime `CONTAMINATED`
(salvo `--force`), e grava ao lado de **cada** célula: `host_busy_pct`, `host_busy_cores`,
`host_oversub`, `host_free_physical`, `host_bench_share_pct`, `host_verdict`, os top-5
contaminantes e os contadores de CPU usados. Telemetria em `scratch/regime_probe.jsonl`.

Verificação ao vivo (21:50–21:51, três sondagens com o bench parado):
`busy = 26,4% / 29,3% / 25,8%`, contaminantes estáveis `GoogleDriveFS` (7,4–8,8 cpu-s),
`chrome` (6,1–8,4), `firefox` (0,7–7,7). **O host estava sujo mesmo antes de eu começar a
medir** — não foi o bench que criou a carga.

### 6.26.5 O que fica em dúvida por causa disso

**Toda** a varredura de threads (§6.25.2) e as varreduras 6.12/6.13 herdadas **precisam ser
re-medidas em regime `QUIET`**, porque ambas foram feitas sem telemetria de host. O
"ótimo = 7 para modelos ≤1B" das varreduras antigas pode ser tanto um artefato de
contaminação quanto um ótimo real — **não dá para saber sem re-medir.** O mesmo vale para
grande parte da matriz de 16/09.

**O que NÃO fica em dúvida:** os resultados de **razão** dentro de uma mesma passada quando
as células foram medidas *intercaladas* e as duas pontas concordam (ex.: a paridade
GPU×CPU do §6.22, em que o dispositivo é o fator de 3,7×, muito maior que a variação de
host). Razões robustas sobrevivem; valores absolutos de t/s, não.

> **REGRA PERMANENTE (nova):** nenhuma medição de velocidade nesta máquina é citável sem
> a linha de regime do host (`oversub`, `busy_cores`, `free_physical`). `regime_probe.jsonl`
> é parte do dado, não um extra.

> **REGRA PERMANENTE 2 (nova, 03/10):** *silêncio não é conclusão.* O sweep travou às 14:19 e
> ficou 5h44m sem escrever — sem erro, sem exceção, o log simplesmente parou. Antes de
> declarar qualquer varredura concluída: (a) conferir o **mtime do log** contra o relógio;
> (b) conferir se há **processo de bench ativo**. Nenhum dos dois é automático hoje.

> **REGRA PERMANENTE 3 (nova, 03/10):** todo valor derivado passa pelo teste **"é fisicamente
> possível?"**. Os 4 bugs de instrumento de hoje (§6.27.1) emitiram números plausíveis; só o
> teste de impossibilidade (`busy_pct > 100%`) e a comparação de **duas execuções do mesmo
> comando** os pegaram.

## 6.19 Incidente de host: queda de energia, auditoria e o que o reboot curou (02/10/2026)

**Causa:** queda de energia às 08:42 (fios derrubados). Auditoria pós-reboot completa.

### Integridade: tudo intacto

6 modelos conferidos **byte a byte** contra os tamanhos exatos da fonte. Todos OK, nenhum
`.partN` órfão:

| Modelo | Bytes na fonte = no disco |
|---|---:|
| Qwen3-8B-Q4_K_M | 5.027.784.512 |
| LFM2.5-8B-A1B-Q4_K_M | 5.155.564.768 |
| Phi-4-mini-instruct-Q4_K_M | 2.491.874.272 |
| DeepSeek-R1-Distill-Qwen-7B-Q4_K_M | 4.683.073.504 |
| Qwen3-VL-4B-Instruct-Q4_K_M | 2.497.282.336 |
| Qwen2-VL-2B-Instruct-Q4_K_M | 986.046.944 |

### O que o reboot CURou: a fadiga do driver Vulkan

Smoke test: Qwen2.5-0.5B, `-ngl 45` → `model loaded`, `listening`, **zero
`OutOfHostMemory`**, inferência **correta** (17×23 = 391) a **20,11 t/s**.
**O reboot é o remédio do modo de falha.** Regra operacional: ~20 ciclos de criar/destruir
dispositivo Vulkan é o teto; ao atingi-lo, **reiniciar** em vez de degradar para CPU.

### O que o reboot QUEBROU: perda de meia bateria

O `Nemotron-1.5B` tinha 3 tarefas medidas e **perdeu tudo**, porque o harness só escrevia a
linha do JSONL **no fim das 9 tarefas**. **Corrigido:** checkpoint **por tarefa** em
`*.partial.jsonl`. Um novo reboot custa no máximo **1 tarefa**.
Lição: **resultado medido que não está no disco não existe.**

### Bug de método corrigido: threads fixas em 7 para CPU e GPU

`-t 7` fixo subutilizava o Xeon (14 físicos) em ~2×. Agora o **6º argumento** é o `nthreads`.
As comparações CPU-vs-CPU anteriores seguem válidas; as **CPU-vs-GPU estavam penalizando a CPU**.

### Incidente de disco: F: em 100% (692 MB livres de 477 GB)

**Causa-raiz: a Lixeira do próprio `F:` acumulava 2.659 MB** (um zip de 1 GB de maio e um
`.msi` de 543 MB, ambos com pastas extraídas já no disco). **Ação:** esvaziamento →
**3,19 GB livres**. Duas lições:

1. **A Lixeira conta como espaço usado.** Em disco apertado, esvaziar a lixeira é o primeiro
   passo, antes de mover ou apagar qualquer coisa.
2. **O failsafe `safe-delete` bloqueou o delete direto** (`FAIL_CLOSED`) — comportamento
   correto — mas o `Remove-Item` retornou erro **enquanto os arquivos sumiram**. Verificar
   sempre o **estado no disco**, nunca o exit code.

### Processos "órfãos" que não eram órfãos

Dois `python server.py` (PIDs 13672/13680) foram investigados **antes** de qualquer kill:
não eram restos do benchmark — são o stack Rotor OpenRouter / AetherMind Mesh Gateway
(UI `:8091`, API `:8088` e `:5001`). **Deixados intactos.**
Lição: identificar o processo pela CommandLine e porta **antes** de terminar.

---

## 6.27 ✅ CONTAGEM DE TOKENS VERIFICADA NOS 11 REGISTROS (03/10/2026)

A revisão #2 entregou um pacote com um verificador **independente** (`rotor_metrics.py`), cujo
`check-legacy` foi desenhado para **testar a hipótese nos dados reais do usuário** antes de
qualquer recálculo: casa a tarefa *i* com a requisição *i* do log e exige
`tok_antigo == prompt_n + gen_n`, declarando "CONFIRMADA" só com **≥80% de casamento exato**.

Rodei-o contra os 11 registros, casando cada um com o log da **mesma execução**:

| tag | casa | tok/acerto antigo | **correto** | prompt médio |
|---|---:|---:|---:|---:|
| Qwen25-Coder-7B-CPU | 9/9 | 50,8 | **14,1** | 36,7 |
| MiniCPM5-2B-GPU | 9/9 | 150,8 | **110,4** | 35,9 |
| Phi4-mini-GPU | 9/9 | 241,0 | **111,0** | 28,9 |
| Qwen3-1.7B-GPU | 9/9 | 311,9 | **276,6** | 35,3 |
| R1-Distill-7B-CPU | 9/9 | 320,7 | **288,7** | 32,0 |
| LFM25-8B-CPU-14t | 9/9 | 434,3 | **333,6** | 78,3 |
| LFM25-8B | 9/9 | 483,7 | **368,0** | 77,1 |
| Qwen3-8B-CPU | 9/9 | 410,4 | **370,6** | 35,3 |
| M5-1B-CPU | 9/9 | 705,8 | **625,0** | 35,9 |
| M5-1B-CPU-v2 | 9/9 | 1785,0 | **1677,3** | 35,9 |
| Nemotron-1.5B-GPU | 9/9 | 2484,5 | **2405,0** | 35,3 |

**11/11 CONFIRMADOS, 9/9 casamentos exatos em todos.** O ranking inteiro foi corrigido
**sem refazer a bateria**. Artefato: `scratch/quality_results_recomputed_from_logs.json`.

**Correção de uma afirmação minha anterior:** eu havia escrito "Coder-7B = **15** gen/acerto".
O valor exato é **14,1** (127 tokens de geração ÷ 9 acertos). O número estava arredondado para
cima por engano; a conclusão (≈14, não 51) permanece.

**A ordem do ranking muda em UM ponto:** `LFM25-8B-CPU-14t` (333,6) e `LFM25-8B` (368,0)
passam à frente de `Qwen3-8B-CPU` (370,6) — troca nas posições 6/7/8. O topo (1–5) e o fundo
(9–11) ficam iguais. A afirmação anterior ("a ordem sobrevive, a magnitude não") fica
**refinada**: sobrevive quase toda, com uma troca no meio.

**O `prompt_tokens_mean` confirma o artefato de prefill:** 28,9–78,3 tokens por prompt. A
medição de prefill original (330 tokens ÷ 9 tarefas = 37) era warm-up, como o §6.25.5 diz.

### 6.27.1 Quatro defeitos no MEU instrumento de regime, todos encontrados hoje

Registro porque a lição é sobre método, não sobre este host:

| # | Defeito | Sintoma que expôs | Correção |
|---|---|---|---|
| 1 | `LOGICAL_CPUS = 16` fixo (máquina tem 28) | `busy_pct = 153%` — **impossível** | detectar via `os.cpu_count()`; guarda que devolve `BUG_INSTRUMENTO` se `>100%` |
| 2 | Julgar por `busy_pct` sem modo | portão **abortava 100% das vezes** (pré-voo sem bench) | modos `preflight` e `during` separados |
| 3 | Sondar **depois** do subprocess | `bench_share = 0` sempre → toda célula `CONTAMINATED` | sonda em **thread concorrente** |
| 4 | `bench_share` como critério primário | `share=70%` em 28 CPUs **não** significa fome | critério = **oversub = núcleos_ocupados ÷ 14 físicos** |

O defeito 4 é o mais conceitual: numa máquina de 28 CPUs lógicas, `bench_share` mede
"outros processos estão ocupados", **não** "o benchmark está faminto". Com 28 CPUs e 10
ocupadas, as 7 threads do bench têm 18 CPUs livres. O que importa é se a demanda total passa
dos **14 núcleos físicos** — aí hyperthreads disputam de verdade. Banda nova:
`oversub ≤ 0,85` → `QUIET`; `≤ 1,15` → `MINOR_LOAD`; `> 1,15` → `CONTAMINATED`.
`bench_share` segue registrado como **informação**, nunca como critério.

**Lição transversal:** cada um desses 4 bugs produzia números *plausíveis*. Nenhum deles
teria sido pego lendo a saída — só comparando duas execuções do mesmo comando, ou
perguntando "este valor é fisicamente possível?".

---

## 6.28 BATERIA DE 50 TAREFAS — e ela discrimina o que a de 9 não discriminava (05/10/2026)

Fecha o item 5 da revisão #2, o maior pendente. Dois problemas resolvidos juntos:

**Problema 1 — n=9 não ranqueia.** O R1 fez 9/9 numa passada e 8/9 na outra, na **mesma**
configuração. Uma tarefa de diferença não é reportável. A bateria foi de **9 → 50 tarefas**
(math 22, code 19, extract 9), toda com verificação **determinística**.

**Problema 2 — faltava repetição.** `QH_REPS=N` roda a bateria N vezes e grava
`acuracia_por_rep[]`, `acuracia_media` e `acuracia_ic95` (t de Student, gl = reps−1).

### 6.28.1 Validação dos gabaritos (feita ANTES de medir)

Tarefa com resposta esperada **errada** marca modelo **correto** como errado — pior que não
medir. `scratch/validate_tasks.py` verifica cada classe por um caminho independente:

| classe | verificação | resultado |
|---|---|---|
| code (19) | solução de referência roda nos próprios casos do `check` | **19/19 passam** |
| math (17 novas) | valor recalculado em Python é aceito pelo próprio `check` | **17/17 aceitos** |
| extract (9) | `check` REJEITA JSON errado (sem falso positivo) | **9/9 rejeitam** |

### 6.28.2 Primeira execução: MiniCPM5-1B (CPU, 14 threads, 2048 ctx)

```
acertos 23/35 pontuáveis (66%) | bruto 23/50 | TRUNCADOS 15
25.212 tok gerados + 1.545 prefill em 841s
1.096 tok GERADOS por acerto
```

| categoria | n | ok | trunc | ok% |
|---|---:|---:|---:|---:|
| code | 19 | 10 | 6 | **77%** |
| math | 22 | 11 | 7 | **73%** |
| extract | 9 | 2 | 2 | **29%** |

### 6.28.3 Os dois achados que só aparecem com 50 tarefas

**1. `extract` é o ponto fraco real (29%), e o modo de falha é específico.** O modelo **não
extrai — ele ecoa** o texto de origem. Pedido o campo `produto`, devolveu a frase inteira
`'O notebook custa 3500 reais.'` em vez de `'notebook'`. Os nomes dos campos estão **explícitos
no enunciado**, então não é adivinhação de esquema: é falha de capacidade. Com 9 tarefas havia
**uma** tarefa de extração — impossível ver um padrão.

**2. 15 de 50 truncam (30%).** O modelo queima os 1200 tokens do teto em tarefa **simples** de
aritmética. Com 9 tarefas isso mal aparecia (1 truncado em 9); com 50 virou padrão sistemático.
Consequência direta no custo: **1.096 tok/acerto**, contra **14** do Coder-7B — quase **80×**
mais verboso por acerto.

**O que isso muda:** a bateria de 9 reportava "competência básica" e escondia tanto a
distribuição por categoria quanto a taxa de truncamento. As duas só ficam visíveis com massa.

### 6.28.4 Estado do mecanismo — VALIDADO com ≥2 repetições

`QH_REPS` verificado de ponta a ponta nos dois ramos:

**Ramo `reps=1`** (MiniCPM5-1B): gravou `acuracia_por_rep=[0.46]`, `acuracia_media=0.46` e
`acuracia_ic95=None` — correto, IC exige ≥2 repetições.

**Ramo `reps=3`** (Qwen2.5-0.5B-Instruct, CPU, 14 threads, 2048 ctx):

```
reps          : 3
por_rep       : [0.60, 0.62, 0.62]
media         : 0.6133
IC95          : [0.5846, 0.6420]
acertos/total : 92/150   (0 truncados)
32.5 tok GERADOS/acerto
```

**Matemática conferida à mão** (gl = reps−1 = 2): média 0,61333; variância amostral 0,0001333;
sd 0,011547; erro padrão 0,006667; t₉₅(2) = 4,303; margem 0,028688 → **IC [0,58464, 0,64202]**.
Confere com o gravado.

**O que isso destrava:** a bateria agora reporta acurácia por repetição, média e **intervalo de
confiança entre repetições** — exatamente o que torna "9/9 vs 8/9" reportável ou não. As três
passadas deram 60%/62%/62%, ou seja, o modelo é estável e a IC é estreita (±3 pontos).

### 6.28.5 Achado lateral: o menor venceu em custo

| modelo | acurácia | truncados | tok/acerto | tempo |
|---|---:|---:|---:|---:|
| MiniCPM5-1B | 66% (23/35) | **15** | **1.096** | 841 s / 50 tarefas |
| Qwen2.5-0.5B | 61% (92/150) | **0** | **32,5** | 86 s / 150 tarefas |

O 0.5B é **~34× menos verboso por acerto** e **~10× mais rápido**, com acurácia 5 pontos menor.
Para uso em cascata (onde o custo importa), o 0,5B é a escolha melhor — e a bateria de 9 tarefas
nunca teria mostrado isso, porque os 15 truncamentos do 1B só aparecem com massa.

### 6.28.6 `QH_REPS=3` no topo do ranking — Coder-7B (05/10)

Primeiro 7B/8B do ranking a fechar o IC. **Qwen2.5-Coder-7B-Instruct Q4_K_M, CPU (ngl=0),
14 threads, 4096 ctx, `QH_REPS=3`** — 150 execuções, 8m01s, **0 truncamentos**.

```
reps          : 3
por_rep       : [0.8800, 0.8800, 0.9000]   (44/50, 44/50, 45/50)
media         : 0.8867
IC95          : [0.8580, 0.9154]  ->  [86%, 92%]
bruto         : 133/150
truncados     : 0
geracao       : 2414 tok   (completion_tokens)
prefill       : 4216 tok
18.2 tok GERADOS/acerto      (legado: 49.8)
por_categoria : math 57/66 | code 54/57 | extract 22/27
```

**Matemática conferida à mão** (gl=2, t₉₅=4,303): média 0,88667; sd amostral 0,011547; erro
padrão 0,006667; margem 0,028688 → **IC [0,8580, 0,9154]**. Confere com o gravado.

**Três coisas que isto fecha:**

1. **A correção de contabilidade de tokens vale 2,74×** — medido *diretamente numa terceira
   execução*, não recomputado de log. O legado (`prefill+generacao`) dava 49,8 tok/acerto; o
   correto (`completion_tokens` apenas) dá **18,2**. O prefill (4.216 tok) é **1,75× a geração
   total** (2.414 tok): num prompt de ~28 tok/tarefa, somar prefill domina o número e o infla.
   Todo ranking anterior por `usage.total_tokens` está **inflado na mesma proporção**.
2. **O topo do ranking é ESTÁVEL, não ruidoso.** `sd = 0,0115` = **±1 tarefa** entre as três
   passadas. É o oposto do Qwen-0.5B (`[0,60, 0,62, 0,62]`, sd 0,0115 — mesma dispersão, mas
   sobre 60% de acurácia). A diferença 89% vs 61% está **fora** dos dois ICs, então é reportável.
3. **A hipótese de que `n=9` não ranqueava se confirma pela via oposta:** com 50 tarefas × 3
   reps, o Coder-7B acerta consistentemente 44–45/50. Um `9/9` de uma passada (§6.28.4) não
   distinguia isso de `8/9` por acaso; agora há margem para dizer que ele é o melhor.

**Custo do run:** 8m01s para 150 execuções (3,2 s/execução). Bem acima do que a estimativa
ingênua de 9-tarefas sugeria (0,10 h), porque o tempo é dominado por *carga do servidor* e pelo
prefill de 4096 ctx, não pelo número de tarefas.

### 6.28.7 R1-Distill-7B e LFM25-8B fechados — o ranking inteiro ganha IC95 (05/10)

**R1-Distill-Qwen-7B Q4_K_M, CPU (ngl=0), 14 threads, 4096 ctx, `QH_REPS=3`** — 150 execuções,
**71m14s**, 0 truncamentos:

```
por_rep       : [0.8800, 0.9400, 0.9400]   (44/50, 47/50, 47/50)
media         : 0.9200
IC95          : [0.8339, 1.0000]  ->  [83%, 100%]
geracao       : 34579 tok   prefill: 2420 tok   em 4274 s
250,6 tok GERADOS/acerto      (legado: 268,1)
por_categoria : math 66/66 | code 55/57 | extract 17/27
```

**LFM2.5-8B-A1B Q4_K_M, GPU (ngl=45), 7 threads, 4096 ctx, `QH_REPS=3`** — 150 execuções, 32m52s:

```
por_rep       : [0.6400, 0.6600, 0.6200]   (32/50, 33/50, 31/50)
media         : 0.6400
IC95          : [0.5903, 0.6897]  ->  [59%, 69%]
geracao       : 42233 tok   prefill: 8071 tok
439,9 tok GERADOS/acerto      (legado: 524,0)
por_categoria : code 51/57 | math 40/66 | extract 5/27
```

**As duas descobertas que só aparecem com 3 repetições:**

1. **R1 é o mais preciso (92%) mas o MAIS variável** — `sd = 0,0346`, **3× o sd do Coder-7B**
   (0,0115). A rep 0 fez 44/50 e as reps 1–2 fizeram 47/50. O IC `[83%, 100%]` é largo
   *precisamente* por isso: com n=3 e essa dispersão, não dá para distinguir R1 de Coder-7B.
   **A acurácia de 92% é real e reprodutível em 2 de 3 reps — mas a vantagem sobre os 88,7%
   do Coder-7B está DENTRO do intervalo.** Com 1 só passada (n=9) isso era invisível: ambos
   davam 9/9.
2. **`math = 66/66` perfeito, `extract = 17/27` (63%)** — o padrão se repete em 3 modelos
   diferentes: **todo modelo que "raciocina" falha em extract**. R1 66/66 math mas 63% extract;
   LFM 18,5% extract; e o extract do Qwen-1B tinha sido 29%. O problema não é matemática —
   é **obedecer formato**. Isso torna `extract` o eixo mais discriminante da bateria.

**Custo vs acurácia (tok GERADOS/acerto, só geração):**

| modelo | acurácia | IC95 | tok/acerto | tempo/150 |
|---|---:|---|---:|---:|
| **Qwen25-Coder-7B** | 88,7% | [86%, 92%] | 18,2 | 8m01s |
| **Qwen3-8B** | **98,0%** | [98%, 98%] | 283,2 | 93m52s |
| **Qwen3-8B (QH_THINK=0)** | 90,7% | [88%, 94%] | **16,4** | 13m51s |
| R1-Distill-7B | 92,0% | [83%, 100%] | 250,6 | 71m14s |
| MiniCPM5-1B | 66% | — | 1.096 | 841s |
| LFM25-8B | 64,0% | [59%, 69%] | 439,9 | 32m52s |
| Qwen2.5-0.5B | 61,3% | [58%, 64%] | 32,5 | 86s |

**O Coder-7B domina o eixo custo×acurácia de forma brutal:** 88,7% de acurácia a **18,2
tok/acerto** — 15,6× mais barato que o Qwen3-8B com thinking default (283,2) e 13,8× mais
barato que o R1 (250,6), por 9,3 e 3,3 pontos de acurácia a menos respectivamente, e ~12×
mais rápido que o Qwen3-8B. Para cascata, é a escolha óbvia. *(06/10: a linha
QH_THINK=0 do §6.28.9 retoma essa leitura — com thinking desligado o Qwen3-8B fica ainda
mais barato que o Coder (16,4) mas paga 7,3 p.p. de acurácia.)*

### 6.28.8 Qwen3-8B `QH_REPS=3` — o mais preciso E o menos variável da bateria

**Qwen3-8B Q4_K_M, CPU (ngl=0), 14 threads, 4096 ctx, `QH_REPS=3`** — 150 execuções, 93m52s:

```
por_rep       : [0.9800, 0.9800, 0.9800]   (49/50, 49/50, 49/50)
media         : 0.9800                     sd = 0,0000
IC95          : [0.98, 0.98]  ->  [98%, 98%]
geracao       : 41628 tok   prefill: 3000 tok
283,2 tok GERADOS/acerto      (legado: 303,6)
truncados     : 3   backend_errors: 0
por_categoria : code 54/57 | math 66/66 | extract 27/27
```

**O resultado inverte a intuição do §6.28.7.** Qwen3-8B não é apenas o mais preciso
(98% > R1 92% > Coder 88,7%) — é também o de **menor variância observada**: `sd = 0`
entre as 3 reps, as três deram **exatamente 49/50**. R1, o vice-campeão, tem `sd = 0,0346`.
**Ressalva (06/10):** `sd=0` amostral com n=3 **não é** variância zero de verdade — é o
menor valor que 3 repetições idênticas podem produzir, e o IC t de Student com 2 g.l. é
largo. O que se pode afirmar honestamente: *não houve variação observada entre as 3 reps*,
não "o modelo é determinístico" nem "o IC é um ponto real". As tarefas desta bateria têm
resposta curta e temperature 0.2, o que **favorece** repetibilidade — não a prova.

**Os 3 não-acertos são TODOS a MESMA tarefa (`c6`), truncada nas 3 reps** — não são
respostas erradas, são respostas que não couberam no teto de 1200 tok. Removendo
truncamentos: **147/147 = 100% do que foi pontuado**. Qwen3-8B é o **único modelo da
bateria que nunca errou uma resposta pontuável** (com max_tokens=1200).

**`math` 66/66 e `extract` 27/27 perfeitos.** Isso REFINA o achado do §6.28.7 ("todo
modelo que raciocina falha em extract"). Qwen3 é um modelo com modo de raciocínio, e
mesmo assim fez extract 27/27. **A regra anterior estava forte demais:** o que separa
o R1 (extract 17/27) e o LFM (5/27) do Qwen3 (27/27) não é "raciocinar", é **manter o
formato de saída depois de raciocinar**. Qwen3 raciocina e ainda entrega JSON limpo;
R1 raciocina e despeja o raciocínio no lugar do formato. `extract` continua sendo o
eixo mais discriminante, mas o mecanismo é **controle de formato pós-reasoning**, não
a presença de reasoning.

**Custo:** 283,2 tok/acerto é caro (15,6× o Coder-7B) porque o Qwen3 gasta muito em
tokens de raciocínio antes de responder — mas o teto de 1200 tok **truncou `c6`** e
provavelmente inflou a contagem dos demais. Num perfil de produção com thinking
desligado (como os `QH_THINK=0` já medidos em outros modelos), esses 283 cairiam muito.
**Isso é o próximo experimento óbvio** (`QH_THINK=0` no Qwen3-8B), e não muda o veredito
de acurácia: 98% com sd=0. *(→ o §6.28.9 mede exatamente esse perfil.)*

**Nota de incidente:** a primeira tentativa desta medição foi **abortada pelo próprio
harness** quando o `llama-server` morreu silenciosamente no meio da rep 0 (morte nativa,
log sem erro; 63/150 tarefas; registro gravado com `"ABORTADO": true`). O harness recusou
pontuar um falso 0/9 — comportamento fail-closed correto. Re-rodado com wrapper de retry
(`E:\rotor_tmp\run_qwen3_reps3.sh`); a tentativa 1 da re-execução completou limpa.

### 6.28.9 Qwen3-8B `QH_THINK=0` `QH_REPS=3` — o reasoning só pagava em math

**Qwen3-8B Q4_K_M, CPU (ngl=0), 14 threads, 4096 ctx, `QH_REPS=3`, `QH_THINK=0`**
(→ `chat_template_kwargs={"enable_thinking": false}`; `"thinking": "0"` no JSONL) —
150 execuções; **tempo de execução das tarefas 388,3 s** (o wall da campanha foi 13m51s
e inclui boot do servidor, prefill e overhead do wrapper — **não** usar como medida de
speedup; não houve amostragem de regime do host *durante* a corrida). Tentativa 1 limpa.
Wrapper derivado 1:1 do do §6.28.8 (`E:\rotor_tmp\run_qwen3_reps3_thinkoff.sh`), com
snapshot de regime do host antes de cada tentativa: **QUIET, oversub 0,300** (preflight —
fora do bench o modo "during" exige `bench_share>=60` p/ QUIET e reportaria MINOR_LOAD
esporio). O snapshot é **pré-voo**: não caracteriza o regime ao longo das 150 execuções.

```
por_rep       : [0.9000, 0.9200, 0.9000]   (45/50, 46/50, 45/50)
media         : 0.9067
IC95          : [0.878, 0.9354]  ->  [88%, 94%]
geracao       : 2234 tok    prefill: 4611 tok
16,4 tok GERADOS/acerto       (legado: 50,3)
truncados     : 0   backend_errors: 0
por_categoria : code 57/57 | math 52/66 | extract 27/27
```

**Resposta à pergunta do §6.28.8: a posição de custo do Qwen3-8B era CONFIGURAÇÃO, não
destino.** Com thinking desligado (sucessos: 147 → 136; **−11 acertos pontuáveis**):

| eixo | think ON (§6.28.8) | think OFF (esta seção) | delta |
|---|---:|---:|---:|
| acurácia | 98,0% (sd=0) | 90,67% | **−7,3 p.p.** |
| acertos pontuáveis | 147/150 | 136/150 | **−11** |
| tok GERADOS/acerto | 283,2 | **16,4** | **17,3× menos** (métrica de trabalho de geração) |
| tempo de execução | — (não medido igual) | 388,3 s | **não comparável** (wall ≠ tempo de tarefa) |
| code | 54/57 (c6 truncado ×3) | **57/57** | +3, sem truncamento |
| math | 66/66 | 52/66 | **−14** |
| extract | 27/27 | 27/27 | 0 |

**O inverso por categoria é o achado central.** Desligar o reasoning **CONSERTOU o
code** (`c6` — a tarefa truncada nas 3 reps com thinking — passa agora com 82 tok,
4/4 casos) e **QUEBROU o math**: os 14 acertos perdidos são TODOS math (16 perdidos −
2 ganhos em code... na conta por categoria: math 52 vs 66 = −14; code 57 vs 54 = +3;
soma −11). O reasoning do Qwen3-8B não é enfeite: é **carga estrutural do math** — e em
code ele era anti-econômico no teto de 1200 tok (verbosidade → truncamento → erro).

**Estrutura dos erros: padrão repetido, não prova de determinismo.** 4 tarefas falham
nas 3 reps com a MESMA resposta errada (`m4`: 18≠2; `m11`: 175≠325; `m14`: 48≠56;
`m22`: 180≠100), todas `finish_reason=stop` com 3–9 tok de completamento — falha de
raciocínio genuína, não truncamento nem ruído. `m15` (30≠42) é o único elemento
estocástico: erra nas reps 0 e 2, acerta na rep 1. **Cuidado:** a mesma resposta errada
em 3 reps é **falha estável observada**, não prova de `sd=0` em tarefas novas — com 3
reps o IC é largo e não mede a variância real do modelo.

**Decisão prática (substitui a leitura única do §6.28.7/§6.28.8):**
- **Acurácia crítica** → Qwen3-8B com thinking ON: 98%, sd=0, único modelo que nunca
  errou resposta pontuável. Paga 283,2 tok/acerto.
- **Custo crítico** → Qwen3-8B com thinking OFF: **16,4 tok/acerto, o MENOR da bateria
  inteira** (abaixo do Coder-7B, 18,2), a 90,7% de acurácia. O modelo é o mesmo; é a
  config de serving que escolhe o ponto da curva custo×acurácia.
- **Meio-termo** → Coder-7B segue dominando o meio (88,7% a 18,2, 8min) e é o que menos
  exige decisão de config.

**Hipótese que este par de medições abre (a ser VALIDADA, não afirmada):** as
categorias são complementares — ON ganha em math, OFF ganha em code, empata em extract.
A combinação retroativa (ON em math + OFF em code/extract) daria 150/150 **nas mesmas 50
tarefas**, mas isso é **post-hoc e não é resultado medido**: é o desenho de um
experimento, não a conclusão dele. Validar com regra de roteamento congelada, bateria
held-out nova e medição pareada — ver o plano em
`evidence/PLANO_ROTEAMENTO_THINKING_20261006.md`.

**Regras de comparação respeitadas:** o custo 16,4 NÃO é somado às linhas default da
tabela do §6.28.7 sem o rótulo `(QH_THINK=0)` explícito — mudou o regime de saída
(`thinking: 0` gravado no JSONL), e comparar sem rótulo seria o erro de proveniência
que o §6.28.8 já antevia.

---

## Ferramentas de medição (estado atual)

| Script | Função |
|---|---|
| `agi/quality_harness.py` | bateria de qualidade, checkpoint por tarefa, `QH_OUT` configurável, `nthreads` por arg |
| `scripts/report_quality.py` | consolida ranking + audita o efeito da correção do verificador |
| `scripts/bench_via_server.py` | pp/tg via llama-server + **VRAM real** via WMI |
| `agi/router.py` | `MODEL_TABLE` + `suggest_model` guiados por medição |
| `scripts/segmented_download.py` | download em 16 segmentos |
| `scripts/gguf_llama4_to_llama.py` | cirurgia de header GGUF |
| `scratch/regime_probe.py` | **regime do host por amostra** (oversub, busy_cores, free_physical, contaminantes) |
| `scratch/thread_sweep_gated.py` | varredura de threads que **recusa** rodar em `CONTAMINATED` |
| `scratch/recompute_all_from_logs.py` | recalcula a bateria inteira a partir dos logs, com verificação |
| `scratch/validate_tasks.py` | **valida os gabaritos** da bateria (referência roda nos próprios casos) |
| `scratch/fa_sweep.py` | `-fa` na métrica certa: `pp` em 512 e 2048, `-r 5` |

**Suíte de testes do Layer 1: 46 + 13 + 17 + 23 = 99 verde.**

### 6.28.10 Roteamento seletivo de thinking — C ganha dos dois regimes fixos

Primeira medição **na bateria HELD-OUT** (150 tarefas novas × 1 rep, nunca vistas
pela regra de roteamento): `agi/heldout_tasks.py`. Três braços, MESMA bateria, o que
torna a comparação pareada. Host gate **concorrente** (§7 do plano): os três braços
rodaram em regime **CONTAMINATED** (oversub médio 1,15–1,24), portanto comparáveis
entre si — mas nenhum em QUIET, e o custo absoluto deve ser lido com essa ressalva.

| braço | acurácia | tok GERADOS/acerto | tempo tarefas | math | code | extract |
|---|---:|---:|---:|---|---|---|
| **A — sempre ON** | 94,6% | 288,5 | 5280 s | 65/66 | 55/57 | 21/27 |
| **B — sempre OFF** | 83,3% | **19,2** | **399 s** | 45/66 | **57/57** | 23/27 |
| **C — seletivo** | **96,7%** | 107,2 | 2005 s | **65/66** | **57/57** | 23/27 |

**Critério pré-registrado (plano §6) — todos passam:**
1. `C ≥ A` em acurácia? 96,67% ≥ 94,60% → **sim**
2. `C ≥ B` em acurácia? 96,67% ≥ 83,30% → **sim**
3. `C ≤ 50%` dos tok de A? 107,2 / 288,5 = **37,2%** → **sim**

**→ SUCESSO.** C supera o **melhor braço fixo** em **+2,1 p.p.** (96,7% vs 94,6%) com
**37% dos tokens** de A. É o **melhor em acurácia E melhor em custo do que A**.

**Decomposição — C não é apenas "meio termo", é composição ótima.** C pegou o melhor
de cada braço por construção: `math 65/66` (igual a A, +20 sobre B) e `code 57/57`
(igual a B, +2 sobre A). A `extract` ficou em 23/27, **igual a B** — e não os 21/27 de A.

**Achado colateral forte: o `extract` NÃO é neutro ao thinking.** A regra roteia
extract para OFF (arquivo `think_router.py`), e B/C dão 23/27, enquanto A (ON) dá
21/27. Ou seja: nesta bateria **thinking custa 2 tarefas de extract**. Isto **refina o
§6.28.8**, que dizia "extract empata nos dois regimes" — na bateria ORIGINAL empatava
(27/27); na HELD-OUT o thinking atrapalha. Mais um motivo para OFF em extract.

**Replicação do eixo math na bateria nova:** OFF perdeu **20** tarefas de math
(45/66 vs 65/66) — efeito MAIOR que os 14 medidos na bateria original, e agora com
66 tarefas reais em vez de 22 × 3 reps. O achado do §6.28.9 é sólido.

**CUSTO DO ROTEAMENTO (o que o plano §6 pediu para contabilizar):** a regra
`agi/think_router.py` é **regex puro, sem modelo** — zero tokens, zero tempo de rede.
O custo do roteamento é **0**; os 107,2 tok/acerto de C são todos do modelo.

**CAVEAT CRÍTICO (plano §10): a regra separa a held-out 150/150** — e isso é
**artefato do desenho** (as 150 tarefas foram escritas com marcadores limpos). Então
C mede o **melhor caso** do roteamento. A comparação pareada A/B/C é válida; a
generalização para prompts reais **NÃO está medida**. Rodada 2 precisa de bateria com
categoria embutida/ambígua.

**Artefatos:** `evidence/bench/routing_arm{A,B,C}_20261006.json`, runner
`scratch/run_routing_arm.py`, regra `agi/think_router.py`, plano + caveat em
`evidence/PLANO_ROTEAMENTO_THINKING_20261006.md`.

> **COLD-AUDIT CORRECTION — 2026-10-06: §6.28.11 below is superseded historical narrative.** The authoritative §6.28.11 cold-audit addendum at the end retracts the26/29 claim, model-mental explanations, controlled-latency inference, and imported manifest-bump requirement. Raw historical evidence remains unchanged. Exact original bytes are preserved in `.pre_coldreview_20261006`. Current audit status: **BLOCKED_PENDING_REPAIRS_AND_CODE_ISOLATION**; no new benchmark score or total-project certification.

### 6.28.11 ⚠️ RODADA 2 (bateria adversarial) — REBAIXA o §6.28.10 de "SUCESSO" para "melhor caso de desenho"

A rodada 2 respondeu a pergunta que o §6.28.10 deixou aberta: *"e quando a
categoria está EMBUTIDA atrás de formato, em vez de legível no prompt?"*
Bateria nova de **29 tarefas adversariais** (`agi/round2_tasks.py`), 5 classes
construídas para atacar o ponto cego da regra. Previsões **pré-registradas** antes
de rodar (plano §12).

**Achado estrutural:** a regra congelada manda **27 das 29 tarefas para OFF**
(só 2 vão para ON, e são E5 controle — por acidente). Ela não é um roteador;
**é um detector de "número nu no prompt".**

| classe | n | A (ON) | B (OFF) | C (seletivo) | A vs C |
|---|---:|---:|---:|---:|---|
| E1 code_com_calculo | 8 | 7/8 | **8/8** | **8/8** | A < C |
| E2 extract_com_calculo | 6 | **6/6** | 4/6 | 4/6 | **A > C** |
| E3 math_disfarcado | 6 | **6/6** | 5/6 | 5/6 | **A > C** |
| E4 code_disfarcado | 3 | **3/3** | 2/3 | 2/3 | **A > C** |
| E5 controle | 6 | 6/6 | 6/6 | 6/6 | empate |
| **total** | **29** | **28 (96,6%)** | 25 (86,2%) | 25 (86,2%) | |

Custo: A 317,0 tok/acerto | B 23,3 | C 30,8. Truncados: A 1, B 0, C 0.
Host: os três braços em **CONTAMINATED** (oversub médio 1,07–1,17).

**C ≡ B, tarefa por tarefa.** Nas 27 tarefas que C roteia para OFF, **0
divergências** de acerto/erro contra o braço B. C é o "sempre OFF" com verniz de
roteador.

**Previsões pré-registradas:** P1 (A > C em E3) **CONFIRMADA**; P2 (E1/E2 em
aberto) medida — E1 **C ≥ A**, E2 **A > C**; P3 (E4 empata) **REFUTADA** (A 3/3 vs
C 2/3); P4 (E5 não regride) **CONFIRMADA**. A P3 refutada é informativa: E4
*parece* código mas **é** raciocínio (proporcionalidade inversa), então "OFF é bom
para código" não protege. O eixo real não é "código vs não-código", é
**"precisa deduzir uma relação?"**.

**Análise das falhas.** A (1 falha): `r2_c03` **truncado** no teto de 1200 tok
(`reasoning_len=4442`) — hiperverbosidade, não incompreensão. B/C (3 falhas
reais): `r2_e06` média com denominador errado (16 vs 17); `r2_m06` fração
invertida (360 vs 300); `r2_d02` **proporcionalidade inversa** (24 vs 6 — 8
operários levam *menos* dias, mas multiplicou). Sem rascunho, os erros são
escorregões de um passo e relações invertidas — exatamente o que o thinking compra.

**REBAIXAMENTO (compromisso do plano §12 cumprido):** o §6.28.10 mediu o melhor
caso numa bateria que a regra separa **150/150 por construção**. Na rodada 2, com
o sinal embutido atrás de formato, a regra **erra 4 das 23 tarefas que roteia para
OFF (17%)** que o braço sempre-ON acerta. Os dois resultados são compatíveis e se
leem juntos: rodada 1 = *"com sinal limpo, rotear economiza 63% de tokens sem
perder acurácia"* (sim); rodada 2 = *"com sinal sujo, a regra colapsa para
sempre-OFF e perde acurácia"*. **Veredito combinado: o roteador atual NÃO está
pronto.**

**BUG DE INSTRUMENTO achado nesta rodada (`_v_json`, plano §13):** o checker
compara **string**, não número — `{"preco_final": 2800.0}` é marcado errado contra
gabarito `2800`, apesar de numericamente idêntico. O gabarito da rodada 2 tem
8/8 tarefas de extract com chave `int`, então o bug **pune exatamente os braços que
respondem número cru (B/C) e absolve A**. Impacto: 2 falsos negativos confirmados
(`r2_e01` em B e em C) → B e C são na verdade **26/29 = 89,7%**, não 86,2%. A
vantagem de A encolhe de 10,4 p.p. para 6,9 p.p. Correção exige bump do
`FROZEN_EVAL_MANIFEST.json` + rerun limpo.

**Artefatos:** `evidence/bench/routing_arm{A,B,C}_20261006.json` (+ backups
`routing_r2_arm*`), tabela `scratch/round2_class_table.py`, bateria
`agi/round2_tasks.py`, validador `agi/validate_round2.py`, plano §12–§14 em
`evidence/PLANO_ROTEAMENTO_THINKING_20261006.md`.

