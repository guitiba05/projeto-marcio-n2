# Roteiro Completo de Defesa perante a Banca Examinadora (CEFSA N2)
## Módulo Trusses (Treliças Planas) — MdSolids 4.0 Re-engenharia

**Disciplina:** Mecânica dos Sólidos  
**Docente Avaliador:** Prof. Márcio  
**Peso da Apresentação Teórica:** 4,0 Pontos (Critério Eliminatório e Principal)  
**Peso da Bateria Prática:** 2,0 Pontos (8 Exercícios Canônicos)  
**Tempo Total de Apresentação:** 15 a 18 minutos (+ arguição da banca)  
**Materiais de Apoio Prontos:**
1. Apresentação Interativa: `docs/apresentacao/slides.html` (ou `slides.md` via Marp)
2. Aplicação em Execução Local: `http://127.0.0.1:8000` (`python serve.py`)
3. Dossiê de Relatórios Impressos / PDF: `docs/relatorios/index.html` (12 casos canônicos)

---

## 1. Distribuição de Papéis e Preparação da Apresentação

Para apresentação em dupla (conforme permitido pelo enunciado):
- **Apresentador 1 (Engenharia Teórica & Solver):** Focado nas deduções matriciais, hipóteses H1–H5, matrizes $k_e$ e $K_{\text{global}}$, autovalores de mecanismos, Método dos Nós e tensões normais.
- **Apresentador 2 (Modelagem de Dados, Software & Resultados):** Focado na obtenção dos dados, parametrização da malha, apoios, cargas, arquitetura em 3 camadas, demonstração prática ao vivo e interpretação física dos esforços.

*Nota:* Se a apresentação for individual, o roteiro segue a mesma ordem cronológica unificada.

---

## 2. Os 13 Blocos Cronometrados da Defesa

```
+-----------------------------------------------------------------------------------------------+
|  BLOCO 1: Abertura, Contexto e Paridade MdSolids                           (00:00 - 01:15)    |
|  BLOCO 2: Idealização Estrutural e as 5 Hipóteses H1-H5                    (01:15 - 02:45)    |
|  BLOCO 3: Obtenção dos Dados de Entrada (Grade, Nós, Vínculos, Cargas)      (02:45 - 04:00)    |
|  BLOCO 4: Tratamento no Software (Arquitetura 3 Camadas e Unidades)        (04:00 - 05:15)    |
|  BLOCO 5: Grau de Estaticidade e Análise de Determinismo                    (05:15 - 06:30)    |
|  BLOCO 6: Equilíbrio Estático Externo e Reações de Apoio                   (06:30 - 07:45)    |
|  BLOCO 7: Método dos Nós Matricial e Convenção Unívoca de Sinais           (07:45 - 09:00)    |
|  BLOCO 8: Método das Seções (Ritter) para Conferência Local                (09:00 - 10:15)    |
|  BLOCO 9: Método da Rigidez Direta (Matriz de Barra, T e K Global)         (10:15 - 12:15)    |
|  BLOCO 10: Detecção Espectral de Mecanismos via Autovalores de K_ff         (12:15 - 13:30)    |
|  BLOCO 11: Identificação Geométrica de Barras de Força Zero (R1-R3)        (13:30 - 14:45)    |
|  BLOCO 12: Tensões Normais (sigma = N/A) e Dimensionamento Inverso (A_req) (14:45 - 16:15)    |
|  BLOCO 13: Demonstração ao Vivo, Auditoria de Resíduos e Conclusão         (16:15 - 18:00)    |
+-----------------------------------------------------------------------------------------------+
```

---

### BLOCO 1: Abertura, Contexto e Paridade MdSolids (00:00 - 01:15)
- **Orador:** Apresentador 1 / Dupla
- **Slide de Apoio:** Slide 1 (Capa) e Slide 2 (Agenda)
- **Mensagem Central:** Apresentar a equipe, o objetivo de reconstruir e aprimorar o módulo Trusses do MdSolids 4.0, destacando que a teoria foi compreendida e implementada de forma autônoma pela equipe.
- **O que Falar (Verbalização Recomendada):**
  > "Boa tarde, professor Márcio e colegas. O objetivo deste trabalho é a modelagem computacional rigorosa, a implementação matemática e a validação do módulo Trusses do software MdSolids 4.0 para a avaliação N2.
  > Como o tema de treliças não foi lecionado em sala de aula, nossa equipe dedicou-se ao estudo autônomo e aprofundado da mecânica dos sólidos e dos métodos matriciais de estruturas.
  > Desenvolvemos uma aplicação que não apenas atinge 100% de paridade com os formulários do MdSolids — como a definição de grade paramétrica, snap magnético, cálculo de esforços normais, classificação de tração e compressão, identificação de barras de força zero e dimensionamento de seção transversal —, mas que vai além: implementamos um solver matricial da rigidez capaz de resolver tanto treliças isostáticas quanto hiperestáticas, auditoria espectral de mecanismos para evitar falhas ou números absurdos, e um algoritmo independente do Método dos Nós para validação cruzada dual-solver com resíduos abaixo de $10^{-14}$."
- **Ação na Tela:** Manter a capa projetada ou alternar para a tela inicial do software local.

---

