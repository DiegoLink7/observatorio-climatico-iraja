# AE1 - Planejamento do Observatório Climático Local (Irajá, RJ)

19/11/2026

O projeto vai analisar como foram a temperatura e a chuva em Irajá, Zona Norte do Rio de Janeiro, entre 15/10/2026 e 13/11/2026. O resultado será um resumo simples e confiável para os moradores do bairro e a associação de moradores.

## Identificação

| Item | Informação |
| --- | --- |
| Aluno | Diego Santos Nogueira |
| Curso | Ciência de Dados |
| Instituição | UNIMAR |
| Disciplina | Projeto Integrador Extensionista 2 |
| Professor | Luiz Bueno |
| Formato | Individual |
| Projeto | Observatório Climático Local |

## Problema e necessidade extensionista

Calor forte e chuva intensa mexem com a rotina de quem mora em Irajá, do caminho para o trabalho até a rua que alaga. Quem mora no bairro sente isso no dia a dia, mas raramente tem um registro organizado de quantos dias foram muito quentes ou quanto choveu num período.

O projeto usa dados abertos para montar esse registro. A pergunta que guia o trabalho é: como foi o tempo em Irajá nesses 30 dias, em números que um morador entende?

Com esse resumo na mão, a associação de moradores tem números para levar às conversas com a comunidade e aos pedidos feitos ao poder público.

A percepção de que calor e chuva forte são os temas que mais pesam no bairro ainda é uma hipótese. Ela será conferida em conversa com representantes da comunidade, como o professor recomendou.

## Público-alvo

O público são os moradores de Irajá, com a associação de moradores como ponte para a comunidade. Para eles, o que importa é saber quais foram os dias mais quentes, quais foram os mais chuvosos e quanto choveu no total. Médias técnicas sem explicação ajudam pouco.

Para não montar a análise só com base no que eu imagino ser importante, o plano prevê:

1. Uma conversa curta com pelo menos um representante da associação ou um morador antigo do bairro, para perguntar que informação sobre o tempo seria útil para eles.
2. Ajustar as perguntas analíticas se a conversa apontar outra prioridade, registrando a mudança e o motivo.
3. Usar linguagem simples e unidades explícitas (°C e mm) em tudo que for mostrado ao público.

## Recorte

