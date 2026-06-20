"""
PROGRAMA 4 — Cobertura de Combinações de 12 Elementos
Versão final: estratégia BITWISE (bitmask) + geração de candidatos restrita ao
alvo não-coberto + avaliação vetorizada com NumPy + PARALELISMO (multiprocessing).

Resumo das otimizações aplicadas sobre a versão original (coverage_greedy.py):

  (1) BITMASK em vez de matriz booleana (N, 25) por linha.
      Cada combinação de 25 elementos cabe num único uint32. Isso reduz a
      avaliação de cobertura de uma operação O(N) por par (alvo, candidato)
      para uma operação O(1) (AND + comparação), e reduz a memória de
      ~25 bytes/alvo para 4 bytes/alvo.

  (2) GERAÇÃO DE CANDIDATOS A PARTIR DO ALVO NÃO-COBERTO.
      Em vez de testar os C(25,15)=3.268.760 candidatos possíveis a cada
      iteração, geram-se apenas os C(25-12,15-12)=C(13,3)=286 candidatos que
      contêm um alvo Y fixado. Redução de ~11.400x no espaço de busca por
      iteração (ver análise no enunciado, seção de complexidade).

  (3) AVALIAÇÃO VETORIZADA com NumPy (broadcasting sobre uint32), evitando
      laço Python alvo-a-alvo: o teste "alvo ⊆ candidato" é feito para TODOS
      os alvos de uma vez via (targets_bitmask & ~cand_mask) == 0.

  (4) PARALELISMO (multiprocessing) na avaliação dos candidatos de cada
      iteração. Os ~286 candidatos são divididos em chunks entre os processos
      do pool; cada processo avalia seu chunk contra o array de alvos NÃO-
      COBERTOS (compartilhado via multiprocessing.shared_memory, para não
      serializar ~5,2M elementos a cada iteração) e devolve o melhor candidato
      do seu chunk. O processo principal escolhe o melhor entre os vencedores.

POR QUE shared_memory (e não passar o array normalmente):
    Se o array de alvos fosse passado como argumento comum para cada chamada
    de pool.map, o multiprocessing faria PICKLE do array inteiro (~20MB em
    uint32) a cada iteração, para cada um dos processos — isso é I/O caro o
    bastante para anular o ganho da paralelização, já que há centenas/milhares
    de iterações. Com shared_memory, o array é alocado UMA VEZ no início e
    todos os processos acessam a MESMA região de memória física, sem cópia.

GRANULARIDADE: paraleliza-se os ~286 CANDIDATOS por iteração, não os ~5,2M
ALVOS. Isso dá poucos chunks grandes (baixo overhead de I/O entre processos)
em vez de muitos chunks pequenos, e cada processo já faz seu próprio trabalho
vetorizado internamente.

LIMITAÇÃO CONHECIDA (importante para a seção de Análise de Complexidade):
A cota inferior teórica (Schönheim) para este problema já indica algo em torno
de 11.000+ blocos mínimos necessários. O paralelismo reduz o tempo por
iteração por um fator próximo ao número de cores físicos disponíveis, mas não
muda a ordem de grandeza do número de iterações necessárias — o gargalo
combinatório do problema permanece. Isso deve ser discutido na análise de
escalabilidade: paralelismo dá ganho CONSTANTE (limitado pelo nº de cores),
não ganho assintótico.
"""

import time
from dataclasses import dataclass, field
from itertools import combinations
from multiprocessing import shared_memory
import multiprocessing as mp

import numpy as np

import combinatorics as C
from coverage_greedy import GreedyResult


# ---------------------------------------------------------------------------
# Conversão entre tuplas e bitmask
# ---------------------------------------------------------------------------

def combo_para_bitmask(combo: tuple[int, ...]) -> int:
    """Converte uma tupla de elementos (1..N) em um inteiro bitmask."""
    mask = 0
    for x in combo:
        mask |= (1 << (x - 1))
    return mask


def bitmask_para_combo(mask: int, n: int) -> tuple[int, ...]:
    """Converte um bitmask de volta para a tupla ordenada de elementos."""
    return tuple(i + 1 for i in range(n) if (mask >> i) & 1)


