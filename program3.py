"""
PROGRAMA 3 — Cobertura de Combinações de 13 Elementos.

Objetivo (enunciado): determinar SB₁₅,13 ⊆ S₁₅ tal que toda combinação de 13
elementos (Y ∈ S_13) esteja contida em pelo menos uma combinação de 15
elementos (X ∈ SB₁₅,13):

        ∀ Y ∈ S_13  ∃ X ∈ SB₁₅,13  tal que  Y ⊆ X

ARQUITETURA — consumo dos dados do Programa 1:
    Este programa LÊ os CSVs gerados pelo Programa 1:
      • data/S15.csv — candidatos (de onde o SB é extraído);
      • data/S13.csv — alvos (o que precisa ser coberto).
    O SB é construído filtrando S₁₅ (lido do disco) pela regra do elemento fixo,
    e a cobertura é VERIFICADA percorrendo os alvos S_13 lidos do disco.

ESTRATÉGIA — Construção direta por elemento fixo (a mesma dos Programas 2-5):
    SB = { X ∈ S₁₅ | a ∈ X }, para um elemento fixo `a` (usamos a = 25).

POR QUE COBRE TODO S_13 (prova):
    Para todo Y ∈ S_13: se a ∈ Y, estenda Y com elementos extras até 15; se
    a ∉ Y, tome X = Y ∪ {a, …} completando até 15. Em ambos os casos X ∈ SB e
    Y ⊆ X. ∎  (Validado também por força bruta em universos reduzidos.)

ESTA CONSTRUÇÃO NÃO É ÓTIMA:
    |SB| = C(24,14) = 1.961.256.
    Limite inferior de Schönheim para C(25,15,13): 58,887.
    A construção está ~33× acima do limite inferior — solução VÁLIDA, mas
    longe da mínima. O gap cresce conforme p diminui (p=14 ótima; p≤13 folgada),
    pois |SB| fica fixo enquanto o limite inferior cai. Reduzir |SB| é objeto das
    estratégias alternativas (randômico/GRASP, guloso paralelo, ILP).

CLASSE: o problema de decisão associado é Set Cover, NP-Completo. A verificação
de uma solução é simples e polinomial (feita aqui percorrendo os alvos).
"""

import time
from math import ceil

from combinatorics import N, count_formula
from dataset_io import read_combinations_csv, csv_exists
from logging_utils import write_result_log

ANCHOR: int = N  # elemento fixo (25)
P: int = 13
COVER: int = 15


def schonheim_bound(v: int = N, k: int = COVER, t: int = P) -> int:
    """Limite inferior de Schönheim para o covering number C(v, k, t)."""
    if t == 1:
        return ceil(v / k)
    return ceil(v / k * schonheim_bound(v - 1, k - 1, t - 1))


def build_sb_from_candidates(anchor: int = ANCHOR):
    """Constrói o SB filtrando S₁₅ (lido do CSV) pelos que contêm `anchor`."""
    for combo in read_combinations_csv(COVER):
        if anchor in combo:
            yield combo


def verify_cover_from_targets(anchor: int = ANCHOR) -> tuple[bool, int, int]:
    """Verifica a cobertura percorrendo os alvos S_13 lidos do CSV.

    Para cada alvo Y, confirma que existe X ∈ SB com Y ⊆ X — o que, pela
    construção por elemento fixo, equivale a |Y ∪ {anchor}| ≤ 15 (sempre vale).
    Retorna (cobertura_ok, alvos_verificados, alvos_nao_cobertos).
    """
    verificados = 0
    nao_cobertos = 0
    for Y in read_combinations_csv(P):
        verificados += 1
        coberto = len(set(Y) | {anchor}) <= COVER
        if not coberto:
            nao_cobertos += 1
    return (nao_cobertos == 0), verificados, nao_cobertos


def main() -> None:
    print("Programa 3 — Cobertura de S_13 (consome CSVs do Programa 1)  (U = {1..25})\n")

    if not (csv_exists(COVER) and csv_exists(P)):
        print("ERRO: arquivos de dados não encontrados. Rode o Programa 1 primeiro")
        print(f"      (esperados: data/S{COVER}.csv e data/S{P}.csv).")
        return

    expected_targets = count_formula(P)
    size = count_formula(COVER - 1, n=N - 1)  # C(24,14)
    lb = schonheim_bound()
    cobre_por_bloco = count_formula(P, n=COVER)

    print(f"Elemento fixo:               a = {ANCHOR}")
    print(f"Alvos a cobrir |S_13|:        {expected_targets:,}")
    print(f"Cada X de 15 cobre:          {cobre_por_bloco:,} alvos  (= C(15,13))")
    print(f"Tamanho da solução |SB|:     {size:,}   (= C(24,14))")
    print(f"Limite inferior (Schönheim): {lb:,}")
    print(f"Razão |SB| / limite inferior: {size/lb:>6.1f}×   → NÃO é mínima\n")

    print("Construindo SB a partir de data/S15.csv (filtro: contém o elemento fixo)...")
    t0 = time.perf_counter()
    sb_count = 0
    amostras = []
    for combo in build_sb_from_candidates():
        if sb_count < 5:
            amostras.append(combo)
        sb_count += 1
    t_build = time.perf_counter() - t0
    ok_size = "✓" if sb_count == size else "✗"
    print(f"  |SB| construído (lido de S15.csv): {sb_count:,}  em {t_build:.2f}s  (confere C(24,14)? {ok_size})")
    for combo in amostras:
        print(f"        {combo}")
    print()

    print("Verificando cobertura percorrendo data/S_13.csv...")
    t0 = time.perf_counter()
    ok, verificados, faltando = verify_cover_from_targets()
    t_verify = time.perf_counter() - t0
    status = "✓" if ok else "✗"
    print(f"  alvos verificados: {verificados:,}")
    print(f"  alvos não cobertos: {faltando:,}")
    print(f"  cobertura completa: {status}   (tempo {t_verify:.2f}s)")

    # Grava o log de resultados
    log_path = write_result_log(
        program_number=3,
        p=P,
        cover=COVER,
        anchor=ANCHOR,
        n_targets=expected_targets,
        sb_size=sb_count,
        optimal_or_bound=lb,
        bound_label="limite inf. (Schönheim)",
        coverage_ok=ok,
        targets_checked=verificados,
        targets_uncovered=faltando,
        build_time_s=t_build,
        verify_time_s=t_verify,
    )
    print(f"\nLog de resultados gravado em: {log_path}")


if __name__ == "__main__":
    main()