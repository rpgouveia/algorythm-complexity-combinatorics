"""
PROGRAMAS 2 a 5 — Cobertura de Combinações usando GRASP multistart.

GRASP = Greedy Randomized Adaptive Search Procedure. Metaheurística multistart:
repete-se K vezes um ciclo de duas fases independentes, guardando a melhor
solução encontrada entre todas as partidas.

    Fase 1 — CONSTRUÇÃO gulosa-randomizada (RCL por cardinalidade):
        a cada passo, ranqueia os candidatos pelo ganho (alvos novos cobertos),
        monta a Lista Restrita de Candidatos (RCL) com os `k` melhores e SORTEIA
        um deles. k=1 colapsa para guloso puro; k grande tende ao aleatório.
        Isso dá DIVERSIDADE entre partidas — cada start gera um SB diferente.

    Fase 2 — BUSCA LOCAL (remoção de redundância):
        encolhe o SB removendo blocos cuja cobertura já é garantida pelos demais.
        Usa um vetor de CONTAGEM de cobertura por alvo para decidir redundância
        em tempo barato, sem recomputar a cobertura a cada remoção.

    Laço MULTISTART (próxima etapa): repete fase 1 + fase 2 e mantém o menor SB.

REUSO: apoia-se em bitmask.py (combo↔uint32, geração vetorizada) e no mesmo
padrão de candidatos restritos ao alvo já usado em random_cover.py e
greedy_cover.py. A solução produzida é um SB verificável de forma independente
por verifier.py (auditoria O(|SB|·|S_p|), idêntica para qualquer estratégia).

CLASSE: o problema de decisão associado é Set Cover, NP-Completo. A construção
sempre termina cobrindo todo S_p (existência garantida); a otimalidade NÃO é
garantida (metaheurística incompleta quanto ao mínimo). O guloso subjacente
oferece, ainda assim, um piso teórico de qualidade — aproximação H(n) ≈ ln|S_p|.
"""

import os
import time
import concurrent.futures
from dataclasses import dataclass, field

import numpy as np

import combinatorics as C
from bitmask import bitmask_to_combo, generate_bitmasks

# tqdm é OPCIONAL: se instalado, habilita barras de progresso; se não, o código
# cai em saída textual (heartbeat por print). Não vira dependência obrigatória.
try:
    from tqdm import tqdm as _tqdm

    _TQDM_OK = True
except ImportError:
    _tqdm = None
    _TQDM_OK = False


# ---------------------------------------------------------------------------
# Persistência do SB em CSV (formato de combinações, consistente com data/)
# ---------------------------------------------------------------------------


def salvar_sb_csv(chosen_masks: list[int], n: int, path: str) -> str:
    """Grava o SB (lista de bitmasks) em CSV, uma combinação por linha.

    Formato idêntico ao de dataset_io (elementos crescentes separados por
    vírgula), para que o SB possa ser inspecionado e reauditado pelas mesmas
    ferramentas do projeto. Cria o diretório-pai se necessário.

    Usado como CHECKPOINT: gravar o SB logo após a construção (fase 1) blinda
    contra perda de horas de processamento caso uma etapa posterior falhe.
    """
    import csv
    import os

    pasta = os.path.dirname(path)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for m in chosen_masks:
            writer.writerow(bitmask_to_combo(m, n))
    return path


# ---------------------------------------------------------------------------
# Estrutura de resultado (espelha GreedyResult / RandomResult)
# ---------------------------------------------------------------------------


@dataclass
class GraspResult:
    """Resultado de uma execução do GRASP para um dado ``p``."""

    p: int
    """Tamanho dos alvos cobertos (14, 13, 12 ou 11)."""

    chosen: list[tuple[int, ...]]
    """Combinações de 15 selecionadas (SB), como tuplas ordenadas."""

    n_targets: int
    """|S_p| — quantos alvos havia para cobrir."""

    elapsed_s: float
    """Tempo de execução, em segundos."""

    n_starts: int = 0
    """Quantas partidas (starts) o multistart executou até este resultado."""

    size_inicial: int = 0
    """|SB| logo após a construção (antes da busca local) — referência de ganho."""

    cobertura_parcial: bool = False
    """True se a execução parou por TEMPO com cobertura INCOMPLETA (parcial)."""

    @property
    def size(self) -> int:
        """Tamanho de SB (número de combinações de 15 escolhidas)."""
        return len(self.chosen)


