"""
Cada combinação é representada por uma tupla ordenada de inteiros.
"""

from itertools import combinations
from math import comb
from typing import Iterator

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
    """
    if not 0 <= p <= len(universe):
        raise ValueError(f"p deve estar em [0, {len(universe)}]; recebido p={p}.")
    return combinations(universe, p)


def count_formula(p: int, n: int = N) -> int:
    """Cardinalidade esperada |S_p| = C(n, p) = n! / (p! · (n-p)!)."""
    return comb(n, p)


def materialize(p: int) -> list[tuple[int, ...]]:
    """Materializa todas as combinações de tamanho ``p`` numa lista.
    """
    return list(combinations_of_size(p))
