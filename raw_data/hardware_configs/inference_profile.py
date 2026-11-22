# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 rotor-llm contributors

"""ROTOR Inference Profile Registry.

Architect & Leader: Mestre Ruan
Standard: Radical Truth Protocol & Protocolo O.M.E.G.A.

Separation of Concerns:
- Cognitive Router owns COMPETENCE: "Qual modelo resolve melhor a tarefa?"
- Inference Profile Registry owns PERFORMANCE: "Como esse modelo deve ser executado no hardware e contexto?"
- Backend Lifecycle Manager owns PROCESSES: "Garante estado físico, inicialização, memória e encerramento."

O registry é estritamente declarativo. Ele NÃO decide qual modelo usar.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("rotor.inference_profile")


@dataclass(frozen=True, slots=True)
class InferenceProfile:
    """Especificação declarativa canônica de execução física de um modelo."""

    profile_id: str
    model_id: str
    backend_id: str
    build: str
    threads: int
    affinity_mask: str
    priority: str
    speculation: dict[str, Any]
    kv: dict[str, Any]
    context_limit: int
    expected_ram: dict[str, Any]
    performance_ranges: dict[str, Any]
    evidence: dict[str, Any]
    status: str
    model_file: str | None = None
    binary_path: str | None = None

    @property
    def affinity_cores(self) -> list[int]:
        """Calcula os IDs de cores lógicos ativos a partir da máscara hexadecimal."""
        try:
            mask_int = int(self.affinity_mask, 16) if isinstance(self.affinity_mask, str) else int(self.affinity_mask)
            cores = [i for i in range(64) if (mask_int & (1 << i))]
            return cores
        except Exception:
            return []

    @property
    def estimated_ram_bytes(self) -> int:
        return int(self.expected_ram.get("estimated_ram_bytes", 0))

    @property
    def headroom_bytes(self) -> int:
        return int(self.expected_ram.get("headroom_bytes", 2 * 1024 * 1024 * 1024))

    def build_command(self, port: int, host: str = "127.0.0.1") -> list[str]:
        """Gera a linha de comando exata com flags auditadas para o llama-server."""
        binary = self.binary_path or r"F:\tools\lc_b10749\llama-server.exe"
        model_path = self.model_file or r"F:\data\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"

        cmd = [
            binary,
            "-m",
            model_path,
            "--host",
            host,
            "--port",
            str(port),
            "--threads",
            str(self.threads),
            "-C",
            self.affinity_mask,
            "--ctx-size",
            str(self.context_limit),
            "--prio",
            "-1" if self.priority == "below_normal" else "0",
            "-np",
            "1",
            "--no-repack",
        ]

        # KV cache quantization
        k_type = self.kv.get("k", "q8_0")
        v_type = self.kv.get("v", "q8_0")
        cmd.extend(["-ctk", str(k_type), "-ctv", str(v_type)])

        # Flash Attention (opcional — ativado por perfil via kv["flash_attention"])
        if self.kv.get("flash_attention", False):
            cmd.extend(["-fa", "1"])

        # Speculative decoding (MTP)
        spec_mode = self.speculation.get("mode", "none")
        draft_n_max = int(self.speculation.get("draft_n_max", 0))
        if spec_mode == "draft-mtp" and draft_n_max > 0:
            cmd.extend(["--spec-type", "draft-mtp", "--spec-draft-n-max", str(draft_n_max)])
        else:
            cmd.extend(["--spec-type", "none"])

        return cmd


class InferenceProfileRegistry:
    """Registry declarativo em memória com perfis canônicos homologados."""

    def __init__(self) -> None:
        self._profiles: dict[str, InferenceProfile] = {}
        self._model_to_profile: dict[str, str] = {}
        self._register_canonical_defaults()

    def register(self, profile: InferenceProfile) -> None:
        self._profiles[profile.profile_id] = profile
        self._model_to_profile[profile.model_id.lower()] = profile.profile_id
        log.info("[profile_registry] Registered profile %s for model %s", profile.profile_id, profile.model_id)

    def get(self, profile_id: str) -> InferenceProfile | None:
        return self._profiles.get(profile_id)

    def get_for_model(self, model_id: str, backend_id: str | None = None) -> InferenceProfile | None:
        norm = model_id.lower().split("/")[-1]
        compact = re.sub(r"[^a-z0-9]", "", norm)
        # Direct lookup
        pid = self._model_to_profile.get(norm)
        if pid and pid in self._profiles:
            return self._profiles[pid]

        # Fuzzy match
        for p in self._profiles.values():
            if norm in p.model_id.lower() or p.model_id.lower() in norm:
                return p
            profile_compact = re.sub(r"[^a-z0-9]", "", p.model_id.lower())
            if compact in profile_compact or profile_compact in compact:
                return p
            if backend_id and p.backend_id.lower() == backend_id.lower():
                return p

        return None

    def list_profiles(self) -> list[InferenceProfile]:
        return list(self._profiles.values())

    def _register_canonical_defaults(self) -> None:
        # Perfil Canônico v1 congelado para Qwen 35B MoE
        p_35b = InferenceProfile(
            profile_id="qwen35b_xeon_perf_v1",
            model_id="qwen3.6-35b-a3b",
            backend_id="qwen36-35b-moe",
            build="b10749",
            threads=12,
            affinity_mask="0x5555550",
            priority="below_normal",
            speculation={"mode": "draft-mtp", "draft_n_max": 2},
            kv={"k": "q8_0", "v": "q8_0"},
            context_limit=2048,
            expected_ram={
                "estimated_ram_bytes": 12 * 1024 * 1024 * 1024,
                "headroom_bytes": 2048 * 1024 * 1024,
                "min_available_ram_before_load_gb": 14.0,
            },
            performance_ranges={
                "normal_workload_tps": "~10",
                "observed_peak_short_ctx_tps": 12.21,
            },
            evidence={
                "source": "MTP_CONTEXT_CURVE_BENCHMARK.json",
                "gate": "KV_FINAL_VALIDATION_GATE.json",
            },
            status="empirically_validated_v1",
            model_file=r"F:\data\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf",
            binary_path=r"F:\tools\lc_b10749\llama-server.exe",
        )
        self.register(p_35b)

        # Perfil Canônico v1 para Qwen 7B
        p_7b = InferenceProfile(
            profile_id="qwen25_7b_xeon_v1",
            model_id="qwen2.5-7b-instruct",
            backend_id="qwen25-7b-gpu",
            build="b10749",
            threads=10,
            affinity_mask="0x5555550",
            priority="below_normal",
            speculation={"mode": "none", "draft_n_max": 0},
            kv={"k": "f16", "v": "f16"},
            context_limit=4096,
            expected_ram={
                # -ngl 99 -> pesos na VRAM, ~2 GB sys RAM (mmap + KV cache + overhead)
                "estimated_ram_bytes": 2 * 1024 * 1024 * 1024,
                "headroom_bytes": 1024 * 1024 * 1024,
                "min_available_ram_before_load_gb": 3.0,
            },
            performance_ranges={
                "normal_workload_tps": "~8.6",
                "observed_peak_short_ctx_tps": 8.60,
            },
            evidence={"source": "INFERENCE_PROFILE_BENCHMARK.json"},
            status="empirically_validated_v1",
            model_file=r"F:\data\models\Qwen2.5-7B-Instruct-Q4_K_M.gguf",
            binary_path=r"F:\tools\lc_b10749\llama-server.exe",
        )
        self.register(p_7b)

        # Perfil Canônico v1 para Qwen 3.5 4B (Planejador / Coder / Ágil)
        p_qwen35_4b = InferenceProfile(
            profile_id="qwen35_4b_xeon_v1",
            model_id="qwen3.5-4b",
            backend_id="qwen35-4b-compact",
            build="b10749",
            threads=12,
            affinity_mask="0x5555550",
            priority="below_normal",
            speculation={"mode": "none", "draft_n_max": 0},
            kv={"k": "f16", "v": "f16"},
            context_limit=4096,
            expected_ram={
                "estimated_ram_bytes": 4500 * 1024 * 1024,
                "headroom_bytes": 2048 * 1024 * 1024,
                "min_available_ram_before_load_gb": 6.0,
            },
            performance_ranges={
                "normal_workload_tps": "~18-22",
                "observed_peak_short_ctx_tps": 22.0,
            },
            evidence={"source": "MEGAZORD_FLEET_BENCHMARK.json"},
            status="fleet_v1_candidate",
            model_file=r"F:\data\models\Qwen3.5-4B-Q4_K_M.gguf",
            binary_path=r"F:\tools\lc_b10749\llama-server.exe",
        )
        self.register(p_qwen35_4b)

        # Perfil Canônico v1 para Granite 3.1 2B (Tool Calling / JSON Estrito)
        p_granite_2b = InferenceProfile(
            profile_id="granite31_2b_xeon_v1",
            model_id="granite-3.1-2b",
            backend_id="granite31-2b-tools",
            build="b10749",
            threads=12,
            affinity_mask="0x5555550",
            priority="below_normal",
            speculation={"mode": "none", "draft_n_max": 0},
            kv={"k": "f16", "v": "f16"},
            context_limit=4096,
            expected_ram={
                "estimated_ram_bytes": 2500 * 1024 * 1024,
                "headroom_bytes": 1024 * 1024 * 1024,
                "min_available_ram_before_load_gb": 4.0,
            },
            performance_ranges={
                "normal_workload_tps": "~22-28",
                "observed_peak_short_ctx_tps": 28.0,
            },
            evidence={"source": "MEGAZORD_FLEET_BENCHMARK.json"},
            status="fleet_v1_candidate",
            model_file=r"F:\data\models\granite-3.1-2b-instruct-Q4_K_M.gguf",
            binary_path=r"F:\tools\lc_b10749\llama-server.exe",
        )
        self.register(p_granite_2b)

        # Perfil Canônico v1 para Ministral 3 3B (Juiz Dedutivo / Raciocínio)
        p_ministral_3b = InferenceProfile(
            profile_id="ministral3_3b_xeon_v1",
            model_id="ministral-3-3b",
            backend_id="ministral3-3b-reasoning",
            build="b10749",
            threads=12,
            affinity_mask="0x5555550",
            priority="below_normal",
            speculation={"mode": "none", "draft_n_max": 0},
            kv={
                "k": "f16",
                "v": "f16",
                "flash_attention": True,   # OBRIGATÓRIO: prefill 101.8 tok/s, geração 17.7 tok/s no Haswell
            },
            context_limit=4096,
            expected_ram={
                "estimated_ram_bytes": 3500 * 1024 * 1024,
                "headroom_bytes": 1024 * 1024 * 1024,
                "min_available_ram_before_load_gb": 5.0,
            },
            performance_ranges={
                "normal_workload_tps": "~16-18",
                "observed_peak_short_ctx_tps": 17.73,  # PROVADO: llama-bench 2026-09-12
            },
            evidence={
                "source": "llama-bench físico 2026-09-12",
                "config": "-ctk f16 -ctv f16 -fa 1 -t 12",
            },
            status="fleet_v1_optimized",
            model_file=r"F:\data\models\Ministral-3-3B-Reasoning-2512.Q4_K_M.gguf",
            binary_path=r"F:\tools\lc_b10749\llama-server.exe",
        )
        self.register(p_ministral_3b)

        # Perfil Canônico v1 para Nemotron 3 Nano 4B (Crítico / Auditor Independente)
        p_nemotron_4b = InferenceProfile(
            profile_id="nemotron3_4b_xeon_v1",
            model_id="nemotron-3-nano-4b",
            backend_id="nemotron3-4b-critic",
            build="b10749",
            threads=12,
            affinity_mask="0x5555550",
            priority="below_normal",
            speculation={"mode": "none", "draft_n_max": 0},
            kv={"k": "f16", "v": "f16"},
            context_limit=4096,
            expected_ram={
                "estimated_ram_bytes": 4500 * 1024 * 1024,
                "headroom_bytes": 2048 * 1024 * 1024,
                "min_available_ram_before_load_gb": 6.0,
            },
            performance_ranges={
                "normal_workload_tps": "~18-22",
                "observed_peak_short_ctx_tps": 22.0,
            },
            evidence={"source": "MEGAZORD_FLEET_BENCHMARK.json"},
            status="fleet_v1_candidate",
            model_file=r"F:\data\models\NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf",
            binary_path=r"F:\tools\lc_b10749\llama-server.exe",
        )
        self.register(p_nemotron_4b)

        # Perfil Canônico v1 para Phi-4 Mini 3.8B (Matemática / Raciocínio Científico)
        p_phi4_mini = InferenceProfile(
            profile_id="phi4_mini_xeon_v1",
            model_id="phi-4-mini",
            backend_id="phi4-mini-math",
            build="b10749",
            threads=12,
            affinity_mask="0x5555550",
            priority="below_normal",
            speculation={"mode": "none", "draft_n_max": 0},
            kv={
                "k": "f16",
                "v": "f16",
                "flash_attention": True,   # OBRIGATÓRIO: prefill 70 tok/s, geração 14.7 tok/s
            },
            context_limit=4096,
            expected_ram={
                "estimated_ram_bytes": 4000 * 1024 * 1024,
                "headroom_bytes": 2048 * 1024 * 1024,
                "min_available_ram_before_load_gb": 6.0,
            },
            performance_ranges={
                "normal_workload_tps": "~14-16",
                "observed_peak_short_ctx_tps": 14.94,  # PROVADO: llama-bench 2026-09-12
            },
            evidence={
                "source": "llama-bench físico 2026-09-12",
                "config": "-ctk f16 -ctv f16 -fa 1 -t 12",
            },
            status="fleet_v1_optimized",
            model_file=r"F:\data\models\Phi-4-mini-instruct.Q4_K_M.gguf",
            binary_path=r"F:\tools\lc_b10749\llama-server.exe",
        )
        self.register(p_phi4_mini)

        # Perfil Canônico v1 para InternVL2.5 4B (Visão Computacional / OCR)
        p_internvl_4b = InferenceProfile(
            profile_id="internvl25_4b_xeon_v1",
            model_id="internvl2.5-4b",
            backend_id="internvl25-vision",
            build="b10749",
            threads=12,
            affinity_mask="0x5555550",
            priority="below_normal",
            speculation={"mode": "none", "draft_n_max": 0},
            kv={"k": "f16", "v": "f16"},
            context_limit=2048,
            expected_ram={
                "estimated_ram_bytes": 4000 * 1024 * 1024,
                "headroom_bytes": 2048 * 1024 * 1024,
                "min_available_ram_before_load_gb": 6.0,
            },
            performance_ranges={
                "normal_workload_tps": "~15-18",
                "observed_peak_short_ctx_tps": 18.0,
            },
            evidence={"source": "MEGAZORD_FLEET_BENCHMARK.json"},
            status="fleet_v1_candidate",
            model_file=r"F:\data\models\InternVL2_5-4B-Q4_K_M.gguf",
            binary_path=r"F:\tools\lc_b10749\llama-server.exe",
        )
        self.register(p_internvl_4b)

        # Perfil Canônico v1 para Ring-mini-2.0 (MoE 16.8B / 1.4B Ativo - Candidato L1)
        # BENCHMARK FÍSICO (2026-09-11): -ctk q8_0 -ctv f16 -fa 1 -t 12 → 28.77 tok/s
        # vs configuração anterior sem flash attention: 10.95 tok/s (+163% de melhora)
        p_ring_mini = InferenceProfile(
            profile_id="ring_mini_xeon_v1",
            model_id="ring-mini-2.0",
            backend_id="ring-mini-fast",
            build="b10749",
            threads=12,
            affinity_mask="0x5555550",
            priority="below_normal",
            speculation={"mode": "none", "draft_n_max": 0},
            kv={
                "k": "q8_0",
                "v": "f16",                # CHAVE: f16 > q8_0 no Haswell via AVX2
                "flash_attention": True,   # OBRIGATÓRIO: -fa 1 ativa o caminho otimizado
            },
            context_limit=4096,
            expected_ram={
                "estimated_ram_bytes": 11500 * 1024 * 1024,
                "headroom_bytes": 2048 * 1024 * 1024,
                "min_available_ram_before_load_gb": 13.0,
            },
            performance_ranges={
                "normal_workload_tps": "~20-28",
                "observed_peak_short_ctx_tps": 28.77,     # PROVADO: llama-bench 2026-09-11
                "baseline_without_fa_tps": 10.95,          # referência histórica
            },
            evidence={
                "source": "llama-bench físico 2026-09-11",
                "config": "-ctk q8_0 -ctv f16 -fa 1 -t 12",
                "improvement": "+163% vs baseline q8_0+q8_0 sem flash attention",
            },
            status="fleet_v1_optimized",
            model_file=r"F:\data\models\Ring-mini-2.0-Q4_K_M.gguf",
            binary_path=r"F:\tools\lc_b10749\llama-server.exe",
        )
        self.register(p_ring_mini)

        # Model Lab 2026-09-23: profiles are execution facts, not competence
        # scores.  The Decision Engine may use them only after capability and
        # health checks; this registry records hardware/launch parameters and
        # the immutable benchmark evidence reference.
        model_lab_profiles = (
            (
                "qwen25coder15b_model_lab_v1",
                "qwen2.5-coder-1.5b-instruct",
                "local-qwen25coder15b",
                1175,
                25.54,
                r"F:\data\models\qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
                "empirically_validated_model_lab",
            ),
            (
                "minicpm5_2b_model_lab_v1",
                "minicpm5-2b",
                "local-minicpm5-2b",
                2038,
                17.43,
                r"F:\data\models\MiniCPM5-2B-Q4_K_M.gguf",
                "empirically_validated_model_lab",
            ),
            (
                "granite42_3b_model_lab_v1",
                "granite-4.2-3b",
                "local-granite42-3b",
                2484,
                12.66,
                r"F:\data\models\granite-4.2-3b-Q4_K_M.gguf",
                "empirically_validated_model_lab",
            ),
            (
                "qwen34b_rlm_model_lab_v1",
                "qwen3-4b-rlm-sft",
                "local-qwen34b-rlm",
                3181,
                11.01,
                r"F:\data\models\Qwen3-4B-Instruct-2507-RLM-SFT-v3-per-root-turn--.Q4_K_M.gguf",
                "empirically_validated_model_lab",
            ),
            (
                "rlmqwen38b_model_lab_v1",
                "rlm-qwen3-8b",
                "local-rlmqwen38b",
                5349,
                8.13,
                r"F:\data\models\rlm-qwen3-8b-v0.1-q4_k_m.gguf",
                "empirically_validated_model_lab",
            ),
            (
                "qwen38_9b_model_lab_disabled",
                "qwen3.8-9b-distill-heretic",
                "local-qwen38-9b",
                9973,
                4.21,
                r"F:\data\models\Qwen3.8-9B-Distill-Heretic-Uncensored-Q8_0.gguf",
                "disabled_below_speed_floor",
            ),
        )
        for profile_id, model_id, backend_id, ram_mb, speed, model_file, status in model_lab_profiles:
            self.register(
                InferenceProfile(
                    profile_id=profile_id,
                    model_id=model_id,
                    backend_id=backend_id,
                    build="b10749",
                    threads=14,
                    affinity_mask="0x5555550",
                    priority="below_normal",
                    speculation={"mode": "none", "draft_n_max": 0},
                    kv={"k": "q8_0", "v": "q8_0"},
                    context_limit=4096,
                    expected_ram={"estimated_ram_bytes": ram_mb * 1024 * 1024, "headroom_bytes": 2 * 1024**3},
                    performance_ranges={"steady_gen_tok_s_median": speed, "golden_rule_tok_s": 7.0},
                    evidence={"source": "BENCHMARK_CAMPEONATO_RESULTS.json", "metric": "steady_gen_tok_s_median"},
                    status=status,
                    model_file=model_file,
                    binary_path=r"F:\tools\lc_b10749\llama-server.exe",
                )
            )


# Instância singleton global do registry
profile_registry = InferenceProfileRegistry()