# ---------------------------------------------------------------------------
# Geração de candidatos (bitmask) que contêm um alvo
# Mesma ideia de random_cover.gerar_candidatos_por_alvo / greedy_cover.
# ---------------------------------------------------------------------------


def _candidatos_que_contem(
    alvo_mask: int, k: int, alvo_size: int, universe: tuple[int, ...]
) -> np.ndarray:
    """Gera, como array de bitmasks uint32, todos os blocos de tamanho `k` que
    contêm o alvo dado.

    Equivale a: alvo + combinações de (k - alvo_size) elementos do restante do
    universo. Convertido direto para bitmask, sem passar por tuplas.
    """
    from itertools import combinations

    faltam = k - alvo_size
    resto = [x for x in universe if not (alvo_mask >> (x - 1)) & 1]

    masks_extra = []
    for extra in combinations(resto, faltam):
        extra_mask = 0
        for x in extra:
            extra_mask |= 1 << (x - 1)
        masks_extra.append(alvo_mask | extra_mask)

    return np.array(masks_extra, dtype=np.uint32)


# ---------------------------------------------------------------------------
# FASE 1 — Construção gulosa-randomizada com RCL por cardinalidade
# ---------------------------------------------------------------------------


def construir_rcl(
    p: int,
    targets: np.ndarray,
    k: int,
    cover: int,
    universe: tuple[int, ...],
    rng: np.random.Generator,
    on_progress=None,
    progress_every: int = 50,
    deadline: float | None = None,
) -> tuple[list[int], bool]:
    """Constrói um SB por construção gulosa-randomizada (fase 1 do GRASP).

    A cada passo:
        1. escolhe um alvo ainda não coberto;
        2. gera os candidatos (blocos de tamanho `cover`) que contêm esse alvo;
        3. ranqueia os candidatos pelo ganho = nº de alvos não-cobertos que cada
           um cobre;
        4. monta a RCL com os `k` melhores e SORTEIA um deles;
        5. adiciona o escolhido ao SB e marca seus alvos como cobertos.

    Termina por SUCESSO quando todos os alvos estão cobertos, ou por TEMPO se
    `deadline` for atingido antes (retornando cobertura PARCIAL). Retorna a tupla
    (lista de bitmasks escolhidos, parou_por_tempo).

    Args:
        p: tamanho dos alvos.
        targets: array de bitmasks de todos os alvos S_p.
        k: tamanho da RCL (k melhores candidatos). k=1 → guloso puro.
        cover: tamanho dos blocos candidatos (15).
        universe: universo de elementos.
        rng: gerador aleatório (numpy) para o sorteio na RCL.
        on_progress: callback opcional chamado a cada `progress_every` blocos
            com a assinatura on_progress(n_blocos, n_cobertos, n_total). Mantém
            esta função AGNÓSTICA de como o progresso é exibido (tqdm, print ou
            nada) — quem chama decide. Se None, não há emissão (comportamento
            padrão, sem custo).
        progress_every: intervalo (em blocos escolhidos) entre chamadas do
            callback.
        deadline: timestamp absoluto (time.perf_counter()) em que a construção
            deve PARAR mesmo sem cobrir tudo. Permite parada por TEMPO DENTRO de
            uma partida — essencial para p baixo, onde uma única partida pode
            levar horas. None = roda até cobrir tudo. Ao estourar o deadline, a
            construção retorna a cobertura PARCIAL obtida até então.
    """
    n_targets = len(targets)
    covered = np.zeros(n_targets, dtype=bool)
    chosen_masks: list[int] = []
    n_cobertos = 0
    parou_por_tempo = False

    while not covered.all():
        # parada por tempo DENTRO da construção (checada a cada bloco)
        if deadline is not None and time.perf_counter() >= deadline:
            parou_por_tempo = True
            break

        # 1) primeiro alvo ainda não coberto
        idx_nao_cobertos = np.flatnonzero(~covered)
        alvo_idx = int(idx_nao_cobertos[0])
        alvo_mask = int(targets[alvo_idx])

        # 2) candidatos que contêm esse alvo
        cand_masks = _candidatos_que_contem(alvo_mask, cover, p, universe)

        # 3) ganho de cada candidato sobre os alvos AINDA não cobertos
        targets_und = targets[idx_nao_cobertos]
        ganhos = np.empty(len(cand_masks), dtype=np.int64)
        for i, cand_mask in enumerate(cand_masks):
            cand_int = np.uint32(cand_mask)
            cobre = (targets_und & ~cand_int) == 0
            ganhos[i] = int(cobre.sum())

        # 4) RCL = índices dos k melhores por ganho; sorteia um
        k_efetivo = min(k, len(cand_masks))
        # argpartition traz os k maiores para o fim (sem ordenar tudo)
        rcl_idx = np.argpartition(ganhos, -k_efetivo)[-k_efetivo:]
        escolhido_local = int(rng.choice(rcl_idx))
        escolhido_mask = int(cand_masks[escolhido_local])

        # 5) adiciona e atualiza cobertura
        cobre_escolhido = (targets & ~np.uint32(escolhido_mask)) == 0
        covered |= cobre_escolhido
        chosen_masks.append(escolhido_mask)

        # heartbeat opcional: emite progresso a cada `progress_every` blocos
        if on_progress is not None and (len(chosen_masks) % progress_every == 0):
            n_cobertos = int(covered.sum())
            on_progress(len(chosen_masks), n_cobertos, n_targets)

    # emissão final do progresso (cobertos reais, que podem ser < total se
    # parou por tempo)
    if on_progress is not None:
        n_cobertos = int(covered.sum())
        on_progress(len(chosen_masks), n_cobertos, n_targets)

    return chosen_masks, parou_por_tempo


