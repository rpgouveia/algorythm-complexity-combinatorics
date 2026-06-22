"""
Persistência dos conjuntos de combinações em CSV.

Arquitetura do projeto: o Programa 1 GERA e grava em disco os conjuntos S₁₅ e
S₁₄..S₁₁; os Programas 2 a 5 LEEM esses arquivos e operam sobre eles.

Formato CSV: uma combinação por linha, elementos separados por vírgula, em
ordem crescente. Exemplo de linha de S₁₅:
    1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
"""

import csv
import os
from itertools import islice
from typing import Iterator

from combinatorics import combinations_of_size, count_formula

DATA_DIR = "data"
"""Diretório onde os CSVs são gravados/lidos."""


def csv_path(p: int, data_dir: str = DATA_DIR) -> str:
    """Caminho do arquivo CSV do conjunto S_p (ex.: data/S15.csv)."""
    return os.path.join(data_dir, f"S{p}.csv")


def write_combinations_csv(p: int, data_dir: str = DATA_DIR) -> tuple[int, str]:
    """Gera S_p em streaming e grava em CSV, uma combinação por linha.

    Retorna (quantidade_escrita, caminho_do_arquivo). A geração é em streaming
    (uma combinação por vez), de modo que a memória usada é O(1) — só o disco
    cresce. Retorna a contagem para o Programa 1 conferir contra C(25, p).
    """
    os.makedirs(data_dir, exist_ok=True)
    path = csv_path(p, data_dir)
    count = 0
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for combo in combinations_of_size(p):
            writer.writerow(combo)
            count += 1
    return count, path


def read_combinations_csv(p: int, data_dir: str = DATA_DIR) -> Iterator[tuple[int, ...]]:
    """Lê S_p do CSV em STREAMING, devolvendo uma tupla de inteiros por linha.

    Streaming (linha a linha) para não materializar o conjunto inteiro em
    memória de uma vez quando isso não for necessário. Quem precisar de tudo em
    memória pode fazer list(...) explicitamente, ciente do custo.
    """
    path = csv_path(p, data_dir)
    with open(path, "r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            yield tuple(int(x) for x in row)


def csv_exists(p: int, data_dir: str = DATA_DIR) -> bool:
    """Indica se o CSV de S_p já foi gerado (para os Programas 2-5 checarem)."""
    return os.path.isfile(csv_path(p, data_dir))


def sample_csv(p: int, n: int = 5, data_dir: str = DATA_DIR) -> list[tuple[int, ...]]:
    """Lê as primeiras `n` combinações do CSV de S_p (para exibição)."""
    return list(islice(read_combinations_csv(p, data_dir), n))