"""
Representação NumPy das combinações para os Programas de cobertura (2 a 5).
"""

from typing import Iterable
import numpy as np
from combinatorics import N

# Tipos
BoolMatrix = np.ndarray  # forma (m, N), dtype=bool
BoolVector = np.ndarray  # forma (N,),   dtype=bool


def combo_to_row(combo: tuple[int, ...], n: int = N) -> BoolVector:
    """Converte uma combinação (tupla de inteiros 1..n) em vetor booleano de n posições."""
    row = np.zeros(n, dtype=bool)
    # combo guarda elementos 1..n; a coluna correspondente é o índice elemento-1.
    row[[x - 1 for x in combo]] = True
    return row


def row_to_combo(row: BoolVector) -> tuple[int, ...]:
    """Converte um vetor booleano de volta para a tupla ordenada de elementos (para exibição)."""
    return tuple(int(i + 1) for i in np.nonzero(row)[0])


def combos_to_matrix(combos: Iterable[tuple[int, ...]], n: int = N) -> BoolMatrix:
    """Materializa um iterável de combinações numa matriz booleana (m, n).

    ATENÇÃO: materializa tudo em memória. Para |S_13| ≈ 5,2 M, são ~130 MB.
    Use conscientemente nos Programas 2-5; a geração em si continua em streaming.
    """
    rows = [combo_to_row(c, n) for c in combos]
    if not rows:
        return np.zeros((0, n), dtype=bool)
    return np.vstack(rows)


def is_subset(y_row: BoolVector, x_row: BoolVector) -> bool:
    """Testa Y ⊆ X para duas combinações: todo elemento de Y está em X.

    Y ⊆ X  ⟺  não existe posição em Y que não esteja em X  ⟺  (Y & ~X) é tudo False.
    """
    return not np.any(y_row & ~x_row)


def covered_by_any(y_row: BoolVector, x_matrix: BoolMatrix) -> bool:
    """Testa se a combinação Y está contida em ALGUMA linha X de x_matrix (vetorizado).

    Para cada linha X: Y ⊆ X  ⟺  (Y & ~X) não tem nenhum True naquela linha.
    Calcula isso para todas as linhas de uma vez e verifica se alguma satisfaz.
    """
    # (~x_matrix) tem forma (m, n); y_row faz broadcast para (m, n).
    violations_por_linha = np.any(y_row & ~x_matrix, axis=1)  # True onde Y ⊄ X
    return bool(np.any(~violations_por_linha))


def coverage_count(x_row: BoolVector, targets: BoolMatrix) -> int:
    """Quantas combinações-alvo (linhas de `targets`) estão contidas em X.

    Útil no passo guloso: medir o 'ganho' de escolher X. Vetorizado sobre todos
    os alvos de uma vez.
    """
    # Para cada alvo Y (linha): Y ⊆ X ⟺ nenhuma posição de Y fora de X.
    violations = np.any(targets & ~x_row, axis=1)  # True onde Y ⊄ X
    return int(np.count_nonzero(~violations))