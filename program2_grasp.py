"""
PROGRAMA 2 (GRASP) — Cobertura de Combinações de 14 Elementos.

Variante por metaheurística GRASP multistart do Programa 2. Coexiste com o
program2.py original (construção direta por elemento-âncora), sem substituí-lo:
grava em logs/program2_grasp.log, separado de logs/program2.log.

Objetivo (enunciado): determinar SB₁₅,₁₄ ⊆ S₁₅ tal que
        ∀ Y ∈ S₁₄  ∃ X ∈ SB₁₅,₁₄  tal que  Y ⊆ X

PERSISTÊNCIA (importante): por padrão salva o SB em CSV de combinações em
data_grasp/, em DOIS momentos:
    • checkpoint da CONSTRUÇÃO (fase 1) — gravado ANTES da busca local, blinda
      contra perda das horas de construção caso algo falhe na fase 2;
    • SB FINAL (pós-busca-local) — o entregável, menor que o checkpoint.
Os arquivos permitem reauditar o SB depois, sem reexecutar.

DOIS MODOS (controlados por MODO abaixo):
    • "observar" → SEQUENCIAL com heartbeat: progresso DENTRO da partida
      (|SB| atual, alvos cobertos, ritmo). 1 core, mais lento, observável.
    • "rapido"   → PARALELO: partidas entre os cores (8 no Ryzen). Mais rápido,
      progresso interno opaco. Barra macro de lotes.

Detalhes de classe, parada, completude e verificação: ver grasp_entry.py e
grasp_cover.py.
"""

from grasp_entry import run_grasp_program

P: int = 14
PROGRAM_NUMBER: int = 2

# Alterne entre "observar" (sequencial + heartbeat) e "rapido" (paralelo).
MODO: str = "observar"


def main() -> None:
    if MODO == "observar":
        run_grasp_program(
            program_number=PROGRAM_NUMBER,
            p=P,
            bound_label="limite inf. (Schönheim)",
            k_rcl=5,
            paralelo=False,
            max_starts=1,           # 1 partida completa p/ obter |SB| real
            heartbeat=True,
            use_tqdm=True,
            progress_every=10,      # feedback frequente em p=14
            checkpoint_dir="data_grasp",          # checkpoint da construção
            save_final_path="data_grasp/SB_p14_grasp.csv",  # SB final
            seed=42,
            verbose=True,
        )
    else:  # "rapido"
        run_grasp_program(
            program_number=PROGRAM_NUMBER,
            p=P,
            bound_label="limite inf. (Schönheim)",
            k_rcl=5,
            paralelo=True,
            n_starts=8,
            use_tqdm=True,
            seed=42,
            verbose=True,
        )


if __name__ == "__main__":
    main()