### BLOCO 2: Idealização Estrutural e as 5 Hipóteses Fundamentais (01:15 - 02:45)
- **Orador:** Apresentador 1
- **Slide de Apoio:** Slide 7 (Hipóteses H1 a H5)
- **Mensagem Central:** Uma treliça real possui nós soldados e deformações complexas; a modelagem matemática requer 5 hipóteses fundamentais que simplificam o problema sem perda de precisão.
- **O que Falar (Verbalização Recomendada):**
  > "Para transformar uma estrutura metálica física em um modelo matemático resolúvel por um sistema linear de equações, apoiamo-nos em cinco hipóteses clássicas da Mecânica das Estruturas:
  > **Primeira (H1):** As barras são biarticuladas, ou seja, possuem rótulas perfeitas e sem atrito em suas extremidades. Essa hipótese elimina qualquer transmissão de momento fletor ($M = 0$) ou esforço cortante ($V = 0$). Consequentemente, cada barra comporta-se como um elemento de dois esforços, submetido unicamente a esforço normal axial $N$.
  > **Segunda (H2):** O carregamento externo é aplicado estritamente sobre os nós. Isso assegura que não haja flexão transversal distribuída na barra, garantindo que o esforço normal seja estritamente constante de um nó ao outro. Por essa razão, nosso programa recusa cargas no meio das barras.
  > **Terceira (H3):** O material obedece ao regime elástico linear ($\sigma = E \cdot \varepsilon$). A relação entre esforço e deformação axial é regida puramente pela Lei de Hooke: $\Delta L = \frac{N L}{EA}$.
  > **Quarta (H4):** Pequenas deformações ($\Delta L \ll L$). O equilíbrio estático é formulado com total exatidão sobre a geometria inicial indeformada da treliça.
  > **Quinta (H5):** A treliça e os carregamentos são puramente coplanares (2D), de modo que cada nó livre possui rigorosamente 2 graus de liberdade translacionais: $u_x$ e $u_y$."
- **Ponto de Atenção da Banca:** Se o professor perguntar: *"E se o peso próprio for muito alto?"*, responder: *"O peso próprio da barra pode ser discretizado dividindo-se metade para cada nó adjacente como cargas nodais verticais concentradas, mantendo a conformidade estrita com H1 e H2."*

---

### BLOCO 3: Obtenção dos Dados de Entrada (02:45 - 04:00)
- **Orador:** Apresentador 2
- **Slide de Apoio:** Slide 3 (Grade e Nós) e Slide 4 (Apoios e Cargas)
- **Mensagem Central:** Explicar como a geometria e os vínculos são inseridos na aplicação e como o software higieniza os dados de entrada.
- **O que Falar (Verbalização Recomendada):**
  > "Passando para o primeiro critério avaliativo: a obtenção dos dados de entrada.
  > Inspirados pelo formulário `frmDefGrid` do MdSolids original, nosso software permite parametrizar uma malha bidimensional através do número de vãos horizontais e verticais e seus respectivos espaçamentos.
  > Na interface interativa em SVG, implementamos um sistema de snap magnético com raio de tolerância. Quando o usuário clica próximo a um vértice da grade, o nó é magnetizado automaticamente.
  > Mais importante ainda: criamos uma rotina de deduplicação nodal. Se o usuário clicar repetidas vezes na mesma coordenada $(x, y)$, o software identifica a existência do nó prévio com tolerância de $10^{-4}\,\text{m}$, impedindo nós duplicados ou barras de comprimento zero.
  > Quanto aos vínculos de apoio, modelamos com precisão as condições de contorno essenciais:
  > - Articulação fixa (pino): restringe translação em $x$ e $y$, fornecendo 2 reações ($R_x, R_y$).
  > - Apoio móvel horizontal (rolete): restringe apenas $y$, fornecendo $R_y$ e liberando $u_x$.
  > - Apoio móvel vertical: restringe $x$, fornecendo $R_x$ e liberando $u_y$.
  > - Nó livre: sem restrições.
  > Note-se que o software rejeita apoios engastados, pois restringir a rotação violaria a hipótese H1 de articulação livre."
- **Ação na Tela:** Apontar na interface gráfica os ícones de pino (triângulo verde com articulação) e de rolete (rodízios sob a base).

---

### BLOCO 4: Tratamento no Software e Isolamento de Unidades (04:00 - 05:15)
- **Orador:** Apresentador 2
- **Slide de Apoio:** Slide 5 (Arquitetura 3 Camadas) e Slide 6 (Unidades e Testes)
- **Mensagem Central:** Detalhar a arquitetura em 3 camadas, o isolamento numérico na borda e a robustez contra erros.
- **O que Falar (Verbalização Recomendada):**
  > "No segundo critério avaliativo — o tratamento no software —, a principal decisão de engenharia foi o desacoplamento total em três camadas:
  > 1. A Camada de Apresentação (Frontend SPA): em HTML5, CSS3 moderno e SVG interativo, responsável por renderizar a geometria, capturar eventos de mouse e exibir tabelas. Ela não faz nenhuma conta de engenharia.
  > 2. A Camada de Serviços (FastAPI): expõe endpoints REST que recebem e devolvem contratos JSON estruturados, gerando inclusive os relatórios técnicos em padrão A4.
  > 3. O Núcleo Matemático (Core): localizado em `app/core/`, construído em Python puro com NumPy. É onde residem os algoritmos matriciais, a decomposição espectral e os testes de equilíbrio. Ele não tem dependência de interface gráfica ou web.
  > Uma fonte crônica de erros em softwares estruturais é a conversão confusa de unidades. Para resolver isso em definitivo, adotamos o princípio da unidade invariante na borda:
  > O usuário pode fornecer entradas em kN, N, kgf, tf ou unidades imperiais como kip e libras-força, bem como comprimentos em metros, milímetros ou polegadas.
  > Assim que a requisição atinge a borda da aplicação, todos os valores são convertidos para a base do SI: kN para forças, metros para coordenadas, mm² para seções transversais e MPa para tensões normais. Todo o solver matricial opera nessa base limpa, e o resultado é reconvertido para a visualização desejada."
- **Ação na Tela:** Mostrar o arquivo `pyproject.toml` ou os 215 testes passando no terminal.

---

