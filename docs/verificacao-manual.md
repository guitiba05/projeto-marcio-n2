# Verificação manual no navegador (roteiro da defesa)

Checklist executável em ~10 minutos, na mesma máquina e navegador da apresentação.
Cada passo indica o resultado esperado — se algo divergir, é defeito, não "jeito do
navegador".

```powershell
python serve.py            # abre http://127.0.0.1:8000/
```

## 1. Grade e criação de nós

| # | Ação | Esperado |
|---|---|---|
| 1.1 | Na barra **Grade**, preencher `Δx=1`, `Δy=1`, `nx=4`, `ny=3` e clicar **Aplicar** | grade desenhada com 5×4 pontos; o quadro se reenquadra |
| 1.2 | Botão **Nó** (atalho `N`), clicar em (0,0) | nó `A` criado e selecionado; inspetor mostra `Nó A` |
| 1.3 | Clicar de novo em (0,0) | nenhum nó duplicado (mesmo `A`) |
| 1.4 | Clicar em (4,0) e (2,3) | nós `B` e `C` |

## 2. Barras por arraste

| # | Ação | Esperado |
|---|---|---|
| 2.1 | Botão **Barra** (`B`), arrastar de A até B | linha fantasma durante o movimento; barra `AB` criada |
| 2.2 | Arrastar B→C e C→A | treliça triangular fechada, 3 barras |
| 2.3 | Arrastar A→B novamente | nada acontece (barra duplicada é recusada) |

## 3. Apoios e carga

| # | Ação | Esperado |
|---|---|---|
| 3.1 | Duplo clique no nó A | apoio alterna: `sem apoio` → `pin` |
| 3.2 | Duplo clique no nó B | `roller` |
| 3.3 | Selecionar C, digitar `Fy = -10` no inspetor | seta de carga para baixo com rótulo `10,0` |

## 4. Cálculo

| # | Ação | Esperado |
|---|---|---|
| 4.1 | **Calcular** (ou `Ctrl+Enter`) | chip `calculado` |
| 4.2 | Tabela de esforços | `AB +3,333 tração`, `BC −6,009 compressão`, `CA −6,009 compressão` |
| 4.3 | Reações | `A: Rx 0, Ry 5`; `B: Ry 5` |
| 4.4 | Verificações | `ΣFx`, `ΣFy`, `ΣM`, resíduo nodal todos `ok` |
| 4.5 | Nota do método dos nós | "diferença máxima 0" |

## 5. Tensões normais

| # | Ação | Esperado |
|---|---|---|
| 5.1 | Selecionar `AB`, digitar `área = 100`, botão **Aplicar esta área a todas** | as 3 barras com área 100 |
| 5.2 | Painel **Tensões normais** → **Calcular tensões** | `AB 33,333`, `BC/CA −60,093` MPa |
| 5.3 | Marcar a caixa `σ` na barra de ferramentas | rótulos do diagrama passam a `σ 33,3`, `σ −60,1` |
| 5.4 | Modo **área requerida**, `σ adm = 50` | `A req`: `AB 66,667`, `BC/CA 120,185` mm²; diagonais "insuficiente" |

## 6. Paleta e relatório

| # | Ação | Esperado |
|---|---|---|
| 6.1 | Seletor **Paleta** → `MdSolids` | tração ciano, compressão ouro, força zero magenta |
| 6.2 | Voltar para `padrão` | azul/vermelho; ciano desaparece |
| 6.3 | **Relatório** | nova aba com título, diagrama, tabelas e a seção "Tensões normais (σ = N/A)" com `33.333` |
| 6.4 | No relatório, **Imprimir / salvar PDF** | pré-visualização A4 sem cortar tabelas |

## 7. Teclado (acessibilidade)

| # | Ação | Esperado |
|---|---|---|
| 7.1 | `Tab` até o quadro (contorno azul visível) | foco no quadro; dica menciona setas e Enter |
| 7.2 | Setas ←→↑↓ | cursor em cruz se move ponto a ponto da grade |
| 7.3 | `N` e depois `Enter` sobre um ponto vazio | nó criado na posição do cursor |
| 7.4 | `B`, `Enter` na origem, setas, `Enter` no destino | barra criada entre os dois nós |
| 7.5 | `Esc` durante a criação | origem cancelada, nada criado |
| 7.6 | `Enter` no modo **Selecionar** sobre um nó | apoio alterna (mesmo efeito do duplo clique) |

## 8. Casos de erro

| # | Ação | Esperado |
|---|---|---|
| 8.1 | Caso pronto `10-mecanismo` | "Entrada recusada" citando o GDL `B.uy`; painel de tensões volta à instrução |
| 8.2 | Caso pronto `09-hipostatica` | mensagem de hipostática com `g < 0` |
| 8.3 | Importar um JSON com `"id": "<img src=x onerror=alert(1)>"` | o texto aparece literal na tela; **nenhum** alerta, nenhuma imagem criada |

## 9. Console

| # | Ação | Esperado |
|---|---|---|
| 9.1 | Abrir DevTools → Console e repetir 4.1, 5.2, 6.1, 6.3 | zero erros e zero avisos |

---

## Verificação automatizada equivalente

O que é verificável sem navegador já está na suíte:

```powershell
python -m pytest -q                      # 474 testes
python -m pytest tests/test_security.py  # injeção, paleta, dimensões, mecanismo
```

Cobertura por HTTP: `tabindex` e `aria-live` no HTML, presença de `esc`/`onCanvasKeyDown`
no JS, contraste das cores no CSS, `/api/figure` com `width` inválido e com modelo
inválido (sem HTTP 500), escape do relatório de erro.
