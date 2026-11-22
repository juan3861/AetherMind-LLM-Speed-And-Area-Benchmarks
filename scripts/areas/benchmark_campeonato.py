"""CAMPEONATO DE MODELOS PEQUENOS - Harness forense (Fase 1.4 do Plano Mestre).

Mede os 3 novatos do Campeonato + o incumbente do slot de codigo, todos nas MESMAS
condicoes, para adjudicar os duelos com prova empirica e zero teatro tecnico.

Modelos-alvo:
  - MiniCPM5-2B-Q4_K_M            (novato, candidato a L0/L1 universal)
  - granite-4.2-3b-Q4_K_M         (novato, adversario direto do MiniCPM5)
  - qwen2.5-coder-1.5b            (novato, especialista codigo ultraleve)
  - granite-3.1-2b-instruct       (INCUMBENTE do slot codigo/tools - necessario p/ duelo justo)

Metricas exigidas pelo plano mestre:
  TTFT | tok/s geracao | RAM Peak RSS | JSON/Schema adherence | Tool selection accuracy
  | Instruction following (PT) | Coding/debug | Matematica simples | % resolvido sem escalacao

DECISOES METODOLOGICAS DELIBERADAS (registradas para reprodutibilidade):

1. CPU PURA (-ngl 0) em todos os quatro. Os numeros canonicos do registro (Ring-mini
   20.82, Granite-3.1-2B 17.5, GPT-OSS 13.10 tok/s) sao de inferencia em CPU. Misturar
   offload na RX 580 so para alguns modelos quebraria a comparabilidade do duelo. Se o
   vencedor quiser GPU depois, isso e uma medicao separada, nao um retroajuste.

2. --jinja aplicado uniformemente. Os tres novatos vendem tool-use / modos de
   raciocinio que so existem dentro do proprio chat template. Sem --jinja o servidor
   impoe um template generico e o teste mediria o template, nao o modelo. Se o boot com
   --jinja falhar, ha fallback automatico e o fato fica registrado no campo "jinja".

3. Cold start E steady state, os dois. O duelo Official vs UD provou que a distincao
   importa mais que o numero absoluto (o MTP regrediu em cold e venceu em hot). Portanto:
     - cold: load_time + TTFT + tok/s da primeira requisicao (comparavel ao registro)
     - steady: mediana de 3 geracoes com o servidor ja aquecido (keep-alive)
   A REGRA DE OURO (>= 7,0 tok/s) e decidida pelo steady state, que e a realidade
   operacional do Rotor. O cold start e reportado como diagnostico.

4. RAM Peak por AMOSTRAGEM CONTINUA (thread a cada 100 ms) e nao por leitura pontual
   antes/depois. O script antigo lia o RSS apos a resposta e perdia o pico de mmap.

5. Codigo do modelo é EXECUTADO, nao comparado por string. Um teste de codificacao
   que so checa semelhanca textual e teatro. Aqui o codigo extraido roda num subprocesso
   com sandbox (denylist de importacao e timeout) e o grade é a assercao passando.

6. "Resolvido sem escalacao" = proporcao das 10 sondas funcionais que passam INTEGRAS
   na PRIMEIRA tentativa, sem retry. Em benchmark de modelo unico nao ha router para
   escalar; a traducao honesta do conceito e "primeira resposta ja é correta e bem
   formada". Definicao fixada aqui para nao virar metrica elastica depois.

7. temperature=0.0 e seed fixa em tudo. Cada sonda roda 2 vezes para expor
   nondeterminismo residual de threading; divergencias sao reportadas, nao escondidas.

8. finish_mode EXPLICITO por modelo, verificado por calibracao. O diag_probe_raw provou
   que MiniCPM5-2B é um modelo de raciocinio: com --jinja o template nativo emite
   reasoning_content ANTES de content, e as sondas de teto baixo (16..96 tokens) viam o
   orcamento ser consumido pelo pensamento -- finish_reason=length, content vazio, 8/10
   FAIL. Isso era defeito do harness, nao do modelo. Correlato medido nos proprios
   GGUF: granite-4.2-3b expoe enable_thinking (default True) e reasoning_effort no
   template (toggle real, acionavel via --chat-template-kwargs); MiniCPM5 nao expoe
   variavel nenhuma (preso em reasoning, so cabe subir o teto); qwen2.5-coder-1.5b e
   granite-3.1-2b sao instruct puros. Cada entrada de MODELS declara agora finish_mode +
   template_kwargs + thinking_budget, e _verify_mode confere na pele se o modo valeu:
   modo declarado que nao pega vira MODE_VIOLATION no JSON, nunca no-op silencioso.

9. TRUNCAMENTO NAO E CONTESTACAO. Sonda que estoura o teto de tokens nao mediu
   capacidade, mediu orcamento. O harness escala o teto (4x, cap 2048) e re-tenta antes
   de julgar; se ainda assim truncar, a sonda sai do DENOMINADOR e é reportada a parte
   como inutilizavel. Punir um modelo por pensar demais com orçamento curto é fabricar
   numero -- e o "resolvido sem escalacao" passa a ter denominador explícito no JSON.

Uso:
  python benchmark_campeonato.py                 # todos os 4 modelos
  python benchmark_campeonato.py --only qwen25coder15b   # smoke test de 1 modelo
  python benchmark_campeonato.py --quick         # menos repeticoes de latencia
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

# Console UTF-8: o download_campeonato.py morreu exatamente aqui (cp1252 nao codifica
# glifos). Forcar UTF-8 com replace blinda o harness contra o mesmo modo de falha.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import psutil
except ImportError:
    psutil = None

LLAMA_SERVER = r"F:\tools\lc_b10749\llama-server.exe"
PORT = 11499
BASE_URL = f"http://127.0.0.1:{PORT}"
SCRATCH = Path(r"F:/rotor-llm/scratch")
OUT_FILE = Path(r"F:/rotor-llm/BENCHMARK_CAMPEONATO_RESULTS.json")

GOLDEN_RULE_TOK_S = 7.0
THREADS = "14"          # nucleos fisicos do E5-2697 v3, uniforme
CTX_SIZE = "4096"       # escopo: tarefas agenticas curtas, nao teste de contexto longo
TEMPERATURE = 0.0
SEED = 42

# finish_mode: como o modelo DEVE fechar o turno durante a bateria.
#   "direct"   -> sem raciocinio visivel; content sai direto. Esperado: reasoning_len == 0.
#   "reasoning" -> o template emite reasoning_content antes de content. O teto de tokens
#                 precisa cobrir pensamento + resposta, senao a sonda so mede orcamento.
# template_kwargs: variaveis injetadas no chat template via --chat-template-kwargs.
# thinking_budget: tokens extras somados a TODO sonda quando finish_mode == "reasoning".
# Verificado por calibracao em _verify_mode(); declaracao que nao pega vira MODE_VIOLATION.
MODELS = [
    {
        "id": "minicpm5_2b",
        "name": "MiniCPM5-2B Q4_K_M",
        "path": r"F:\data\models\MiniCPM5-2B-Q4_K_M.gguf",
        "role_under_test": "L0/L1 universal (duelo A)",
        "extra_args": [],
        # Template de 9060 chars com reasoning_content embutido e NENHUMA variavel de
        # toggle (nenhum enable_thinking). Preso em modo raciocinio: a unica alavanca
        # honesta e subir o teto de tokens. Nao fingir que da para desligar.
        "finish_mode": "reasoning",
        "template_kwargs": {},
        "thinking_budget": 512,
    },
    {
        "id": "granite42_3b",
        "name": "Granite 4.2-3B Q4_K_M",
        "path": r"F:\data\models\granite-4.2-3b-Q4_K_M.gguf",
        "role_under_test": "L0/L1 universal (duelo A)",
        "extra_args": [],
        # Template expoe enable_thinking (default True) e reasoning_effort. Medimos o
        # modelo no modo OPERACIONAL do Rotor: thinking desligado para sondas de
        # formato/latencia (direct). O custo do thinking é medido a parte, nao misturado.
        "finish_mode": "direct",
        "template_kwargs": {"enable_thinking": False, "reasoning_effort": "low"},
        "thinking_budget": 0,
    },
    {
        "id": "qwen25coder15b",
        "name": "Qwen2.5-Coder-1.5B Instruct Q4_K_M",
        "path": r"F:\data\models\qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        "role_under_test": "slot codigo (duelo B)",
        "extra_args": [],
        # Template de 2509 chars, zero vars de raciocinio. Instruct puro.
        "finish_mode": "direct",
        "template_kwargs": {},
        "thinking_budget": 0,
    },
    {
        "id": "granite31_2b",
        "name": "Granite-3.1-2B Instruct Q4_K_M (INCUMBENTE)",
        "path": r"F:\data\models\granite-3.1-2b-instruct-Q4_K_M.gguf",
        "role_under_test": "slot codigo/tools (baseline do duelo B)",
        "extra_args": [],
        # Template de 3224 chars, zero vars de raciocinio. Instruct puro (baseline).
        "finish_mode": "direct",
        "template_kwargs": {},
        "thinking_budget": 0,
    },
    {
        "id": "qwen34b_rlm",
        "name": "Qwen3-4B-Instruct-2507-RLM-SFT-v3-per-root-turn Q4_K_M",
        "path": r"F:/data/models/Qwen3-4B-Instruct-2507-RLM-SFT-v3-per-root-turn--.Q4_K_M.gguf",
        "role_under_test": "L0/L1 universal (duelo C)",
        "extra_args": [],
        "finish_mode": "direct",
        "template_kwargs": {},
        "thinking_budget": 0,
    },
    {
        "id": "qwen38_9b_heretic",
        "name": "Qwen3.8-9B-Distill-Heretic-Uncensored Q8_0",
        "path": r"F:/data/models/Qwen3.8-9B-Distill-Heretic-Uncensored-Q8_0.gguf",
        "role_under_test": "L1 universal grande (novato)",
        "extra_args": [],
        # Template (7756 chars) expoe enable_thinking (default True), reasoning_content
        # e tools. Medimos no modo OPERACIONAL do Rotor: thinking DESLIGADO, para nao
        # misturar custo de raciocinio com aderencia de formato/latencia.
        "finish_mode": "direct",
        "template_kwargs": {"enable_thinking": False},
        "thinking_budget": 0,
    },
    {
        "id": "rlm8b_q4km",
        "name": "RLM-Qwen3-8B-v0.1 Q4_K_M",
        "path": r"F:/data/models/rlm-qwen3-8b-v0.1-q4_k_m.gguf",
        "role_under_test": "L1 RLM/REPL recursivo (novato)",
        "extra_args": [],
        # ATENCAO: este GGUF NAO traz tokenizer.chat_template. O llama.cpp aplica o
        # template padrao do arch qwen3 (ChatML). O benchmark registra o fallback no
        # campo "jinja" quando ocorre, para nao fingir que medimos o template do autor.
        "finish_mode": "direct",
        "template_kwargs": {},
        "thinking_budget": 0,
    },
    {
        # Config OTIMIZADA achada pela varredura llama-bench (scratch/sweep_iq4_xs_focused.json):
        # t14_fa venceu com 7.20 tok/s tg (vs 7.09 base). A varredura tambem provou que
        # MAIS threads PIORA a geracao (t20=2.99, t28=2.31 no Q8_0: bandwidth-bound) e
        # que -ub 512 ajuda no Q8_0 (4.36) mas DESTROI o IQ4_XS (5.73).
        "id": "qwen38_9b_heretic_iq4xs",
        "name": "Qwen3.8-9B-Distill-Heretic-Uncensored IQ4_XS (otimizado)",
        "path": r"F:/data/models/Qwen3.8-9B-Heretic-IQ4_XS.gguf",
        "role_under_test": "L1 universal grande (novato, quant otimizada p/ Regra de Ouro)",
        "extra_args": ["-fa", "1"],
        "finish_mode": "direct",
        "template_kwargs": {"enable_thinking": False},
        "thinking_budget": 0,
    },
    {
        # Config GPU: RX 580 via Vulkan (build lc_vulkan 10819). Entrada AUTORIZADA
        # pelo Mestre com protocolo incremental (ngl 5/15/30/45/60/99 - estavel ate o
        # plato, llama-bench pp512=142.92 / tg128=14.56). NAO e o mesmo binario do
        # CPU-only: o build b10749 nao tem backend Vulkan. Se o driver voltar a
        # instabilizar, este e o unico alvo a remover da rota.
        "id": "qwen38_9b_heretic_iq4xs_gpu",
        "name": "Qwen3.8-9B-Distill-Heretic-Uncensored IQ4_XS (RX 580, offload total)",
        "path": r"F:/data/models/Qwen3.8-9B-Heretic-IQ4_XS.gguf",
        "role_under_test": "L1 universal grande (rota GPU Vulkan)",
        "extra_args": ["-fa", "1"],
        "server": r"F:\tools\lc_vulkan\llama-server.exe",
        "ngl": "99",
        "finish_mode": "direct",
        "template_kwargs": {"enable_thinking": False},
        "thinking_budget": 0,
    },
]


# --------------------------------------------------------------------------
# Infra: amostragem de pico de RAM, boot do servidor, chamada chat
# --------------------------------------------------------------------------
class PeakSampler:
    """Amostra RSS continuamente durante toda a vida do processo."""

    def __init__(self, pid, interval=0.1):
        self.pid = pid
        self.interval = interval
        self.peak = 0.0
        self._stop = threading.Event()
        self._thread = None

    def _loop(self):
        if psutil is None:
            return
        try:
            proc = psutil.Process(self.pid)
        except Exception:
            return
        while not self._stop.is_set():
            try:
                rss = proc.memory_info().rss / (1024 * 1024)
                if rss > self.peak:
                    self.peak = rss
            except Exception:
                return
            time.sleep(self.interval)

    def __enter__(self):
        if psutil is not None:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        return False


def wait_ready(timeout_s=180):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=2) as r:
                if r.status in (200, 204):
                    return True
        except Exception:
            pass
        time.sleep(1.0)
    return False


def template_kwargs_args(kw):
    """Constroi o par --chat-template-kwargs '<json>' a partir do dict do modelo.

    Passado como UM elemento de argv (subprocess com lista, sem shell) -- portanto as
    aspas do JSON nunca passam pelo Git Bash e nao ha corruptacao de escaping no Windows.
    Escopo deliberado: e SERVER-level, vale para todo o turno daquela sessao. Como cada
    modelo roda numa sessao dedicada com um unico finish_mode, isso e exatamente a
    semantica desejada; nao existe mistura de direct/reasoning na mesma sessao.
    """
    if not kw:
        return []
    return ["--chat-template-kwargs", json.dumps(kw, separators=(",", ":"))]


def boot(model_path, extra_args, log_path, server=None, ngl="0"):
    """Sobe llama-server. Padrao = CPU pura (-ngl 0, build lc_b10749).

    Override por modelo (dict cfg): cfg["server"] troca o binario (ex.: build
    lc_vulkan para testes de GPU) e cfg["ngl"] troca o offload. Sem override,
    comportamento identico ao historico do campeonato (CPU puro, b10749).
    """
    cmd = [
        server or LLAMA_SERVER,
        "-m", model_path,
        "--host", "127.0.0.1",
        "--port", str(PORT),
        "--threads", THREADS,
        "--ctx-size", CTX_SIZE,
        "-ngl", str(ngl),
        "-np", "1",
        "--prio", "-1",
        "--no-repack",
        "--seed", str(SEED),
    ] + list(extra_args)
    fh = open(log_path, "w", encoding="utf-8", errors="replace")
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=fh), fh, cmd


def chat(messages, max_tokens=96, temperature=TEMPERATURE, timeout=300):
    """Uma chamada /v1/chat/completions. Retorna dict com text, timings e error."""
    payload = {
        "model": "campeonato",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "seed": SEED,
        "stream": False,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        wall_ms = (time.perf_counter() - t0) * 1000.0
        data = json.loads(raw)
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text = msg.get("content") or ""
        # reasoning_content: campos separado que alguns templates (MiniCPM5, Granite 4.2)
        # preenchem ANTES do content. Capturado sempre, mesmo quando o modo e direct --
        # e assim que _verify_mode detecta um reasoning vazando apesar do toggle.
        reasoning = msg.get("reasoning_content") or ""
        usage = data.get("usage") or {}
        timings = data.get("timings") or {}
        return {
            "ok": True,
            "text": text,
            "reasoning_len": len(reasoning),
            "wall_ms": wall_ms,
            "prompt_ms": timings.get("prompt_ms"),
            "predicted_ms": timings.get("predicted_ms"),
            "prompt_tok_s": timings.get("prompt_per_second"),
            "gen_tok_s": timings.get("predicted_per_second"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "finish_reason": choice.get("finish_reason"),
        }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return {"ok": False, "error": f"HTTP {e.code}: {body}",
                "wall_ms": (time.perf_counter() - t0) * 1000.0}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}",
                "wall_ms": (time.perf_counter() - t0) * 1000.0}


def _looks_like_template_error(response):
    """Return whether a failed response indicates chat-template incompatibility.

    The first request is the only safe point to retry without ``--jinja``.  Keep
    this classifier narrow: transport, timeout, and generic HTTP failures must
    not silently trigger a different measurement mode.
    """
    if not isinstance(response, dict) or response.get("ok"):
        return False
    error = str(response.get("error") or "").lower()
    template_markers = (
        "chat template",
        "jinja",
        "template key",
        "template error",
        "missing template",
    )
    return any(marker in error for marker in template_markers)


# --------------------------------------------------------------------------
# Extratores e graders
# --------------------------------------------------------------------------
FENCE_RE = re.compile(r"```(?:[a-zA-Z]+)?\s*(.*?)```", re.DOTALL)


def strip_fences(text):
    m = FENCE_RE.search(text or "")
    return m.group(1).strip() if m else (text or "").strip()


def extract_json(text):
    """Extrai o primeiro objeto JSON plausivel, tolerando cercas e prosa em volta."""
    cand = strip_fences(text)
    try:
        return json.loads(cand)
    except Exception:
        pass
    start = cand.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(cand)):
        if cand[i] == "{":
            depth += 1
        elif cand[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(cand[start:i + 1])
                except Exception:
                    return None
    return None


def extract_python(text):
    """Prioriza bloco ```python; senao qualquer cerca; senao o texto nu."""
    for m in FENCE_RE.finditer(text or ""):
        body = m.group(1).strip()
        if "def " in body or "import" in body:
            return body
    return strip_fences(text)


NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def first_number(text):
    m = NUM_RE.search(strip_fences(text).replace("R$", " ").replace("\u00a0", " "))
    if not m:
        return None
    tok = m.group(0).replace(",", ".")
    try:
        return float(tok)
    except ValueError:
        return None


# Sandbox de execucao de codigo gerado: denylist explicita, sem rede, com timeout.
DENY_RE = re.compile(
    r"(^|\W)(import\s+(os|sys|subprocess|socket|shutil|ctypes|pathlib|requests|urllib|__future__)"
    r"|from\s+(os|sys|subprocess|socket|shutil|ctypes|pathlib|requests|urllib)\s+import"
    r"|__import__|\beval\s*\(|\bexec\s*\(|\bopen\s*\(|\bglobals\s*\(|\bgetattr\s*\("
    r"|os\.|sys\.|subprocess\.)",
    re.MULTILINE,
)


def run_python_probe(code, tests_body, timeout_s=10):
    """Executa codigo do modelo + assercoes num subprocesso isolado. Retorna (bool, detail)."""
    if not code or not code.strip():
        return False, "EMPTY_CODE"
    if DENY_RE.search(code):
        return False, "SANDBOX_DENY: codigo tentou acesso a sistema/arquivos/rede"
    if "def " not in code:
        return False, "NO_FUNCTION_DEFINIDA"

    script = code + "\n\n" + tests_body + "\nprint('PROBE_PASS')\n"
    tmpdir = tempfile.mkdtemp(prefix="campeonato_probe_")
    src = Path(tmpdir) / "probe.py"
    try:
        src.write_text(script, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-I", "-B", str(src)],
            capture_output=True, text=True, timeout=timeout_s, cwd=tmpdir,
        )
        if "PROBE_PASS" in (proc.stdout or ""):
            return True, "EXEC_OK"
        err = (proc.stderr or "").strip().splitlines()
        return False, ("EXEC_FAIL: " + (err[-1] if err else f"rc={proc.returncode}"))[:220]
    except subprocess.TimeoutExpired:
        return False, "EXEC_TIMEOUT"
    except Exception as e:
        return False, f"EXEC_ERROR: {e}"
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# --------------------------------------------------------------------------
# Baterias de sondas funcionais (10 no total)
# --------------------------------------------------------------------------
TOOLS_SPEC = (
    "Voce tem estas ferramentas:\n"
    "- get_weather(city: string)\n"
    "- search_web(query: string)\n"
    "- set_timer(duration_seconds: number, label: string)\n"
    "- send_email(to: string, subject: string, body: string)\n"
)
TOOL_JSON_RULE = (
    "Responda APENAS com um objeto JSON, sem prosa e sem close de codigo, no formato:\n"
    '{"tool": "<nome_da_ferramenta>", "args": { ... }}\n'
)


def build_probes():
    probes = []

    # --- JSON / schema adherence (2) ---
    probes.append({
        "id": "json_flat",
        "dim": "json",
        "messages": [{"role": "user", "content":
            "Extraia os dados e responda APENAS com JSON valido, sem prosa: "
            "Maria, 34 anos, engenheira, mora em Belo Horizonte. "
            'Use exatamente as chaves: nome (string), idade (inteiro), '
            "profissao (string), cidade (string)."}],
        "grade": lambda t: _grade_json_flat(t),
        "max_tokens": 96,
    })
    probes.append({
        "id": "json_nested",
        "dim": "json",
        "messages": [{"role": "user", "content":
            "Responda APENAS com JSON valido, sem prosa: a lista dos numeros pares "
            'de 1 a 10 e a soma deles. Use as chaves "pares" (lista de inteiros) '
            'e "soma" (inteiro).'}],
        "grade": lambda t: _grade_json_nested(t),
        "max_tokens": 128,
    })

    # --- Tool selection (2) ---
    probes.append({
        "id": "tool_timer",
        "dim": "tool",
        "messages": [
            {"role": "system", "content": TOOLS_SPEC + TOOL_JSON_RULE},
            {"role": "user", "content": "Me avise de tomar o remedio daqui a 30 minutos."},
        ],
        "grade": lambda t: _grade_tool(t, "set_timer", {"duration_seconds": 1800}),
        "max_tokens": 96,
    })
    probes.append({
        "id": "tool_weather",
        "dim": "tool",
        "messages": [
            {"role": "system", "content": TOOLS_SPEC + TOOL_JSON_RULE},
            {"role": "user", "content": "Esta chovendo agora em Curitiba?"},
        ],
        "grade": lambda t: _grade_tool(t, "get_weather", {"city_contains": "Curitiba"}),
        "max_tokens": 96,
    })

    # --- Instruction following PT (2) ---
    probes.append({
        "id": "instr_bullets",
        "dim": "instruction",
        "messages": [{"role": "user", "content":
            "Em portugues, explique o que faz um kernel de sistema operacional usando "
            "EXATAMENTE 3 itens em bullets, cada um comecando com '- '. "
            "Nao use blocos de codigo. Nao escreva nada antes nem depois dos bullets."}],
        "grade": lambda t: _grade_bullets(t),
        "max_tokens": 160,
    })
    probes.append({
        "id": "instr_one_word",
        "dim": "instruction",
        "messages": [{"role": "user", "content":
            "Responda com UMA unica palavra em portugues: como se diz 'server'?"}],
        "grade": lambda t: _grade_exact(t, ["servidor"]),
        "max_tokens": 16,
    })

    # --- Matematica simples (2) ---
    probes.append({
        "id": "math_discount",
        "dim": "math",
        "messages": [{"role": "user", "content":
            "Um produto custa R$ 80 e recebe 15% de desconto. Qual e o preco final? "
            "Responda apenas com o numero, sem unidades."}],
        "grade": lambda t: _grade_num(t, 68.0, tol=0.01),
        "max_tokens": 32,
    })
    probes.append({
        "id": "math_trap",
        "dim": "math",
        "messages": [{"role": "user", "content":
            "Se 5 maquinas produzem 5 pecas em 5 minutos, quantos minutos 100 maquinas "
            "levam para produzir 100 pecas? Responda apenas com o numero em minutos."}],
        "grade": lambda t: _grade_num(t, 5.0, tol=0.01),
        "max_tokens": 32,
    })

    # --- Codigo: conclusao e depuracao, ambos EXECUTADOS (2) ---
    probes.append({
        "id": "code_write",
        "dim": "coding",
        "messages": [{"role": "user", "content":
            "Escreva em Python a funcao `soma_digitos(n)` que retorna a soma dos "
            "digitos de um inteiro positivo n. Responda apenas com o codigo Python "
            "dentro de um bloco ```python```, sem explicacao."}],
        "grade": lambda t: run_python_probe(extract_python(t), (
            "assert soma_digitos(123) == 6\n"
            "assert soma_digitos(9999) == 36\n"
            "assert soma_digitos(0) == 0\n"
            "assert soma_digitos(100000) == 1\n"
        )),
        "max_tokens": 220,
    })
    buggy = (
        "def fatorial(n):\n"
        "    resultado = 0\n"
        "    for i in range(1, n):\n"
        "        resultado *= i\n"
        "    return resultado\n"
    )
    probes.append({
        "id": "code_debug",
        "dim": "coding",
        "messages": [{"role": "user", "content":
            "Esta funcao Python deveria calcular o fatorial mas esta com bugs:\n\n"
            "```python\n" + buggy + "```\n\n"
            "Corrija os bugs e responda apenas com o codigo corrigido num bloco "
            "```python```, mantendo o nome `fatorial`. Sem explicacao."}],
        "grade": lambda t: run_python_probe(extract_python(t), (
            "assert fatorial(5) == 120\n"
            "assert fatorial(0) == 1\n"
            "assert fatorial(1) == 1\n"
            "assert fatorial(7) == 5040\n"
        )),
        "max_tokens": 240,
    })
    return probes


# ---- graders especificos ----
def _grade_json_flat(text):
    j = extract_json(text)
    if not isinstance(j, dict):
        return False, "JSON_INVALIDO"
    need = {"nome": str, "idade": int, "profissao": str, "cidade": str}
    missing = [k for k in need if k not in j]
    if missing:
        return False, f"CHAVES_AUSENTES:{missing}"
    bad = [k for k, tp in need.items()
           if not (isinstance(j[k], tp) or (tp is int and isinstance(j[k], int) and not isinstance(j[k], bool)))]
    if bad:
        return False, f"TIPOS_ERRADOS:{bad}"
    ok = (str(j["nome"]).strip().lower() == "maria" and int(j["idade"]) == 34
          and "engenheira" in str(j["profissao"]).lower()
          and "belo horizonte" in str(j["cidade"]).lower())
    return (True, "OK") if ok else (False, f"VALORES_ERRADOS:{j}")


def _grade_json_nested(text):
    j = extract_json(text)
    if not isinstance(j, dict):
        return False, "JSON_INVALIDO"
    if "pares" not in j or "soma" not in j:
        return False, f"CHAVES_AUSENTES:{list(j.keys())}"
    pares = j["pares"]
    if not isinstance(pares, list) or [int(x) for x in pares] != [2, 4, 6, 8, 10]:
        return False, f"PARES_ERRADOS:{pares}"
    if int(j["soma"]) != 30:
        return False, f"SOMA_ERRADA:{j['soma']}"
    return True, "OK"


def _grade_tool(text, expected_tool, arg_checks):
    j = extract_json(text)
    if not isinstance(j, dict):
        return False, "JSON_INVALIDO"
    got = str(j.get("tool", "")).strip()
    if got != expected_tool:
        return False, f"FERRAMENTA_ERRADA:esperava={expected_tool};obtive={got}"
    args = j.get("args")
    if not isinstance(args, dict):
        return False, "ARGS_NAO_OBJETO"
    for k, v in arg_checks.items():
        if k.endswith("_contains"):
            field = k[: -len("_contains")]
            if field not in args or v.lower() not in str(args[field]).lower():
                return False, f"ARG_FAIL:{k}->{args}"
        else:
            if k not in args:
                return False, f"ARG_AUSENTE:{k}"
            try:
                if float(args[k]) != float(v):
                    return False, f"ARG_VALOR:esperava={v};obtive={args[k]}"
            except (TypeError, ValueError):
                return False, f"ARG_TIPO:{k}->{args[k]}"
    return True, "OK"


PT_MARKERS = ("kernel", "sistema", "operacional", "gerencia", "memoria", "hardware",
              "processo", "recursos", "programas", "computador", "soberano", "abstrai")


def _grade_bullets(text):
    t = (text or "").strip()
    if "```" in t:
        return False, "USOU_BLOCO_DE_CODIGO"
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    bullets = [ln for ln in lines if ln.startswith("- ")]
    if len(bullets) != 3:
        return False, f"N_BULLETS={len(bullets)} (esperado 3)"
    if len(lines) != 3:
        return False, f"PROSA_EXTRA_FORA_DOS_BULLETS:{len(lines)} linhas"
    low = t.lower()
    if not any(m in low for m in PT_MARKERS):
        return False, "SEM_MARCADOR_DE_PORTUGUES"
    return True, "OK"


