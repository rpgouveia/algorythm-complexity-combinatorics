"""
PROGRAMAS 2 a 5 — Cobertura de Combinações usando Algoritmo Randômico (GRASP-lite)

Este algotitmo reimplementa as otimizações de bitmask internamente para garantir que a 
avaliação seja extremamente rápida, mas adota uma estratégia probabilística:

    1. Sorteia um alvo Y AINDA NÃO COBERTO.
    2. Gera o conjunto restrito de candidatos (tamanho 15) que contêm Y.
    3. Sorteia uma amostra aleatória pequena desses candidatos.
    4. Escolhe o melhor candidato APENAS DENTRO DESSA AMOSTRA ALEATÓRIA.

Isso quebra o gargalo computacional das iterações iniciais, permitindo encontrar
boas soluções em tempo recorde.
"""

import time
from dataclasses import dataclass, field
from itertools import combinations
import numpy as np
import combinatorics as C


# Estrutura de Dados
@dataclass
class RandomResult:
    """Resultado de uma execução do randômico para um dado p."""
    p: int
    chosen: list[tuple[int, ...]]
    n_targets: int
    elapsed_s: float
    gains: list[int] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.chosen)

# Funções de Bitmask

def combo_para_bitmask(combo: tuple[int, ...]) -> int:
    """Converte uma tupla de elementos (1..N) em um inteiro bitmask (uint32)."""
    mask = 0
    for x in combo:
        mask |= (1 << (x - 1))
    return mask

def bitmask_para_combo(mask: int, n: int) -> tuple[int, ...]:
    """Converte um bitmask de volta para a tupla ordenada de elementos."""
    return tuple(i + 1 for i in range(n) if (mask >> i) & 1)

def gerar_bitmasks(p: int, universe: tuple[int, ...] = C.UNIVERSE) -> np.ndarray:
    """Gera todas as combinações de tamanho p como array NumPy de bitmasks."""
    return np.fromiter(
        (combo_para_bitmask(c) for c in combinations(universe, p)),
        dtype=np.uint32,
    )

def gerar_candidatos_por_alvo(alvo_mask: int, k: int, alvo_size: int, universe: tuple[int, ...]) -> np.ndarray:
    """Gera todos os blocos de tamanho k que contêm o alvo_mask."""
    faltam = k - alvo_size
    resto = [x for x in universe if not (alvo_mask >> (x - 1)) & 1]

    masks_extra = []
    for extra in combinations(resto, faltam):
        extra_mask = 0
        for x in extra:
            extra_mask |= (1 << (x - 1))
        masks_extra.append(alvo_mask | extra_mask)

    return np.array(masks_extra, dtype=np.uint32)

# Motor Randômico
def randomized_cover(
    p: int,
    k: int = 15,
    universe: tuple[int, ...] = C.UNIVERSE,
    sample_size: int = 5,
    max_iters: int | None = None,
    verbose: bool = False,
    log_every: int = 1
) -> RandomResult:
    """
    Executa a cobertura de forma randomizada (GRASP-lite).
    
    Args:
        p: tamanho dos alvos (ex: 14, 13, 12, 11).
        k: tamanho dos blocos candidatos (15).
        universe: universo de elementos (1 a 25).
        sample_size: quantos candidatos avaliar por alvo sorteado (controla a aleatoriedade).
        max_iters: limite de iterações (para testes rápidos). Passar None roda até o fim.
        verbose: se True, imprime log no estilo do seu console.
        log_every: de quantos em quantos passos imprime o log.
    """
    n = len(universe)
    t0 = time.perf_counter()
    
    targets = gerar_bitmasks(p, universe)
    n_targets = len(targets)
    
    if verbose:
        print(f"  alvos S_{p} gerados: {n_targets:,} em {time.perf_counter()-t0:.1f}s")
        print(f"  estratégia: Randômica com amostra de {sample_size} candidato(s) por iteração")

    covered = np.zeros(n_targets, dtype=bool)
    chosen_masks: list[int] = []
    gains: list[int] = []

    rng = np.random.default_rng()
    t_inicio = time.perf_counter()
    passo = 0

    while not covered.all():
        passo += 1
        if max_iters is not None and passo > max_iters:
            break

        # 1. Sorteia um alvo ainda não coberto
        idx_nao_cobertos = np.flatnonzero(~covered)
        alvo_idx = rng.choice(idx_nao_cobertos)
        alvo_mask = int(targets[alvo_idx])

        # 2. Gera candidatos válidos que contêm esse alvo exato
        cand_masks = gerar_candidatos_por_alvo(alvo_mask, k, p, universe)

        # 3. Sorteia uma amostra dos candidatos
        if sample_size > 0 and sample_size < len(cand_masks):
            cand_masks = rng.choice(cand_masks, size=sample_size, replace=False)

        # 4. Avalia a amostra usando vetorização veloz do NumPy
        targets_und = targets[idx_nao_cobertos]
        melhor_gain = -1
        melhor_mask = -1
        melhor_cobertura = None

        for cand_mask in cand_masks:
            cand_mask_int = np.uint32(cand_mask)
            # O alvo é coberto se (alvo AND NOT candidato) for 0
            cobre = (targets_und & ~cand_mask_int) == 0
            gain = int(cobre.sum())
            
            if gain > melhor_gain:
                melhor_gain = gain
                melhor_mask = int(cand_mask)
                melhor_cobertura = cobre

        # 5. Registra o vencedor da amostra e aplica a cobertura
        covered[idx_nao_cobertos] |= melhor_cobertura
        chosen_masks.append(melhor_mask)
        gains.append(melhor_gain)

        if verbose and (passo % log_every == 0 or covered.all()):
            elapsed = time.perf_counter() - t_inicio
            print(
                f"  passo {passo:>6}: + {melhor_gain:>2} alvos | "
                f"{int(covered.sum()):>9,}/{n_targets:,} cobertos | "
                f"{elapsed:>7.1f}s decorridos"
            )

    elapsed = time.perf_counter() - t_inicio
    chosen_combos = [bitmask_para_combo(m, n) for m in chosen_masks]

    return RandomResult(
        p=p,
        chosen=chosen_combos,
        n_targets=n_targets,
        elapsed_s=elapsed,
        gains=gains,
    )


if __name__ == "__main__":
    print("=== Execução Completa do Algoritmo Randômico (n=25, k=15, p=14) ===")
    
    # max_iters=None e log_every=1 para rodar até o fim mostrando todos os passos
    resultado = randomized_cover(
        p=14, 
        k=15, 
        sample_size=3,    # Avalia 3 candidatos randômicos por iteração
        verbose=True, 
        log_every=1       # Log passo a passo reativado
    )
    
    print(f"\nCobertura finalizada!")
    print(f"Tamanho do conjunto escolhido (SB): {resultado.size:,} combinações")
    print(f"Tempo total: {resultado.elapsed_s:.1f} segundos")
    if resultado.size > 0:
        print(f"Ritmo médio global: {resultado.elapsed_s/resultado.size:.3f} s/iteração")