# ---------------------------------------------------------------------------
# FASE 2 — Busca local por remoção de redundância
# ---------------------------------------------------------------------------


def busca_local_redundancia(
    chosen_masks: list[int],
    targets: np.ndarray,
    rng: np.random.Generator,
) -> list[int]:
    """Encolhe o SB removendo blocos redundantes (fase 2 do GRASP).

    Um bloco X é REDUNDANTE se todo alvo que ele cobre já é coberto por algum
    outro bloco do SB. Para decidir isso, mantém-se um vetor de CONTAGEM:
    cobertura_count[i] = quantos blocos do SB cobrem o alvo i.

        X é redundante  ⟺  para todo alvo coberto por X, cobertura_count ≥ 2.

    Ao remover X, decrementa-se a contagem dos alvos que ele cobria. A ordem de
    tentativa é ALEATÓRIA (reforça a diversidade entre starts no multistart).
    Garante que o SB resultante AINDA cobre todo S_p (nenhuma remoção deixa
    algum alvo com contagem 0).

    COMPLEXIDADE DE ESPAÇO (importante): esta versão NÃO materializa as B máscaras
    de cobertura de uma vez (isso seria Θ(B·m) — para B≈680k e m≈4,46M chega a
    TERABYTES e TRAVA a máquina). Em vez disso, recomputa a cobertura de cada
    bloco SOB DEMANDA (Θ(m) por bloco), usando apenas o vetor de contagem
    (Θ(m)) e uma máscara temporária (Θ(m)). O tempo continua Θ(B·m) (duas
    passadas: uma para montar a contagem, outra para tentar remoções), mas o
    espaço cai de Θ(B·m) para Θ(m) — viável para os tamanhos reais do problema.

    Retorna a lista (possivelmente menor) de bitmasks.
    """
    n_targets = len(targets)

    # 1) contagem de quantos blocos cobrem cada alvo — UMA passada, sem guardar
    #    as máscaras (recomputa cada cobertura e descarta).
    cobertura_count = np.zeros(n_targets, dtype=np.int32)
    for m in chosen_masks:
        cob = (targets & ~np.uint32(m)) == 0
        cobertura_count += cob

    # 2) tenta remover cada bloco em ordem aleatória. Para decidir redundância,
    #    recomputa a cobertura do bloco da vez (Θ(m)) — não há lista guardada.
    mantidos_flag = np.ones(len(chosen_masks), dtype=bool)
    ordem = list(range(len(chosen_masks)))
    rng.shuffle(ordem)

    for bloco_idx in ordem:
        m = chosen_masks[bloco_idx]
        cob = (targets & ~np.uint32(m)) == 0
        # redundante? todo alvo coberto por este bloco tem contagem >= 2
        if np.all(cobertura_count[cob] >= 2):
            cobertura_count[cob] -= 1
            mantidos_flag[bloco_idx] = False

    return [chosen_masks[i] for i in range(len(chosen_masks)) if mantidos_flag[i]]