def _grade_exact(text, accepted):
    t = strip_fences(text).strip().strip(".!?:;,\"'").lower()
    t = re.sub(r"\s+", " ", t)
    return (True, "OK") if t in accepted else (False, f"RESPOSTA={t[:60]!r}")


def _grade_num(text, expected, tol=0.01):
    n = first_number(text)
    if n is None:
        return False, "SEM_NUMERO"
    return (True, "OK") if abs(n - expected) <= tol else (False, f"NUMERO={n};esperado={expected}")


# --------------------------------------------------------------------------
# finish_mode: calibracao e tratamento de truncamento (reguas 8 e 9 do cabecalho)
# --------------------------------------------------------------------------
TRUNCATION_ESCALATION_FACTOR = 4
MAX_TOKENS_CAP = 2048


def _probe_budget(p, cfg):
    """Teto inicial da sonda = teto nominal + reserva para raciocinio, quando o modelo
    pensa. O nominal foi calibrado para resposta direta; aplicar o mesmo teto a um
    modelo de raciocinio seria medir o orcamento, nao o modelo."""
    base = int(p.get("max_tokens", 128))
    return min(MAX_TOKENS_CAP, base + int(cfg.get("thinking_budget", 0)))


def _verify_mode(cfg, budget_probe):
    """Audita na pele se o finish_mode declarado pegou. Um modo declarado que nao vale
    e um no-op silencioso envenena o duelo -- entao o desvio vira campo no JSON.

    - direct esperado + reasoning vazando  -> MODE_VIOLATION (o toggle nao pegou ou o
      template ignora a variavel; o numero "direct" nao existe de fato)
    - reasoning esperado + zero reasoning   -> MODE_SUSPECT (budget nao usado, ou o
      template nao emite em campo separado)
    - otherwise                            -> MODE_CONFIRMED
    """
    declared = cfg.get("finish_mode", "direct")
    rl = int((budget_probe or {}).get("reasoning_len") or 0)
    v = {
        "declared": declared,
        "template_kwargs": cfg.get("template_kwargs") or {},
        "thinking_budget": int(cfg.get("thinking_budget", 0)),
        "observed_reasoning_len": rl,
        "observed_finish_reason": (budget_probe or {}).get("finish_reason"),
    }
    if not (budget_probe or {}).get("ok"):
        v["verdict"] = "MODE_UNVERIFIED_CALL_FAILED"
    elif declared == "direct" and rl > 0:
        v["verdict"] = "MODE_VIOLATION"
    elif declared == "reasoning" and rl == 0:
        v["verdict"] = "MODE_SUSPECT_NO_REASONING"
    else:
        v["verdict"] = "MODE_CONFIRMED"
    return v


