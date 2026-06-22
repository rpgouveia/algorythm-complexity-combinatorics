"""
PROGRAMA 1 — Geração das Combinações.

Gera integralmente os conjuntos S₁₅, S₁₄, S₁₃, S₁₂ e S₁₁ do universo U = {1..25}
e os PERSISTE em disco (CSV, um por conjunto), para que os Programas 2 a 5 os
consumam. Imprime um relatório: cardinalidade obtida vs. esperada, amostras,
tempo e caminho do arquivo.

A geração é feita em STREAMING (uma combinação por vez): a combinação é escrita
direto no CSV, sem materializar o conjunto inteiro em memória. Assim a memória
usada é O(1); só o disco cresce (~1 GB no total dos cinco conjuntos).

Papel na arquitetura: este é o ÚNICO programa que gera os dados. Os Programas
2 a 5 leem os CSVs aqui produzidos (S₁₅ como candidatos; S_p como alvos) e
operam sobre eles.
"""

import time

from combinatorics import TARGET_SIZES, count_formula
from dataset_io import write_combinations_csv, sample_csv, DATA_DIR

SAMPLES = 5  # quantas combinações iniciais exibir por conjunto


def main() -> None:
    print("Programa 1 — Geração das Combinações  (U = {1..25})")
    print(f"Os conjuntos serão gravados em CSV no diretório '{DATA_DIR}/'.\n")

    header = f"{'p':>3} | {'esperado':>12} | {'obtido':>12} | {'ok':>3} | {'tempo (s)':>10} | arquivo"
    print(header)
    print("-" * len(header))

    grand_total = 0
    t_start = time.perf_counter()

    for p in TARGET_SIZES:
        expected = count_formula(p)

        # Gera em streaming E grava no CSV ao mesmo tempo. A contagem retornada
        # prova que a geração é íntegra (deve bater com C(25, p)).
        t0 = time.perf_counter()
        count, path = write_combinations_csv(p)
        elapsed = time.perf_counter() - t0

        grand_total += count
        ok = "✓" if count == expected else "✗"
        print(f"{p:>3} | {expected:>12,} | {count:>12,} | {ok:>3} | {elapsed:>10.3f} | {path}")

        # Amostras lidas de volta do próprio CSV (confirma que o arquivo é legível).
        for combo in sample_csv(p, SAMPLES):
            print(f"        {combo}")
        if count > SAMPLES:
            print(f"        ... (mais {count - SAMPLES:,} combinações no arquivo) ...")
        print()

    total_elapsed = time.perf_counter() - t_start
    expected_total = sum(count_formula(p) for p in TARGET_SIZES)
    ok_total = "✓" if grand_total == expected_total else "✗"
    print("-" * len(header))
    print(f"TOTAL: {grand_total:,} combinações (esperado {expected_total:,}) {ok_total}")
    print(f"Tempo total: {total_elapsed:.3f} s")
    print(f"\nArquivos gravados em '{DATA_DIR}/'.")


if __name__ == "__main__":
    main()