# ---------------------------------------------------------------------------
# Uma partida completa (construção + busca local)
# ---------------------------------------------------------------------------


def um_start(
    p: int,
    targets: np.ndarray,
    k: int,
    cover: int,
    universe: tuple[int, ...],
    rng: np.random.Generator,
    on_progress=None,
    progress_every: int = 50,
    checkpoint_constr: str | None = None,
    save_final: str | None = None,
    deadline: float | None = None,
) -> tuple[list[int], int, bool]:
    """Executa UMA partida do GRASP: constrói (fase 1) e encolhe (fase 2).

    Retorna (sb_masks, size_inicial, parou_por_tempo), onde size_inicial é |SB|
    logo após a construção, antes da busca local — útil para medir o ganho da
    fase 2. parou_por_tempo indica se a construção foi interrompida por deadline
    (cobertura PARCIAL).

    on_progress/progress_every: repassados a construir_rcl para heartbeat da
    fase de construção (ver construir_rcl). A busca local não emite progresso
    (é rápida em relação à construção).

    checkpoint_constr: se fornecido, salva o SB da CONSTRUÇÃO (fase 1) neste
        caminho CSV ANTES da busca local. É o seguro contra perda das horas de
        construção caso a fase 2 falhe. None desativa.
    save_final: se fornecido, salva o SB FINAL (pós-busca-local) neste caminho
        CSV. None desativa.
    deadline: timestamp absoluto p/ parada por tempo dentro da construção.

    Nota: se a construção parar por tempo (cobertura parcial), a BUSCA LOCAL é
    PULADA — não faz sentido refinar uma cobertura incompleta, e gastaria tempo
    extra após o deadline. Nesse caso sb_final == sb_constr.
    """
    n = len(universe)
    sb_constr, parou_por_tempo = construir_rcl(
        p,
        targets,
        k,
        cover,
        universe,
        rng,
        on_progress=on_progress,
        progress_every=progress_every,
        deadline=deadline,
    )
    size_inicial = len(sb_constr)

    # CHECKPOINT: grava o SB da construção antes da fase 2 (não perde horas).
    if checkpoint_constr is not None:
        salvar_sb_csv(sb_constr, n, checkpoint_constr)

    # Busca local só faz sentido sobre cobertura COMPLETA. Se parou por tempo,
    # devolve o SB parcial como está.
    if parou_por_tempo:
        sb_final = sb_constr
    else:
        sb_final = busca_local_redundancia(sb_constr, targets, rng)

    if save_final is not None:
        salvar_sb_csv(sb_final, n, save_final)

    return sb_final, size_inicial, parou_por_tempo


# ---------------------------------------------------------------------------
# Worker paralelo: gera S_p UMA vez e roda vários starts localmente
# ---------------------------------------------------------------------------


def _worker_starts(
    p: int,
    k: int,
    cover: int,
    universe: tuple[int, ...],
    n_starts_local: int,
    seed: int,
) -> tuple[list[int], int]:
    """Roda `n_starts_local` partidas num processo e devolve o MELHOR SB local.

    Gera os alvos S_p uma única vez (custo amortizado entre as partidas deste
    worker) e executa as partidas com sementes derivadas de `seed`. Retorna
    (melhor_sb_masks, melhor_size_inicial) — apenas o menor SB encontrado aqui,
    para minimizar o que trafega de volta ao processo principal.
    """
    targets = generate_bitmasks(p, universe)
    rng = np.random.default_rng(seed)

    melhor_sb: list[int] | None = None
    melhor_size_inicial = 0

    for _ in range(n_starts_local):
        sb_masks, size_inicial, _ = um_start(p, targets, k, cover, universe, rng)
        if melhor_sb is None or len(sb_masks) < len(melhor_sb):
            melhor_sb = sb_masks
            melhor_size_inicial = size_inicial

    return melhor_sb, melhor_size_inicial


# ---------------------------------------------------------------------------
# Motor multistart SEQUENCIAL (didático; usado em instâncias pequenas e na
# verificação dos critérios de parada — tempo-limite e estagnação)
# ---------------------------------------------------------------------------


