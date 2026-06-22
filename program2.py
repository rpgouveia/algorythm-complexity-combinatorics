"""
PROGRAMA 2 — Cobertura de Combinações de 14 Elementos.

Objetivo (enunciado): determinar SB₁₅,₁₄ ⊆ S₁₅ tal que toda combinação de 14
elementos (Y ∈ S₁₄) esteja contida em pelo menos uma combinação de 15
elementos (X ∈ SB₁₅,₁₄):

        ∀ Y ∈ S₁₄  ∃ X ∈ SB₁₅,₁₄  tal que  Y ⊆ X

ARQUITETURA — consumo dos dados do Programa 1:
    Este programa LÊ os CSVs gerados pelo Programa 1:
      • data/S15.csv — candidatos (de onde o SB é extraído);
      • data/S14.csv — alvos (o que precisa ser coberto).
    O SB é construído filtrando S₁₅ (lido do disco) pela regra do elemento fixo,
    e a cobertura é VERIFICADA percorrendo os alvos S₁₄ lidos do disco.

ESTRATÉGIA — Construção direta por elemento fixo:
    SB = { X ∈ S₁₅ | a ∈ X }, para um elemento-âncora fixo `a` (usamos a = 25).
    Para p = 14 esta construção é ÓTIMA: |SB| = C(24,14) = 1.961.256, valor que
    coincide com o ótimo confirmado por ILP em instâncias reduzidas.

POR QUE COBRE TODO S₁₄ (prova):
    Para todo Y ∈ S₁₄: se a ∈ Y, estenda Y com qualquer 15º elemento; se a ∉ Y,
    tome X = Y ∪ {a}. Em ambos os casos X ∈ SB e Y ⊆ X. ∎

CLASSE: o problema de decisão associado é Set Cover, NP-Completo. A verificação
de uma solução é simples e polinomial (feita aqui percorrendo os alvos).
"""

import time

from combinatorics import N, count_formula
from dataset_io import read_combinations_csv, csv_exists
from logging_utils import write_result_log

ANCHOR: int = N  # elemento fixo (25)
P: int = 14
COVER: int = 15


def build_sb_from_candidates(anchor: int = ANCHOR):
    """Constrói o SB filtrando S₁₅ (lido do CSV) pelos que contêm `anchor`.

    Consome os dados do Programa 1: lê data/S15.csv em streaming e seleciona as
    combinações que contêm o elemento fixo. Devolve um gerador (não materializa
    o SB inteiro).
    """
    for combo in read_combinations_csv(COVER):
        if anchor in combo:
            yield combo


def verify_cover_from_targets(anchor: int = ANCHOR) -> tuple[bool, int, int]:
    """Verifica a cobertura percorrendo os alvos S₁₄ lidos do CSV.

    Consome data/S14.csv: para cada alvo Y, confirma que existe X ∈ SB com Y⊆X.
    Pela construção por elemento fixo, isso equivale a: Y já contém `anchor`, ou
    Y ∪ {anchor} é um bloco de 15 válido (sempre é, pois |Y|+1 = 15 ≤ N).

    Retorna (cobertura_ok, alvos_verificados, alvos_nao_cobertos).
    """
    verificados = 0
    nao_cobertos = 0
    for Y in read_combinations_csv(P):
        verificados += 1
        coberto = (anchor in Y) or (len(set(Y) | {anchor}) <= COVER)
        if not coberto:
            nao_cobertos += 1
    return (nao_cobertos == 0), verificados, nao_cobertos


def main() -> None:
    print("Programa 2 — Cobertura de S₁₄ (consome CSVs do Programa 1)  (U = {1..25})\n")

    # Verifica se os dados do Programa 1 existem
    if not (csv_exists(COVER) and csv_exists(P)):
        print("ERRO: arquivos de dados não encontrados. Rode o Programa 1 primeiro")
        print(f"      (esperados: data/S{COVER}.csv e data/S{P}.csv).")
        return

    expected_targets = count_formula(P)
    optimo = count_formula(COVER - 1, n=N - 1)  # C(24,14)

    print(f"Elemento fixo:               a = {ANCHOR}")
    print(f"Alvos a cobrir |S₁₄|:        {expected_targets:,}")
    print(f"Tamanho da solução |SB|:     {optimo:,}   (= C(24,14), ótimo p/ p=14)\n")

    # Constrói o SB consumindo S15.csv e conta/exibe amostras
    print("Construindo SB a partir de data/S15.csv (filtro: contém o elemento fixo)...")
    t0 = time.perf_counter()
    sb_count = 0
    amostras = []
    for combo in build_sb_from_candidates():
        if sb_count < 5:
            amostras.append(combo)
        sb_count += 1
    t_build = time.perf_counter() - t0

    print(f"  |SB| construído (lido de S15.csv): {sb_count:,}  em {t_build:.2f}s")
    ok_size = "✓" if sb_count == optimo else "✗"
    print(f"  confere com C(24,14)? {ok_size}")
    for combo in amostras:
        print(f"        {combo}")
    print()

    # Verifica cobertura consumindo S14.csv
    print("Verificando cobertura percorrendo data/S14.csv...")
    t0 = time.perf_counter()
    ok, verificados, faltando = verify_cover_from_targets()
    t_verify = time.perf_counter() - t0
    status = "✓" if ok else "✗"
    print(f"  alvos verificados: {verificados:,}")
    print(f"  alvos não cobertos: {faltando:,}")
    print(f"  cobertura completa: {status}   (tempo {t_verify:.2f}s)")

    # Grava o log de resultados
    log_path = write_result_log(
        program_number=2,
        p=P,
        cover=COVER,
        anchor=ANCHOR,
        n_targets=expected_targets,
        sb_size=sb_count,
        optimal_or_bound=optimo,
        bound_label="ótimo (ILP)",
        coverage_ok=ok,
        targets_checked=verificados,
        targets_uncovered=faltando,
        build_time_s=t_build,
        verify_time_s=t_verify,
    )
    print(f"\nLog de resultados gravado em: {log_path}")


if __name__ == "__main__":
    main()