def gerar_bitmasks(p: int, universe: tuple[int, ...] = C.UNIVERSE) -> np.ndarray:
    """Gera todas as combinações de tamanho p como array NumPy de bitmasks (uint32)."""
    return np.fromiter(
        (combo_para_bitmask(c) for c in combinations(universe, p)),
        dtype=np.uint32,
    )


def _candidatos_bitmask_que_contem(
    alvo_mask: int, k: int, alvo_size: int, universe: tuple[int, ...]
) -> np.ndarray:
    """Gera, como array de bitmasks, todos os blocos de tamanho k que contêm o alvo.

    Equivalente a: alvo + combinações de (k - alvo_size) elementos do restante
    do universo, convertido direto para bitmask (sem passar por tuplas).
    """
    faltam = k - alvo_size
    resto = [x for x in universe if not (alvo_mask >> (x - 1)) & 1]

    masks_extra = []
    for extra in combinations(resto, faltam):
        extra_mask = 0
        for x in extra:
            extra_mask |= (1 << (x - 1))
        masks_extra.append(alvo_mask | extra_mask)

    return np.array(masks_extra, dtype=np.uint32)


# ---------------------------------------------------------------------------
# Worker paralelo: cada processo avalia um chunk de candidatos
# ---------------------------------------------------------------------------

# Estado global do worker, inicializado UMA VEZ por processo (via initializer
# do Pool), apontando para a memória compartilhada -- evita reabrir o shared
# memory a cada chamada de tarefa.
_worker_state: dict = {}


def _cobertura_de(cand_mask: int, targets_und: np.ndarray) -> np.ndarray:
    """Máscara booleana (relativa a targets_und) dos alvos cobertos por cand_mask."""
    cand_mask_int = np.uint32(cand_mask)
    nao_cobre = (targets_und & ~cand_mask_int) != 0
    return ~nao_cobre


# ---------------------------------------------------------------------------
# Guloso paralelo
# ---------------------------------------------------------------------------

def greedy_cover_bitmask_paralelo(
    p: int,
    k: int = 15,
    universe: tuple[int, ...] = C.UNIVERSE,
    verbose: bool = False,
    log_every: int = 100,
    max_iters: int | None = None,
    n_workers: int | None = None,
) -> GreedyResult:
    """Guloso com bitmask + paralelismo para cobrir S_p com blocos de tamanho k.

    Args:
        p: tamanho dos alvos (12 no Programa 4).
        k: tamanho dos blocos candidatos (15).
        universe: universo de elementos.
        verbose: imprime progresso periódico.
        log_every: intervalo (em iterações) entre logs de progresso.
        max_iters: corta a execução após N iterações (None = roda até cobrir tudo).
        n_workers: número de processos no pool. Se None, usa todos os cores
            disponíveis (os.cpu_count()).
    """
    n = len(universe)
    n_workers = n_workers or mp.cpu_count()

    t0 = time.perf_counter()
    targets = gerar_bitmasks(p, universe)
    n_targets = len(targets)
    if verbose:
        print(f"  alvos S_{p} gerados: {n_targets:,} em {time.perf_counter()-t0:.1f}s")
        print(f"  paralelismo: {n_workers} processo(s)")

    covered = np.zeros(n_targets, dtype=bool)
    chosen: list[int] = []
    gains: list[int] = []

    # Aloca a memória compartilhada com tamanho MÁXIMO (n_targets) uma única
    # vez. A cada iteração, escrevemos nela apenas os alvos ainda não
    # cobertos (nas primeiras `m` posições) e os workers leem só essa fatia
    # via shm_shape atualizado, evitando realocar a cada passo.
    shm = shared_memory.SharedMemory(create=True, size=targets.nbytes)
    shm_array = np.ndarray(targets.shape, dtype=targets.dtype, buffer=shm.buf)

    pool = mp.Pool(
        processes=n_workers,
        initializer=_init_worker_dynamic_size,
        initargs=(shm.name, str(targets.dtype)),
    )

    t_inicio = time.perf_counter()
    passo = 0

    try:
        while not covered.all():
            passo += 1
            if max_iters is not None and passo > max_iters:
                break

            # 1) escolhe um alvo ainda não coberto
            idx_nao_cobertos = np.flatnonzero(~covered)
            alvo_idx = idx_nao_cobertos[0]
            alvo_mask = int(targets[alvo_idx])

            # 2) gera candidatos (bitmask) que contêm esse alvo
            cand_masks = _candidatos_bitmask_que_contem(alvo_mask, k, p, universe)

            # 3) publica os alvos não-cobertos na memória compartilhada
            #    (escreve só os primeiros m elementos; workers sabem o tamanho m)
            targets_und = targets[idx_nao_cobertos]
            m = len(targets_und)
            shm_array[:m] = targets_und

            # 4) divide os candidatos em chunks, um por worker, e avalia em paralelo
            chunks = np.array_split(cand_masks, n_workers)
            chunks = [c for c in chunks if len(c) > 0]
            resultados = pool.starmap(
                _avaliar_chunk_dynamic, [(chunk, m) for chunk in chunks]
            )

            # 5) escolhe o melhor entre os vencedores de cada chunk
            melhor_gain, melhor_mask = max(resultados, key=lambda r: r[0])

            # 6) recalcula a máscara de cobertura do vencedor (sequencial, é O(m) só)
            cobertura_mask = _cobertura_de(melhor_mask, targets_und)
            covered[idx_nao_cobertos] |= cobertura_mask

            chosen.append(melhor_mask)
            gains.append(melhor_gain)

            if verbose and (passo % log_every == 0 or covered.all()):
                elapsed = time.perf_counter() - t_inicio
                print(
                    f"  passo {passo:>6}: +{melhor_gain:>4} alvos | "
                    f"{int(covered.sum()):>9,}/{n_targets:,} cobertos | "
                    f"{elapsed:>7.1f}s decorridos"
                )
    finally:
        pool.close()
        pool.join()
        shm.close()
        shm.unlink()

    elapsed = time.perf_counter() - t_inicio
    chosen_combos = [bitmask_para_combo(m, n) for m in chosen]

    return GreedyResult(
        p=p,
        chosen=chosen_combos,
        n_targets=n_targets,
        elapsed_s=elapsed,
        gains=gains,
    )


