"""
Núcleo do algoritmo GULOSO (greedy) para os Programas 2 a 5.

Problema (Set Cover): dado o universo de alvos S_p (todas as combinações de
tamanho p de U) e a família de candidatos S_15 (combinações de tamanho 15),
escolher um subconjunto SB ⊆ S_15 o menor possível tal que toda combinação de
S_p esteja contida em pelo meno um X ∈ SB.

Estratégia GULOSA (versão ingênua / clássica de Set Cover):
    A cada passo, escolher o candidato X ∈ S_15 que cobre o MAIOR número de
    alvos AINDA DESCOBERTOS. Marcar esses alvos como cobertos e repetir até não
    sobrar alvo descoberto.

Por que "ingênua": a cada iteração reavalia TODOS os candidatos de S_15 contra
todos os alvos. É simples de entender, mas é o passo caro tornado-se um gargalo.
Isto justifica as otimizações como o paralelismo.
"""

import time
from dataclasses import dataclass, field
import numpy as np
import combinatorics as C
from representations import BoolMatrix, row_to_combo


@dataclass
class GreedyResult:
    """Resultado de uma execução do guloso para um dado ``p``."""

    p: int
    """Tamanho dos alvos cobertos (14, 13, 12 ou 11)."""

    chosen: list[tuple[int, ...]]
    """Combinações de 15 selecionadas (SB), como tuplas ordenadas."""

    n_targets: int
    """|S_p| — quantos alvos havia para cobrir."""

    elapsed_s: float
    """Tempo de execução do guloso, em segundos."""

    gains: list[int] = field(default_factory=list)
    """Ganho (alvos novos cobertos) de cada escolha, na ordem em que ocorreram."""

    @property
    def size(self) -> int:
        """Tamanho de SB (número de combinações de 15 escolhidas)."""
        return len(self.chosen)


def _coverage_matrix(candidates: BoolMatrix, targets: BoolMatrix) -> np.ndarray:
    """Matriz de cobertura booleana de forma (n_candidatos, n_alvos).

    Entrada ``[i, j]`` é True sse o alvo ``j`` está contido no candidato ``i``,
    isto é, se todo elemento do alvo j também pertence ao candidato i.

    Y ⊆ X  ⟺  não há elemento de Y fora de X  ⟺  (Y AND NOT X) é tudo False.

    ATENÇÃO de memória: esta matriz tem n_candidatos × n_alvos entradas. Para
    S_15 × S_14 seria 3,2 M × 4,4 M — inviável de materializar inteira. Por isso
    o guloso abaixo NÃO chama esta função no caso completo; ela existe para
    clareza conceitual e para uso em instâncias pequenas (testes/força bruta).
    """
    # (n_cand, 1, N) AND NOT (1, n_alvos, N) → reduz no eixo N. Custa muita RAM.
    raise NotImplementedError(
        "Materializar a matriz de cobertura completa é inviável para S_15×S_p; "
        "o guloso avalia candidato a candidato. Função mantida apenas como "
        "documentação da relação de cobertura."
    )