def _call_with_escalation(messages, cap):
    """Chama o endpoint subindo o teto enquanto houver truncamento.

    Retorna (resp, trace). O trace registra cada teto tentado e o que aconteceu -- a
    escalacao e transparente e auditavel, nao um retry escondido que maquiaria o numero.
    """
    trace = []
    while True:
        r = chat(messages, max_tokens=cap)
        if not r.get("ok"):
            trace.append({"max_tokens": cap, "error": str(r.get("error", ""))[:120]})
            return r, trace
        fr = r.get("finish_reason")
        trace.append({
            "max_tokens": cap,
            "finish_reason": fr,
            "reasoning_len": r.get("reasoning_len", 0),
            "content_len": len(r.get("text") or ""),
        })
        if fr == "length" and cap < MAX_TOKENS_CAP:
            cap = min(MAX_TOKENS_CAP, cap * TRUNCATION_ESCALATION_FACTOR)
            continue
        return r, trace


def run_probe(p, cfg, tries):
    """Executa uma sonda e devolve o resultado ja com a semantica de truncamento.

    finish_reason == "length" no teto maximo NAO vira resposta errada: vira
    scored=False / status=UNUSABLE_TRUNCATED e sai do denominador. Pontuar truncamento
    como incompetencia fabricaria numero contra o modelo.
    """
    cap0 = _probe_budget(p, cfg)
    graded, traces = [], []
    last_cap = cap0
    for _ in range(tries):
        r, tr = _call_with_escalation(p["messages"], cap0)
        traces.append(tr)
        if tr:
            last_cap = tr[-1].get("max_tokens", last_cap)
        if not r.get("ok"):
            graded.append((False, f"REQUEST_ERROR:{str(r.get('error', ''))[:80]}"))
            continue
        if r.get("finish_reason") == "length":
            graded.append((None, "UNUSABLE_TRUNCATED"))
            continue
        try:
            ok, detail = p["grade"](r["text"])
        except Exception as e:
            ok, detail = False, f"GRADER_EXCEPTION:{e}"
        graded.append((bool(ok), detail))

    scored = [g for g in graded if g[0] is not None]
    if not scored:
        return {
            "id": p["id"], "dim": p["dim"], "scored": False,
            "status": "UNUSABLE_TRUNCATED",
            "first_attempt_pass": None, "stable_pass": None,
            "detail": "UNUSABLE_TRUNCATED",
            "max_tokens_final": last_cap,
            "escalation_trace": traces,
            "latency_ms": None,
        }
    first_ok = scored[0][0]
    full_pass = all(g[0] for g in scored)
    out = {
        "id": p["id"], "dim": p["dim"], "scored": True,
        "status": "SCORED",
        "first_attempt_pass": first_ok,
        "stable_pass": full_pass,
        "detail": scored[0][1],
        "max_tokens_final": last_cap,
        "escalated": any(len(t) > 1 for t in traces),
        "n_attempts": len(graded),
        "n_unusable": len(graded) - len(scored),
        "latency_ms": None,
    }
    return out