### BLOCO 5: Grau de Estaticidade e Análise de Determinismo (05:15 - 06:30)
- **Orador:** Apresentador 1
- **Slide de Apoio:** Slide 8 (Estaticidade e Determinismo)
- **Mensagem Central:** Deduzir $g = b + r - 2n$ e justificar por que essa fórmula clássica é necessária, mas não suficiente.
- **O que Falar (Verbalização Recomendada):**
  > "Entrando nos conceitos teóricos de cálculo (terceiro critério avaliativo):
  > Em uma treliça plana com $n$ nós, cada nó dispõe de duas equações fundamentais de equilíbrio estático: $\sum F_x = 0$ e $\sum F_y = 0$, totalizando $2n$ equações algébricas lineares independentes.
  > As incógnitas do sistema estrutural são os $b$ esforços axiais nas barras mais as $r$ reações de apoio externas.
  > O grau de indeterminação estática é dado pela relação:
  > $$g = b + r - 2n$$
  > Se $g < 0$, a treliça é hipostática. Faltam vínculos essenciais e a estrutura é um mecanismo cinemático que não sustenta carregamentos.
  > Se $g = 0$, a estrutura é isostática. O número de equações iguala o de incógnitas; os esforços axiais $N$ podem ser obtidos puramente pelo equilíbrio, sem depender do módulo de elasticidade $E$ ou da área $A$.
  > Se $g > 0$, a estrutura é hiperestática. Existem mais incógnitas do que equações de equilíbrio da estática; os esforços dependem obrigatoriamente da rigidez relativa $EA$ das barras.
  > Mas há um aspecto crucial que destacamos em nosso dossiê: a condição $b + r = 2n$ é estritamente necessária, porém **não suficiente**. Se as barras forem mal posicionadas (por exemplo, três nós articulados colineares sem triangulação), a treliça formará um mecanismo interno com $g = 0$. Demonstraremos adiante como nosso software soluciona isso."

---

### BLOCO 6: Equilíbrio Estático Externo e Reações de Apoio (06:30 - 07:45)
- **Orador:** Apresentador 1
- **Slide de Apoio:** Slide 4 (Equilíbrio e Apoios) e Slide 10 (Triângulo Canônico)
- **Mensagem Central:** Demonstrar o cálculo analítico das reações de apoio no corpo rígido global para o caso de referência `01-triangulo`.
- **O que Falar (Verbalização Recomendada):**
  > "Antes de calcular os esforços internos, o corpo inteiro da treliça deve satisfazer as três equações globais de equilíbrio estático da estática clássica:
  > $$\sum F_x = 0, \quad \sum F_y = 0, \quad \sum M_{\text{origem}} = 0$$
  > Tomemos como exemplo o caso canônico de referência da nossa apresentação, o caso `01-triangulo`:
  > Temos o nó A em $(0,0)$ com apoio fixo (reações $R_{Ax}$ e $R_{Ay}$), o nó B em $(4,0)$ com rolete horizontal (reação $R_{By}$ vertical), e o nó C em $(2,3)$ submetido a uma carga vertical descendente $F_y = -10\,\text{kN}$.
  > Aplicando o equilíbrio de forças horizontais:
  > $$\sum F_x = 0 \implies R_{Ax} = 0$$
  > Aplicando o momento em relação ao nó A:
  > $$\sum M_A = 0 \implies R_{By} \cdot 4\,\text{m} - 10\,\text{kN} \cdot 2\,\text{m} = 0 \implies R_{By} = \frac{20}{4} = +5.0\,\text{kN}$$
  > Aplicando o equilíbrio de forças verticais:
  > $$\sum F_y = 0 \implies R_{Ay} + R_{By} - 10 = 0 \implies R_{Ay} = 10 - 5 = +5.0\,\text{kN}$$
  > O software obtém exatamente estes valores matricialmente e confirma que a soma residual é menor que $10^{-15}$."

---

### BLOCO 7: Método dos Nós Matricial e Convenção Unívoca de Sinais (07:45 - 09:00)
- **Orador:** Apresentador 1
- **Slide de Apoio:** Slide 12 (Validação Cruzada dos Nós)
- **Mensagem Central:** Apresentar a convenção de sinais (tração positiva) e a resolução do nó C e nó A da treliça de referência.
- **O que Falar (Verbalização Recomendada):**
  > "Para a determinação analítica dos esforços normais, adotamos a convenção canônica da Mecânica dos Sólidos:
  > **Tração é rigorosamente positiva ($N > 0$) e compressão é negativa ($N < 0$).**
  > As forças normais das barras são desenhadas sempre apontando para fora do nó (saindo do pino). Se a álgebra resultar em sinal positivo, a barra está sob tração. Se resultar em sinal negativo, a força real aponta para dentro do nó, indicando compressão.
  > Resolvendo o **Nó C** do triângulo de referência:
  > As barras AC e BC possuem comprimento $L = \sqrt{2^2 + 3^2} = \sqrt{13} \approx 3.6055\,\text{m}$.
  > Os versores diretores saindo de C são: $\hat{n}_{CA} = (-2/\sqrt{13}, -3/\sqrt{13})$ e $\hat{n}_{CB} = (2/\sqrt{13}, -3/\sqrt{13})$.
  > Pelo equilíbrio em $x$:
  > $$\sum F_x = 0 \implies -\frac{2}{\sqrt{13}} N_{AC} + \frac{2}{\sqrt{13}} N_{BC} = 0 \implies N_{AC} = N_{BC}$$
  > Pelo equilíbrio em $y$:
  > $$\sum F_y = 0 \implies -2 \left(\frac{3}{\sqrt{13}}\right) N_{AC} - 10 = 0 \implies N_{AC} = N_{BC} = -\frac{5\sqrt{13}}{3} \approx -6.0093\,\text{kN}$$
  > O sinal negativo comprova fisicamente que as duas diagonais trabalham em **compressão**.
  > No **Nó A**:
  > $$\sum F_x = 0 \implies N_{AB} + \frac{2}{\sqrt{13}} N_{AC} + R_{Ax} = 0 \implies N_{AB} = -\frac{2}{\sqrt{13}}(-6.0093) = +\frac{10}{3} \approx +3.3333\,\text{kN}$$
  > O sinal positivo confirma que o banzo inferior está sob **tração**, como previsto fisicamente."

