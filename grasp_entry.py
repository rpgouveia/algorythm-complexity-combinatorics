"""
Orquestração comum dos Programas 2 a 5 na variante GRASP.

Cada program{2..5}_grasp.py é um entry point FINO que apenas fixa o p do seu
conjunto-alvo e delega a este módulo. A lógica é idêntica entre os quatro
programas (só muda p e o rótulo), então centralizá-la aqui evita manter quatro
cópias em sincronia — o que é um risco real na hora da defesa, se uma cópia
divergir das demais.

FLUXO (idêntico para p = 14, 13, 12, 11):
    1. Roda o GRASP multistart (grasp_cover) — gera S_p em memória, não usa CSV.
    2. AUDITA o SB resultante de forma independente (verifier.verify), exatamente
       o mesmo verificador usado pelas demais estratégias — a auditoria não
       confia no algoritmo que produziu o SB.
    3. Calcula o limite inferior de Schönheim como referência de qualidade.
    4. Grava logs/programN_grasp.log (separado do log da construção direta).

POR QUE GERA S_p EM MEMÓRIA (e não lê os CSVs do Programa 1):
    A construção direta (program2..5.py) lê data/S15.csv porque sua estratégia é
    FILTRAR S₁₅ do disco pelo elemento-âncora. O GRASP NÃO filtra S₁₅: ele
    constrói candidatos sob demanda (apenas os blocos que contêm o alvo
    não-coberto da vez) e opera inteiramente em bitmask. Ler o CSV só para
    reconverter em bitmask adicionaria I/O e parsing sem nenhum ganho. Por isso
    esta variante independe de data/ estar populado.

CLASSE: o problema de decisão associado é Set Cover, NP-Completo. O GRASP é uma
metaheurística: sempre termina com uma cobertura VÁLIDA (verificada), mas NÃO
garante o |SB| mínimo. O guloso subjacente oferece um piso teórico de qualidade
(aproximação H(n) ≈ ln|S_p|).
"""

import time
from math import ceil

from combinatorics import N, count_formula
from grasp_cover import grasp_multistart, grasp_multistart_seq
from grasp_logging import write_grasp_log
from verifier import verify, print_report

COVER: int = 15
"""Tamanho dos blocos da solução (combinações de 15)."""


def schonheim_bound(v: int, k: int, t: int) -> int:
    """Limite inferior de Schönheim para o covering number C(v, k, t).

    Mesma formulação iterativa-recursiva usada nos programas de construção
    direta (program3/4/5.py), reproduzida aqui para manter este módulo
    autocontido.
    """
    if t == 1:
        return ceil(v / k)
    return ceil(v / k * schonheim_bound(v - 1, k - 1, t - 1))