def grasp_multistart_seq(
    p: int,
    k: int = 5,
    cover: int = 15,
    universe: tuple[int, ...] = C.UNIVERSE,
    max_starts: int | None = 50,
    time_limit_s: float | None = None,
    no_improve_limit: int | None = None,
    seed: int | None = None,
    verbose: bool = False,
    log_every: int = 1,
    heartbeat: bool = False,
    use_tqdm: bool = True,
    progress_every: int = 50,
    checkpoint_dir: str | None = None,
    save_final_path: str | None = None,
) -> GraspResult:
    """GRASP multistart sequencial: repete construção + busca local, guarda o
    menor SB.

    Critérios de PARADA (o primeiro que ocorrer encerra o laço):
        • max_starts        — número máximo de partidas;
        • time_limit_s      — tempo-limite em segundos;
        • no_improve_limit  — nº de partidas consecutivas SEM melhora do melhor SB
                              (estagnação).
    Pelo menos um critério deve estar ativo. A solução retornada SEMPRE cobre
    todo S_p (cada partida produz uma cobertura válida); o que o multistart faz
    é escolher a MENOR entre as partidas — não há garantia de otimalidade.

    HEARTBEAT (observação de perto): com heartbeat=True, imprime progresso da
    fase de CONSTRUÇÃO de cada partida (|SB| atual, alvos cobertos, ritmo),
    matando o "terminal mudo" em partidas longas. Usa barra tqdm se use_tqdm=True
    e a biblioteca estiver instalada; caso contrário, imprime linhas textuais.
    progress_every controla a frequência (em blocos) das atualizações.

    Retorna GraspResult com o melhor SB, nº de partidas executadas e o |SB|
    inicial (pré-busca-local) da melhor partida.
    """
    if max_starts is None and time_limit_s is None and no_improve_limit is None:
        raise ValueError(
            "Defina ao menos um critério de parada "
            "(max_starts, time_limit_s ou no_improve_limit)."
        )

    n = len(universe)
    targets = generate_bitmasks(p, universe)
    n_targets = len(targets)
    rng = np.random.default_rng(seed)

    if verbose:
        print(f"  alvos S_{p} gerados: {n_targets:,}")
        print(
            f"  GRASP multistart sequencial: k(RCL)={k}, "
            f"max_starts={max_starts}, time_limit={time_limit_s}, "
            f"no_improve_limit={no_improve_limit}"
        )

    melhor_sb: list[int] | None = None
    melhor_size_inicial = 0
    starts = 0
    sem_melhora = 0
    cobertura_parcial = False
    t_inicio = time.perf_counter()

    # Heartbeat da CONSTRUÇÃO: callback que imprime |SB| e cobertura durante a
    # fase 1 de cada partida (mata o "terminal mudo" em partidas longas). Usa
    # tqdm se disponível e use_tqdm=True; caso contrário, print textual.
    def _fazer_callback(start_atual: int):
        if not heartbeat:
            return None, None
        if use_tqdm and _TQDM_OK:
            barra = _tqdm(
                total=n_targets,
                unit="alvo",
                leave=False,
                desc=f"start {start_atual+1} (construção)",
            )
            estado = {"ultimo": 0}

            def cb(n_blocos, n_cobertos, n_total):
                barra.update(n_cobertos - estado["ultimo"])
                estado["ultimo"] = n_cobertos
                barra.set_postfix(blocos=n_blocos)

            return cb, barra
        else:

            def cb(n_blocos, n_cobertos, n_total):
                pct = 100.0 * n_cobertos / n_total
                elapsed = time.perf_counter() - t_inicio
                ritmo = n_blocos / elapsed if elapsed > 0 else 0
                print(
                    f"    [start {start_atual+1}] blocos={n_blocos:>5} | "
                    f"cobertos={n_cobertos:>10,}/{n_total:,} ({pct:5.1f}%) | "
                    f"{ritmo:5.0f} blocos/s",
                    flush=True,
                )

            return cb, None

    # deadline absoluto para parada por tempo DENTRO de uma partida
    deadline = (t_inicio + time_limit_s) if time_limit_s is not None else None

    while True:
        # --- checagem dos critérios de parada ANTES de cada partida ---
        if max_starts is not None and starts >= max_starts:
            motivo = "max_starts"
            break
        if (
            time_limit_s is not None
            and (time.perf_counter() - t_inicio) >= time_limit_s
        ):
            motivo = "time_limit"
            break
        if no_improve_limit is not None and sem_melhora >= no_improve_limit:
            motivo = "estagnacao"
            break

        cb, barra = _fazer_callback(starts)
        # checkpoint por partida: sufixa o nº do start para não sobrescrever
        ckpt = None
        if checkpoint_dir is not None:
            import os

            ckpt = os.path.join(checkpoint_dir, f"sb_p{p}_start{starts+1}_constr.csv")
        sb_masks, size_inicial, parou_tempo = um_start(
            p,
            targets,
            k,
            cover,
            universe,
            rng,
            on_progress=cb,
            progress_every=progress_every,
            checkpoint_constr=ckpt,
            deadline=deadline,
        )
        if barra is not None:
            barra.close()
        starts += 1

        # Se a partida foi interrompida por tempo, sua cobertura é PARCIAL.
        # Ela só vira o resultado retornado se for ESTRITAMENTE melhor (menor)
        # que a melhor cobertura COMPLETA já obtida — ou se não houver nenhuma
        # completa ainda. Caso contrário, descartamos a parcial e mantemos a
        # melhor completa (que cobre tudo), evitando reportar "parcial" quando
        # na verdade temos uma solução completa melhor em mãos.
        if parou_tempo:
            if melhor_sb is None:
                # nenhuma partida completou antes do deadline → só temos a parcial
                melhor_sb = sb_masks
                melhor_size_inicial = size_inicial
                cobertura_parcial = True
            # se já existe um melhor_sb (de partida completa), mantemos ele
            motivo = "time_limit"
            break

        if melhor_sb is None or len(sb_masks) < len(melhor_sb):
            melhor_sb = sb_masks
            melhor_size_inicial = size_inicial
            sem_melhora = 0
        else:
            sem_melhora += 1

        if verbose and (starts % log_every == 0):
            elapsed = time.perf_counter() - t_inicio
            print(
                f"  start {starts:>4}: |SB|={len(sb_masks):>3} | "
                f"melhor={len(melhor_sb):>3} | "
                f"sem_melhora={sem_melhora:>3} | {elapsed:>6.1f}s"
            )

    elapsed = time.perf_counter() - t_inicio
    if verbose:
        print(
            f"  PARADA por '{motivo}' após {starts} partida(s); "
            f"melhor |SB|={len(melhor_sb)} em {elapsed:.1f}s"
        )

    # grava o SB final (melhor partida, pós-busca-local) em CSV de combinações
    if save_final_path is not None:
        salvar_sb_csv(melhor_sb, n, save_final_path)
        if verbose:
            print(f"  SB final salvo em: {save_final_path}")

    chosen_combos = [bitmask_to_combo(m, n) for m in melhor_sb]
    return GraspResult(
        p=p,
        chosen=chosen_combos,
        n_targets=n_targets,
        elapsed_s=elapsed,
        n_starts=starts,
        size_inicial=melhor_size_inicial,
        cobertura_parcial=cobertura_parcial,
    )