---

### BLOCO 8: Método das Seções (Ritter) para Conferência Local (09:00 - 10:15)
- **Orador:** Apresentador 1
- **Slide de Apoio:** Slide 12 (Validação Cruzada) e Dossiê Teórico
- **Mensagem Central:** Explicar como o Método de Ritter permite auditar barras internas sem resolver a treliça nó a nó, usando o Caso 05.
- **O que Falar (Verbalização Recomendada):**
  > "Para estruturas com grande quantidade de nós, o Método dos Nós torna-se moroso para cálculos manuais de verificação. Por isso, utilizamos o Método das Seções de Ritter como uma conferência independente de alta confiabilidade.
  > No método de Ritter, cortamos a estrutura em duas partes passando por no máximo 3 barras cujas linhas de ação não convirjam para o mesmo ponto.
  > Exercitamos isso formalmente no caso `05-forca-zero-T`:
  > Uma treliça retangular com diagonal interna AC e carga externa no nó C ($F_x = +6\,\text{kN}, F_y = -10\,\text{kN}$).
  > Passamos uma seção vertical cortando as barras CD, AC e AB, e isolamos o corpo rígido da esquerda (nós D e A).
  > Tomando o somatório de momentos em relação ao nó A:
  > $$\sum M_A = 0 \implies -3 \cdot N_{CD} = 0 \implies N_{CD} = 0$$
  > Em seguida, pelo equilíbrio vertical:
  > $$\sum F_y = 0 \implies 0.6 \cdot N_{AC} + R_{Ay} = 0 \implies N_{AC} = \frac{4.5}{0.6} = +7.5\,\text{kN} \text{ (Tração)}$$
  > E pelo equilíbrio horizontal:
  > $$\sum F_x = 0 \implies N_{AB} + 0.8 \cdot N_{AC} + N_{CD} + R_{Ax} = 0 \implies N_{AB} = 0$$
  > O método de Ritter confirma instantaneamente que $N_{CD} = 0$, $N_{AB} = 0$ e $N_{AC} = +7.5\,\text{kN}$, com exata paridade em relação ao Método da Rigidez do nosso solver."

---

### BLOCO 9: Método da Rigidez Direta — Dedução e Montagem Global (10:15 - 12:15)
- **Orador:** Apresentador 1
- **Slide de Apoio:** Slide 9 (Rigidez Direta) e Slide 10 (Montagem Global e Solução)
- **Mensagem Central:** Dedução formal da matriz de rigidez do elemento $k_e$ ($4 \times 4$), propriedades mecânicas (simetria, posto 1), montagem de $K_{\text{global}}$ e imposição das condições de contorno essenciais.
- **O que Falar (Verbalização Recomendada):**
  > "O motor computacional do nosso software baseia-se no Método dos Elementos Finitos aplicado a barras: o **Método da Rigidez Direta**.
  > Ele é universal: resolve tanto treliças isostáticas quanto hiperestáticas e nos fornece diretamente a deformada e os deslocamentos nodais.
  > Seja uma barra ligando os nós A e B, de comprimento $L$, área $A$, módulo de Young $E$ e cossenos diretores $c = \cos\theta, s = \sin\theta$.
  > O alongamento elástico $\Delta L$ no sistema global é a projeção dos deslocamentos nodais:
  > $$\Delta L = \begin{bmatrix} -c & -s & c & s \end{bmatrix} \mathbf{u}_e$$
  > Aplicando a Lei de Hooke e o Princípio dos Trabalhos Virtuais, obtemos a matriz de rigidez da barra no referencial global:
  > $$k_e = \frac{EA}{L} \begin{bmatrix}
  >  c^2  &  cs & -c^2 & -cs \\
  >  cs   &  s^2 & -cs & -s^2 \\
  > -c^2  & -cs &  c^2 &  cs \\
  > -cs   & -s^2 &  cs &  s^2
  > \end{bmatrix}$$
  > Esta matriz possui três propriedades mecânicas fundamentais que auditamos em nossos testes unitários:
  > 1. É simétrica ($k_e = k_e^T$), em obediência ao Teorema da Reciprocidade de Maxwell-Betti.
  > 2. Tem posto igual a 1: ela possui apenas um autovalor não nulo ($\lambda = 2EA/L$). A barra física só resiste à solicitação axial; os outros três autovalores nulos representam os três movimentos de corpo rígido no plano (duas translações e uma rotação).
  > A montagem da matriz de rigidez global $K$ ($2n \times 2n$) é feita somando as contribuições de cada barra nos respectivos graus de liberdade.
  > Em seguida, particionamos a matriz separando os graus de liberdade livres ($f$) e os vinculados pelos apoios ($s$):
  > Impondo a condição de contorno essencial $\mathbf{u}_s = \mathbf{0}$, obtemos:
  > $$\mathbf{K}_{ff} \mathbf{u}_f = \mathbf{F}_f \implies \mathbf{u}_f = \mathbf{K}_{ff}^{-1} \mathbf{F}_f$$
  > E as reações de apoio saem diretamente de:
  > $$\mathbf{R} = \mathbf{K}_{sf} \mathbf{u}_f - \mathbf{F}_s$$
  > Uma vez obtidos os deslocamentos nodais, recuperamos o esforço normal exato de cada barra através de $N = \frac{EA}{L} \Delta L$."

---

