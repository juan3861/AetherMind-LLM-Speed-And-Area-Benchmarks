import time
import json
import urllib.request

url = "http://127.0.0.1:8083/v1/chat/completions"

prompt = "Escreva uma explicacao clara e objetiva sobre como funciona a arquitetura de Mistura de Especialistas (MoE) em redes neurais."

payload = {
    "model": "gpt-oss-20b-Q4_K_M.gguf",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 200,
    "temperature": 0.2
}

print("=" * 70)
print("TESTADOR DE VELOCIDADE — GPT-OSS 20B (:8083)")
print(f"Prompt: '{prompt}'")
print("Aguardando geracao...")
print("=" * 70)

t0 = time.time()
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        elapsed = time.time() - t0
        data = json.loads(resp.read().decode("utf-8"))
        choice = data["choices"][0]["message"]
        content = choice.get("content") or choice.get("reasoning_content") or ""
        usage = data.get("usage", {})
        comp_tokens = usage.get("completion_tokens", 0)
        timings = data.get("timings", {})
        tok_s = timings.get("predicted_per_second", (comp_tokens / elapsed) if elapsed > 0 else 0)

        print("\n>>> RESPOSTA GERADA:")
        print(content.strip())
        print("\n" + "=" * 70)
        print(f"Tempo total:        {elapsed:.2f} segundos")
        print(f"Tokens gerados:     {comp_tokens} tokens")
        print(f"VELOCIDADE REAL:    {tok_s:.2f} tokens/segundo (tok/s)")
        print("=" * 70)
except Exception as e:
    print("Erro ao conectar:", e)
    print("Verifique se o servidor 'iniciar_gpt_20b.bat' ja terminou de carregar na porta 8083.")
