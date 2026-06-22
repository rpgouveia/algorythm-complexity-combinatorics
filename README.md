# Cobertura de Combinações — RA3

**PUCPR · Complexidade de Algoritmos · Trabalho Avaliativo RA3**

Implementação de um pipeline para o problema de **cobertura de combinações** sobre o universo U = {1, …, 25}: encontrar o menor subconjunto SB ⊆ S₁₅ tal que toda combinação de _p_ elementos esteja contida em pelo menos um bloco de 15 elementos.

```
∀ Y ∈ Sₚ  ∃ X ∈ SB  tal que  Y ⊆ X
```

---

## Problema

| Conjunto-alvo | Cardinalidade | Limite inferior (Schönheim) | Estratégia usada |
|---|---|---|---|
| S₁₄ | C(25,14) = 4.457.400 | — (solução ótima) | Construção direta |
| S₁₃ | C(25,13) = 5.200.300 | 58.887 | Construção direta |
| S₁₂ | C(25,12) = 5.200.300 | ~11.000+ | Construção direta |
| S₁₁ | C(25,11) = 4.457.400 | — | Construção direta |

O problema de decisão associado é **Set Cover (NP-Completo)**. A verificação de uma solução é polinomial.

---

## Arquitetura

```
main.py              ← orquestrador (ponto de entrada único)
│
├── program1.py      ← Geração: S₁₅..S₁₁ → data/*.csv  (streaming, O(1) memória)
├── program2.py      ← Cobertura de S₁₄  (construção direta, solução ótima)
├── program3.py      ← Cobertura de S₁₃  (construção direta + limite de Schönheim)
├── program4.py      ← Cobertura de S₁₂  (bitmask + paralelismo)
├── program5.py      ← Cobertura de S₁₁  (bitmask + paralelismo)
│
├── combinatorics.py ← geração de combinações em streaming, fórmulas
├── bitmask.py       ← conversões combo ↔ uint32, geração vetorizada
├── dataset_io.py    ← persistência CSV (leitura e escrita em streaming)
├── greedy_cover.py  ← guloso paralelo (bitmask + multiprocessing + shared_memory)
├── random_cover.py  ← abordagem randômica GRASP-lite
├── verifier.py      ← verificação de cobertura
├── logging_utils.py ← gravação de logs de resultado
│
├── data/            ← CSVs gerados pelo Programa 1 (S11.csv … S15.csv)
├── logs/            ← logs de execução dos Programas 2–5
└── docs/            ← enunciado do trabalho (PDF)
```

### Fluxo de dados

```
Programa 1 → data/S11.csv … S15.csv → Programas 2–5
```

Os Programas 2–5 dependem dos CSVs gerados pelo Programa 1. O orquestrador (`main.py`) garante a ordem correta de execução.

---

## Estratégias implementadas

### Construção direta (Programas 2–5)

Usa um **elemento fixo** `a = 25`:

```
SB = { X ∈ S₁₅ | a ∈ X }   →   |SB| = C(24, 14) = 1.961.256
```

**Prova de cobertura:** para todo Y ∈ Sₚ, se `a ∈ Y`, estenda com elementos extras até 15; se `a ∉ Y`, tome `X = Y ∪ {a, …}` completando até 15. Em ambos os casos `X ∈ SB` e `Y ⊆ X`. ✓

- Para `p = 14`: solução **ótima** (coincide com o ótimo confirmado por ILP).
- Para `p ≤ 13`: solução válida, mas acima do limite de Schönheim (gap cresce conforme p diminui).

### Guloso paralelo (`greedy_cover.py`)

Otimizações sobre o guloso ingênuo:

1. **Bitmask (uint32):** cada combinação de 25 elementos em 4 bytes; teste de subconjunto em O(1) via AND.
2. **Candidatos restritos:** em vez de testar todos C(25,15) candidatos, gera apenas C(25−p, 15−p) candidatos que contêm o alvo não-coberto escolhido (redução ~11.400× para p=12).
3. **Avaliação vetorizada:** NumPy broadcasting avalia todos os alvos de uma vez (`(targets & ~cand) == 0`).
4. **Paralelismo:** `multiprocessing.Pool` + `shared_memory` — o array de alvos é alocado uma única vez e compartilhado entre processos sem serialização por pickle.

### GRASP-lite randômico (`random_cover.py`)

Abordagem randomizada como comparativo. Produz soluções menores que a construção direta ao custo de tempo muito maior (não garante término em tempo razoável para os tamanhos do enunciado).

---

## Uso

```bash
# Pipeline completo (Programa 1 gera os dados, depois 2–5 cobrem)
python main.py

# Apenas o Programa 1 (gera os CSVs em data/)
python main.py --only 1

# Apenas Programas 2 e 3 (exige data/ já populado)
python main.py --only 2 3

# Pula a geração (data/ já existe)
python main.py --skip-gen

# Ao final, roda guloso e randômico limitados para S₁₁ (comparação de ritmo)
python main.py --comparar
```

> **Nota:** `--comparar` roda apenas 200 iterações de cada abordagem (demonstração). A execução completa do guloso para S₁₁ leva horas.

---

## Dependências

- Python 3.10+
- NumPy

```bash
pip install numpy
```

---

## Estrutura dos dados

Os CSVs em `data/` têm uma combinação por linha, elementos em ordem crescente separados por vírgula:

```
1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
1,2,3,4,5,6,7,8,9,10,11,12,13,14,16
...
```

O tamanho total dos cinco arquivos é de aproximadamente 1 GB.

---

## Análise de complexidade (resumo)

| Operação | Complexidade |
|---|---|
| Geração de Sₚ (streaming) | O(C(25, p)) tempo, O(1) memória |
| Construção do SB (filtro) | O(C(25, 15)) |
| Verificação de cobertura | O(\|Sₚ\|) |
| Guloso por iteração (p=12) | O(C(13,3) · \|Sₚ\|) / n_cores via paralelismo |

O paralelismo reduz o tempo por iteração por um fator próximo ao número de cores físicos, mas não altera a ordem de grandeza do número de iterações — o gargalo combinatório do problema permanece.
