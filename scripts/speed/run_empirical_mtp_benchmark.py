import os
import sys
import time
import json
import subprocess
import urllib.request
import urllib.error

LLAMA_SERVER = r"F:\tools\lc_b10749\llama-server.exe"
PORT = 8085
HOST = "127.0.0.1"
BASE_URL = f"http://{HOST}:{PORT}"
LOG_FILE = r"F:\data\models\benchmark_live.log"

PROMPT = "Escreva uma explicacao clara e estruturada sobre como funciona a arquitetura Transformer e o mecanismo de atencao em modelos de linguagem."

def log(msg):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {msg}\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

def wait_for_server(timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{BASE_URL}/health")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False

def query_completion(prompt, n_predict=60):
    payload = json.dumps({
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": 0.2,
        "stream": False
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/completion",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    start_t = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    wall_time = time.time() - start_t
    timings = data.get("timings", {})
    tok_per_sec = timings.get("predicted_per_second", 0)
    prompt_per_sec = timings.get("prompt_per_second", 0)
    tokens = timings.get("predicted_n", 0)
    if tok_per_sec == 0 and tokens > 0 and wall_time > 0:
        tok_per_sec = tokens / wall_time
    return {
        "tokens": tokens,
        "tok_per_sec": round(tok_per_sec, 2),
        "prompt_per_sec": round(prompt_per_sec, 2),
        "wall_time": round(wall_time, 2)
    }

def run_single_benchmark(model_path, spec_type, draft_max, threads, ctx_size=2048, runs=3):
    cmd = [
        LLAMA_SERVER,
        "-m", model_path,
        "--host", HOST,
        "--port", str(PORT),
        "--threads", str(threads),
        "--ctx-size", str(ctx_size),
        "--no-repack"
    ]
    if spec_type:
        cmd.extend(["--spec-type", spec_type])
    if draft_max:
        cmd.extend(["--spec-draft-n-max", str(draft_max)])

    desc = f"Model={os.path.basename(model_path)} | MTP={spec_type or 'OFF'} | Draft={draft_max or 0} | Threads={threads}"
    log(f"========================================================")
    log(f"Iniciando Teste: {desc}")
    log(f"Comando: {' '.join(cmd)}")
    log(f"========================================================")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    ready = wait_for_server(timeout=90)
    if not ready:
        log("ERRO: Servidor nao respondeu no healthcheck dentro do prazo.")
        proc.kill()
        return None

    log("Servidor pronto! Aquecendo e executando passes de benchmark...")
    # Warmup pass
    try:
        query_completion("Ola, teste rapido.", n_predict=10)
    except Exception as e:
        log(f"Aviso warmup: {e}")

    results = []
    for i in range(1, runs + 1):
        try:
            res = query_completion(PROMPT, n_predict=80)
            log(f"  [Passo {i}/{runs}] {res['tokens']} tokens em {res['wall_time']}s -> {res['tok_per_sec']} tok/s (Prompt eval: {res['prompt_per_sec']} t/s)")
            results.append(res["tok_per_sec"])
        except Exception as e:
            log(f"  [Passo {i}/{runs}] Erro na requisicao: {e}")

    # Terminar processo
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
    time.sleep(2)

    if results:
        avg = round(sum(results) / len(results), 2)
        max_speed = max(results)
        log(f"-> RESULTADO: MEDIA = {avg} tok/s | MAXIMO = {max_speed} tok/s")
        return {
            "desc": desc,
            "spec_type": spec_type or "OFF",
            "draft_max": draft_max or 0,
            "threads": threads,
            "avg_tok_s": avg,
            "max_tok_s": max_speed,
            "runs": results
        }
    return None

if __name__ == "__main__":
    # Limpa log anterior
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")

    test_suite = [
        # Testes no Qwen 3.6 35B MoE (A3B)
        {
            "model": r"F:\data\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf",
            "cases": [
                {"spec_type": None, "draft_max": None, "threads": 14},
                {"spec_type": "draft-mtp", "draft_max": 2, "threads": 14},
                {"spec_type": "draft-mtp", "draft_max": 3, "threads": 14},
                {"spec_type": "draft-mtp", "draft_max": 4, "threads": 14},
                {"spec_type": "draft-mtp", "draft_max": 5, "threads": 14},
                {"spec_type": "draft-mtp", "draft_max": 6, "threads": 14},
                # Threads tuning com draft 4
                {"spec_type": "draft-mtp", "draft_max": 4, "threads": 12},
                {"spec_type": "draft-mtp", "draft_max": 4, "threads": 8},
            ]
        },
        # Testes no Qwen 3.8 27B Denso (IQ4_XS)
        {
            "model": r"F:\data\models\Qwen3.8-27B-UD-IQ4_XS.gguf",
            "cases": [
                {"spec_type": None, "draft_max": None, "threads": 14},
                {"spec_type": "draft-mtp", "draft_max": 3, "threads": 14},
                {"spec_type": "draft-mtp", "draft_max": 4, "threads": 14},
                {"spec_type": "draft-mtp", "draft_max": 5, "threads": 14},
                {"spec_type": "draft-mtp", "draft_max": 6, "threads": 14},
                # Threads tuning
                {"spec_type": "draft-mtp", "draft_max": 4, "threads": 12},
                {"spec_type": "draft-mtp", "draft_max": 4, "threads": 8},
            ]
        },
        # Testes no Qwen 3.8 27B Denso (Q3_K_XL)
        {
            "model": r"F:\data\models\Qwen3.8-27B-UD-Q3_K_XL.gguf",
            "cases": [
                {"spec_type": None, "draft_max": None, "threads": 14},
                {"spec_type": "draft-mtp", "draft_max": 4, "threads": 14},
                {"spec_type": "draft-mtp", "draft_max": 5, "threads": 14},
            ]
        }
    ]

    all_results = []
    report_file = r"F:\data\models\relatorio_benchmark_mtp.json"

    for suite in test_suite:
        model_path = suite["model"]
        if not os.path.exists(model_path):
            log(f"Modelo nao encontrado: {model_path}, pulando...")
            continue
        model_name = os.path.basename(model_path)
        log(f"=================================================================")
        log(f"INICIANDO BATERIA DE BENCHMARKS PARA MODELO: {model_name}")
        log(f"=================================================================")
        for c in suite["cases"]:
            res = run_single_benchmark(
                model_path=model_path,
                spec_type=c["spec_type"],
                draft_max=c["draft_max"],
                threads=c["threads"],
                ctx_size=2048,
                runs=3
            )
            if res:
                res["model"] = model_name
                all_results.append(res)
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(all_results, f, indent=2)

    log("TODOS OS TESTES CONCLUIDOS COM SUCESSO!")
    log(f"Relatorio salvo em: {report_file}")