### BLOCO 10: Detecção Espectral de Mecanismos e Instabilidade (12:15 - 13:30)
- **Orador:** Apresentador 1 / Apresentador 2
- **Slide de Apoio:** Slide 11 (Detecção Espectral e Caso 10)
- **Mensagem Central:** Explicar como o software lida com matrizes singulares via análise espectral de autovalores, sem cair em `ZeroDivisionError` ou números absurdos.
- **O que Falar (Verbalização Recomendada):**
  > "Um dos pontos altos da nossa modelagem computacional foi o tratamento rigoroso de mecanismos e instabilidades geométricas.
  > Em softwares ingênuos, quando uma treliça é instável, a submatriz $K_{ff}$ é singular e o programa trava ou gera deslocamentos absurdos da ordem de $10^{16}\,\text{m}$.
  > Em nossa implementação, **antes** de tentar resolver o sistema linear, calculamos os autovalores de $K_{ff}$ através da decomposição espectral simétrica:
  > $$K_{ff} \mathbf{\phi}_i = \lambda_i \mathbf{\phi}_i$$
  > Se qualquer autovalor $\lambda_i$ for inferior à tolerância de $10^{-9}$, o software identifica instantaneamente que a estrutura possui um modo cinemático livre (mecanismo).
  > Mais ainda: o autovetor $\mathbf{\phi}_i$ correspondente nos aponta exatamente quais nós e quais direções compõem o mecanismo!
  > Um exemplo magistral disso é o nosso caso `10-mecanismo`:
  > Temos dois pinos fixos nas pontas A e C, e um nó livre B no centro com duas barras colineares. Pela contagem clássica, $b + r = 2 + 4 = 6 = 2n$, o que daria $g = 0$ (aparentemente isostática!).
  > No entanto, o nó B não possui nenhuma triangulação para conter o movimento vertical. A análise espectral do nosso software revela $\lambda = 0.000$ no grau de liberdade $B.u_y$.
  > O programa imediatamente interrompe o cálculo e informa ao usuário: *'A treliça tem mecanismo interno: a matriz de rigidez é singular no GDL [B.uy]'*, demonstrando robustez impecável sem crash."

---

### BLOCO 11: Identificação Geométrica de Barras de Força Zero (13:30 - 14:45)
- **Orador:** Apresentador 2
- **Slide de Apoio:** Slide 13 (Barras de Força Zero R1-R3)
- **Mensagem Central:** Definir as regras geométricas R1, R2 e R3, suas justificativas estáticas e a importância física dessas barras.
- **O que Falar (Verbalização Recomendada):**
  > "O software identifica e justifica analiticamente as barras de força zero ($N = 0$) através de inspeção topológica nos nós descarregados e sem apoio:
  > - **Regra R1:** Nó descarregado onde concorre apenas uma barra $\implies N = 0$.
  > - **Regra R2:** Nó descarregado onde concorrem exatamente duas barras não colineares $\implies$ ambas possuem $N_1 = N_2 = 0$. (Exercitada no Caso 05).
  > - **Regra R3:** Nó descarregado onde concorrem três barras, sendo duas colineares $\implies$ a terceira barra não colinear possui necessariamente $N_3 = 0$. (Exercitada no montante CT do Caso 06).
  > É essencial enfatizar perante a banca um conceito físico que frequentemente gera confusão:
  > **Uma barra de força zero não deve ser removida da treliça real.**
  > Ela possui esforço nulo naquele carregamento específico, mas continua tendo rigidez axial ($EA$). Ela desempenha duas funções vitais:
  > 1. Reduz o comprimento de flambagem dos banzos comprimidos adjacentes;
  > 2. Estabiliza a treliça contra cargas acidentais não previstas no modelo inicial (como vento, vibração ou carregamentos móveis)."

---

### BLOCO 12: Tensões Normais e Dimensionamento Inverso (14:45 - 16:15)
- **Orador:** Apresentador 1 / Apresentador 2
- **Slide de Apoio:** Slide 14 (Tensões e Dimensionamento Inverso)
- **Mensagem Central:** Apresentar a relação constitutiva $\sigma = N/A$, a determinação da barra crítica e o dimensionamento inverso $A_{\text{req}} = |N|/\sigma_{\text{adm}}$.
- **O que Falar (Verbalização Recomendada):**
  > "Cumprindo integralmente a paridade com o comando `frmTrussStress` do MdSolids 4.0, nosso módulo contempla o cálculo das tensões normais e o dimensionamento de seções:
  > Pela hipótese H1 de barras biarticuladas com esforço axial puro, a tensão normal distribui-se uniformemente na seção transversal:
  > $$\sigma = \frac{N}{A} \quad [\text{MPa}] = \frac{N\,[\text{kN}] \times 10^3}{A\,[\text{mm}^2]}$$
  > A convenção de sinal é preservada: $\sigma > 0$ representa tensão de tração e $\sigma < 0$ representa tensão de compressão.
  > A barra crítica do ponto de vista resistente é aquela que atinge o maior valor em módulo de tensão normal ($|\sigma|_{\text{máx}}$).
  > No problema inverso de dimensionamento, dado o material com tensão admissível $\sigma_{\text{adm}}$, o software calcula a área mínima necessária:
  > $$A_{\text{req}} = \frac{|N|}{\sigma_{\text{adm}}} \quad [\text{mm}^2]$$
  > O uso do módulo $|N|$ garante que a área da seção seja sempre estritamente positiva, tanto para escoras comprimidas quanto para tirantes tracionados.
  > Implementamos também a taxa de utilização:
  > $$u = \frac{|\sigma|}{\sigma_{\text{adm}}} = \frac{A_{\text{req}}}{A_{\text{atual}}}$$
  > Se $u \le 1.0$, a barra é segura; se $u > 1.0$, a seção é insuficiente e requer redimensionamento."

---