# ---------------------------------------------------------------------------
# Motor multistart PARALELO: distribui as partidas entre os cores
# ---------------------------------------------------------------------------


def grasp_multistart(
    p: int,
    k: int = 5,
    cover: int = 15,
    universe: tuple[int, ...] = C.UNIVERSE,
    n_starts: int = 50,
    n_workers: int | None = None,
    seed: int | None = None,
    verbose: bool = False,
    use_tqdm: bool = True,
) -> GraspResult:
    """GRASP multistart PARALELO: distribui `n_starts` partidas entre os cores
    e guarda o menor SB encontrado entre todas.

    Cada start é independente (não há estado compartilhado), então a
    paralelização é trivial: dividem-se as partidas em lotes, um por worker, e
    cada worker gera S_p uma única vez e roda seu lote localmente (evita
    regenerar os alvos a cada partida). O processo principal coleta o melhor SB
    de cada worker e escolhe o menor global.

    Critério de parada: número total de partidas (`n_starts`). Para parada por
    TEMPO ou ESTAGNAÇÃO, use grasp_multistart_seq (a coordenação desses
    critérios entre processos exigiria sincronização que não compensa aqui).

    PROGRESSO: com use_tqdm=True e tqdm instalado, mostra uma barra MACRO que
    avança conforme cada WORKER (lote) termina. ATENÇÃO de granularidade: a barra
    conta lotes concluídos, não partidas individuais — o progresso DENTRO de uma
    partida fica opaco no modo paralelo (os workers rodam em processos separados
    e não podem imprimir sem embaralhar o terminal). Para ver o progresso dentro
    de uma partida, use grasp_multistart_seq com heartbeat=True.

    Retorna GraspResult com o melhor SB e n_starts efetivamente executados.
    """
    n = len(universe)
    n_workers = n_workers or os.cpu_count() or 4
    n_workers = min(n_workers, n_starts)

    # distribui n_starts entre os workers (lotes quase iguais)
    base = n_starts // n_workers
    resto = n_starts % n_workers
    lotes = [base + (1 if i < resto else 0) for i in range(n_workers)]
    lotes = [l for l in lotes if l > 0]

    if verbose:
        print(
            f"  GRASP multistart paralelo: {n_starts} partidas em "
            f"{len(lotes)} worker(s), k(RCL)={k}"
        )
        print(f"  lotes por worker: {lotes}")

    seed_base = seed if seed is not None else int(time.time())
    t_inicio = time.perf_counter()

    melhor_sb: list[int] | None = None
    melhor_size_inicial = 0

    # barra macro: avança a cada lote (worker) concluído
    usar_barra = use_tqdm and _TQDM_OK
    barra = (
        _tqdm(total=len(lotes), unit="lote", desc="partidas (lotes)")
        if usar_barra
        else None
    )

    with concurrent.futures.ProcessPoolExecutor(max_workers=len(lotes)) as executor:
        futures = [
            executor.submit(_worker_starts, p, k, cover, universe, lote, seed_base + i)
            for i, lote in enumerate(lotes)
        ]
        for future in concurrent.futures.as_completed(futures):
            sb_masks, size_inicial = future.result()
            if melhor_sb is None or len(sb_masks) < len(melhor_sb):
                melhor_sb = sb_masks
                melhor_size_inicial = size_inicial
            if barra is not None:
                barra.update(1)
                barra.set_postfix(melhor=len(melhor_sb))
            elif verbose:
                concluidos = sum(1 for f in futures if f.done())
                elapsed = time.perf_counter() - t_inicio
                print(
                    f"  lote concluído ({concluidos}/{len(lotes)}) | "
                    f"melhor |SB|={len(melhor_sb)} | {elapsed:.1f}s",
                    flush=True,
                )

    if barra is not None:
        barra.close()

    elapsed = time.perf_counter() - t_inicio
    targets_count = C.count_formula(p, n=n)

    if verbose:
        print(
            f"  melhor |SB|={len(melhor_sb)} entre {n_starts} partidas "
            f"em {elapsed:.1f}s"
        )

    chosen_combos = [bitmask_to_combo(m, n) for m in melhor_sb]
    return GraspResult(
        p=p,
        chosen=chosen_combos,
        n_targets=targets_count,
        elapsed_s=elapsed,
        n_starts=n_starts,
        size_inicial=melhor_size_inicial,
    )


