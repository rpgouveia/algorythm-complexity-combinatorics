"""
    Descrição do main 
"""

# ---------------------------------------------------------


#Programas do 2 ao 5: usando a contrução direta
from program1 import main as program1_main
from program2 import main as program2_main
from program3 import main as program3_main
from program4 import main as program4_main
from program5 import main as program5_main


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







if __name__ == "__main__":
    main()


    