### BLOCO 13: Demonstração ao Vivo, Auditoria de Resíduos e Conclusão (16:15 - 18:00)
- **Orador:** Apresentador 2 / Dupla
- **Slide de Apoio:** Slide 15 (Resíduos), Slide 16 (Gabarito) e Slide 18 (Conclusão)
- **Mensagem Central:** Apresentar a aplicação em tempo real, demonstrar a resolução do caso canônico, conferir os resíduos $< 10^{-14}$ e concluir a apresentação.
- **O que Falar (Verbalização Recomendada):**
  > "Para finalizar a apresentação e passar para a bateria prática:
  > Convidamos o professor a observar na tela a aplicação em execução.
  > Carregando o caso `01-triangulo`:
  > Em tempo real, a interface desenha o diagrama vetorial em SVG: banzo inferior em azul com $+3.33\,\text{kN}$ (<span class="badge-blue">Tração</span>), diagonais em vermelho com $-6.01\,\text{kN}$ (<span class="badge-red">Compressão</span>), reações em verde com $5.00\,\text{kN}$ nos apoios A e B.
  > Na aba de verificações:
  > - $\sum F_x = 4.44 \times 10^{-16}\,\text{kN} \approx 0$
  > - $\sum F_y = 8.88 \times 10^{-16}\,\text{kN} \approx 0$
  > - $\sum M = 3.55 \times 10^{-15}\,\text{kN}\cdot\text{m} \approx 0$
  > - Resíduo nodal máximo: $8.88 \times 10^{-16}\,\text{kN} \approx 0$
  > A concordância com o Método dos Nós independente é exata com resíduo nulo.
  > Clicando no botão 'Relatório Técnico', o software gera imediatamente o dossiê formal em HTML formatado para A4, com diagrama vetorial em alta resolução, tabelas de esforços e tensões, pronto para arquivamento ou exportação em PDF.
  > Temos ainda o plano de contingência com todos os 12 casos canônicos pré-compilados em `docs/relatorios/`.
  > Concluímos assim a defesa teórica dos 4,0 pontos, demonstrando domínio completo da obtenção dos dados, do tratamento computacional, dos conceitos matemáticos envolvidos e da interpretação física dos resultados.
  > Estamos prontos para a arguição da banca e para a bateria de 8 exercícios."

---

## 3. Gabarito de Arguição da Banca (Perguntas Desafiadoras Antecipadas e Respostas Prontas)

Aqui estão as 12 perguntas mais prováveis que o Prof. Márcio pode fazer durante a arguição, acompanhadas das respostas técnicas exatas:

---

### Pergunta 1:
**"Por que vocês implementaram o Método da Rigidez Direta se a maioria dos exercícios propostos em sala ou na avaliação N2 são treliças isostáticas que poderiam ser resolvidas apenas pelo Método dos Nós à mão?"**

**Resposta do Grupo:**
> "Professor, a escolha do Método da Rigidez Direta foi uma decisão de engenharia de longo alcance:
> Primeiro, o Método da Rigidez é a formulação padrão da indústria moderna de cálculo estrutural (base de softwares como SAP2000, ANSYS e Ftool).
> Segundo, o Método dos Nós manual só resolve estruturas isostáticas; se a banca nos propuser uma treliça hiperestática (como o nosso Caso 08), o Método dos Nós falha porque há mais incógnitas do que equações de equilíbrio. O Método da Rigidez resolve isostáticas e hiperestáticas com a mesma elegância.
> Terceiro, o Método da Rigidez fornece de forma analítica e direta os **deslocamentos nodais e a deformada da treliça**, o que enriquece enormemente a interpretação física.
> E para garantir total integridade, nós mantivemos o Método dos Nós implementado como um segundo solver independente no código, usando-o para validação cruzada contínua."

---

### Pergunta 2:
**"Se eu duplicar a área $A$ ou o módulo de elasticidade $E$ de todas as barras de uma treliça isostática, o que acontece com os esforços normais $N$? E o que acontece se a treliça for hiperestática?"**

**Resposta do Grupo:**
> "Em uma **treliça isostática**, os esforços normais $N$ **não sofrem nenhuma alteração**! Em estruturas isostáticas, os esforços internos são determinados exclusivamente pelas equações de equilíbrio da estática ($\sum F = 0, \sum M = 0$). O que muda ao duplicar $EA$ são apenas os deslocamentos nodais $\mathbf{u}$, que são reduzidos pela metade ($\mathbf{u} = \mathbf{K}^{-1} \mathbf{F}$).
> Já em uma **treliça hiperestática** ($g > 0$), os esforços normais **dependem fundamentalmente da rigidez relativa $EA$ das barras**. Barras com maior rigidez axial atraem maiores parcelas do esforço interno. Se alterarmos a área de apenas uma barra em uma treliça hiperestática, todos os esforços normais da estrutura se redistribuem para satisfazer a compatibilidade dos deslocamentos."

---

### Pergunta 3:
**"Por que a fórmula de estaticidade $b + r = 2n$ ($g = 0$) é uma condição necessária, mas não suficiente para garantir a estabilidade?"**

**Resposta do Grupo:**
> "A fórmula $b + r = 2n$ é uma contagem meramente escalar de equações e incógnitas algébricas. Ela garante apenas que a quantidade de incógnitas coincide com o número de graus de liberdade nodais.
> Contudo, a estabilidade física depende da **distribuição geométrica espacial** dessas barras e apoios.
> Se três nós estiverem dispostos em linha reta colinear (como demonstrado no nosso Caso 10), as barras não fornecem nenhuma componente de rigidez perpendicular à sua linha de ação. Mesmo tendo $b + r = 2n$, a estrutura forma um mecanismo com translação livre perpendicular, correspondendo a um autovalor nulo na matriz de rigidez global. Portanto, a contagem é condição necessária, mas a suficiência só é assegurada se o determinante da matriz de rigidez $\mathbf{K}_{ff}$ for estritamente positivo."

---

### Pergunta 4:
**"Como o algoritmo de vocês detecta que uma treliça é um mecanismo sem gerar erro fatal (`ZeroDivisionError`) ou números astronômicos na tela?"**

