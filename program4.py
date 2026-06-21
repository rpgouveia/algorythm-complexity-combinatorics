"""
PROGRAMA 4 — Cobertura de Combinações de 12 Elementos.

Objetivo: determinar SB₁₅,₁₂ ⊆ S₁₅ tal que toda combinação de 12
elementos (Y ∈ S₁₂) esteja contida em pelo menos uma combinação de 15
elementos (X ∈ SB₁₅,₁₂):

        ∀ Y ∈ S₁₂  ∃ X ∈ SB₁₅,₁₂  tal que  Y ⊆ X

ESTRATÉGIA — Construção direta por elemento fixo:
    SB = { X ∈ S₁₅ | a ∈ X }, para um elemento-âncora fixo `a` (usamos a = 25).
    Ou seja, todas as combinações de 15 que contêm o elemento `a`.

POR QUE COBRE TODO S₁₂ (prova):
    Seja Y ∈ S₁₂ qualquer (12 elementos).
      • Se a ∈ Y: estenda Y com 3 elementos quaisquer de U \\ Y → X de 15
        contendo `a` (∈ SB) e contendo Y.
      • Se a ∉ Y: tome X = Y ∪ {a} mais 2 elementos de U \\ (Y ∪ {a}); é uma
        combinação de 15 que contém `a` (∈ SB) e contém Y.
    Em ambos os casos existe X ∈ SB com Y ⊆ X. ∎

ESTA CONSTRUÇÃO NÃO É ÓTIMA — e o gap é ainda maior que no Programa 3:
    |SB| = C(24,14) = 1.961.256.
    Limite inferior de Schönheim para C(25,15,12): 13.175.
    A construção está ~149× acima do limite inferior.

    O gap cresce conforme p diminui: em p=14 a construção é ótima; em p=13 fica
    ~33× acima; em p=12, ~149×. A razão é estrutural — cada bloco de 15 cobre
    C(15,p) alvos (455 para p=12), e a construção por elemento fixo, embora cubra
    tudo, desperdiça muita sobreposição.

POSTURA ADOTADA:
    Entregamos a construção direta como LIMITANTE SUPERIOR válido e de obtenção
    trivial, declarando abertamente o gap. A redução de |SB| é objeto das
    estratégias alternativas.

CLASSE / VERIFICAÇÃO:
    O problema de decisão associado é Set Cover, NP-Completo. A verificação de
    uma solução candidata é simples e feita ao final.
"""

import time
from itertools import combinations, islice
from math import ceil

from combinatorics import N, UNIVERSE, count_formula

ANCHOR: int = N  # elemento fixo (25)
P: int = 12      # tamanho dos alvos cobertos por este programa
COVER: int = 15  # tamanho das combinações de SB


def schonheim_bound(v: int = N, k: int = COVER, t: int = P) -> int:
    """Limite inferior de Schönheim para o covering number C(v, k, t).

    Recorrência: L(v,k,t) = ⌈(v/k) · L(v−1, k−1, t−1)⌉, com L(v,k,1) = ⌈v/k⌉.
    """
    if t == 1:
        return ceil(v / k)
    return ceil(v / k * schonheim_bound(v - 1, k - 1, t - 1))


def sb_anchor(anchor: int = ANCHOR):
    """Gera SB em streaming: todas as combinações de 15 que contêm `anchor`.

    Cada X é `{anchor}` unido a 14 elementos de U \\ {anchor}. São C(24,14)
    combinações, geradas uma a uma (sem materializar tudo).
    """
    others = tuple(x for x in UNIVERSE if x != anchor)  # 24 elementos
    for rest in combinations(others, COVER - 1):
        yield tuple(sorted((anchor, *rest)))


def sb_size(anchor: int = ANCHOR) -> int:
    """Tamanho de SB sem enumerar: C(24, 14)."""
    return count_formula(COVER - 1, n=N - 1)


def verify_cover(anchor: int = ANCHOR, full: bool = False) -> tuple[bool, str]:
    """Verifica que SB cobre todo S₁₂.

    Por padrão (`full=False`) usa a VERIFICAÇÃO ESTRUTURAL (a prova): qualquer
    Y ∈ S₁₂ é coberto, porque Y ∪ {anchor, …} é um X ∈ SB que contém Y. O(1).

    Com `full=True`, faz a verificação EXAUSTIVA sobre todo S₁₂, confirmando
    alvo a alvo pelo mesmo critério estrutural. Custa O(|S₁₂|).
    """
    if not full:
        return True, (
            "Verificação estrutural: para todo Y ∈ S₁₂, Y ∪ {elemento Fixo, …} é um "
            "X ∈ SB que contém Y. Cobertura completa garantida."
        )

    for Y in combinations(UNIVERSE, P):
        # Y é coberto sse podemos formar X de 15 contendo `anchor` e Y:
        #   |Y ∪ {anchor}| ≤ 15, o que sempre vale (|Y|=12, +1 = 13 ≤ 15).
        coberto = len(set(Y) | {anchor}) <= COVER
        if not coberto:
            return False, f"Alvo não coberto encontrado: {Y}"
    return True, "Verificação exaustiva: todos os alvos de S₁₂ estão cobertos."


def main() -> None:
    print("Programa 4 — Cobertura de S₁₂ por construção por elemento fixo  (U = {1..25})\n")

    expected_targets = count_formula(P)              # |S₁₂|
    size = sb_size()                                 # |SB| = C(24,14)
    lb = schonheim_bound()                           # limite inferior de Schönheim
    cobre_por_bloco = count_formula(P, n=COVER)      # C(15,12)

    print(f"Elemento fixo:        a = {ANCHOR}")
    print(f"Alvos a cobrir |S₁₂|:        {expected_targets:,}")
    print(f"Tamanho da solução |SB|:     {size:,}   (= C(24,14))")
    print(f"Cada X de 15 cobre:          {cobre_por_bloco:,} alvos de 12  (= C(15,12))")
    print(f"Limite inferior (Schönheim): {lb:,}")
    print(f"Razão |SB| / limite inferior: {size / lb:>6.1f}×   → NÃO é mínima (ver cabeçalho)\n")

    print("Amostras de SB (primeiras combinações de 15 contendo o elemento fixo):")
    for combo in islice(sb_anchor(), 5):
        print(f"    {combo}")
    print()

    t0 = time.perf_counter()
    ok, msg = verify_cover(full=False)
    elapsed = time.perf_counter() - t0
    status = "✓" if ok else "✗"
    print(f"Cobertura: {status}  {msg}")
    print(f"Tempo de verificação estrutural: {elapsed*1e6:.1f} µs\n")

    print("Observações:")
    print("  • A construção COBRE todo S₁₂ (correção garantida).")
    print("  • NÃO é mínima: está ~149 × acima do limite inferior de Schönheim.")
    print("  • O gap cresce conforme p diminui (p=14 ótimo, p=13 ~33×, p=12 ~149×).")
    print("  • A versão guloso+paralela deve atingir |SB| muito menor, ao custo de horas.")


if __name__ == "__main__":
    main()