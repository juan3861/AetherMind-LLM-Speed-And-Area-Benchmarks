"""Comparativo de REASONERS peso-mosca em CPU pura (ROTOR, 2026-10-01).

Pergunta do Mestre: "qual modelo peso mosca PENSA melhor?"

tok/s NAO responde isso. Um modelo que pensa 500 tokens e acerta vence um que
pensa 5000 tokens e tambem acerta - na CPU isso e a diferenca entre 20s e 3min.
Entao medimos por (modelo, problema):

  1. acerto            - a resposta final esta certa?
  2. thinking_tokens   - quanto o modelo gastou "pensando" (reasoning_content)
  3. tok_por_acerto    - METRICA-REI: tokens de saida gastos por acerto
  4. wall_s            - latencia real na maquina
  5. bateu_teto        - over-thinking: finish_reason == "length" (nao terminou)

ARQUITETURA (importante):
  Este script NAO sobe o llama-server. Ele CONECTA num servidor ja no ar.
  Motivo: neste ambiente o sandbox mata filhos de subprocess.Popen (SIGTERM),
  entao o servidor precisa ser lancado fora do processo, em background.
  Fluxo: subir servidor (bash, run_in_background) -> rodar este script ->
  derrubar o servidor.

  POST /v1/chat/completions foi escolhido em vez de llama-cli porque separa
  `reasoning_content` de `content` em campos proprios e devolve `usage` +
  `timings` estruturados -> zero parsing fragil de stdout. (O flag -st do
  llama-cli ainda quebra neste build b10749.)

  Proxy: o proxy local desta maquina intercepta ate 127.0.0.1, entao TODAS as
  chamadas usam ProxyHandler({}) - mesma razao do segmented_download.py.

HARD LOCK respeitado: o servidor e sempre lancerado com -ngl 0.

Uso:
  python bench_reasoners_cpu.py --port 8099 --label qwen3-0.6b
"""
import argparse
import json
import os
import re
import time
import urllib.request

OUT_DIR = r"F:\rotor-llm\scratch"
SEED = 1234


# 8 problemas com resposta final DETERMINISTICA e verificavel por regex.
# Mix proposital: aritmetica multi-passo, armadilha de enunciado, logica formal.
PROBLEMS = [
    {
        "id": "marbles",
        "q": ("Ana has 3 times as many marbles as Bruno. Together they have 84 "
              "marbles. Carla has 7 fewer marbles than Bruno. How many marbles "
              "does Carla have?"),
        "answer": "14",
        "re": r"\b14\b",
    },
    {
        "id": "carwash",
        "q": ("I want to wash my car. The car wash is 50 meters away from my "
              "house. Should I walk to the car wash or drive there?"),
        "answer": "drive",
        "re": r"\bdriv\w*\b",
        "neg": r"\bwalk\w*\b",
    },
    {
        "id": "machine",
        "q": ("A machine produces 5 parts every 3 minutes. At this rate, how "
              "many parts does it produce in 2 hours?"),
        "answer": "200",
        "re": r"\b200\b",
    },
    {
        "id": "div35",
        "q": ("How many integers between 1 and 100 inclusive are divisible by 3 "
              "but NOT divisible by 5?"),
        "answer": "27",
        "re": r"\b27\b",
    },
    {
        "id": "fatherson",
        "q": ("A father is 4 times as old as his son. In 20 years, the father "
              "will be twice as old as his son. How old is the son now?"),
        "answer": "10",
        "re": r"\b10\b",
    },
    {
        "id": "pricedrop",
        "q": ("A product's price first increases by 20%, and then decreases by "
              "20%. What is the net percentage change in price?"),
        "answer": "-4%",
        "re": r"(-\s*4\s*%|4\s*%\s*(decreas|lower|drop|reduc)|"
              r"(decreas|lower|drop|reduc)\w*\s*(by\s*)?4\s*%)",
    },
    {
        "id": "sequence",
        "q": ("What is the next number in this sequence: 2, 6, 12, 20, 30, ?"),
        "answer": "42",
        "re": r"\b42\b",
    },
    {
        "id": "syllogism",
        "q": ("All Bloops are Razzies. Some Razzies are Lazzies. Does it "
              "necessarily follow that all Bloops are Lazzies? Answer yes or no."),
        "answer": "no",
        "re": r"\bno\b",
        "neg": r"\byes\b",
    },
]