**Resposta do Grupo:**
> "Nós implementamos uma etapa preventiva de **decomposição espectral dos autovalores da submatriz $\mathbf{K}_{ff}$** antes da etapa de inversão ou fatoração de Cholesky.
> Como $\mathbf{K}_{ff}$ é simétrica e definida positiva para treliças estáveis, todos os seus autovalores reais $\lambda_i$ devem ser estritamente maiores que zero.
> Se o menor autovalor satisfizer $\lambda_{\text{mín}} < 10^{-9}$, o solver detecta a existência de um modo de corpo rígido sem rigidez elástica.
> O algoritmo examina as componentes do autovetor correspondente $\mathbf{\phi}$ para identificar quais graus de liberdade nodais compõem o mecanismo cinemático, interrompe o cálculo com segurança e retorna uma mensagem diagnóstica clara para o usuário (por exemplo, `mecanismo no GDL [B.uy]`), sem travar o software."

---

### Pergunta 5:
**"Por que a matriz de rigidez do elemento $k_e$ ($4 \times 4$) tem posto igual a 1 e quais são seus outros três autovalores?"**

**Resposta do Grupo:**
> "A matriz $k_e$ possui dimensões $4 \times 4$ porque atua sobre os quatro deslocamentos nodais da barra no plano: $(u_{ax}, u_{ay}, u_{bx}, u_{by})$.
> No entanto, sob a hipótese H1, a barra só resiste elasticamente à variação do seu comprimento próprio (deformação axial $\Delta L$). Existe, portanto, **apenas um modo de deformação elástica**, cujo autovalor não nulo é exatamente $\lambda_1 = \frac{2EA}{L}$.
> Os outros três autovalores são rigorosamente nulos ($\lambda_2 = \lambda_3 = \lambda_4 = 0$). Eles representam os três graus de liberdade de **movimento de corpo rígido da barra no plano**:
> 1. Translação pura em $x$;
> 2. Translação pura em $y$;
> 3. Rotação infinitesimal de corpo rígido em torno do centro de massa.
> Qualquer um desses três movimentos não gera deformação elástica e, portanto, não gera forças nodais."

---

### Pergunta 6:
**"Por que a matriz global de rigidez $\mathbf{K}$ é sempre simétrica? Qual é a justificativa física para isso?"**

**Resposta do Grupo:**
> "A simetria da matriz de rigidez global ($\mathbf{K} = \mathbf{K}^T$, isto é, $K_{ij} = K_{ji}$) é consequência física direta do **Teorema da Reciprocidade de Maxwell-Betti** e da existência de uma função de Energia Potencial Elástica de Deformação ($U = \frac{1}{2} \mathbf{u}^T \mathbf{K} \mathbf{u}$).
> Fisicamente, $K_{ij}$ representa a força gerada no grau de liberdade $i$ devido a um deslocamento unitário imposto no grau de liberdade $j$. O teorema de Betti postula que o trabalho realizado pelas forças do estado A nos deslocamentos do estado B é igual ao trabalho realizado pelas forças do estado B nos deslocamentos do estado A. Isso impõe matematicamente que a matriz hessiana da energia de deformação seja estritamente simétrica."

---

### Pergunta 7:
**"Se o software calcula $N = 0$ em uma barra de força zero, por que não podemos simplesmente apagar essa barra da treliça na obra?"**

**Resposta do Grupo:**
> "Porque a condição de força zero é um resultado estático válido **exclusivamente para a combinação de cargas pontuais analisada naquele instante**.
> Em uma estrutura real sujeita a intempéries:
> 1. Se a direção do vento mudar ou se houver uma carga de manutenção em um nó adjacente, a barra passará a receber esforço axial significativo.
> 2. Mais importante: as barras de força zero funcionam como **travamento lateral anti-flambagem**. Elas reduzem o comprimento de flambagem efetivo ($L_{\text{flamb}}$) das barras comprimidas longas que se cruzam naquele nó. Removê-las dobraria o comprimento livre de flambagem, reduzindo a carga crítica de Euler a apenas um quarto ($P_{\text{cr}} = \frac{\pi^2 EI}{L^2}$), o que poderia levar a treliça ao colapso por instabilidade elástica."

---

### Pergunta 8:
**"Como é feito o dimensionamento inverso e por que o módulo $|N|$ é utilizado na equação $A_{\text{req}} = |N| / \sigma_{\text{adm}}$?"**

**Resposta do Grupo:**
> "A tensão normal média é dada por $\sigma = N / A$. Adotando a convenção de tração positiva e compressão negativa, o esforço normal $N$ carrega sinal.
> Como a área de uma seção transversal de aço ou alumínio é uma grandeza estritamente positiva ($A > 0$), a área requerida para não ultrapassar a tensão admissível deve ser computada tomando o valor absoluto do esforço normal:
> $$A_{\text{req}} = \frac{|N|}{\sigma_{\text{adm}}}$$
> Além disso, nosso software permite configurar limites de tensão admissível assimétricos para tração ($\sigma_{\text{adm, tração}}$) e compressão ($\sigma_{\text{adm, comp}}$), o que é indispensável para materiais frágeis ou que apresentem comportamento diferenciado."

---

### Pergunta 9:
**"O que garante que os números apresentados na tela são a solução real do problema e não um bug de programação ou arredondamento numérico?"**

**Resposta do Grupo:**
> "Nós implementamos uma **auditoria quádrupla independente de equilíbrio e um segundo solver desacoplado**:
> 1. Verificamos se $\sum F_x = 0$, $\sum F_y = 0$ e $\sum M = 0$ no corpo global, com resíduos inferiores a $10^{-14}$.
> 2. Calculamos o resíduo nodal local em cada nó isolado: a soma vetorial de todas as barras e forças incidentes no nó fecha em zero com precisão na ordem de $10^{-15}$.
> 3. Cruzamos o resultado com o Método dos Nós em forma matricial, que usa um algoritmo puramente geométrico sem utilizar a rigidez $EA$ nem os deslocamentos nodais. Como dois métodos matematicamente distintos convergem para o mesmo número até a 14ª casa decimal, temos a prova matemática e científica da correção dos resultados."

