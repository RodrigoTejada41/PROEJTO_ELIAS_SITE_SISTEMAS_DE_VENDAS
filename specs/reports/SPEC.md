# REL-001 — Relatório de estoque

Estado: VALIDATED no piloto local Docker em 05/11/2026. Evidências no checkpoint. Revisão independente pendente.

Relatório de saldo por SKU, com busca por código ou descrição e estado ativo/inativo para MASTER. Operador consulta e exporta somente SKUs ativos. Mesmos filtros e fonte de dados para tela e CSV. Tela paginada em 50 registros, exportação limitada a 10 mil SKUs, com erro explícito se exceder. Totais consideram todos os registros filtrados, independentemente da página.

CSV UTF-8 com cabeçalho e neutralização de fórmulas em campos textuais. Saldo vem da soma do livro de movimentos. Consulta e totais usam a mesma visão transacional. Sem efeitos de escrita. Aceite inclui filtros, soma dos saldos exportados, autorização de inativos, limite, caracteres especiais e teclado em português/espanhol. Relatórios financeiros, de venda, lotes e validade dependem das respectivas fontes de dados.

## REL-002 — Vendas e fluxo financeiro

Autorizado no piloto de 05/11/2026. MASTER consulta vendas confirmadas por período da confirmação e vendedor, com cliente e vendedor preservados, total líquido em USD e equivalente PYG na taxa da venda. Vendas canceladas são excluídas da apuração de vendas confirmadas. Produtos mais vendidos são classificados pela quantidade de SKUs em vendas confirmadas, sem presumir alocação do desconto de cabeçalho.

Fluxo financeiro deriva das baixas e seus estornos, usando a moeda efetivamente recebida ou paga. Estorno entra no período do próprio estorno. Recebimentos são entradas e pagamentos são saídas, com sinais invertidos em estornos. Totais são separados em USD e PYG. Venda confirmada, recebimento, comissão apurada e comissão paga permanecem conceitos distintos.

Filtros de datas inclusivos em UTC e fonte idêntica para tela e CSV. Tela paginada em 50, exportação até 10 mil registros e erro explícito acima disso. Não somar moedas distintas. Nenhum desses relatórios publica reconhecimento contábil ou fiscal.

## REL-003 — Painel de vendas e filtros gerenciais

Estado: aprovado pelo usuário, implementado e validado no piloto local. Revisão independente pendente.

### Painel

O painel inicial de MASTER e DEV mantém os cartões operacionais e ganha um resumo comercial com filtro de período e vendedor. O período inicial são os últimos 30 dias, incluindo o dia atual. Mostrar quantidade de vendas confirmadas, total líquido em USD e equivalente em PYG pela cotação preservada em cada venda, ticket médio em USD, evolução diária e cinco SKUs mais vendidos por quantidade. A evolução tem leitura textual e gráfico responsivo. Vendas canceladas ou em rascunho ficam fora dos indicadores. A tela indica ausência de vendas no período e oferece atalhos para **Nova venda** e os relatórios correspondentes. Operador conserva a visão operacional atual.

### Relatórios

| Área | Filtros e informações |
| --- | --- |
| Vendas | Período e vendedor, com total e quantidade das vendas confirmadas. |
| Mais vendidos | Aba própria com período, vendedor e busca por SKU ou descrição. Ranking por unidades vendidas, com ordenação determinística em empates. |
| Estoque | Busca, situação ativo/inativo e faixa de saldo positivo, zero ou negativo. Totais do conjunto filtrado. |
| Financeiro | Fluxo realizado por período, moeda e natureza de recebimento, pagamento ou estorno. Totais separados por moeda. Atalhos para contas a receber e a pagar no Financeiro, onde ficam os títulos em aberto. |

Reutilizar as consultas e as regras de REL-001/002. Usar a mesma definição de período para o painel e para o relatório correspondente. Preservar os filtros ao paginar, exportar e abrir atalhos relacionados. As exportações CSV respeitam os filtros e limites da tela. O fluxo financeiro apresenta baixas e estornos pelo próprio evento e fica separado do valor de vendas confirmadas. MASTER e DEV acessam indicadores comerciais e financeiros. Operador consulta e exporta estoque de SKUs ativos conforme autorização vigente.

### Implementação e aceite

1. Ampliar consultas e páginas existentes em FastAPI, PostgreSQL e AdminLTE 3, sem migração prevista.
2. Conferir totais do painel com os relatórios sob os mesmos filtros, incluindo limites de data, vendas canceladas, períodos vazios, estoque negativo, filtros financeiros e separação USD/PYG.
3. Validar permissões por acesso direto, paginação, CSV filtrado e navegação por teclado em português e espanhol, a 390 e 1280 px.