| Item | Definição |
| --- | --- |
| Localidade | Irajá, Rio de Janeiro (RJ) |
| Coordenadas | latitude -22,8344; longitude -43,3272 ([Wikipedia](https://en.wikipedia.org/wiki/Iraj%C3%A1)) |
| Fuso horário | America/Sao_Paulo |
| Período | 15/10/2026 a 13/11/2026 (30 dias consecutivos) |
| Variável 1 | Temperatura máxima diária (°C) |
| Variável 2 | Temperatura mínima diária (°C) |
| Variável 3 | Precipitação diária acumulada (mm) |
| Fonte | API histórica do [Open-Meteo](https://open-meteo.com/) |
| Tabela principal | Uma linha por dia, uma coluna por variável |

Os dados do Open-Meteo vêm de modelos meteorológicos e reanálise, calculados para uma grade. Não são medições de uma estação instalada em Irajá, e o projeto vai deixar isso claro em todas as entregas.

O período termina poucos dias antes da coleta. Se a API ainda não tiver os últimos dias consolidados, a coleta vai mostrar valores ausentes e o período será deslocado para trás, mantendo 30 dias seguidos e registrando o ajuste.

## Perguntas analíticas e indicadores

Cada pergunta tem um indicador que a responde diretamente. Todos serão calculados com SQL sobre a tabela principal.

| # | Pergunta analítica | Indicador | Cálculo | Unidade |
| --- | --- | --- | --- | --- |
| P1 | Qual foi a maior temperatura máxima do período e em que dia ela ocorreu? | Temperatura máxima absoluta | Maior valor de temperatura máxima diária, com a data | °C |
| P2 | Quanto choveu no total e quais foram os 5 dias mais chuvosos? | Precipitação acumulada no período | Soma da precipitação diária dos 30 dias, mais o ranking dos 5 maiores dias | mm |
| P3 | A temperatura máxima média foi diferente entre dias com chuva e dias sem chuva? | Número de dias com chuva | Contagem de dias com precipitação maior ou igual a 1,0 mm; depois, média da máxima em cada grupo | dias e °C |

Critério de dia com chuva: precipitação diária maior ou igual a 1,0 mm. Abaixo disso o dia conta como sem chuva, para não tratar garoa mínima como dia chuvoso.

Na P3, uma diferença entre os grupos será descrita com cautela. Trinta dias não permitem afirmar que a chuva causou temperaturas menores, só que as duas coisas apareceram juntas nesse período.

Gráficos previstos para o painel (etapa futura):

1. Linha com as temperaturas máxima e mínima de cada dia (°C).
2. Barras com a precipitação de cada dia (mm), destacando os dias acima de 1,0 mm.

## Ferramentas, repositório e etapas

| Ferramenta | Papel no projeto |
| --- | --- |
| Python + Requests | Coleta dos dados na API e gravação da resposta original em JSON |
| pandas | Tratamento e validação: nomes de colunas, tipos, datas, ausentes e duplicados |
| DuckDB | Banco com a tabela principal, uma linha por dia |
| SQL | Consultas que respondem às três perguntas |
| Streamlit | Painel com indicadores e gráficos (etapa futura) |
| Git e GitHub | Histórico de versões e entrega do projeto |

O `.gitignore` vai excluir o ambiente virtual, arquivos temporários e qualquer arquivo com senha ou chave. A API do Open-Meteo usada aqui não exige chave.

Etapas, na ordem:

1. Criar o repositório, o README inicial e registrar este planejamento em `docs/escopo-1/AE1`.
2. Preparar o ambiente virtual e instalar as dependências com `pip`.
3. Coletar os dados e guardar o JSON original sem alterações.
4. Tratar, validar e carregar no DuckDB sem gerar duplicados quando o processo rodar de novo.
5. Escrever as consultas SQL e calcular os indicadores.
6. Montar o painel em Streamlit e o relatório final em PDF.
7. Apresentar o resumo a um representante da comunidade e registrar o retorno.

## Critérios de sucesso

O projeto será considerado bem-sucedido se cumprir os critérios abaixo. A última coluna diz em que etapa cada um pode ser conferido.

| Critério | Como verificar | Etapa |
| --- | --- | --- |
| Cobertura completa | A tabela tem exatamente 30 linhas, uma por dia, de 15/10 a 13/11/2026 | AE2 |
| Sem duplicados | Nenhuma data repetida, mesmo rodando a carga duas vezes | AE2 |
| Ausentes tratados | Zero valores ausentes, ou cada ausência registrada e explicada, sem troca por zero | AE2 |
| Valores coerentes | Temperatura máxima sempre maior ou igual à mínima; precipitação nunca negativa | AE2 |
| Perguntas respondidas | As 3 perguntas têm consulta SQL e resultado interpretado | AE2 |
| Reprodutível | Outra pessoa recria a base do zero seguindo só o README | AE2 |
| Painel coerente | Indicadores e gráficos do painel batem com o banco e com o relatório | Painel |
| Útil para o público | Um representante da comunidade entende o resumo e aponta pelo menos um uso prático | Devolutiva |

## Limitações, riscos e cuidados éticos

- O projeto descreve dias que já passaram. Ele não diz como o tempo vai ficar e não substitui os alertas da Defesa Civil.
- Os valores do Open-Meteo saem de um modelo calculado em grade, não de uma estação em Irajá. Podem diferir do que um termômetro ou pluviômetro na rua marcaria, e chuva muito localizada pode aparecer menor do que foi.
- Trinta dias dão um retrato do período. Não dá para falar em tendência climática nem em causa e efeito com isso.
- Os últimos dias do período talvez não estejam consolidados na data da coleta. A validação confere isso antes de qualquer análise.
- O projeto não coleta dados de moradores. Nas conversas com a comunidade, nomes só entram com autorização; sem ela, o registro fica como "representante da associação" ou "morador".
- Nenhuma senha ou chave vai para o repositório.

## Fontes

- [Open-Meteo](https://open-meteo.com/): fonte dos dados meteorológicos.
- [Irajá, Wikipedia](https://en.wikipedia.org/wiki/Iraj%C3%A1): coordenadas do bairro.
- Aula 1 do Projeto Integrador Extensionista CD 2, Prof. Luiz Bueno, Unimar EAD.
