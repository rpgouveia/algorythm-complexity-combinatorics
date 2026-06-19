"""
Gera integralmente os conjuntos S₁₅, S₁₄, S₁₃, S₁₂ e S₁₁ do universo U = {1..25}
e imprime um relatório: cardinalidade obtida vs. esperada, amostras e tempo.

A geração é feita em STREAMING (uma combinação por vez): materializar os cinco
conjuntos simultaneamente como tuplas custaria ~3,6 GB de memória.
"""

import time
from itertools import islice

from combinatorics import TARGET_SIZES, combinations_of_size, count_formula

SAMPLES = 5  # quantas combinações iniciais exibir por conjunto

def main() -> None:
    print("Programa 1 — Geração das Combinações  (U = {1..25})\n")
    header = f"{'p':>3} | {'esperado':>12} | {'obtido':>12} | {'ok':>3} | {'tempo (s)':>10}"
    print(header)
    print("-" * len(header))

    grand_total = 0
    t_start = time.perf_counter()

    for p in TARGET_SIZES:
        expected = count_formula(p)
        gen = combinations_of_size(p)

        # Percorre todo o conjunto contando (prova que a geração é íntegra),
        # guardando apenas as primeiras amostras e a última combinação.
        t0 = time.perf_counter()
        first_samples = list(islice(gen, SAMPLES))
        count = len(first_samples)
        last = first_samples[-1] if first_samples else None
        for combo in gen:
            last = combo
            count += 1
        elapsed = time.perf_counter() - t0

        grand_total += count
        ok = "✓" if count == expected else "✗"
        print(f"{p:>3} | {expected:>12,} | {count:>12,} | {ok:>3} | {elapsed:>10.3f}")

        for combo in first_samples:
            print(f"        {combo}")
        if last is not None and count > SAMPLES:
            print(f"        ... ({count - SAMPLES - 1:,} combinações) ...")
            print(f"        {last}")
        print()

    total_elapsed = time.perf_counter() - t_start
    expected_total = sum(count_formula(p) for p in TARGET_SIZES)
    ok_total = "✓" if grand_total == expected_total else "✗"
    print("-" * len(header))
    print(f"TOTAL: {grand_total:,} combinações (esperado {expected_total:,}) {ok_total}")
    print(f"Tempo total: {total_elapsed:.3f} s")


if __name__ == "__main__":
    main()