# ---------------------------------------------------------------------------
# Demo do multistart — instância pequena, exercita os dois motores
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    from verifier import verify, print_report

    # U = {1..9}, blocos de 6, alvos de 4 → |S_4| = C(9,4) = 126.
    U = tuple(range(1, 10))
    COVER = 6
    P = 4
    K = 5

    print(
        f"=== Demo GRASP multistart em instância pequena "
        f"(U={{1..{len(U)}}}, k_bloco={COVER}, p={P}, RCL k={K}) ===\n"
    )

    print("--- Motor SEQUENCIAL (parada por estagnação: 15 sem melhora) ---")
    res_seq = grasp_multistart_seq(
        p=P,
        k=K,
        cover=COVER,
        universe=U,
        max_starts=None,
        no_improve_limit=15,
        seed=42,
        verbose=True,
        log_every=5,
    )
    print(
        f"  → melhor |SB| = {res_seq.size} "
        f"(inicial da melhor partida: {res_seq.size_inicial}); "
        f"{res_seq.n_starts} partidas\n"
    )

    print("--- Motor PARALELO (40 partidas distribuídas nos cores) ---")
    res_par = grasp_multistart(
        p=P,
        k=K,
        cover=COVER,
        universe=U,
        n_starts=40,
        seed=42,
        verbose=True,
    )
    print(f"  → melhor |SB| = {res_par.size}; {res_par.n_starts} partidas\n")

    print("--- Auditoria independente (verifier.py) do melhor SB paralelo ---")
    res_audit = verify(res_par.chosen, p=P, universe=U)
    print_report(res_audit)