def run_model(cfg, quick=False):
    res = {
        "id": cfg["id"], "name": cfg["name"], "role_under_test": cfg["role_under_test"],
        "path": cfg["path"], "status": "PENDING",
    }
    if not os.path.exists(cfg["path"]):
        res["status"] = "FILE_NOT_READY"
        print(f"  [SKIP] arquivo ausente: {cfg['path']}")
        return res

    SCRATCH.mkdir(parents=True, exist_ok=True)
    log_path = SCRATCH / f"campeonato_{cfg['id']}.log"

    print("\n" + "=" * 78)
    print(f" [MODELO] {cfg['name']}")
    print("=" * 78)

    # Boot + cold start + decisao de jinja na MESMA tentativa. Antes o fallback via
    # apenas falha de boot; porem erro de chat template estoura na primeira CHAMADA,
    # depois do break -- na pratica o fallback nunca acontecia. Agora, se o --jinja
    # quebrar o primeiro turno com erro de template, o servidor cai e sobe sem ele,
    # e o fato fica registrado no campo "jinja" (false = medimos sem template nativo).
    #
    # O amostrador de RAM nasce no instante do Popen e vive ate o fim da sessao do
    # modelo: o pico de mmap durante o load entra na conta. A metrica antiga comecava
    # a amostrar depois do /health responder e perdia justamente o momento de maior
    # consumo de memoria -- que e o unico que importa para o MemoryGuard do Rotor.
    tkw_args = template_kwargs_args(cfg.get("template_kwargs"))
    attempts = [cfg["extra_args"] + ["--jinja"] + tkw_args,
                cfg["extra_args"] + tkw_args]
    proc = fh = samp = None
    jinja = None
    load_time_s = None
    cold = None
    for i, extra in enumerate(attempts):
        want_jinja = "--jinja" in extra
        t_boot = time.perf_counter()
        proc, fh, cmd = boot(cfg["path"], extra, log_path,
                             server=cfg.get("server"), ngl=cfg.get("ngl", "0"))
        samp = PeakSampler(proc.pid)
        samp.__enter__()
        ready = wait_ready(180)
        if not ready:
            print(f"  -> boot falhou (tentativa {i + 1}); derrubando servidor")
            samp.__exit__()
            _kill(proc, fh)
            proc = None
            time.sleep(5)
            continue
        load_time_s = round(time.perf_counter() - t_boot, 2)
        cold = chat([{"role": "user", "content":
                      "Explique em dois bullets curtos a diferenca entre processo e thread."}],
                    max_tokens=48)
        if cold.get("ok"):
            jinja = want_jinja
            break
        if want_jinja and _looks_like_template_error(cold):
            print(f"  --jinja quebrou o 1o turno ({str(cold.get('error'))[:70]}); "
                  f"reiniciando sem jinja")
        else:
            print(f"  -> 1a chamada falhou ({str(cold.get('error'))[:90]}); "
                  f"tentativa {i + 1}/{len(attempts)}")
        samp.__exit__()
        _kill(proc, fh)
        proc = None
        cold = None
        time.sleep(5)
    if proc is None:
        return {**res, "status": "STARTUP_OR_FIRST_CALL_FAILED"}

    cold_gen = cold.get("gen_tok_s")
    print(f"  -> load={load_time_s}s | cold: TTFT={_fmt(cold.get('prompt_ms'))}ms | "
          f"gen={_fmt(cold_gen)} tok/s | RAMpeak pos-load={_fmt(samp.peak)}MB | "
          f"jinja={jinja}")

    with samp:

        # ---- 2. steady state: mediana de N geracoes ----
        reps = 2 if quick else 3
        steady = []
        for _ in range(reps):
            r = chat([{"role": "user", "content":
                       "Liste cinco rios brasileiros e diga o estado de cada um."}],
                     max_tokens=64)
            if r.get("ok") and r.get("gen_tok_s"):
                steady.append(float(r["gen_tok_s"]))
        steady_med = statistics.median(steady) if steady else None
        print(f"  -> steady: mediana={_fmt(steady_med)} tok/s ({len(steady)} amostras)")

        # ---- 3a. calibracao do finish_mode (regua 8) ----
        # Uma sonda neutra com teto generoso, ANTES da bateria: revela se o modelo
        # realmente emite reasoning_content e se o toggle declarado pegou. Sem isso o
        # duelo poderia comparar um "direct" fantasma contra um reasoning de verdade.
        calib = chat([{"role": "user", "content":
                       "Some 17 e 25. Responda apenas com o numero."}],
                     max_tokens=_probe_budget({"max_tokens": 64}, cfg) + 128)
        mode_check = _verify_mode(cfg, calib)
        print(f"  -> finish_mode declarado={mode_check['declared']} | "
              f"kwargs={mode_check['template_kwargs'] or '-'} | "
              f"reasoning_obs={mode_check['observed_reasoning_len']} | "
              f"{mode_check['verdict']}")
        if mode_check["verdict"] == "MODE_VIOLATION":
            print("  !! O toggle NAO pegou: o modelo esta raciocinando apesar de direct. "
                  "Os numeros desta sessao estao contaminados e serao marcados.")

        # ---- 3b. bateria funcional (regua 9: truncamento nao pontua) ----
        probes = build_probes()
        probe_results = []
        for p in probes:
            tries = 1 if quick else 2
            pr = run_probe(p, cfg, tries)
            probe_results.append(pr)
            if not pr["scored"]:
                print(f"     [{pr['status']}] {p['id']:<18} "
                      f"teto final={pr['max_tokens_final']} (sai do denominador)")
            else:
                flag = "OK " if pr["first_attempt_pass"] else "FAIL"
                esc = " (escalou teto)" if pr.get("escalated") else ""
                print(f"     [{flag}] {p['id']:<18} {pr['detail'][:60]}{esc}")

        peak_mb = samp.peak or None

    _kill(proc, fh)
    time.sleep(6)  # cool-down: libera RAM/paginação para o proximo cold start ser honesto

    # ---- agregacao (regua 9: denominador so conta sonda PONTUAVEL) ----
    scored_prs = [pr for pr in probe_results if pr.get("scored")]
    unusable_prs = [pr for pr in probe_results if not pr.get("scored")]

    dims = {}
    for pr in scored_prs:
        d = dims.setdefault(pr["dim"], {"pass": 0, "total": 0})
        d["total"] += 1
        if pr["first_attempt_pass"]:
            d["pass"] += 1
    for d in dims.values():
        d["pct"] = round(100.0 * d["pass"] / d["total"], 1)

    n_total = len(scored_prs)
    n_first = sum(1 for pr in scored_prs if pr["first_attempt_pass"])
    n_stable = sum(1 for pr in scored_prs if pr["stable_pass"])
    resolved_no_escalation = round(100.0 * n_first / n_total, 1) if n_total else 0.0
    stability = round(100.0 * n_stable / n_total, 1) if n_total else 0.0
    if unusable_prs:
        print(f"  -> {len(unusable_prs)} sonda(s) INUTILIZAVEIS por truncamento no teto "
              f"max ({', '.join(p['id'] for p in unusable_prs)}) - FORA do denominador")

    decides = steady_med if steady_med is not None else cold_gen
    res.update({
        "status": "SUCCESS",
        "jinja": jinja,
        "finish_mode_check": mode_check,
        "n_probes_scored": n_total,
        "n_probes_unusable_truncated": len(unusable_prs),
        "unusable_probe_ids": [p["id"] for p in unusable_prs],
        "denominator_note": ("metricas funcionais dividem apenas por sondas PONTUAVEIS; "
                             "truncamento no teto maximo sai do denominador (regua 9)"),
        "load_time_s": load_time_s,
        "cold_ttft_ms": _rnd(cold.get("prompt_ms")),
        "cold_prompt_tok_s": _rnd(cold.get("prompt_tok_s")),
        "cold_gen_tok_s": _rnd(cold_gen),
        "steady_gen_tok_s_median": _rnd(steady_med),
        "steady_samples": steady,
        "ram_peak_mb": _rnd(peak_mb),
        "golden_rule_tok_s": GOLDEN_RULE_TOK_S,
        "golden_rule_metric": "steady_gen_tok_s_median (keep-alive = realidade operacional)",
        "passes_golden_rule": (decides is not None and decides >= GOLDEN_RULE_TOK_S),
        "dimensions": dims,
        "resolved_without_escalation_pct": resolved_no_escalation,
        "stability_pct": stability,
        "probes": probe_results,
    })
    print(f"  => VEREDITO VELOCIDADE: {'APROVADO' if res['passes_golden_rule'] else 'REPROVADO'} "
          f"({decides:.2f} tok/s vs piso {GOLDEN_RULE_TOK_S}) | sem escalacao={resolved_no_escalation}% "
          f"| estabilidade={stability}%" if decides is not None else
          "  => VEREDITO VELOCIDADE: SEM DADOS")
    return res


