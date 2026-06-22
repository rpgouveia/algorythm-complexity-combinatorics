"""
Geração de logs de resultados para os Programas 2 a 5.

Cada programa grava um arquivo de texto legível em logs/programN.log, com o
resumo da execução: parâmetros, tamanho da solução, cobertura e tempos. O log
é sobrescrito a cada execução (registra o resultado mais recente).
"""

import os
from datetime import datetime

LOG_DIR = "logs"
"""Diretório onde os logs são gravados."""


def write_result_log(
    program_number: int,
    p: int,
    cover: int,
    anchor: int,
    n_targets: int,
    sb_size: int,
    optimal_or_bound: int,
    bound_label: str,
    coverage_ok: bool,
    targets_checked: int,
    targets_uncovered: int,
    build_time_s: float,
    verify_time_s: float,
    log_dir: str = LOG_DIR,
) -> str:
    """Grava o resumo de resultados de um programa de cobertura em logs/programN.log.

    Args:
        program_number: número do programa (2 a 5).
        p: tamanho dos alvos cobertos.
        cover: tamanho dos blocos da solução (15).
        anchor: elemento fixo usado na construção.
        n_targets: |S_p|, total de alvos.
        sb_size: |SB|, tamanho da solução construída.
        optimal_or_bound: valor de referência (ótimo, para p=14; ou limite
            inferior de Schönheim, para p≤13).
        bound_label: rótulo do valor de referência (ex.: "ótimo (ILP)" ou
            "limite inferior (Schönheim)").
        coverage_ok: se a cobertura foi confirmada completa.
        targets_checked: quantos alvos foram efetivamente verificados.
        targets_uncovered: quantos alvos ficaram descobertos (esperado 0).
        build_time_s: tempo de construção do SB (leitura de S15.csv).
        verify_time_s: tempo de verificação (leitura de S_p.csv).
        log_dir: diretório de saída.

    Returns:
        Caminho do arquivo de log gravado.
    """
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"program{program_number}.log")

    status = "COMPLETA" if coverage_ok else "INCOMPLETA"
    razao = sb_size / optimal_or_bound if optimal_or_bound else float("nan")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    linhas = [
        "=" * 60,
        f"PROGRAMA {program_number} — Cobertura de S_{p}  (resumo de resultados)",
        f"Execução em: {timestamp}",
        "=" * 60,
        "",
        "Parâmetros:",
        f"  universo U          = {{1..25}}",
        f"  tamanho dos alvos p = {p}",
        f"  tamanho dos blocos  = {cover}",
        f"  elemento fixo       = {anchor}",
        "",
        "Resultados:",
        f"  alvos |S_{p}|         = {n_targets:,}",
        f"  tamanho |SB|        = {sb_size:,}",
        f"  {bound_label:<19} = {optimal_or_bound:,}",
        f"  razão |SB|/ref      = {razao:.1f}×",
        "",
        "Verificação de cobertura:",
        f"  alvos verificados   = {targets_checked:,}",
        f"  alvos não cobertos  = {targets_uncovered:,}",
        f"  cobertura           = {status}",
        "",
        "Tempos:",
        f"  construção do SB    = {build_time_s:.2f} s",
        f"  verificação         = {verify_time_s:.2f} s",
        f"  total               = {build_time_s + verify_time_s:.2f} s",
        "=" * 60,
        "",
    ]
    conteudo = "\n".join(linhas)

    with open(path, "w") as f:
        f.write(conteudo)

    return path