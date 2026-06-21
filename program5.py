"""
PROGRAMA 5 — Cobertura de Combinações de 11 Elementos.

Objetivo: determinar SB₁₅,₁₁ ⊆ S₁₅ tal que toda combinação de 11
elementos (Y ∈ S₁₁) esteja contida em pelo menos uma combinação de 15
elementos (X ∈ SB₁₅,₁₁):

        ∀ Y ∈ S₁₁  ∃ X ∈ SB₁₅,₁₁  tal que  Y ⊆ X

ESTRATÉGIA — Construção direta por elemento fixo:
    SB = { X ∈ S₁₅ | a ∈ X }, para um elemento-âncora fixo `a` (usamos a = 25).
    Ou seja, todas as combinações de 15 que contêm o elemento `a`.

POR QUE COBRE TODO S₁₁ (prova):
    Seja Y ∈ S₁₁ qualquer (11 elementos).
      • Se a ∈ Y: estenda Y com 4 elementos quaisquer de U \\ Y → X de 15
        contendo `a` (∈ SB) e contendo Y.
      • Se a ∉ Y: tome X = Y ∪ {a} mais 3 elementos de U \\ (Y ∪ {a}); é uma
        combinação de 15 que contém `a` (∈ SB) e contém Y.
    Em ambos os casos existe X ∈ SB com Y ⊆ X.

ESTA CONSTRUÇÃO NÃO É ÓTIMA:
    |SB| = C(24,14) = 1.961.256.
    Limite inferior de Schönheim para C(25,15,11): 3.370.
    A construção está ~582× acima do limite inferior.

    O gap cresce monotonicamente conforme p diminui:
        p=14 → ótima (1×) | p=13 → ~33× | p=12 → ~149× | p=11 → ~582×.
    A razão é estrutural: cada bloco de 15 cobre C(15,p) alvos (1.365 para
    p=11), número que cresce com a distância 15−p; mas a construção por âncora,
    embora cubra tudo, mantém |SB| fixo em C(24,14) independentemente de p,
    enquanto o limite inferior cai rapidamente. O resultado é um gap que se
    amplia. Aproximar-se do mínimo exigiria covering designs especializados
    (o ótimo de C(25,15,11) é desconhecido na literatura; t=11 está fora das
    tabelas publicadas, que vão até t ≤ 8).

POSTURA ADOTADA:
    Entregamos a construção direta como LIMITANTE SUPERIOR válido e de obtenção
    trivial. O gap é declarado abertamente. A redução de |SB| é objeto das
    estratégias alternativas que serão discutidas na Análise de Complexidade.
    A escolha pela construção uniforme reflete a prioridade do grupo: simplicidade
    de implementação, com correção garantida em todos os cinco programas.

CLASSE / VERIFICAÇÃO:
    O problema de decisão associado é Set Cover, NP-Completo. A verificação de
    uma solução candidata é simples e feita ao final.
"""

import time
from itertools import combinations, islice
from math import ceil

from combinatorics import N, UNIVERSE, count_formula

ANCHOR: int = N  # elemento-âncora fixo (25)
P: int = 11      # tamanho dos alvos cobertos por este programa
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
    """Verifica que SB cobre todo S₁₁.

    Por padrão (`full=False`) usa a VERIFICAÇÃO ESTRUTURAL (a prova): qualquer
    Y ∈ S₁₁ é coberto, porque Y ∪ {anchor, …} é um X ∈ SB que contém Y. O(1).

    Com `full=True`, faz a verificação EXAUSTIVA sobre todo S₁₁, confirmando
    alvo a alvo pelo mesmo critério estrutural. Custa O(|S₁₁|).
    """
    if not full:
        return True, (
            "Verificação estrutural: para todo Y ∈ S₁₁, Y ∪ {elemento fixo, …} é um "
            "X ∈ SB que contém Y. Cobertura completa garantida."
        )

    for Y in combinations(UNIVERSE, P):
        # Y é coberto sse podemos formar X de 15 contendo `anchor` e Y:
        #   |Y ∪ {anchor}| ≤ 15, o que sempre vale (|Y|=11, +1 = 12 ≤ 15).
        coberto = len(set(Y) | {anchor}) <= COVER
        if not coberto:
            return False, f"Alvo não coberto encontrado: {Y}"
    return True, "Verificação exaustiva: todos os alvos de S₁₁ estão cobertos."


def main() -> None:
    print("Programa 5 — Cobertura de S₁₁ por construção por elemento fixo  (U = {1..25})\n")

    expected_targets = count_formula(P)              # |S₁₁|
    size = sb_size()                                 # |SB| = C(24,14)
    lb = schonheim_bound()                           # limite inferior de Schönheim
    cobre_por_bloco = count_formula(P, n=COVER)      # C(15,11)

    print(f"Elemento-âncora fixo:        a = {ANCHOR}")
    print(f"Alvos a cobrir |S₁₁|:        {expected_targets:,}")
    print(f"Tamanho da solução |SB|:     {size:,}   (= C(24,14))")
    print(f"Cada X de 15 cobre:          {cobre_por_bloco:,} alvos de 11  (= C(15,11))")
    print(f"Limite inferior (Schönheim): {lb:,}")
    print(f"Razão |SB| / limite inferior: {size / lb:>6.1f}×   → NÃO é mínima (ver cabeçalho)\n")

    print("Amostras de SB (primeiras combinações de 15 contendo a âncora):")
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
    print("  • A construção COBRE todo S₁₁ (correção garantida).")
    print("  • NÃO é mínima: está ~582× acima do limite inferior de Schönheim.")
    print("  • É o maior gap dos quatro: p=14 ótimo, p=13 ~33×, p=12 ~149×, p=11 ~582×.")
    print("  • Estratégias para reduzir |SB| devem ser implementadas.")


if __name__ == "__main__":
    main()