def _load_time_from_log(log_path):
    """llama-server loga 'load_backend: loaded ... ' e 'server: startup time ...'.
    Retorna segundos quando o log expoe isso; None caso contrario (nunca inventar)."""
    try:
        txt = Path(log_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    m = re.findall(r"startup time:\s*([\d.]+)\s*ms", txt)
    if m:
        return round(float(m[-1]) / 1000.0, 2)
    m = re.findall(r"load_model: .*?took\s+([\d.]+)\s*ms", txt)
    if m:
        return round(float(m[-1]) / 1000.0, 2)
    return None


def _kill(proc, fh):
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    if fh is not None:
        try:
            fh.close()
        except Exception:
            pass


def _rnd(x):
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return None


def _fmt(x):
    return "-" if x is None else f"{float(x):.2f}"


# --------------------------------------------------------------------------
# Relatorio
# --------------------------------------------------------------------------
def report(results):
    print("\n" + "#" * 78)
    print("# CAMPEONATO DE MODELOS PEQUENOS - TABELA CONSOLIDADA")
    print("#" * 78)
    hdr = (f"{'Modelo':<34}{'steady':>8}{'cold':>8}{'TTFTms':>8}{'RAMpk':>8}"
           f"{'semEsc%':>9}{'estab%':>8}{'Regra':>7}")
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        if r.get("status") != "SUCCESS":
            print(f"{r['name']:<34}{'-' * 8}{r.get('status'):>24}")
            continue
        # f-strings aninhadas com aspas iguais so funcionam em Python >= 3.12. O
        # interpretador canônico aqui é 3.11 -- entao os campos sao pré-formatados em
        # variaveis separadas. (Este bug estava adormecido: so estourava quando o
        # relatorio rodava, e as sessoes anteriores paravam antes dele.)
        ttft = r.get("cold_ttft_ms")
        ramp = r.get("ram_peak_mb")
        ttft_s = "-" if ttft is None else f"{ttft:.0f}"
        ramp_s = "-" if ramp is None else f"{ramp:.0f}"
        regra = "PASS" if r.get("passes_golden_rule") else "FAIL"
        print(f"{r['name'][:33]:<34}"
              f"{_fmt(r.get('steady_gen_tok_s_median')):>8}"
              f"{_fmt(r.get('cold_gen_tok_s')):>8}"
              f"{ttft_s:>8}"
              f"{ramp_s:>8}"
              f"{r.get('resolved_without_escalation_pct', 0):>9}"
              f"{r.get('stability_pct', 0):>8}"
              f"{regra:>7}")

    print("\nDIMENSOES FUNCIONAIS (% de passagem na 1a tentativa, denominador = sondas pontuaveis):")
    for r in results:
        if r.get("status") != "SUCCESS":
            continue
        dims = r.get("dimensions", {})
        line = " | ".join(f"{k}:{v['pct']}%({v['pass']}/{v['total']})"
                          for k, v in sorted(dims.items()))
        extra = ""
        if r.get("n_probes_unusable_truncated"):
            extra = f"  [+{r['n_probes_unusable_truncated']} truncada fora do denominador]"
        fmc = r.get("finish_mode_check") or {}
        print(f"  {r['name'][:32]:<34}{line}{extra}")
        print(f"  {'':34}finish_mode={fmc.get('declared','-')} "
              f"({fmc.get('verdict','-')}, reasoning_obs={fmc.get('observed_reasoning_len','-')})")

    print("\nFALHAS DETALHADAS (para nao esconder evidencia negativa):")
    for r in results:
        for pr in r.get("probes", []) or []:
            if pr.get("scored") and not pr["first_attempt_pass"]:
                print(f"  {r['id']:<16}{pr['id']:<18}{pr['detail'][:90]}")
            elif not pr.get("scored"):
                print(f"  {r['id']:<16}{pr['id']:<18}[{pr.get('status')}] teto final={pr.get('max_tokens_final')}")
    print("#" * 78)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="roda apenas um modelo por id (smoke test)")
    ap.add_argument("--quick", action="store_true", help="menos repeticoes (validacao de plumbing)")
    ap.add_argument("--out", default=str(OUT_FILE))
    args = ap.parse_args()

    if psutil is None:
        print("[AVISO] psutil ausente - RAM Peak nao sera medido. "
              "Instale no venv do projeto para obter a metrica completa.")

    # --only aceita UM ou VARIOS ids separados por virgula (ex.: --only a,b).
    only_ids = {x.strip() for x in args.only.split(",") if x.strip()} if args.only else None
    targets = [m for m in MODELS if (not only_ids or m["id"] in only_ids)]
    if not targets:
        print(f"[ERRO] --only {args.only} nao casa com nenhum modelo. ids: "
              f"{[m['id'] for m in MODELS]}")
        return 2

    print("=" * 78)
    print(f" CAMPEONATO FASE 1.4 | CPU pura | {THREADS} threads | ctx {CTX_SIZE} | "
          f"temp {TEMPERATURE} | porta {PORT}")
    print(f" Alvos: {[t['id'] for t in targets]}")
    print("=" * 78)

    results = []
    for cfg in targets:
        try:
            results.append(run_model(cfg, quick=args.quick))
        except Exception as e:
            print(f"  [FALHA] {cfg['id']}: {type(e).__name__}: {e}")
            results.append({"id": cfg["id"], "name": cfg["name"], "status": f"CRASH:{e}"})
        # salva incrementalmente: crash nao apaga a evidencia ja coletada
        payload = {
            "meta": {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "engine": LLAMA_SERVER,
                "threads": THREADS, "ctx_size": CTX_SIZE, "ngl": 0,
                "temperature": TEMPERATURE, "seed": SEED,
                "golden_rule_tok_s": GOLDEN_RULE_TOK_S,
                "golden_rule_metric": "steady_gen_tok_s_median",
                "quick": args.quick,
            },
            "results": results,
        }
        Path(args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                                  encoding="utf-8")

    report(results)
    print(f"\nEvidencia salva em: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