def http_json(url, payload=None, timeout=3600):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data else "GET")
    # ProxyHandler({}) = sem proxy. O proxy local intercepta 127.0.0.1 e
    # devolve "upstream connect failed" (erro 10061).
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def grade(prob, content):
    """Acerta se o padrao positivo aparece no texto FINAL e o negativo nao.

    A negacao so conta na resposta final: o modelo pode citar 'walk' no meio do
    raciocinio enquanto descarta a hipotese errada.
    """
    tail = content[-800:] if len(content) > 800 else content
    hits = [m.start() for m in re.finditer(prob["re"], tail, flags=re.I)]
    if not hits:
        return False
    if prob.get("neg"):
        negs = [m.start() for m in re.finditer(prob["neg"], tail, flags=re.I)]
        if negs and max(negs) > max(hits):
            return False
    return True


def ask(base, prob, maxnew, temp):
    payload = {
        "messages": [{"role": "user", "content": prob["q"]}],
        "max_tokens": int(maxnew),
        "temperature": float(temp),
        "top_p": 0.95 if temp > 0 else 1.0,
        "seed": SEED,
        "stream": False,
    }
    t0 = time.time()
    r = http_json(f"{base}/v1/chat/completions", payload)
    wall = time.time() - t0
    ch = (r.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    return {
        "content": msg.get("content") or "",
        "reasoning": msg.get("reasoning_content") or "",
        "finish_reason": ch.get("finish_reason"),
        "usage": r.get("usage") or {},
        "timings": r.get("timings") or {},
        "wall_s": round(wall, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--label", default="")
    ap.add_argument("--maxnew", type=int, default=4096)
    ap.add_argument("--budget", type=int, default=2048)
    ap.add_argument("--temps", default="0.6")
    args = ap.parse_args()

    base = f"http://127.0.0.1:{args.port}"
    try:
        props = http_json(f"{base}/props", timeout=10)
        srv_model = os.path.basename(props.get("model_path", "?"))
    except Exception as e:
        print(f"FALHA: sem servidor em {base} ({e}).", flush=True)
        print("Suba antes:  llama-server -m <gguf> -ngl 0 -t 14 -c 8192 "
              f"--jinja --reasoning on --reasoning-budget {args.budget} "
              f"--host 127.0.0.1 --port {args.port} --no-webui -np 1",
              flush=True)
        return 1

    label = args.label or srv_model
    temps = [float(t) for t in args.temps.split(",")]
    print(f"===== {label} | servidor={srv_model} | budget={args.budget} "
          f"maxnew={args.maxnew} temps={temps} =====", flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []
    for prob in PROBLEMS:
        for temp in temps:
            try:
                r = ask(base, prob, args.maxnew, temp)
            except Exception as e:
                print(f"  [{prob['id']:10}|T{temp}] ERRO: {e}", flush=True)
                rows.append({"prob_id": prob["id"], "temp": temp, "ok": False,
                             "error": str(e)})
                continue
            think_tok = max(0, round(len(r["reasoning"]) / 4))
            gen_tok = r["usage"].get("completion_tokens") or 0
            ok = grade(prob, r["content"])
            r.update(prob_id=prob["id"], expected=prob["answer"], temp=temp,
                     ok=ok, think_tokens_est=think_tok, gen_tokens=gen_tok,
                     hit_cap=(r["finish_reason"] == "length"))
            rows.append(r)
            print(f"  [{prob['id']:10}|T{temp}] {'OK ' if ok else 'X  '} "
                  f"esp={prob['answer']:<5} think~{think_tok:5}t "
                  f"gen={gen_tok:5}t "
                  f"tg={(r['timings'].get('predicted_per_second') or 0):5.1f} "
                  f"{r['wall_s']:6.1f}s"
                  f"{'  <CAP>' if r['hit_cap'] else ''}", flush=True)

    n_ok = sum(1 for r in rows if r.get("ok"))
    n_tok = sum(r.get("gen_tokens") or 0 for r in rows)
    n_think = sum(r.get("think_tokens_est") or 0 for r in rows)
    total = len(rows)
    summary = {
        "label": label, "server_model": srv_model,
        "budget": args.budget, "maxnew": args.maxnew, "temps": temps,
        "acertos": n_ok, "total": total,
        "acc_pct": round(100.0 * n_ok / total, 1) if total else None,
        "gen_tokens_total": n_tok,
        "think_tokens_total_est": n_think,
        "tokens_por_acerto": round(n_tok / n_ok) if n_ok else None,
        "wall_total_s": round(sum(r.get("wall_s") or 0 for r in rows), 1),
        "rows": rows,
    }
    print(f"\n  >> {n_ok}/{total} acertos | {n_tok} tok gerados | "
          f"~{n_think} tok pensados | {summary['tokens_por_acerto']} tok/acerto "
          f"| {summary['wall_total_s']}s", flush=True)

    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", label)
    out = os.path.join(OUT_DIR, f"reasoners_{safe}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"JSON: {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())