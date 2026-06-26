"""
VERIFICADOR DE COBERTURA — auditoria independente da solução SB.

Chamado ao final de uma execução (Guloso.py ou Random.py) para confirmar que a
solução está CORRETA, isto é, que o conjunto de blocos escolhidos SB realmente
cobre TODO S_p:

        ∀ Y ∈ S_p  ∃ X ∈ SB  tal que  Y ⊆ X

A ideia é comparar dois conjuntos:
    • "antes"  = todos os alvos que DEVERIAM ser cobertos (todo S_p).
    • "depois" = os alvos que de fato FORAM cobertos pelos blocos de SB.
Se forem iguais → cobertura correta (✓). Senão, reporta quantos/quais faltaram.

"""

import time
from dataclasses import dataclass, field

import numpy as np

import combinatorics as C
from bitmask import combo_to_bitmask, bitmask_to_combo, generate_bitmasks

# ---------------------------------------------------------------------------
# Verification result
# ---------------------------------------------------------------------------


@dataclass
class VerificationResult:
    """Result of a coverage audit."""

    p: int
    ok: bool
    """Does SB cover all of S_p? ('before' set == 'after' set)."""

    n_targets: int
    """|S_p| — total targets that should be covered ('before')."""

    n_covered: int
    """How many targets were actually covered by SB ('after')."""

    n_blocks: int
    """Size of the verified SB."""

    elapsed_s: float
    """Verification time, in seconds."""

    missing_sample: list[tuple[int, ...]] = field(default_factory=list)
    """Sample of NOT-covered targets (empty if ok=True)."""

    @property
    def n_missing(self) -> int:
        return self.n_targets - self.n_covered


# ---------------------------------------------------------------------------
# Generic verification
# ---------------------------------------------------------------------------


def verify(
    chosen,
    p: int | None = None,
    universe: tuple[int, ...] = C.UNIVERSE,
    missing_sample: int = 10,
) -> VerificationResult:
    """Audit whether SB (`chosen`) covers all of S_p.

    Args:
        chosen: either the list of chosen blocks (list[tuple[int, ...]]), or a
            result object with `.chosen` and `.p` attributes (GreedyResult /
            RandomResult) — in which case `p` may be omitted.
        p: target size. Required if `chosen` is a plain list.
        universe: universe of elements.
        missing_sample: how many uncovered-target examples to collect for the report.

    Returns:
        VerificationResult with ok, counts and a sample of missing targets.
    
    N(n^2)
    """
    # Accept either the list of blocks or the result object.
    if hasattr(chosen, "chosen"):
        if p is None:
            p = chosen.p
        blocks = chosen.chosen
    else:
        blocks = chosen

    if p is None:
        raise ValueError("p is required when `chosen` is a list of blocks.")

    n = len(universe)
    t0 = time.perf_counter()

    # "before" set: every target of S_p.
    targets = generate_bitmasks(p, universe)
    n_targets = len(targets)

    # "after" set: starts empty and is filled block by block.
    covered = np.zeros(n_targets, dtype=bool)

    # Loop over each block X of SB: mark every target contained in X.
    # Y ⊆ X  ⟺  (Y AND NOT X) == 0.
    for block in blocks:
        x_mask = np.uint32(combo_to_bitmask(tuple(block)))
        covered |= (targets & ~x_mask) == 0

    n_covered = int(covered.sum())
    ok = n_covered == n_targets

    missing = []
    if not ok:
        idx_missing = np.flatnonzero(~covered)
        missing = [
            bitmask_to_combo(int(targets[i]), n) for i in idx_missing[:missing_sample]
        ]

    elapsed = time.perf_counter() - t0

    return VerificationResult(
        p=p,
        ok=ok,
        n_targets=n_targets,
        n_covered=n_covered,
        n_blocks=len(blocks),
        elapsed_s=elapsed,
        missing_sample=missing,
    )


def print_report(res: VerificationResult) -> None:
    """Prints a human-readable report of the verification result.
    
    O(1)
    """
    status = "✓" if res.ok else "✗"
    print(f"Verificação de cobertura S_{res.p}:")
    print(f"  Blocos em SB:        {res.n_blocks:,}")
    print(f"  Alvos (|S_{res.p}|):       {res.n_targets:,}")
    print(f"  Alvos cobertos:      {res.n_covered:,}")
    if res.ok:
        print(f"  Resultado: {status}  cobertura COMPLETA (antes == depois).")
    else:
        print(f"  Resultado: {status}  FALTAM {res.n_missing:,} alvo(s) não cobertos.")
        if res.missing_sample:
            print("  Amostra de alvos não cobertos:")
            for combo in res.missing_sample:
                print(f"      {combo}")
    print(f"  Tempo de verificação: {res.elapsed_s:.3f}s")


if __name__ == "__main__":
    from random import randomized_cover

    # SMALL instance (reduced universe) just so the demo runs instantly:
    # U = {1..8}, blocks of 5, targets of 3 → |S_3| = C(8,3) = 56.
    U = tuple(range(1, 9))
    K = 5
    P = 3

    print(
        f"=== Demo: verifica a solução do randômico em instância pequena "
        f"(U={{1..{len(U)}}}, k={K}, p={P}) ===\n"
    )
    result = randomized_cover(p=P, k=K, universe=U, sample_size=3, verbose=False)
    print(
        f"Randômico terminou: |SB| = {result.size:,} blocos "
        f"em {result.elapsed_s:.3f}s\n"
    )

    res = verify(result, universe=U)
    print_report(res)

    # Negative test: removing one block must break coverage.
    print("\n=== Teste negativo: removendo 1 bloco de SB ===\n")
    res_broken = verify(result.chosen[:-1], p=result.p, universe=U)
    print_report(res_broken)