# ---------------------------------------------------------------------------
# Variante do worker que recebe o tamanho válido m a cada chamada (já que o
# número de alvos não-cobertos diminui a cada iteração, mas o buffer
# compartilhado tem tamanho fixo alocado uma única vez).
# ---------------------------------------------------------------------------

def _init_worker_dynamic_size(shm_name: str, dtype_str: str) -> None:
    shm = shared_memory.SharedMemory(name=shm_name)
    _worker_state["shm"] = shm
    _worker_state["dtype"] = np.dtype(dtype_str)
    _worker_state["shm_buf"] = shm.buf


def _avaliar_chunk_dynamic(cand_masks_chunk: np.ndarray, m: int) -> tuple[int, int]:
    """Igual a _avaliar_chunk, mas lê apenas os m primeiros elementos do buffer
    compartilhado (tamanho de alvos não-cobertos na iteração atual)."""
    dtype = _worker_state["dtype"]
    targets_und = np.ndarray((m,), dtype=dtype, buffer=_worker_state["shm_buf"])

    melhor_gain = -1
    melhor_mask = -1
    for cand_mask in cand_masks_chunk:
        cand_mask_int = np.uint32(cand_mask)
        nao_cobre = (targets_und & ~cand_mask_int) != 0
        gain = int((~nao_cobre).sum())
        if gain > melhor_gain:
            melhor_gain = gain
            melhor_mask = int(cand_mask)

    return melhor_gain, melhor_mask


if __name__ == "__main__":
    print("=== Amostra do Programa 4 real (n=25, k=15, p=12) — 5 iterações apenas ===")
    print("(execução completa demoraria muito mais; isto é só para medir o ritmo)")
    r2 = greedy_cover_bitmask_paralelo(p=12, k=15, verbose=True, log_every=1)
    print(f"\nApós {r2.size} passo(s): tempo {r2.elapsed_s:.1f}s decorridos")
    if r2.size:
        print(f"Ritmo médio: {r2.elapsed_s/r2.size:.2f}s/iteração")