from itertools import combinations

import numpy as np

import combinatorics as C


def combo_to_bitmask(combo: tuple[int, ...]) -> int:
    """Converte uma tupla de elementos (1..N) em um inteiro bitmask."""
    mask = 0
    for x in combo:
        mask |= (1 << (x - 1))
    return mask


def bitmask_to_combo(mask: int, n: int) -> tuple[int, ...]:
    """Converte um bitmask de volta para a tupla ordenada de elementos."""
    return tuple(i + 1 for i in range(n) if (mask >> i) & 1)


def generate_bitmasks(p: int, universe: tuple[int, ...] = C.UNIVERSE) -> np.ndarray:
    """Gera todas as combinações de tamanho p como array NumPy de bitmasks (uint32)."""
    return np.fromiter(
        (combo_to_bitmask(c) for c in combinations(universe, p)),
        dtype=np.uint32,
    )