def run_grasp_program(
    program_number: int,
    p: int,
    bound_label: str = "limite inf. (Schönheim)",
    k_rcl: int = 5,
    n_starts: int = 20,
    paralelo: bool = True,
    max_starts: int | None = None,
    time_limit_s: float | None = None,
    no_improve_limit: int | None = None,
    heartbeat: bool = False,
    use_tqdm: bool = True,
    progress_every: int = 50,
    checkpoint_dir: str | None = None,
    save_final_path: str | None = None,
    seed: int | None = None,
    verbose: bool = True,
) -> None:
    """Executa a variante GRASP para cobrir S_p e grava o log de resultados.

    Args:
        program_number: número do programa (2 a 5), usado no nome do log.
        p: tamanho dos alvos (14, 13, 12 ou 11).
        bound_label: rótulo do valor de referência no log.
        k_rcl: tamanho da RCL na construção (k melhores candidatos).
        n_starts: número de partidas do multistart (modo paralelo).
        paralelo: True usa o motor paralelo (parada por n_starts, barra MACRO de
            lotes); False usa o motor sequencial (parada por max_starts/tempo/
            estagnação, permite HEARTBEAT da construção).
        max_starts: nº máximo de partidas (modo sequencial).
        time_limit_s: tempo-limite, em segundos (modo sequencial).
        no_improve_limit: nº de partidas sem melhora p/ parar (modo sequencial).
        heartbeat: no modo sequencial, imprime progresso DENTRO de cada partida
            (|SB|, cobertura, ritmo) — para observar de perto. Ignorado no
            paralelo (workers em processos separados não podem imprimir).
        use_tqdm: usa barras tqdm se instalado; senão, saída textual.
        progress_every: frequência (em blocos) do heartbeat de construção.
        seed: semente para reprodutibilidade.
        verbose: imprime progresso por partida.
    """
    print(f"Programa {program_number} (GRASP) — Cobertura de S_{p}  (U = {{1..{N}}})\n")

    n_targets = count_formula(p)
    lb = schonheim_bound(N, COVER, p)

    print(f"Alvos a cobrir |S_{p}|:        {n_targets:,}")
    print(f"Limite inferior (Schönheim): {lb:,}")
    print(f"Estratégia:                  GRASP multistart (k_RCL={k_rcl})")
    if paralelo:
        print(f"Parada:                      {n_starts} partidas (paralelo)\n")
    else:
        criterios = []
        if max_starts is not None:
            criterios.append(f"max_starts={max_starts}")
        if no_improve_limit is not None:
            criterios.append(f"estagnação={no_improve_limit}")
        if time_limit_s is not None:
            criterios.append(f"tempo={time_limit_s}s")
        print(f"Parada:                      {', '.join(criterios)} (sequencial)\n")

    # ----- 1) roda o GRASP -----
    print("Rodando GRASP multistart...")
    if paralelo:
        res = grasp_multistart(
            p=p,
            k=k_rcl,
            cover=COVER,
            n_starts=n_starts,
            seed=seed,
            verbose=verbose,
            use_tqdm=use_tqdm,
        )
        stop_reason = "n_starts"
    else:
        res = grasp_multistart_seq(
            p=p,
            k=k_rcl,
            cover=COVER,
            max_starts=max_starts,
            time_limit_s=time_limit_s,
            no_improve_limit=no_improve_limit,
            seed=seed,
            verbose=verbose,
            heartbeat=heartbeat,
            use_tqdm=use_tqdm,
            progress_every=progress_every,
            checkpoint_dir=checkpoint_dir,
            save_final_path=save_final_path,
        )
        if res.cobertura_parcial:
            stop_reason = "time_limit (cobertura PARCIAL)"
        elif time_limit_s is not None:
            stop_reason = "time_limit"
        elif no_improve_limit is not None:
            stop_reason = "estagnacao"
        else:
            stop_reason = "max_starts"

    print(
        f"\n  |SB| inicial (melhor partida): {res.size_inicial:,}  (antes da busca local)"
    )
    print(f"  |SB| final:                    {res.size:,}  (após busca local)")
    print(f"  partidas executadas:           {res.n_starts:,}")
    print(f"  razão |SB|/Schönheim:          {res.size/lb:.1f}×")
    print(f"  tempo de busca:                {res.elapsed_s:.2f}s")
    if res.cobertura_parcial:
        print(f"  *** ATENÇÃO: parada por TEMPO — cobertura PARCIAL (incompleta). ***")
        print(
            f"      O |SB| acima é parcial; a auditoria abaixo mostrará alvos faltando."
        )
    print()

    # ----- 2) auditoria independente -----
    print("Auditando o SB (verifier.py, auditoria independente)...")
    audit = verify(res.chosen, p=p)
    print_report(audit)
    print()

    # ----- 3) grava o log -----
    log_path = write_grasp_log(
        program_number=program_number,
        p=p,
        cover=COVER,
        n_targets=n_targets,
        sb_size=res.size,
        size_inicial=res.size_inicial,
        lower_bound=lb,
        bound_label=bound_label,
        coverage_ok=audit.ok,
        targets_checked=audit.n_targets,
        targets_uncovered=audit.n_missing,
        k_rcl=k_rcl,
        n_starts=res.n_starts,
        stop_reason=stop_reason,
        search_time_s=res.elapsed_s,
        verify_time_s=audit.elapsed_s,
    )
    print(f"Log de resultados gravado em: {log_path}")
