import os
import sys
import time
import json
import subprocess
import urllib.request

LLAMA_SERVER = r"F:\tools\lc_b10749\llama-server.exe"
PORT = 8085
HOST = "127.0.0.1"
BASE_URL = f"http://{HOST}:{PORT}"
MODEL = r"F:\data\models\Qwen3.8-27B-UD-IQ3_XXS.gguf"
PROMPT = "Escreva uma explicacao clara sobre redes neurais e processamento de linguagem natural."

def wait_for_server(timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{BASE_URL}/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
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
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    wall_time = time.time() - start_t
    timings = data.get("timings", {})
    tok_per_sec = timings.get("predicted_per_second", 0)
    tokens = timings.get("predicted_n", 0)
    if tok_per_sec == 0 and tokens > 0 and wall_time > 0:
        tok_per_sec = tokens / wall_time
    return round(tok_per_sec, 2)

def benchmark(spec_type, draft_max, threads):
    cmd = [
        LLAMA_SERVER,
        "-m", MODEL,
        "--host", HOST,
        "--port", str(PORT),
        "--threads", str(threads),
        "--ctx-size", "2048",
        "--no-repack"
    ]
    if spec_type:
        cmd.extend(["--spec-type", spec_type])
    if draft_max:
        cmd.extend(["--spec-draft-n-max", str(draft_max)])

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not wait_for_server(60):
        print("Erro ao subir servidor")
        proc.kill()
        return None

    # warmup
    try: query_completion("teste", 10)
    except: pass

    runs = []
    for _ in range(3):
        try:
            s = query_completion(PROMPT, 60)
            runs.append(s)
        except Exception as e:
            print("Erro req:", e)

    proc.terminate()
    try: proc.wait(5)
    except: proc.kill()
    time.sleep(1)

    avg = round(sum(runs) / len(runs), 2) if runs else 0
    max_s = max(runs) if runs else 0
    return {"spec_type": spec_type or "OFF", "draft": draft_max or 0, "threads": threads, "avg": avg, "max": max_s, "runs": runs}

if __name__ == "__main__":
    results = []
    print("Testando IQ3_XXS Sem MTP...")
    r1 = benchmark(None, None, 14)
    print("Sem MTP:", r1)
    results.append(r1)

    print("Testando IQ3_XXS Com MTP Draft 3 (12 threads)...")
    r2 = benchmark("draft-mtp", 3, 12)
    print("Draft 3 (12t):", r2)
    results.append(r2)

    print("Testando IQ3_XXS Com MTP Draft 4 (8 threads)...")
    r3 = benchmark("draft-mtp", 4, 8)
    print("Draft 4 (8t):", r3)
    results.append(r3)

    with open(r"F:\data\models\iq3xxs_bench.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Concluido!")
