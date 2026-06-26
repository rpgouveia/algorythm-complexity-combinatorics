"""
Cada combinação é representada por uma tupla ordenada de inteiros.
"""

from itertools import combinations
from math import comb
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    import numpy as np

# Universo do problema

N: int = 25
"""Tamanho do universo U."""

UNIVERSE: tuple[int, ...] = tuple(range(1, N + 1))
"""U = {1, 2, ..., 25}."""

TARGET_SIZES: tuple[int, ...] = (15, 14, 13, 12, 11)
"""Tamanhos p pedidos no enunciado (S₁₅, S₁₄, S₁₃, S₁₂, S₁₁), nessa ordem."""


# Geração

def combinations_of_size(
    p: int, universe: tuple[int, ...] = UNIVERSE
) -> Iterator[tuple[int, ...]]:
    """Itera, em streaming, todas as combinações de tamanho ``p`` de ``universe``.

    Cada combinação é uma tupla ordenada (ordem lexicográfica). Como o universo
    é um parâmetro, a mesma função serve para enumerar os subconjuntos de
    qualquer combinação dada, e não só de U.

    Args:
        p: tamanho de cada combinação (0 <= p <= len(universe)).
        universe: conjunto-base do qual extrair as combinações.

    Returns:
        Iterador de tuplas ordenadas de ``p`` elementos.

    Raises:
        ValueError: se ``p`` estiver fora de [0, len(universe)].

        O(1)
    """
    if not 0 <= p <= len(universe):
        raise ValueError(f"p deve estar em [0, {len(universe)}]; recebido p={p}.")
    return combinations(universe, p)


def count_formula(p: int, n: int = N) -> int:
    """Cardinalidade esperada |S_p| = C(n, p) = n! / (p! · (n-p)!).
    
    O(1)
    """
    return comb(n, p)


def materialize_matrix(p: int, universe: tuple[int, ...] = UNIVERSE) -> "np.ndarray":
    """Materializa S_p como matriz booleana NumPy de forma (|S_p|, N).

    Conveniência para os Programas de cobertura (2-5), que precisam do conjunto
    inteiro em memória num formato vetorizável. A geração continua sendo feita
    em streaming por ``combinations_of_size``; só a conversão final é em bloco.

    Importa NumPy localmente para que o Programa 1 (que não usa matriz) não
    dependa de NumPy.

    ATENÇÃO de memória: ~25 bytes por combinação. |S_13| ≈ 5,2 M → ~130 MB.

    O(1)
    """
    from representations import combos_to_matrix

    return combos_to_matrix(combinations_of_size(p, universe))


def materialize(p: int) -> list[tuple[int, ...]]:
    """Materializa todas as combinações de tamanho ``p`` numa lista.

    ATENÇÃO — uso restrito: esta função carrega TODAS as combinações na memória
    de uma só vez. Para os tamanhos-alvo do trabalho (p = 11..15 sobre U), isso
    é inviável: |S_13| = 5.200.300 tuplas custariam vários GB de RAM.

    Destina-se APENAS a testes com ``p`` pequeno e/ou universos reduzidos. Para
    os conjuntos do enunciado, use sempre ``combinations_of_size`` em streaming.
    
    O(C
    """
    return list(combinations_of_size(p))
