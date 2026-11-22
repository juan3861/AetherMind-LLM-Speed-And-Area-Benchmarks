"""Sweep de flags CPU para Gemma 4 E2B e DeepSeek-Coder 1.3B.

Contexto: GPU em HARD LOCK (2 incidentes de travamento), entao tudo aqui e CPU
pura (-ngl 0). Objetivo do Mestre:ACHAR A MAIOR VELOCIDADE DE TOKENS e ter um
comparativo honesto.

Por que reusa o desenho do sweep_qwen38_cpu.py:
  - llama-bench (carga sintetica) e muito mais barato que o harness completo e
    isola exatamente o que queremos medir: throughput de prompt (pp) e geracao (tg).
  - Xeon E5-2697 v3 = 14 fisicos / 28 logicos. O sweep anterior ja provou que
    MAIS threads PIORA a geracao (14t=4.00 vs 20t=2.99 vs 28t=2.31 tok/s) porque
    geracao de token e memory-bandwidth-bound. Entao aqui a dimensao principal
    NAO e "sobe threads", e: flash-attn, KV cache quantizado e tamanho de batch.
  - Cuidado metodologico: rodar configs em ordem Fixa e sem repetir o melhor
    candidato. A fase final RE-RODA o melhor repetidamente para medir variancia
    real (o desvio nao pode ser ruido de maquina - ver docstring do Mestre).

Nao usa a GPU em nenhuma config. Nao toca no HARD LOCK.
"""
import json
import re
import subprocess
import sys
import time

BENCH = r"F:\tools\lc_b10749\llama-bench.exe"

MODELS = {
    "gemma4":  r"E:\models\gguf\gemma-4-E2B-it-IQ4_XS.gguf",
    "dscoder": r"E:\models\gguf\deepseek-coder-1.3b-instruct-Q4_K_M.gguf",
}

# n_gen alto o bastante para a geracao dominar (tg), n_pp para o prefill (pp).
BASE = ["-ngl", "0", "-n", "128", "-p", "512", "-r", "2"]

# Fase 1: vizinhanca do optimum conhecido (14t) + as dimensoes que importam.
CONFIGS = [
    ("t14_plain",     ["-t", "14"]),
    ("t14_fa",        ["-t", "14", "-fa", "1"]),
    ("t14_fa_kvq8",   ["-t", "14", "-fa", "1", "-ctk", "q8_0", "-ctv", "q8_0"]),
    ("t14_fa_ub512",  ["-t", "14", "-fa", "1", "-ub", "512"]),
    ("t12_fa",        ["-t", "12", "-fa", "1"]),
    ("t16_fa",        ["-t", "16", "-fa", "1"]),
    ("t10_fa",        ["-t", "10", "-fa", "1"]),
    ("t28_fa",        ["-t", "28", "-fa", "1"]),
]


def parse(out):
    """Extrai (pp, tg) do formato de tabela do llama-bench."""
    rows = {}
    for line in out.splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 7:
            continue
        test = cells[5]
        m = re.search(r"([\d.]+)\s*±\s*([\d.]+)", cells[6])
        if not m:
            continue
        val, err = float(m.group(1)), float(m.group(2))
        if test.startswith("pp"):
            rows["pp"] = (val, err)
        elif test.startswith("tg"):
            rows["tg"] = (val, err)
    return rows


def run(model_path, label, extra, reps=2, timeout=3600):
    cmd = [BENCH, "-m", model_path] + BASE[:-1] + ["-r", str(reps)] + extra
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return {"label": label, "error": "timeout", "elapsed_s": round(time.time() - t0, 1)}
    r = parse(out)
    if "tg" not in r:
        return {
            "label": label, "args": " ".join(extra), "error": "sem tg",
            "elapsed_s": round(time.time() - t0, 1),
            "raw_tail": out[-700:],
        }
    return {
        "label": label,
        "args": " ".join(extra),
        "tg_tok_s": r["tg"][0], "tg_err": r["tg"][1],
        "pp_tok_s": r.get("pp", (None, None))[0], "pp_err": r.get("pp", (None, None))[1],
        "elapsed_s": round(time.time() - t0, 1),
    }


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "gemma4"
    if which not in MODELS:
        print(f"modelo invalido: {which} (use gemma4 ou dscoder)")
        return 2
    path = MODELS[which]

    import os
    if not os.path.exists(path):
        print(f"ERRO: modelo nao encontrado: {path}")
        return 2

    print(f"modelo : {path}")
    print(f"configs: {len(CONFIGS)} | base={BASE} | GPU OFF (hard lock)")
    results = []
    for label, extra in CONFIGS:
        print(f"\n--- {label}: {' '.join(extra)}", flush=True)
        r = run(path, label, extra)
        if r.get("tg_tok_s"):
            print(f"    tg={r['tg_tok_s']:6.2f} +/-{r['tg_err']:.2f}  "
                  f"pp={r['pp_tok_s']}  ({r['elapsed_s']}s)", flush=True)
        else:
            print(f"    FALHOU: {r.get('error')} | {r.get('raw_tail','')[-200:]}", flush=True)
        results.append(r)

    ok = [r for r in results if r.get("tg_tok_s")]
    ok.sort(key=lambda r: -r["tg_tok_s"])

    out = f"F:/rotor-llm/scratch/sweep_cpu_{which}.json"
    with open(out, "w") as f:
        json.dump({"model": which, "path": path, "base": BASE,
                   "results": results, "ranking": ok}, f, indent=2)

    print("\n===== RANKING (tok/s de geracao, CPU pura) =====", flush=True)
    for r in ok:
        print(f"  {r['tg_tok_s']:6.2f} +/- {r['tg_err']:4.2f}   {r['label']:<14} {r['args']}")
    print(f"\nJSON: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