def greedy_cover(
    p: int,
    candidates: BoolMatrix | None = None,
    targets: BoolMatrix | None = None,
    verbose: bool = False,
) -> GreedyResult:
    """Executa o guloso ingênuo para cobrir S_p usando combinações de S_15.

    Args:
        p: tamanho dos alvos a cobrir (14, 13, 12 ou 11).
        candidates: matriz booleana de S_15 (n_cand, N). Se None, é materializada.
        targets: matriz booleana de S_p (n_alvos, N). Se None, é materializada.
        verbose: imprime o progresso de cada escolha.

    Returns:
        GreedyResult com SB, tamanho, tempos e ganhos por passo.
    """
    if candidates is None:
        candidates = C.materialize_matrix(15)
    if targets is None:
        targets = C.materialize_matrix(p)

    n_cand = candidates.shape[0]
    n_targets = targets.shape[0]

    # Para evitar recomputar "quais alvos cada candidato cobre" a cada iteração,
    # pré-computamos UMA vez, por candidato, o conjunto de alvos que ele cobre.
    # Guardamos como matriz booleana (n_cand, n_targets): linha i = alvos cobertos
    # pelo candidato i. Este é o passo de memória/tempo dominante do ingênuo.
    #
    # cobre[i, j] = alvo j ⊆ candidato i.
    # Calculado em blocos de candidatos para não estourar RAM de uma só vez.
    covered = np.zeros(n_targets, dtype=bool)   # alvos já cobertos por SB
    chosen: list[tuple[int, ...]] = []
    gains: list[int] = []

    t0 = time.perf_counter()

    # Pré-cálculo da relação de cobertura por blocos.
    # cover_rows[i] é um vetor booleano (n_targets,) dos alvos cobertos pelo cand i.
    cover_rows = _precompute_coverage(candidates, targets)

    # Laço guloso: enquanto houver alvo descoberto, escolhe o candidato de maior
    # ganho marginal (alvos novos cobertos).
    while not covered.all():
        undiscovered = ~covered
        # ganho de cada candidato = quantos alvos AINDA descobertos ele cobre.
        # (cover_rows AND undiscovered) somado por linha.
        gains_per_cand = (cover_rows & undiscovered).sum(axis=1)
        best_i = int(np.argmax(gains_per_cand))
        best_gain = int(gains_per_cand[best_i])

        if best_gain == 0:
            # Não deveria ocorrer nesta instância (sempre satisfatível); guarda
            # de segurança contra laço infinito caso algo esteja inconsistente.
            raise RuntimeError(
                "Nenhum candidato cobre alvos restantes — instância inesperadamente "
                "insatisfatível ou erro de construção das matrizes."
            )

        chosen.append(row_to_combo(candidates[best_i]))
        gains.append(best_gain)
        covered |= cover_rows[best_i]

        if verbose:
            print(
                f"  passo {len(chosen):>3}: escolhe {chosen[-1]} "
                f"(+{best_gain} alvos, {covered.sum():,}/{n_targets:,})"
            )

    elapsed = time.perf_counter() - t0

    return GreedyResult(
        p=p,
        chosen=chosen,
        n_targets=n_targets,
        elapsed_s=elapsed,
        gains=gains,
    )


def _precompute_coverage(
    candidates: BoolMatrix, targets: BoolMatrix, block: int = 256
) -> np.ndarray:
    """Pré-calcula, para cada candidato, quais alvos ele cobre.

    Retorna matriz booleana (n_cand, n_targets) onde [i, j] = alvo_j ⊆ cand_i.

    Processa os candidatos em blocos para limitar o pico de memória do cálculo
    intermediário (o produto broadcast é (block, n_targets, N)).

    ATENÇÃO: o resultado em si tem n_cand × n_targets bits. Para S_15 × S_14
    (~3,2 M × ~4,4 M) isso é inviável — ~1,8 Tbit. Esta função, e o guloso
    ingênuo que a usa, são portanto destinados a instâncias REDUZIDAS (testes,
    universos menores, ou p alto onde os conjuntos são menores). A otimização é 
    necessária para o tratamento do caso completo de U=25.
    """
    n_cand = candidates.shape[0]
    n_targets = targets.shape[0]
    result = np.zeros((n_cand, n_targets), dtype=bool)

    for start in range(0, n_cand, block):
        end = min(start + block, n_cand)
        cand_block = candidates[start:end]  # (b, N)
        # alvo_j ⊆ cand_i ⟺ nenhum elemento de alvo_j fora de cand_i.
        # violação = existe elemento do ALVO que NÃO está no CANDIDATO:
        #   targets AND NOT cand_block, reduzido no eixo N.
        # (1, n_targets, N) AND NOT (b, 1, N) → any sobre N.
        violations = np.any(
            targets[None, :, :] & ~cand_block[:, None, :], axis=2
        )  # (b, n_targets): True onde alvo NÃO está contido
        result[start:end] = ~violations

    return result