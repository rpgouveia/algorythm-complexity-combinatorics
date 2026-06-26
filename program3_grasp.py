"""
PROGRAMA 3 (GRASP) — Cobertura de Combinações de 13 Elementos.

Variante por metaheurística GRASP multistart do Programa 3. Coexiste com o
program3.py original (construção direta), sem substituí-lo: grava em
logs/program3_grasp.log, separado de logs/program3.log.

Objetivo (enunciado): determinar SB₁₅,13 ⊆ S₁₅ tal que
        ∀ Y ∈ S_13  ∃ X ∈ SB₁₅,13  tal que  Y ⊆ X

PARADA POR TEMPO (importante p/ p baixo): para p ≤ 12 uma única partida pode
levar MUITAS horas (o custo por iteração é Θ(B·R·m), e R=C(25-p,15-p) explode
conforme p cai — de 11 em p=14 para 1001 em p=11). Por isso este programa roda
com TEMPO-LIMITE: cobre o quanto der no tempo e reporta a cobertura PARCIAL,
salvando o SB obtido. Para a análise comparativa, o RITMO e a TENDÊNCIA já são
informativos; não é necessário cobrir 100%.

PERSISTÊNCIA: salva o SB (parcial ou completo) em data_grasp/, e um checkpoint
da construção. Permite reauditar sem reexecutar.

Detalhes de classe, parada, completude e verificação: ver grasp_entry.py e
grasp_cover.py.
"""

from grasp_entry import run_grasp_program

P: int = 13
PROGRAM_NUMBER: int = 3

# Tempo-limite em segundos (ajuste conforme a paciência/recursos).
TIME_LIMIT_S: float = 1800.0  # 30 min por padrão


def main() -> None:
    run_grasp_program(
        program_number=PROGRAM_NUMBER,
        p=P,
        bound_label="limite inf. (Schönheim)",
        k_rcl=5,
        paralelo=False,  # sequencial p/ parada por tempo + heartbeat
        max_starts=None,
        time_limit_s=TIME_LIMIT_S,
        heartbeat=True,
        use_tqdm=True,
        progress_every=10,
        checkpoint_dir="data_grasp",
        save_final_path=f"data_grasp/SB_p{P}_grasp.csv",
        seed=42,
        verbose=True,
    )


if __name__ == "__main__":
    main()
