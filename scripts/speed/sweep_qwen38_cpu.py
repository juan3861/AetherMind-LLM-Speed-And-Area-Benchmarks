"""Varredura de flags CPU para o Qwen3.8-9B-Heretic.

Objetivo: achar a config de MENOR latencia (maior tok/s) antes de decidir qual
quantizacao entra no campeonato. Usa llama-bench (carga sintetica) porque e
muito mais barato que o harness completo e isola exatamente o que queremos
medir: throughput de prompt (pp) e de geracao (tg).

Dimensoes varridas:
  - threads          : 14 (fisicos) / 20 / 28 (logicos)
  - flash-attn       : off / on
  - cache KV quantizado: f16 / q8_0
  - batch de prompt  : padrao / 1024

Cada config roda n_gen=128, n_pp=512, reps=2.
"""
import json
import re
import subprocess
import sys
import time

BENCH = r"F:\tools\lc_b10749\llama-bench.exe"
MODELS = {
    "q8_0": r"F:\data\models\Qwen3.8-9B-Distill-Heretic-Uncensored-Q8_0.gguf",
    "iq4_xs": r"F:\data\models\Qwen3.8-9B-Heretic-IQ4_XS.gguf",
    "q4_k_m": r"F:\data\models\Qwen3.8-9B-Heretic-Q4_K_M.gguf",
}

BASE = ["-ngl", "0", "-n", "128", "-p", "512", "-r", "2"]

CONFIGS = [
    ("t14_base",        ["-t", "14"]),
    ("t20",             ["-t", "20"]),
    ("t28",             ["-t", "28"]),
    ("t14_fa",          ["-t", "14", "-fa", "1"]),
    ("t14_kvq8",        ["-t", "14", "-ctk", "q8_0", "-ctv", "q8_0"]),
    ("t20_fa_kvq8",     ["-t", "20", "-fa", "1", "-ctk", "q8_0", "-ctv", "q8_0"]),
    ("t14_ub512",       ["-t", "14", "-ub", "512"]),
]


# Fase 2: achado da fase 1 foi que MAIS threads PIORA a geracao (memoria
# bandwidth-bound: 14t=4.00 vs 20t=2.99 vs 28t=2.31 tok/s). Entao a fase 2
# explora a vizinhanca de 14 threads em vez de subir.
CONFIGS_FOCUSED = [
    ("t14_plain",       ["-t", "14"]),
    ("t14_fa",          ["-t", "14", "-fa", "1"]),
    ("t14_ub512",       ["-t", "14", "-ub", "512"]),
    ("t14_ub512_fa",    ["-t", "14", "-ub", "512", "-fa", "1"]),
    ("t14_fa_kvq8",     ["-t", "14", "-fa", "1", "-ctk", "q8_0", "-ctv", "q8_0"]),
    ("t12_fa",          ["-t", "12", "-fa", "1"]),
    ("t16_fa",          ["-t", "16", "-fa", "1"]),
]


def run(model_path, label, extra):
    cmd = [BENCH, "-m", model_path] + BASE + extra
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return {"label": label, "error": "timeout", "elapsed_s": time.time() - t0}
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
    return {
        "label": label,
        "args": " ".join(extra),
        "tg_tok_s": tg,
        "pp_tok_s": pp,
        "elapsed_s": round(time.time() - t0, 1),
        "raw_tail": out[-400:],
    }


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "q8_0"
    focused = len(sys.argv) > 2 and sys.argv[2] == "focused"
    path = MODELS[which]
    cfg = CONFIGS_FOCUSED if focused else CONFIGS
    print(f"modelo: {path}  (fase={'focused' if focused else 'completa'})", flush=True)
    results = []
    for label, extra in cfg:
        print(f"\n--- {label}: {' '.join(extra)}", flush=True)
        r = run(path, label, extra)
        print(f"    tg={r.get('tg_tok_s')} pp={r.get('pp_tok_s')} "
              f"({r.get('elapsed_s')}s)", flush=True)
        results.append(r)
    out = f"F:/rotor-llm/scratch/sweep_{which}{'_focused' if focused else ''}.json"
    with open(out, "w") as f:
        json.dump({"model": which, "path": path, "results": results}, f, indent=2)

    ok = [r for r in results if r.get("tg_tok_s")]
    ok.sort(key=lambda r: -r["tg_tok_s"])
    print("\n===== RANKING (tok/s geracao) =====", flush=True)
    for r in ok:
        print(f"  {r['tg_tok_s']:6.2f}  {r['label']:<14} {r['args']}", flush=True)
    print(f"\nJSON: {out}", flush=True)


if __name__ == "__main__":
    main()
