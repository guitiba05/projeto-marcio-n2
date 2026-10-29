---
marp: true
theme: gaia
_class: lead
paginate: true
backgroundColor: #ffffff
color: #0f172a
style: |
  section {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 22px;
    padding: 36px 48px;
    background-color: #ffffff;
    color: #0f172a;
  }
  h1 {
    color: #1e3a8a;
    font-size: 34px;
    margin-bottom: 12px;
    letter-spacing: -0.02em;
  }
  h2 {
    color: #1e40af;
    font-size: 26px;
    margin-top: 0;
    margin-bottom: 16px;
    border-bottom: 2px solid #3b82f6;
    padding-bottom: 6px;
  }
  h3 {
    color: #2563eb;
    font-size: 20px;
    margin-bottom: 8px;
  }
  table {
    font-size: 17px;
    border-collapse: collapse;
    width: 100%;
    margin-top: 10px;
  }
  th, td {
    border: 1px solid #cbd5e1;
    padding: 6px 12px;
    text-align: left;
  }
  th {
    background-color: #f1f5f9;
    color: #1e293b;
    font-weight: 600;
  }
  .highlight {
    background-color: #eff6ff;
    border-left: 4px solid #2563eb;
    padding: 8px 14px;
    margin: 8px 0;
    font-size: 19px;
  }
  .badge-blue { color: #1d4ed8; font-weight: bold; }
  .badge-red { color: #b91c1c; font-weight: bold; }
  .badge-gray { color: #475569; font-weight: bold; }
  footer {
    font-size: 13px;
    color: #64748b;
  }
  code {
    background: #f1f5f9;
    padding: 2px 6px;
    border-radius: 4px;
    color: #0f172a;
    font-size: 18px;
  }
  pre {
    background: #0f172a;
    color: #f8fafc;
    padding: 12px;
    border-radius: 6px;
    font-size: 16px;
  }
---

<!-- _class: lead -->
# Projeto MdSolids — Módulo Trusses
## Modelagem, Solver Matricial e Verificação de Treliças Planas 2D
### Avaliação N2 — Mecânica dos Sólidos — CEFSA

**Apresentadores:** Equipe de Engenharia  
**Banca Examinadora:** Prof. Márcio  
**Critério Principal:** Domínio Teórico Rigoroso (4,0 Pontos)  
**Validação Experimental:** Bateria de Testes Canônicos (2,0 Pontos)

---

## Agenda da Apresentação (Os 4 Pilares da Avaliação N2)

1. **Obtenção dos Dados de Entrada (Critério 1):**
   - Parametrização da malha geométrica (`frmDefGrid`), snap magnético e deduplicação de nós.
   - Coordenadas nodais, topologia de conectividade e rigidez axial ($EA$).
   - Vínculos de apoio padronizados e cargas nodais concentradas.

2. **Tratamento no Software (Critério 2):**
   - Arquitetura desacoplada em 3 camadas: *Core Domínio*, *API REST* e *SPA Web SVG*.
   - Tratamento numérico robusto de unidades na borda (base interna em kN e metros).
   - Prevenção ativa de exceções e tolerâncias numéricas ($10^{-14}$).

3. **Conceitos Teóricos de Cálculo (Critério 3):**
   - Hipóteses fundamentais H1 a H5 e o elemento de dois esforços.
   - Grau de estaticidade ($g = b + r - 2n$) e análise de determinismo.
   - Dedução do Método da Rigidez Direta: matriz $k_e$ ($4 \times 4$), rotação $T$, montagem de $K_{\text{global}}$.
   - Conferência independente pelo Método dos Nós e Método das Seções (Ritter).
   - Barras de Força Zero (R1–R3), Detecção Espectral de Mecanismos e Dimensionamento Inverso ($\sigma = N/A$).

4. **Apresentação e Interpretação dos Resultados (Critério 4):**
   - Classificação unívoca de esforços, diagramas vetoriais coloridos e deformada elástica.
   - Auditoria de resíduos de equilíbrio estático ($\sum F_x = 0, \sum F_y = 0, \sum M = 0 < 10^{-14}$).
   - Gabarito dos 8 exercícios N2 e plano de contingência offline compilado.

---

## 1. Obtenção dos Dados de Entrada
### 1.1 Parametrização da Malha e Snap Magnético

- **Paridade com o MdSolids 4.0 (`frmDefGrid`):**
  - O usuário parametriza o espaço de trabalho via vãos horizontais/verticais e espaçamento ($\Delta x, \Delta y$).
  - O canvas SVG implementa **snap magnético automático** para os vértices da grade com raio de atração ajustável.
- **Deduplicação de Coordenadas e Criação de Nós:**
  - Tolerância espacial $\varepsilon = 10^{-6}$ (na unidade do modelo): cliques sucessivos no mesmo ponto compartilham a mesma entidade nodal, evitando nós fantasmas.
  - O grafo estrutural constrói nós unívocos $i = \{ \text{id}, x, y, \text{apoio} \}$.

```
Grade Paramétrica:  Δx = 1.0 m, Δy = 1.0 m, Nx = 4, Ny = 3
Nó A: (0.00, 0.00) [Pino]   |   Nó B: (4.00, 0.00) [Rolete]   |   Nó C: (2.00, 3.00) [Livre]
```

---

## 1. Obtenção dos Dados de Entrada
### 1.2 Topologia de Barras, Apoios e Cargas Nodais

- **Conectividade e Propriedades das Barras:**
  - Cada barra $m = \{ a, b, EA, A, \sigma_{\text{adm}} \}$ liga dois nós distintos ($a \neq b$).
  - O comprimento inicial é computado analiticamente: $L = \sqrt{(x_b - x_a)^2 + (y_b - y_a)^2}$.
  - Rejeição imediata de barras degeneradas com $L \le 0$ ou $EA \le 0$.
- **Classificação dos Apoios Padronizados:**
  - **Articulação Fixa (Pino / `pin`):** Restringe $u_x = 0$ e $u_y = 0 \implies 2$ reações ($R_x, R_y$).
  - **Apoio Móvel Horizontal (`roller`):** Restringe $u_y = 0 \implies 1$ reação ($R_y$), livre em $x$.
  - **Apoio Móvel Vertical (`roller_x`):** Restringe $u_x = 0 \implies 1$ reação ($R_x$), livre em $y$.
  - **Nó Livre (`none`):** $0$ vínculos essenciais.
- **Cargas Nodais Concentradas ($F_x, F_y$):**
  - Aplicadas estritamente nos nós em conformidade com a hipótese H2.
  - Cargas distribuídas externas são previamente convertidas em cargas nodais equivalentes nas seções de apoio (ex: caso `02-telhado-pratt`).

---

## 2. Tratamento no Software
### 2.1 Arquitetura Desacoplada em Três Camadas

```
+--------------------------------------------------------------------------+
|  1. INTERFACE WEB SPA (Vanilla JS + SVG Responsivo + CSS3 Moderno)       |
|  - Canvas vetorial interativo com Zoom/Pan, Rubberband e Snap            |
|  - Painel inspetor de propriedades, alternância de paletas e impressão  |
+------------------------------------+-------------------------------------+
                                     | HTTP / JSON REST
+------------------------------------+-------------------------------------+
|  2. SERVIÇOS & API FASTAPI (app/api/server.py, app/render/svg.py)        |
|  - Rotas: /api/solve, /api/stress, /api/report, /api/figure, /api/presets|
|  - Renderizador de relatórios técnicos autocontidos A4 (@media print)    |
+------------------------------------+-------------------------------------+
                                     | Objetos de Domínio Tipados
+------------------------------------+-------------------------------------+
|  3. NÚCLEO MATEMÁTICO PURO (app/core/) - Zero dependência web/GUI        |
|  - Solver Matricial da Rigidez Direta, Validação Cruzada dos Nós        |
|  - Decomposição Espectral, Equilíbrio Global, Barras de Força Zero       |
+--------------------------------------------------------------------------+
```

---

## 2. Tratamento no Software
### 2.2 Isolamento de Unidades e Robustez Numérica

<div class="highlight">
<b>Regra Fundamental de Projeto:</b> O solver matemático interno opera <b>exclusivamente em unidades coerentes do SI (kN para forças, metros para comprimentos, mm² para áreas de seção e MPa para tensões)</b>.
</div>

- **Isolamento na Borda:**
  - Entradas em unidades imperiais (`kip`, `lbf`, `ft`, `in`) ou múltiplos (`N`, `kgf`, `tf`, `cm`, `mm`) são transformadas na fronteira (`app/core/units.py`).
  - As respostas da API são devolvidas na unidade solicitada pelo cliente.
- **Prevenção Ativa de Erros:**
  - O pipeline de validação rejeita antes do cálculo: nós desconexos, geometrias colapsadas, caracteres não numéricos e sistemas sem vínculos.
  - Zero tolerância a erros: 474 testes automatizados cobrindo condições de contorno normais e extremas.

---

## 3. Conceitos Teóricos de Cálculo
### 3.1 As 5 Hipóteses Fundamentais da Mecânica das Treliças

Uma treliça real possui nós rebitados ou soldados. A solução rápida e exata apóia-se em cinco hipóteses clássicas da Resistência dos Materiais:

| # | Hipótese Teórica | Fenômeno Físico Eliminado | Consequência Matemática |
|---|---|---|---|
| **H1** | **Barras biarticuladas** (rótulas ideais sem atrito nas extremidades) | Momento fletor ($M = 0$) e esforço cortante ($V = 0$) | A barra é um **elemento de dois esforços** com solicitação puramente axial ($N$). |
| **H2** | **Cargas aplicadas apenas nos nós** | Flexão local por carga transversal distribuída | O esforço normal $N$ é constante ao longo de todo o comprimento da barra. |
| **H3** | **Material elástico-linear** ($\sigma = E \cdot \varepsilon$) | Escoamento plástico e histerese | Aplicação direta da Lei de Hooke uniaxial: $\Delta L = \frac{N L}{E A}$. |
| **H4** | **Pequenas deformações** ($\Delta L \ll L$) | Não linearidade geométrica | O equilíbrio é formulado rigorosamente na geometria inicial indeformada. |
| **H5** | **Treliça plana bidimensional (2D)** | Esforços e torções fora do plano | Cada nó possui exatamente 2 graus de liberdade translacionais ($u_x, u_y$). |

---

## 3. Conceitos Teóricos de Cálculo
### 3.2 Estaticidade e Determinismo Estrutural

- Para uma treliça com $n$ nós, existem **$2n$ equações algébricas de equilíbrio estático** no plano ($\sum F_x = 0$ e $\sum F_y = 0$ em cada nó).
- As incógnitas totais do sistema são as $b$ forças normais axiais nas barras mais as $r$ reações de apoio nos vínculos.

<div class="highlight">
<b>Grau de Indeterminação Estática:</b>
$$g = b + r - 2n$$
</div>

- **Classificação:**
  - $g < 0$: **Hipostática** (mecanismo; instabilidade global; ausência de solução estática).
  - $g = 0$: **Isostática** (estaticamente determinada; $N$ independe de $EA$).
  - $g > 0$: **Hiperestática** (indeterminada; exige equações de compatibilidade elástica; $N$ depende da rigidez relativa $EA$).

<div class="highlight" style="border-left-color: #dc2626; background: #fef2f2;">
<b>Atenção para a Arguição:</b> A contagem $b + r = 2n$ é condição <b>necessária, mas NÃO suficiente</b>! O caso canônico <code>10-mecanismo</code> tem $g = 0$, porém é instável devido à colinearidade de barras em nó livre.
</div>

---

## 3. Conceitos Teóricos de Cálculo
### 3.3 Método da Rigidez Direta — Formulação do Elemento de Barra

- Seja uma barra orientada do nó $A(x_a, y_a)$ ao nó $B(x_b, y_b)$, de comprimento $L$ e versor diretor $\hat{n} = (\cos\theta, \sin\theta) = (c, s)$:
  $$c = \frac{x_b - x_a}{L}, \quad s = \frac{y_b - y_a}{L}, \quad L = \sqrt{(x_b - x_a)^2 + (y_b - y_a)^2}$$

- Pela cinemática de pequenas deformações (H4), o alongamento axial relativo $\Delta L$ é a projeção dos deslocamentos nodais sobre o eixo da barra:
  $$\Delta L = (u_{bx} - u_{ax})c + (u_{by} - u_{ay})s = \begin{bmatrix} -c & -s & c & s \end{bmatrix} \begin{Bmatrix} u_{ax} \\ u_{ay} \\ u_{bx} \\ u_{by} \end{Bmatrix}$$

- Pela Lei de Hooke (H3), o esforço normal na barra é dado por:
  $$N = \frac{EA}{L} \Delta L \quad (N > 0 \implies \text{Tração}, \quad N < 0 \implies \text{Compressão})$$

---

## 3. Conceitos Teóricos de Cálculo
### 3.4 Matriz de Rigidez da Barra no Sistema Global

Aplicando o Princípio dos Trabalhos Virtuais ou a transformação de coordenadas locais $\to$ globais ($f = T^T k_{\text{local}} T u$):

$$k_e = \frac{EA}{L} \begin{bmatrix}
 c^2  &  cs & -c^2 & -cs \\
 cs   &  s^2 & -cs & -s^2 \\
-c^2  & -cs &  c^2 &  cs \\
-cs   & -s^2 &  cs &  s^2
\end{bmatrix}$$

- **Propriedades Físico-Matemáticas de $k_e$:**
  1. **Simetria:** $k_e = k_e^T$ (consequência direta do Teorema da Reciprocidade de Maxwell-Betti).
  2. **Posto 1:** Dos 4 autovalores, apenas um é não nulo ($\lambda = 2 EA / L$). A barra só oferece resistência elástica ao modo de deformação axial; os outros 3 modos representam movimentos de corpo rígido no plano (2 translações e 1 rotação).
  3. **Invariância Translacional:** $k_e \cdot \begin{bmatrix} 1 & 0 & 1 & 0 \end{bmatrix}^T = \mathbf{0}$.

---

## 3. Conceitos Teóricos de Cálculo
### 3.5 Montagem Global, Partição e Solução

1. **Montagem da Matriz Global $K$ ($2n \times 2n$):**
   - Cada nó $i$ ocupa os graus de liberdade $2i$ ($u_x$) e $2i+1$ ($u_y$).
   - A matriz de rigidez global da estrutura é montada por superposição direta dos elementos:
     $$K = \sum_{e=1}^{b} L_e^T k_e L_e$$

2. **Partição em Graus de Liberdade Livres ($f$) e Restringidos ($s$):**
   $$\begin{bmatrix} K_{ff} & K_{fs} \\ K_{sf} & K_{ss} \end{bmatrix} \begin{Bmatrix} u_f \\ u_s \end{Bmatrix} = \begin{Bmatrix} F_f \\ F_s + R \end{Bmatrix}$$

3. **Imposição das Condições de Contorno Essenciais ($u_s = \mathbf{0}$):**
   - Resolve-se o sistema linear para os deslocamentos livres:
     $$K_{ff} u_f = F_f \implies u_f = K_{ff}^{-1} F_f$$
   - Recuperam-se as reações de apoio nas restrições:
     $$R = K_{sf} u_f - F_s$$

---

## 3. Conceitos Teóricos de Cálculo
### 3.6 Detecção Espectral de Mecanismos e Instabilidades

<div class="highlight" style="border-left-color: #f59e0b; background: #fffbeb;">
<b>Problema Frequente em Softwares Estruturais:</b> Quando a estrutura possui mecanismo interno (graus de liberdade livres desprovidos de rigidez elástica), a submatriz $K_{ff}$ torna-se <b>singular (det $K_{ff} = 0$)</b>.
</div>

- **Tratamento Matemático Implementado:**
  - Em vez de tentar uma eliminação direta que causaria `ZeroDivisionError` ou geraria deslocamentos espúrios de $10^{16}\,\text{m}$, o nosso solver faz a **decomposição em valores singulares de $K_{ff}$** antes de resolver:
    $$K_{ff} = U\,\Sigma\,V^{T}, \qquad \sigma_1 \ge \dots \ge \sigma_n \ge 0$$
  - Critério de instabilidade: **deficiência de posto** de $K_{ff}$ — se o menor valor singular cai abaixo da tolerância de máquina ($s_{\min} \le s_{\max}\cdot n\cdot \epsilon$), existe direção com rigidez nula. Os vetores singulares direitos indicam os GDL. Não usamos $\min(\lambda_i)$ nem $\kappa$: ambos medem condicionamento e recusariam treliça estável com rigidez contrastada. Condicionamento alto sem deficiência de posto gera **aviso**, não recusa.
  - O vetor singular $v_{\text{nulo}}$ revela exatamente quais nós e direções participam do movimento cinemático (ex: caso `10-mecanismo` detecta modo livre no GDL $B.u_y$).
  - O sistema aborta com mensagem amigável e explicativa, sem crash.

---

## 3. Conceitos Teóricos de Cálculo
### 3.7 Conferência Independente: Método dos Nós Matricial

- Como exigência do rigor de engenharia, os resultados obtidos pelo Método da Rigidez são submetidos a uma **conferência cruzada dual-solver** via **Método dos Nós**:
  $$\sum \vec{F}_{\text{nó } i} = \mathbf{0} \implies A_{\text{geom}} \begin{bmatrix} N \\ R \end{bmatrix} = -F_{\text{aplicado}}$$
- Onde $A_{\text{geom}}$ é a matriz puramente geométrica de coeficientes diretores dos versores de cada barra incidente nos nós.
- **Vantagem Científica Fundamental:**
  - O Método dos Nós **não utiliza a rigidez $EA$ nem depende de deslocamentos nodais**. É uma formulação estritamente estática.
  - A concordância entre o Método da Rigidez e o Método dos Nós em todos os casos isostáticos é perfeita (diferença máxima $< 10^{-13}\,\text{kN}$), comprovando que o resultado numérico é uma verdade analítica exata e não um artefato de algoritmo.

---

## 3. Conceitos Teóricos de Cálculo
### 3.8 Identificação Analítica de Barras de Força Zero (Regras R1, R2, R3)

O programa identifica e justifica analiticamente as barras de força zero ($N = 0$) através de inspeção topológica nos **nós descarregados e sem apoio**:

| Regra | Topologia do Nó | Condição de Equilíbrio | Conclusão Física |
|---|---|---|---|
| **R1** | 1 única barra ligada ao nó livre | $\sum F = N \cdot \hat{n} = \mathbf{0}$ | A barra tem necessariamente $N = 0$. |
| **R2** | 2 barras não colineares em nó descarregado | $\sum F_x = 0$ e $\sum F_y = 0$ com $\sin\theta \neq 0$ | As **duas barras têm $N = 0$** (ex: nós superiores do caso `05-forca-zero-T`). |
| **R3** | 3 barras em nó descarregado, sendo 2 colineares | Projeção ortogonal ao eixo comum colinear | A **terceira barra não colinear tem $N = 0$** (ex: montante CT do caso `06-forca-zero-R3`). |

<div class="highlight">
<b>Fundamento Físico:</b> Uma barra de força zero possui $N = 0$ para <i>aquele</i> carregamento específico, mas <b>possui rigidez axial ($EA$) e é essencial para a estabilidade geométrica da treliça</b>, impedindo a formação de mecanismos sob cargas acidentais.
</div>

---

## 3. Conceitos Teóricos de Cálculo
### 3.9 Tensões Normais ($\sigma = N/A$) e Dimensionamento Inverso

Seguindo o módulo `frmTrussStress` do MdSolids 4.0, o software implementa as relações fundamentais de dimensionamento:

1. **Tensão Normal Média na Seção Bruta (Hipóteses H1 e H3):**
   $$\sigma = \frac{N}{A} \quad [\text{MPa}] = \frac{N\,[\text{kN}] \times 10^3}{A\,[\text{mm}^2]}$$
   - Sinal herdado: $\sigma > 0$ indica Tração e $\sigma < 0$ indica Compressão.

2. **Dimensionamento Inverso — Área Requerida ($A_{\text{req}}$):**
   - Dada a tensão admissível do material ($\sigma_{\text{adm}}$):
     $$A_{\text{req}} = \frac{|N|}{\sigma_{\text{adm}}} \quad [\text{mm}^2]$$
   - O uso do módulo $|N|$ garante área estritamente positiva para elementos tracionados e comprimidos.
   - Suporte a tensões admissíveis assimétricas: $\{\sigma_{\text{adm, tração}}, \sigma_{\text{adm, compressão}}\}$.

3. **Taxa de Utilização da Barra:**
   $$u = \frac{|\sigma|}{\sigma_{\text{adm}}} = \frac{A_{\text{req}}}{A} \quad (u \le 1.0 \implies \text{Segura}, \quad u > 1.0 \implies \text{Sobrecarga})$$

---

## 4. Apresentação e Interpretação dos Resultados
### 4.1 Caso Canônico de Referência: Triângulo Isostático (Caso 01)

<div style="display: flex; gap: 24px; align-items: center;">
<div style="flex: 1;">

- **Geometria:**
  - $A(0, 0)$ pino, $B(4, 0)$ rolete, $C(2, 3)$ livre.
  - Carga pontual: $F_y = -10\,\text{kN}$ no nó $C$.
- **Solução Analítica:**
  - Reações: $R_{Ax} = 0$, $R_{Ay} = +5.0\,\text{kN}$, $R_{By} = +5.0\,\text{kN}$.
  - Barra inferior $AB$: $N_{AB} = +10/3 \approx +3.3333\,\text{kN}$ (<span class="badge-blue">Tração</span>).
  - Diagonais $AC$ e $BC$: $N = -5\sqrt{13}/3 \approx -6.0093\,\text{kN}$ (<span class="badge-red">Compressão</span>).
- **Tensões ($A = 100\,\text{mm}^2$):**
  - $\sigma_{AB} = +33.33\,\text{MPa}$, $\sigma_{AC} = \sigma_{BC} = -60.09\,\text{MPa}$.

</div>
<div style="flex: 1; text-align: center; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;">

```
        C (2, 3)  [Fy = -10 kN]
          /\
   -6.01 /  \ -6.01 kN (Comp)
        /    \
       /      \
      A--------B
  (0,0)  +3.33  (4,0)
  [Pino]  kN    [Rolete]
  Ay=5kN (Tração) By=5kN
```

</div>
</div>

---

## 4. Apresentação e Interpretação dos Resultados
### 4.2 Interpretação Física Global e Sentido dos Esforços

- **Comportamento Estrutural Esperado:**
  - Sob cargas gravitacionais descendentes em treliças biapoiadas (Warren e Pratt):
    - **Banzo Superior:** Trabalha predominantemente em **Compressão** ($N < 0$), encurtando e empurrando os nós.
    - **Banzo Inferior:** Trabalha predominantemente em **Tração** ($N > 0$), alongando e puxando os nós.
    - **Diagonais e Montantes:** Alternam tração e compressão conforme a inclinação dos tirantes/escoras na transmissão das forças cortantes para os apoios.
- **Diferenciação entre Isostática e Hiperestática (Caso 08):**
  - Em estruturas isostáticas, os esforços normais $N$ **independem completamente de $EA$** (equilíbrio puro).
  - Em estruturas hiperestáticas ($g > 0$), barras com maior rigidez ($EA$) atraem maior parcela do esforço interno. O software exibe alerta explícito quando $EA$ influencia o dimensionamento.

---

## 4. Apresentação e Interpretação dos Resultados
### 4.3 Auditoria de Equilíbrio e Resíduos Numéricos

O software executa quatro verificações estáticas para cada caso resolvido:

1. **Equilíbrio Global das Forças Horizontais:**
   $$\sum F_x = \sum F_{x, \text{aplicadas}} + \sum R_{x} = 0 \quad (\text{resíduo } < 10^{-14}\,\text{kN})$$
2. **Equilíbrio Global das Forças Verticais:**
   $$\sum F_y = \sum F_{y, \text{aplicadas}} + \sum R_{y} = 0 \quad (\text{resíduo } < 10^{-14}\,\text{kN})$$
3. **Equilíbrio Global dos Momentos na Origem:**
   $$\sum M_{(0,0)} = \sum (x F_y - y F_x) + \sum (x R_y - y R_x) = 0 \quad (\text{resíduo } < 10^{-14}\,\text{kN}\cdot\text{m})$$
4. **Resíduo de Equilíbrio Nodal Local:**
   $$\max_i \left\| \sum_{j \in \text{viz}(i)} \vec{N}_{ij} + \vec{F}_i + \vec{R}_i \right\| < 10^{-14}\,\text{kN}$$

---

## 4. Apresentação e Interpretação dos Resultados
### 4.4 Gabarito Sintético dos Casos Canônicos (Bateria N2)

| Caso | Treliça | Nós / Barras | Estaticidade | Comportamento Principal Auditado | Resíduo Máximo |
|---|---|---|---|---|---|
| **01** | Triângulo Canônico | 3 nós / 3 barras | Isostática ($g=0$) | $N_{AB} = +3.33\,\text{kN}$, $N_{AC} = N_{BC} = -6.01\,\text{kN}$ | $< 10^{-15}$ |
| **02** | Telhado Pratt | 8 nós / 13 barras | Isostática ($g=0$) | Carga distribuída convertida no banzo sup. | $< 10^{-14}$ |
| **03** | Warren (3 vãos) | 7 nós / 11 barras | Isostática ($g=0$) | Simetria estrutural perfeita espelhada | $< 10^{-14}$ |
| **04** | Pratt com Vento | 8 nós / 13 barras | Isostática ($g=0$) | Carga horizontal lateral exercitando pino ($R_x$) | $< 10^{-14}$ |
| **05** | Força Zero em T | 4 nós / 5 barras | Isostática ($g=0$) | Regra R2: nós descarregados com $N = 0$ | $< 10^{-15}$ |
| **06** | Força Zero R3 | 4 nós / 5 barras | Isostática ($g=0$) | Regra R3: 3 barras, montante não colinear $N=0$ | $< 10^{-15}$ |
| **07** | Geometria Irregular | 4 nós / 5 barras | Isostática ($g=0$) | Ângulos não triviais e cargas inclinadas | $< 10^{-15}$ |
| **08** | Hiperestática ($g=1$) | 4 nós / 6 barras | Hiperestática ($g=1$) | Dependência de $EA$ e compatibilidade elástica | $< 10^{-15}$ |
| **09** | Hipostática | 3 nós / 3 barras | Hipostática ($g=-1$) | Recusa controlada amigável (falta vínculo) | Detectado |
| **10** | Mecanismo Interno | 3 nós / 2 barras | Mecanismo ($g=0$) | Autovalor nulo de $K_{ff}$ ($B.u_y$) sem crash | Detectado |
| **11** | Sem Carga | 3 nós / 3 barras | Isostática ($g=0$) | Resposta nula trivial coerente ($N = 0, R = 0$) | $0.00$ |
| **12** | Pratt Grande Ponte | 14 nós / 25 barras | Isostática ($g=0$) | Escalabilidade e legibilidade de grande porte | $< 10^{-13}$ |

---

## 4. Apresentação e Interpretação dos Resultados
### 4.5 Plano de Contingência Offline (Garantia Total para a Banca)

<div class="highlight">
<b>Garantia Operacional:</b> A apresentação conta com um plano de contingência triplo para prevenir imprevistos de rede, projetor ou sistema no laboratório:
</div>

1. **Aplicação Web Interativa Local:**
   - Inicia instantaneamente com `python serve.py` na porta local 8000.
   - Opera 100% offline sem depender de CDNs externos ou compilação npm/webpack.
2. **Dossiê Pré-compilado de Relatórios Técnicos (`docs/relatorios/`):**
   - Todos os 12 casos canônicos pré-renderizados em páginas HTML com CSS para impressão e PDF (`index.html`).
   - Podem ser abertos em qualquer navegador ou impressos fisicamente em papel A4.
3. **Slides Autocontidos Standalone (`docs/apresentacao/slides.html`):**
   - Apresentação completa com navegação por teclado e diagramas vetoriais funcionais em qualquer máquina.

---

<!-- _class: lead -->
# Conclusão e Arguição Técnica

### Resumo das Conquistas do Projeto:
- **Paridade 100% com o MdSolids 4.0 Trusses** (27/27 recursos atendidos).
- **Solver Matemático Rigoroso** baseado no Método da Rigidez Direta com detecção espectral de mecanismos.
- **Validação Cruzada Independente** (Método dos Nós e Ritter) com resíduos $< 10^{-14}$.
- **Cálculo de Tensões Normais e Dimensionamento Inverso** ($\sigma = N/A$, $A_{\text{req}} = |N|/\sigma_{\text{adm}}$).
- **474 Testes Automatizados** cobrindo todos os casos canônicos com 100% de aprovação.

<br>

**A equipe está pronta para a demonstração prática e arguição da banca examinadora.**
