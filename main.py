"""
<<<<<<< HEAD
    Descrição do main 
"""

# ---------------------------------------------------------


#Programas do 2 ao 5: usando a contrução direta
=======
ORQUESTRADOR — ponto de entrada único do projeto.

Pipeline de cobertura de combinações sobre U = {1..25}:

    Programa 1     →  gera S₁₅, S₁₄, S₁₃, S₁₂, S₁₁ e os persiste em data/*.csv
    Programas 2-5  →  leem esses CSVs, constroem o SB por CONSTRUÇÃO DIRETA
                        (elemento fixo), verificam a cobertura e gravam
                        logs/programN.log

Os Programas 2-5 dependem dos dados gerados pelo Programa 1; este orquestrador
executa na ordem correta.

Estratégias de COMPARAÇÃO — guloso paralelo e randômico
Estas ficam DESLIGADAS por padrão, pois sua execução completa leva horas.
Podem ser acionadas em escala limitada com a flag --comparar (usa max_iters para
demonstrar o comportamento sem rodar até o fim).

USO:
    python main.py                  # pipeline completo: Programa 1 e depois 2 a 5
    python main.py --only 1         # só o Programa 1 (gera os dados)
    python main.py --only 2 3       # só os Programas 2 e 3 (exige dados prontos)
    python main.py --skip-gen       # pula o Programa 1 (dados já existem)
    python main.py --comparar       # ao final, roda guloso/randômico LIMITADOS p/ S₁₁
    python main.py --help
"""

import argparse
import sys
import time

from combinatorics import TARGET_SIZES
from dataset_io import csv_exists

# Programas 2 a 5: construção direta
>>>>>>> d4eabf1 (refactor: update main.py, rename greedy and random algorithms, update verifier.py)
from program1 import main as program1_main
from program2 import main as program2_main
from program3 import main as program3_main
from program4 import main as program4_main
from program5 import main as program5_main

<<<<<<< HEAD

# ---------------------------------------------------------
#Programas de comparação no caso 5 (covering de S₁₁):
from Guloso import greedy_cover_bitmask_paralelo
from Random import randomized_cover 


def main () -> None:
    print("Programa principal — comparação de abordagens para cobertura de S₁₁ (U = {1..25})\n")
    print("Rodando o Programa 1 para gerar os dados...")
    program1_main()

    print("\nRodando o Programa 2 para cobertura de S₁₄...")
    program2_main()

    print("\nRodando o Programa 3 para cobertura de S₁₃...")
    program3_main()

    print("\nRodando o Programa 4 para cobertura de S₁₂...")
    program4_main()

    print("\nRodando o Programa 5 para cobertura de S₁₁...")
    program5_main()





=======
# Estratégias de comparação
from greedy import greedy_cover_bitmask_paralelo
from random import randomized_cover

PROGRAM_MAINS = {
    1: program1_main,
    2: program2_main,
    3: program3_main,
    4: program4_main,
    5: program5_main,
}

PROGRAM_TITLES = {
    1: "Geração dos dados (S₁₅..S₁₁ em CSV)",
    2: "Cobertura de S₁₄",
    3: "Cobertura de S₁₃",
    4: "Cobertura de S₁₂",
    5: "Cobertura de S₁₁",
}

REQUIRED_SETS = TARGET_SIZES  # (15, 14, 13, 12, 11)

# Quantas iterações rodar nas estratégias de comparação (apenas demonstração).
COMPARA_MAX_ITERS = 200


def data_is_ready() -> bool:
    """Indica se todos os CSVs necessários já foram gerados pelo Programa 1."""
    return all(csv_exists(p) for p in REQUIRED_SETS)


def run_program(num: int) -> float:
    """Executa o Programa `num` (construção direta) e retorna o tempo decorrido."""
    sep = "#" * 70
    print(f"\n{sep}")
    print(f"#  PROGRAMA {num} — {PROGRAM_TITLES[num]}")
    print(f"{sep}\n")
    t0 = time.perf_counter()
    PROGRAM_MAINS[num]()
    elapsed = time.perf_counter() - t0
    print(f"\n[Programa {num} concluído em {elapsed:.2f}s]")
    return elapsed


def run_comparacao() -> None:
    """Roda guloso e randômico em ESCALA LIMITADA para S₁₁ (comparação).

    Não roda até o fim. Usa max_iters para mostrar o comportamento e o ritmo de cada
    abordagem, conforme discutido na análise de complexidade.
    """
    sep = "#" * 70
    print(f"\n{sep}")
    print("#  COMPARAÇÃO DE ABORDAGENS — alvo: S₁₁")
    print(
        f"#  Execução LIMITADA a {COMPARA_MAX_ITERS} iterações (demonstração de ritmo)"
    )
    print(f"{sep}\n")

    print(
        f"-- Guloso paralelo (bitmask + multiprocessing), {COMPARA_MAX_ITERS} iters --"
    )
    r_guloso = greedy_cover_bitmask_paralelo(
        p=11, k=15, verbose=True, log_every=50, max_iters=COMPARA_MAX_ITERS
    )
    print(
        f"   após {r_guloso.size} passos: {r_guloso.elapsed_s:.1f}s "
        f"(~{r_guloso.elapsed_s/max(r_guloso.size,1)*1000:.0f} ms/iter)\n"
    )

    print(f"-- Randômico (GRASP-lite), {COMPARA_MAX_ITERS} iters --")
    r_random = randomized_cover(
        p=11,
        k=15,
        sample_size=3,
        verbose=True,
        log_every=50,
        max_iters=COMPARA_MAX_ITERS,
    )
    print(
        f"   após {r_random.size} passos: {r_random.elapsed_s:.1f}s "
        f"(~{r_random.elapsed_s/max(r_random.size,1)*1000:.0f} ms/iter)\n"
    )

    print("Nota: ambas LIMITADAS — não cobrem S₁₁ por completo aqui. A execução")
    print("completa atinge |SB| muito menor que a construção direta, ao custo de")
    print("tempo (ver análise de complexidade). A construção direta cobre S₁₁")
    print("integralmente e instantaneamente, porém com |SB| folgado.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orquestrador do pipeline de cobertura de combinações (U={1..25})."
    )
    parser.add_argument(
        "--only",
        nargs="+",
        type=int,
        choices=[1, 2, 3, 4, 5],
        metavar="N",
        help="Executa apenas o(s) programa(s) indicado(s). Ex.: --only 2 3",
    )
    parser.add_argument(
        "--skip-gen",
        action="store_true",
        help="Pula o Programa 1 (geração) e executa apenas os Programas 2 a 5.",
    )
    parser.add_argument(
        "--comparar",
        action="store_true",
        help="Ao final, roda guloso e randômico LIMITADOS para S₁₁ (comparação).",
    )
    args = parser.parse_args()

    if args.only:
        to_run = sorted(set(args.only))
    elif args.skip_gen:
        to_run = [2, 3, 4, 5]
    else:
        to_run = [1, 2, 3, 4, 5]

    # Verifica dependência: rodar 2-5 sem gerar exige dados já presentes
    precisa_dados = any(n != 1 for n in to_run)
    vai_gerar = 1 in to_run
    if precisa_dados and not vai_gerar and not data_is_ready():
        print("ERRO: os Programas 2-5 dependem dos dados do Programa 1, que não")
        print("      foram encontrados em 'data/'. Rode primeiro:")
        print("          python main.py --only 1")
        print("      ou execute o pipeline completo com 'python main.py'.")
        sys.exit(1)

    print("Orquestrador — pipeline de cobertura de combinações (U = {1..25})")
    print(
        f"Programas a executar: {', '.join(str(n) for n in to_run)}"
        + ("  + comparação (limitada)" if args.comparar else "")
    )

    tempos: dict[int, float] = {}
    t_start = time.perf_counter()
    for num in to_run:
        tempos[num] = run_program(num)

    if args.comparar:
        run_comparacao()

    total = time.perf_counter() - t_start

    sep = "=" * 70
    print(f"\n{sep}")
    print("RESUMO DA EXECUÇÃO")
    print(sep)
    for num in to_run:
        print(f"  Programa {num} ({PROGRAM_TITLES[num]:<32}): {tempos[num]:>7.2f}s")
    print(f"  {'TOTAL':<46}: {total:>7.2f}s")
    print(sep)
>>>>>>> d4eabf1 (refactor: update main.py, rename greedy and random algorithms, update verifier.py)


if __name__ == "__main__":
    main()
<<<<<<< HEAD


    








=======
>>>>>>> d4eabf1 (refactor: update main.py, rename greedy and random algorithms, update verifier.py)
