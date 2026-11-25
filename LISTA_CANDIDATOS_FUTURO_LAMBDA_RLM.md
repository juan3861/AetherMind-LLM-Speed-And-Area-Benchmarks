# Candidatos de Alto Desempenho para Reteste em Lambda-RLM

Modelos que já alcançaram alto índice no modo Zero-Shot puro (sem Lambda-RLM) e têm potencial latente de saltar de patamar com autorreparo cognitivo:

| Categoria | Modelo | Quant | Tam (GB) | 13 Áreas | 10 Opus | Velocidade | Potencial Estimado com Lambda |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 3. Leves (1.0B – 1.7B) | **Qwen2.5-1.5B-Claude** | Q8_0 | 1.53 | 31/39 | 0/10 | 19.74 t/s | ➔ 34/39 e 2/10 Opus |
| 4. Camada Média Compacta (2B – 4.5B) | **Gemma4-E4B-Opus** | F16 | 14.02 | 35/39 | 0/10 | 5.17 t/s | ➔ 38/39 e 2/10 Opus |
| 5. Médios (7B – 9B) | **Qwen3.8-9B-Heretic-IQ4_XS** | Q4_K_M | 4.99 | 33/39 | 1/10 | 7.02 t/s | ➔ 36/39 e 3/10 Opus |
| 5. Médios (7B – 9B) | **Poe-8B-Crownelius-Grok-Heretic** | Q4_K_M | 4.68 | 18/39 | 2/10 | 8.16 t/s | ➔ 21/39 e 4/10 Opus |
| 5. Médios (7B – 9B) | **empero-Qwable-9B-Claude-Fable-5** | Q4_K_M | 5.24 | 36/39 | 0/10 | 4.00 t/s | ➔ 39/39 e 2/10 Opus |
| 6. Pesados Densos (12B – 14B) | **Qwen3-14B-GPT-5.2-High-Reasoning-Distill** | Q4_K_M | 8.38 | 33/39 | 1/10 | 4.78 t/s | ➔ 36/39 e 3/10 Opus |
| 8. Super Titãs (30B – 35B+) | **Qwen3-30B-A3B-Thinking-Sonnet.i1-IQ3_M** | IQ3_M | 12.59 | 30/39 | 5/10 | 6.82 t/s | ➔ 33/39 e 7/10 Opus |
| 8. Super Titãs (30B – 35B+) | **Qwen3-30B-A3B-Thinking-Sonnet.i1-IQ4_XS** | IQ4_XS | 15.24 | 30/39 | 4/10 | 11.34 t/s | ➔ 33/39 e 6/10 Opus |
