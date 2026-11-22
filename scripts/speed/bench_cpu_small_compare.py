"""Comparativo CPU puro dos modelos pequenos do cpu_bench (ROTOR).

Objetivo do Mestre: saber a MAIOR velocidade de geracao (tok/s) de cada modelo
na CPU, para comparativo. GPU esta sob HARD LOCK, entao -ngl 0 sempre.

Metodologia: llama-bench (carga sintetica), varredura de threads 7 / 14 / 28
(14 = fisicos, melhor no sweep anterior do Qwen3.8-9B; 7 e 28 para confirmar
se modelos pequenos, menos bandwidth-bound, preferem outra config).

Cada config: pp512, tg128, reps=3. Vence o maior tg.

Uso:
  python bench_cpu_small_compare.py            # roda tudo que existir
  python bench_cpu_small_compare.py deepseek   # roda so um modelo (substring)
"""
import json
import os
import re
import subprocess
import sys
import time

BENCH = r"F:\tools\lc_b10749\llama-bench.exe"
DIR = r"E:\models\gguf\cpu_bench"

MODELS = [
    ("smollm2-360m",  "SmolLM2-360M-Instruct-Q4_K_M.gguf"),
    ("qwen25-0.5b",   "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"),
    ("qwen25-1.5b",   "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"),
    ("smollm2-1.7b",  "SmolLM2-1.7B-Instruct-Q4_K_M.gguf"),
    ("deepseek-1.3b", "deepseek-coder-1.3b-instruct-Q4_K_M.gguf"),
    ("llama32-1b",    "Llama-3.2-1B-Instruct-Q4_K_M.gguf"),
    ("gemma4-e2b",    "gemma-4-E2B-it-IQ4_XS.gguf"),
    ("qwen3-0.6b",    "Qwen3-0.6B-Q4_K_M.gguf"),
    ("qwen35-0.8b",   "Qwen3.5-0.8B-Q4_K_M.gguf"),
    ("gemma3-1b",     "gemma-3-1b-it-Q4_K_M.gguf"),
    ("qwen3-1.7b",    "Qwen3-1.7B-Q4_K_M.gguf"),
    ("granite4-micro","granite-4.0-micro-Q4_K_M.gguf"),
    ("bitnet-2b",     "BitNet-b1.58-2B4T-i2_s.gguf"),
    ("lfm2-1.2b",     "LFM2-1.2B-Q4_K_M.gguf"),
    ("minicpm4-0.5b", "MiniCPM4-0.5B-Q4_K_M.gguf"),
    ("falconh1-1.5b", "Falcon-H1-1.5B-Q4_K_M.gguf"),
    # --- rodada 3 (2026-10-01): MiniCPM5 (sucessor do campeao) + reasoners ---
    ("minicpm5-1b",   "MiniCPM5-1B-Q4_K_M.gguf"),
    ("minicpm5-2b",   "MiniCPM5-2B-Q4_K_M.gguf"),
    ("nemotron-r1.5b","nvidia_OpenReasoning-Nemotron-1.5B-Q4_K_M.gguf"),
    ("mobilellm-r15-950m", "mobilellm-r1.5-950m-q4_k_m.gguf"),
]

# HOST ATUAL (01/10 pos-reboot): 7 fisicos / 14 logicos. NAO e o host
# original de 14/28 do ranking round-2 — numeros so comparaveis DENTRO desta
# sessao, com as ancoras medidas junto. 28t aqui = oversubscribe 2x, fora.
THREADS = ["7", "14"]
REPS = "3"
NGEN = "128"
NPP = "512"


def run(model_path, threads):
    cmd = [BENCH, "-m", model_path, "-ngl", "0", "-p", NPP, "-n", NGEN,
           "-r", REPS, "-t", threads]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=2400)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return {"threads": threads, "error": "timeout",
                "elapsed_s": round(time.time() - t0, 1)}
    tg = pp = None
    m = re.search(r"^\s*tg\d+\s+.*?([\d.]+)\s*±", out, re.M)
    if m:
        tg = float(m.group(1))
    m2 = re.search(r"^\s*pp\d+\s+.*?([\d.]+)\s*±", out, re.M)
    if m2:
        pp = float(m2.group(1))
    if tg is None:
        nums = re.findall(r"([\d.]+)\s*±\s*([\d.]+)", out)
        if len(nums) >= 2:
            pp, tg = float(nums[0][0]), float(nums[1][0])
        elif nums:
            tg = float(nums[0][0])
    err = None
    if tg is None:
        err = out[-300:].replace("\n", " | ")
    return {"threads": threads, "tg_tok_s": tg, "pp_tok_s": pp,
            "elapsed_s": round(time.time() - t0, 1), "error": err}


def main():
    os.makedirs(r"F:\rotor-llm\scratch", exist_ok=True)
    # multiplos filtros separados por virgula; vazio = roda tudo
    wants = ([w.strip() for w in sys.argv[1].split(",")]
             if len(sys.argv) > 1 and sys.argv[1].strip() else [])
    results = {}
    for key, fname in MODELS:
        if wants and not any(w in key for w in wants):
            continue
        path = os.path.join(DIR, fname)
        if not os.path.exists(path):
            print(f"SKIP {key}: arquivo ausente ({fname})", flush=True)
            results[key] = {"missing": fname}
            continue
        print(f"\n===== {key} ({fname}) =====", flush=True)
        runs = []
        for t in THREADS:
            r = run(path, t)
            runs.append(r)
            print(f"  t={t:>2}  tg={r.get('tg_tok_s')}  pp={r.get('pp_tok_s')}"
                  f"  ({r.get('elapsed_s')}s)"
                  f"{'  ERRO: ' + r['error'] if r.get('error') else ''}",
                  flush=True)
            if r.get("error"):
                break  # arquitetura nao suportada etc: nao insiste
        best = max((r for r in runs if r.get("tg_tok_s")),
                   key=lambda r: r["tg_tok_s"], default=None)
        results[key] = {"file": fname, "runs": runs,
                        "best_tg": best["tg_tok_s"] if best else None,
                        "best_tg_threads": best["threads"] if best else None,
                        "best_pp": best["pp_tok_s"] if best else None}
        if best:
            print(f"  >> MELHOR: tg {best['tg_tok_s']} tok/s com {best['threads']} threads",
                  flush=True)

    # r3 = rodada 3 (01/10, host 7C/14T pos-reboot). NAO sobrescreve o JSON do
    # round-2 (host 14C/28T original) — comparacoes entre rodadas sao invalidas.
    out = r"F:\rotor-llm\scratch\bench_cpu_r3.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n========== RANKING FINAL (maior tg tok/s, CPU puro) ==========",
          flush=True)
    rank = [(k, v["best_tg"], v.get("best_tg_threads"), v.get("best_pp"))
            for k, v in results.items() if isinstance(v, dict) and v.get("best_tg")]
    rank.sort(key=lambda x: -x[1])
    for k, tg, t, pp in rank:
        print(f"  {tg:8.2f} tok/s  (pp {pp:8.2f})  t={t:<3} {k}", flush=True)
    print(f"\nJSON: {out}", flush=True)


if __name__ == "__main__":
    main()