---

### Pergunta 10:
**"Por que apoios engastados não estão disponíveis no módulo de treliças?"**

**Resposta do Grupo:**
> "Porque a presença de um apoio engastado restringe o giro do nó ($\theta = 0$), gerando uma reação de momento fletor engastado ($M_R \neq 0$).
> Isso violaria frontalmente a **Hipótese Fundamental H1**, segundo a qual todas as ligações de uma treliça são rótulas perfeitas sem momento fletor.
> Se admitíssemos engaste, as barras deixariam de ser elementos puros de treliça e passariam a se comportar como elementos de pórtico ou viga, sujeitos à flexão composta ($M$ e $V$), o que desvirtuaria a mecânica canônica do módulo Trusses."

---

### Pergunta 11:
**"Se o professor Márcio pedir para resolver na hora uma treliça com carga distribuída sobre a cobertura, como procedemos?"**

**Resposta do Grupo:**
> "Demonstramos imediatamente no software o procedimento consagrado na engenharia estrutural:
> Calculamos a área de influência de cada nó do banzo superior multiplicando a carga distribuída $q\,[\text{kN/m}]$ pela metade dos vãos adjacentes.
> Aplicamos as cargas nodais equivalentes resultantes diretamente nos nós do banzo superior (exatamente como configurado no nosso Caso Canônico 02 de Telhado Pratt), resolvendo a treliça com total fidelidade física à hipótese H2."

---

### Pergunta 12:
**"Qual é a limitação do critério $\sigma = N/A$ para barras muito compridas submetidas a esforço de compressão?"**

**Resposta do Grupo:**
> "Excelente colocação, professor. A equação $\sigma = N/A$ avalia unicamente o escoamento ou ruptura por tensão normal média do material na seção bruta.
> No entanto, para barras delgadas comprimidas (com índice de esbeltez $\lambda = L/i$ elevado), a barra pode falhar catastroficamente por **flambagem elástica global de Euler** sob uma carga crítica $P_{\text{cr}} = \frac{\pi^2 EI}{L^2}$ muito antes de atingir a tensão admissível do material.
> Por isso, em nosso dossiê teórico (Seção 10.5), alertamos explicitamente que o cálculo de $\sigma = N/A$ não substitui a verificação de estabilidade e flambagem por normas estruturais."

---

## 4. Tabela Rápida de Gabarito para Consulta Imediata na Arguição

| Caso | Treliça | Apoios | Nós / Barras | Reações de Apoio | Esforços Críticos das Barras | Resíduo Estático |
|---|---|---|---|---|---|---|
| **01** | Triângulo Canônico | A (pino), B (rolete) | 3 / 3 | $R_{Ax} = 0, R_{Ay} = 5, R_{By} = 5$ | $N_{AB} = +3.33\,\text{kN}$ (T), $N_{AC} = N_{BC} = -6.01\,\text{kN}$ (C) | $< 10^{-15}$ |
| **02** | Telhado Pratt | A (pino), E (rolete) | 8 / 13 | $R_{Ax} = 0, R_{Ay} = 20, R_{Ey} = 20$ | Banzo sup. comprimido, tirantes tracionados | $< 10^{-14}$ |
| **03** | Warren (3 painéis) | A (pino), D (rolete) | 7 / 11 | $R_{Ax} = 0, R_{Ay} = 15, R_{Dy} = 15$ | Simetria perfeita; diagonais alternando T/C | $< 10^{-14}$ |
| **04** | Pratt com Vento | A (pino), E (rolete) | 8 / 13 | $R_{Ax} = -10, R_{Ay} = 15.5, R_{Ey} = 16.5$ | Reação horizontal absorvida inteiramente no pino | $< 10^{-14}$ |
| **05** | Força Zero em T | A (pino), B (rolete) | 4 / 5 | $R_{Ax} = -6, R_{Ay} = -4.5, R_{By} = 14.5$ | $N_{CD} = 0, N_{AB} = 0, N_{AC} = +7.5\,\text{kN}$ (Ritter) | $< 10^{-15}$ |
| **06** | Força Zero R3 | A (pino), B (rolete) | 4 / 5 | $R_{Ax} = 0, R_{Ay} = 5, R_{By} = 5$ | Montante central $N_{CT} = 0$ (Regra R3) | $< 10^{-15}$ |
| **07** | Geometria Irregular | A (pino), B (rolete) | 4 / 5 | $R_{Ax} = -3.54, R_{Ay} = 8.21, R_{By} = 6.33$ | Cargas inclinadas e ângulos oblíquos | $< 10^{-15}$ |
| **08** | Hiperestática ($g=1$) | A (pino), B (rolete) | 4 / 6 | Reações dependentes de compatibilidade | Treliça indeterminada; dependência de $EA$ | $< 10^{-15}$ |
| **09** | Hipostática ($g=-1$) | A (pino), B (livre) | 3 / 3 | Sem solução de equilíbrio | Recusada com erro explicativo amigável | Detectado |
| **10** | Mecanismo ($g=0$) | A (pino), C (pino) | 3 / 2 | Submatriz singular det($K_{ff}$) = 0 | Autovalor nulo $\lambda = 0$ no GDL $B.u_y$ | Detectado |
| **11** | Sem Carga | A (pino), B (rolete) | 3 / 3 | Reações nulas ($R = 0$) | Todas as barras com $N = 0$ | $0.00$ |
| **12** | Pratt Grande Ponte | A (pino), G (rolete) | 14 / 25 | $R_{Ax} = 0, R_{Ay} = 60, R_{Gy} = 60$ | Ponte de 6 painéis; escalabilidade total | $< 10^{-13}$ |

---
**Fim do Roteiro de Defesa. Todos os conceitos e dados estão conferidos e auditados.**
