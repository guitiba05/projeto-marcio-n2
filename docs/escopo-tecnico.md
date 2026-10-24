# Escopo técnico

Documento de trabalho. Objetivo: cobrir o módulo *Trusses* do MdSolids com foco nos
4,0 pontos da apresentação teórica e nos 8 exercícios de verificação.

## 1. Funcionalidades esperadas (paridade com o MdSolids / Trusses)

- [ ] Entrada de geometria da treliça: nós (coordenadas x, y) e barras (nó inicial, nó final)
- [ ] Entrada de apoios: articulação fixa (2 restrições) e apoio móvel/rolete (1 restrição)
- [ ] Entrada de cargas nodais (Fx, Fy)
- [ ] Verificação de estaticidade: `b + r` vs `2n` (isostática / hipostática / hiperestática)
- [ ] Reações de apoio por equilíbrio global
- [ ] Esforços normais em todas as barras (método matricial da rigidez)
- [ ] Classificação automática tração / compressão / força zero
- [ ] Deslocamentos nodais (opcional, sai de graça no método da rigidez)
- [ ] Saída: tabela de resultados + diagrama da treliça com esforços
- [ ] Casos de erro tratados: treliça hipostática, mecanismo, carga fora de nó

## 2. Núcleo de cálculo

Método matricial da rigidez (direto), adequado tanto a treliças isostáticas quanto
hiperestáticas:

1. Para cada barra `i` de nós `(a, b)`:
   - comprimento `L = |p_b - p_a|`
   - cossenos diretores `c = (x_b - x_a)/L`, `s = (y_b - y_a)/L`
   - rigidez local `k = (EA/L) * [c², cs; cs, s²]` expandida a 4x4
2. Montar a matriz de rigidez global `K` (2n x 2n) somando as contribuições
3. Aplicar condições de contorno: eliminar/penalizar graus de liberdade restringidos
4. Resolver `K u = F` para os deslocamentos livres
5. Reações: `R = K u - F` nos graus restringidos
6. Esforço normal na barra: `N = (EA/L) * [ -c, -s, c, s ] · [u_a; u_b]`
   (positivo = tração)

Alternativa de conferência: método dos nós / método das seções para treliças
isostáticas.

## 3. Verificação

- Treliças de referência com solução analítica conhecida (triangular simples, treliça
  de telhado, treliça tipo Pratt/Howe)
- Conferência contra o MdSolids original nos 8 exercícios da banca
- Testes automatizados com valores esperados de reações e esforços normais

## 4. Pontos a definir

- Linguagem / plataforma (enunciado não restringe)
- Interface: desktop, web ou CLI + arquivo de entrada
- Formato de entrada dos dados (JSON é o candidato natural)
