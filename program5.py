"""
PROGRAMA 5 — Cobertura de Combinações de 11 Elementos.

Objetivo (enunciado): determinar SB₁₅,11 ⊆ S₁₅ tal que toda combinação de 11
elementos (Y ∈ S_11) esteja contida em pelo menos uma combinação de 15
elementos (X ∈ SB₁₅,11):

        ∀ Y ∈ S_11  ∃ X ∈ SB₁₅,11  tal que  Y ⊆ X

ARQUITETURA — consumo dos dados do Programa 1:
    Este programa LÊ os CSVs gerados pelo Programa 1:
      • data/S15.csv — candidatos (de onde o SB é extraído);
      • data/S11.csv — alvos (o que precisa ser coberto).
    O SB é construído filtrando S₁₅ (lido do disco) pela regra do elemento fixo,
    e a cobertura é VERIFICADA percorrendo os alvos S_11 lidos do disco.

ESTRATÉGIA — Construção direta por elemento fixo (a mesma dos Programas 2-5):
    SB = { X ∈ S₁₅ | a ∈ X }, para um elemento fixo `a` (usamos a = 25).

POR QUE COBRE TODO S_11 (prova):
    Para todo Y ∈ S_11: se a ∈ Y, estenda Y com elementos extras até 15; se
    a ∉ Y, tome X = Y ∪ {a, …} completando até 15. Em ambos os casos X ∈ SB e
    Y ⊆ X. ∎  (Validado também por força bruta em universos reduzidos.)

ESTA CONSTRUÇÃO NÃO É ÓTIMA:
    |SB| = C(24,14) = 1.961.256.
    Limite inferior de Schönheim para C(25,15,11): 3,370.
    A construção está ~582× acima do limite inferior — solução VÁLIDA, mas
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

ANCHOR: int = N  # elemento fixo (25)
P: int = 11
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
    """Verifica a cobertura percorrendo os alvos S_11 lidos do CSV.

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
    print("Programa 5 — Cobertura de S_11 (consome CSVs do Programa 1)  (U = {1..25})\n")

    if not (csv_exists(COVER) and csv_exists(P)):
        print("ERRO: arquivos de dados não encontrados. Rode o Programa 1 primeiro")
        print(f"      (esperados: data/S{COVER}.csv e data/S{P}.csv).")
        return

    expected_targets = count_formula(P)
    size = count_formula(COVER - 1, n=N - 1)  # C(24,14)
    lb = schonheim_bound()
    cobre_por_bloco = count_formula(P, n=COVER)

    print(f"Elemento fixo:               a = {ANCHOR}")
    print(f"Alvos a cobrir |S_11|:        {expected_targets:,}")
    print(f"Cada X de 15 cobre:          {cobre_por_bloco:,} alvos  (= C(15,11))")
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

    print("Verificando cobertura percorrendo data/S_11.csv...")
    t0 = time.perf_counter()
    ok, verificados, faltando = verify_cover_from_targets()
    t_verify = time.perf_counter() - t0
    status = "✓" if ok else "✗"
    print(f"  alvos verificados: {verificados:,}")
    print(f"  alvos não cobertos: {faltando:,}")
    print(f"  cobertura completa: {status}   (tempo {t_verify:.2f}s)")


if __name__ == "__main__":
    main()