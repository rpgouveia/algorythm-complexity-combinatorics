"""
Geração de logs de resultados para os Programas 2 a 5 na variante GRASP.

Espelha logging_utils.write_result_log, mas registra os campos PRÓPRIOS do
GRASP (k da RCL, nº de partidas/starts, |SB| inicial pré-busca-local, motivo da
parada) que não existem na construção direta. Grava em logs/programN_grasp.log,
um arquivo SEPARADO do log da construção direta (logs/programN.log), para que as
duas estratégias coexistam sem sobrescrita.

O log é sobrescrito a cada execução (registra o resultado mais recente).
"""

import os
from datetime import datetime

from combinatorics import N

LOG_DIR = "logs"
"""Diretório onde os logs são gravados."""


def write_grasp_log(
    program_number: int,
    p: int,
    cover: int,
    n_targets: int,
    sb_size: int,
    size_inicial: int,
    lower_bound: int,
    bound_label: str,
    coverage_ok: bool,
    targets_checked: int,
    targets_uncovered: int,
    k_rcl: int,
    n_starts: int,
    stop_reason: str,
    search_time_s: float,
    verify_time_s: float,
    log_dir: str = LOG_DIR,
) -> str:
    """Grava o resumo de resultados de um programa GRASP em logs/programN_grasp.log.

    Args:
        program_number: número do programa (2 a 5).
        p: tamanho dos alvos cobertos.
        cover: tamanho dos blocos da solução (15).
        n_targets: |S_p|, total de alvos.
        sb_size: |SB|, tamanho da solução final (pós-busca-local).
        size_inicial: |SB| da melhor partida ANTES da busca local (referência
            do ganho da fase 2).
        lower_bound: limite inferior de Schönheim (referência de qualidade).
        bound_label: rótulo do valor de referência.
        coverage_ok: se a cobertura foi confirmada completa (auditoria).
        targets_checked: quantos alvos foram efetivamente verificados.
        targets_uncovered: quantos alvos ficaram descobertos (esperado 0).
        k_rcl: tamanho da RCL usado na construção.
        n_starts: número de partidas (starts) executadas no multistart.
        stop_reason: motivo da parada (ex.: "n_starts", "time_limit",
            "estagnacao").
        search_time_s: tempo de busca do GRASP (todas as partidas).
        verify_time_s: tempo da auditoria independente (verifier.py).
        log_dir: diretório de saída.

    Returns:
        Caminho do arquivo de log gravado.
    """
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"program{program_number}_grasp.log")

    status = "COMPLETA" if coverage_ok else "INCOMPLETA"
    razao = sb_size / lower_bound if lower_bound else float("nan")
    reducao = size_inicial - sb_size
    reducao_pct = (reducao / size_inicial * 100) if size_inicial else 0.0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    linhas = [
        "=" * 60,
        f"PROGRAMA {program_number} (GRASP) — Cobertura de S_{p}  (resumo)",
        f"Execução em: {timestamp}",
        "=" * 60,
        "",
        "Parâmetros:",
        f"  universo U          = {{1..{N}}}",
        f"  tamanho dos alvos p = {p}",
        f"  tamanho dos blocos  = {cover}",
        f"  estratégia          = GRASP multistart (RCL por cardinalidade)",
        f"  k da RCL            = {k_rcl}",
        "",
        "Multistart:",
        f"  partidas (starts)   = {n_starts:,}",
        f"  motivo da parada    = {stop_reason}",
        "",
        "Resultados:",
        f"  alvos |S_{p}|         = {n_targets:,}",
        f"  |SB| inicial (melhor)= {size_inicial:,}   (antes da busca local)",
        f"  |SB| final          = {sb_size:,}   (após busca local)",
        f"  redução busca local = {reducao:,} blocos ({reducao_pct:.1f}%)",
        f"  {bound_label:<19} = {lower_bound:,}",
        f"  razão |SB|/ref      = {razao:.1f}×",
        "",
        "Verificação de cobertura (auditoria independente):",
        f"  alvos verificados   = {targets_checked:,}",
        f"  alvos não cobertos  = {targets_uncovered:,}",
        f"  cobertura           = {status}",
        "",
        "Tempos:",
        f"  busca (GRASP)       = {search_time_s:.2f} s",
        f"  verificação         = {verify_time_s:.2f} s",
        f"  total               = {search_time_s + verify_time_s:.2f} s",
        "=" * 60,
        "",
    ]
    conteudo = "\n".join(linhas)

    with open(path, "w") as f:
        f.write(conteudo)

    return path
