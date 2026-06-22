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
import os
import concurrent.futures
from dataclasses import dataclass, field
from itertools import combinations
import numpy as np
import combinatorics as C
from bitmask import combo_to_bitmask, bitmask_to_combo, generate_bitmasks


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

# Geração de candidatos (bitmask)

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
    log_every: int = 1,
    seed: int | None = None,
    worker_id: int | None = None
) -> RandomResult:
    """
    Executa a cobertura de forma randomizada (GRASP-lite).
    """
    n = len(universe)
    t0 = time.perf_counter()
    
    targets = generate_bitmasks(p, universe)
    n_targets = len(targets)
    
    # Prefixo para identificar qual núcleo está printando
    prefix = f"[Worker {worker_id}]" if worker_id is not None else ""
    
    if verbose:
        print(f"{prefix}  alvos S_{p} gerados: {n_targets:,} em {time.perf_counter()-t0:.1f}s")
        print(f"{prefix}  estratégia: Randômica com amostra de {sample_size} candidato(s) por iteração")

    covered = np.zeros(n_targets, dtype=bool)
    chosen_masks: list[int] = []
    gains: list[int] = []

    rng = np.random.default_rng(seed)
    t_inicio = time.perf_counter()
    passo = 0

    while not covered.all():
        passo += 1
        if max_iters is not None and passo > max_iters:
            break

        idx_nao_cobertos = np.flatnonzero(~covered)
        alvo_idx = rng.choice(idx_nao_cobertos)
        alvo_mask = int(targets[alvo_idx])

        cand_masks = gerar_candidatos_por_alvo(alvo_mask, k, p, universe)

        if sample_size > 0 and sample_size < len(cand_masks):
            cand_masks = rng.choice(cand_masks, size=sample_size, replace=False)

        targets_und = targets[idx_nao_cobertos]
        melhor_gain = -1
        melhor_mask = -1
        melhor_cobertura = None

        for cand_mask in cand_masks:
            cand_mask_int = np.uint32(cand_mask)
            cobre = (targets_und & ~cand_mask_int) == 0
            gain = int(cobre.sum())
            
            if gain > melhor_gain:
                melhor_gain = gain
                melhor_mask = int(cand_mask)
                melhor_cobertura = cobre

        covered[idx_nao_cobertos] |= melhor_cobertura
        chosen_masks.append(melhor_mask)
        gains.append(melhor_gain)

        # Print original restaurado (com o prefixo do Worker)
        if verbose and (passo % log_every == 0 or covered.all()):
            elapsed = time.perf_counter() - t_inicio
            print(
                f"{prefix}  passo {passo:>6}: + {melhor_gain:>2} alvos | "
                f"{int(covered.sum()):>9,}/{n_targets:,} cobertos | "
                f"{elapsed:>7.1f}s decorridos"
            )

    elapsed = time.perf_counter() - t_inicio
    chosen_combos = [bitmask_to_combo(m, n) for m in chosen_masks]

    return RandomResult(
        p=p,
        chosen=chosen_combos,
        n_targets=n_targets,
        elapsed_s=elapsed,
        gains=gains,
    )


if __name__ == "__main__":
    print("=== Execução Paralela do Algoritmo Randômico (n=25, k=15, p=14) ===")
    
    P_ALVO = 14
    EXECUCOES_TOTAIS = 10
    WORKERS = os.cpu_count() or 4
    
    print(f"Iniciando {EXECUCOES_TOTAIS} execuções em {WORKERS} processos...\n")
    
    t_inicio_global = time.perf_counter()
    melhor_resultado = None

    with concurrent.futures.ProcessPoolExecutor(max_workers=WORKERS) as executor:
        futures = []
        
        for i in range(EXECUCOES_TOTAIS):
            future = executor.submit(
                randomized_cover,
                p=P_ALVO,
                sample_size=3,
                verbose=True,       # Logs internos religados!
                log_every=1,
                seed=42 + i,
                worker_id=i + 1     # Identifica de qual processo vem o log
            )
            futures.append(future)

        # Apenas monitora o término para pegar a melhor solução
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if melhor_resultado is None or res.size < melhor_resultado.size:
                melhor_resultado = res

    t_total_global = time.perf_counter() - t_inicio_global
    
    # Bloco final de prints idêntico à sua versão original
    print(f"\nCobertura finalizada!")
    if melhor_resultado is not None:
        print(f"Tamanho do conjunto escolhido (SB): {melhor_resultado.size:,} combinações")
        print(f"Tempo total (Bateria completa): {t_total_global:.1f} segundos")
        print(f"Tempo da melhor execução isolada: {melhor_resultado.elapsed_s:.1f} segundos")
        if melhor_resultado.size > 0:
            print(f"Ritmo médio global da melhor: {melhor_resultado.elapsed_s/melhor_resultado.size:.3f} s/iteração")