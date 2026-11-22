import subprocess
import time
import json
import urllib.request

cmd = [
    r"F:\tools\lc_b10749\llama-server.exe",
    "-m", r"F:\data\models\Qwen3.8-27B-UD-IQ3_XXS.gguf",
    "-md", r"F:\data\models\mtp-Qwen3.8-27B-Q4_0.gguf",
    "--spec-type", "draft-mtp",
    "--spec-draft-n-max", "4",
    "--port", "8086",
    "--host", "127.0.0.1",
    "--threads", "8",
    "--ctx-size", "2048",
    "--no-repack"
]

print("[1] Iniciando llama-server b10749 para 27B + MTP...")
proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

ready = False
for i in range(30):
    time.sleep(2)
    try:
        req = urllib.request.Request("http://127.0.0.1:8086/health")
        with urllib.request.urlopen(req, timeout=1) as resp:
            if resp.status == 200:
                ready = True
                print(f"[2] Servidor pronto aos {i*2}s!")
                break
    except Exception:
        pass

if ready:
    prompt = "Escreva tres vantagens da energia solar fotovoltaica em tópicos curtos."
    data = json.dumps({
        "prompt": prompt,
        "n_predict": 60,
        "temperature": 0.2
    }).encode()
    req = urllib.request.Request("http://127.0.0.1:8086/completion", data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        res = json.loads(resp.read().decode())
        dt = time.time() - t0
        print("\n[RESULTADO 27B + MTP]")
        print("Resposta:\n", res.get("content"))
        timings = res.get("timings", {})
        print("\n--- TIMINGS ---")
        print(f"Tokens preditos: {timings.get('predicted_n', 0)}")
        print(f"Velocidade de geracao: {timings.get('predicted_per_second', 0):.2f} tok/s")
        print(f"Tempo total: {dt:.2f}s")

proc.terminate()
try:
    proc.wait(timeout=5)
except Exception:
    proc.kill()
print("\n[FIM DO TESTE]")
