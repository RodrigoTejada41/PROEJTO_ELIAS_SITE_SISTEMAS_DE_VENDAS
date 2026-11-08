# Produtos

Estado: VALIDATED no piloto local em 04/11/2026. Aprovação registrada a partir da instrução de continuar após a apresentação da Spec.

[Regras funcionais](../../docs/functional/PRODUCTS.md)

## CAT-001 — Cadastro de SKUs do piloto

Proposta de 04/11/2026 para Esther Beauty 777. O catálogo precisa identificar a apresentação comercial que futuramente será referenciada por estoque e vendas. Cada SKU representa uma apresentação, com código interno e identificador de banco estáveis. Fragrância, cor, tonalidade, apresentação ou volume podem distinguir SKUs por meio de um campo de variação descritiva. Agrupamento de SKUs em um produto pai fica para um recorte posterior.

### Escopo e autorização

- MASTER lista, cadastra, edita dados descritivos e inativa SKUs.
- Operador com sessão ativa consulta somente SKUs ativos. Requisições diretas de escrita recebem 403. Visitantes sem sessão são redirecionados ao login.
- Interface em português e espanhol com AdminLTE 3. Reutilizar sessão, autorização e proteção CSRF existentes.
- Preços, custos, moeda, vínculos de fornecedor, saldo, estoque mínimo, lote, validade, importação, reativação e venda ficam para Specs próprias.

### Dados e comportamento

| Campo | Regra proposta |
| --- | --- |
| ID | Chave primária gerada pelo PostgreSQL. Referência futura de estoque e venda. |
| Código interno | Obrigatório, 1 a 64 caracteres ASCII alfanuméricos, ponto, hífen ou sublinhado. Remover espaços externos e normalizar para maiúsculas. Único em toda a instalação, inclusive entre registros inativos. Imutável após cadastro. |
| Descrição | Obrigatória, 1 a 160 caracteres após remover espaços externos. |
| Marca, categoria e variação | Texto opcional, até 100 caracteres por campo. Vazio vira nulo. |
| Código de barras | Texto opcional, 1 a 32 dígitos quando preenchido. Preservar zeros à esquerda e exigir unicidade quando informado. |
| Estado | Ativo ao cadastrar. Inativação lógica idempotente, preservando ID e códigos. |
| Auditoria | Cadastro, alteração e inativação registram ator, ação, SKU e horário na mesma transação da mudança. |

A listagem ordena por descrição e ID e oferece busca por código ou descrição. O cadastro e a edição validam os dados no servidor. Restrições de formato e unicidade no PostgreSQL protegem as regras sob concorrência. Para evitar sobrescrever alterações administrativas simultâneas, a edição verifica a versão lida pelo formulário e informa conflito quando estiver desatualizada.

### Implementação e retorno

Preservar FastAPI, Jinja2, PostgreSQL e AdminLTE 3. Adicionar migração para catálogo e eventos de catálogo, com referência à conta responsável e ao SKU. Usar consultas parametrizadas, autorização no servidor e POST com CSRF para alterações. Não há dependências externas novas previstas.

A migração é aditiva. Em caso de retorno após gravar SKUs, voltar à versão anterior da aplicação e preservar as tabelas e os dados para correção. Validar aplicação da migração em banco descartável antes da homologação.

### Critérios de aceite

1. MASTER cadastra duas apresentações da mesma linha com códigos distintos e edita seus dados descritivos mantendo IDs e códigos internos.
2. Códigos equivalentes após normalização e códigos de barras duplicados são rejeitados, inclusive sob concorrência. Código de barras com zero inicial mantém o valor.
3. MASTER inativa um SKU. O registro continua na listagem administrativa, some da consulta do operador e conserva os códigos. Repetir a inativação não duplica o evento.
4. Operador consulta SKUs ativos. Escrita direta por operador ou POST sem CSRF válido não altera dados. Acesso anônimo redireciona ao login.
5. A segunda edição baseada na mesma versão recebe aviso de conflito e preserva os dados da primeira.
6. Ações administrativas bem-sucedidas registram ator e SKU. Falhas de gravação não deixam alteração parcial.
7. Listagem, cadastro, mensagens e inativação funcionam em português e espanhol com teclado e sem rolagem horizontal nos tamanhos de 390 e 1280 px.

## Decisões para recortes posteriores

Unidades de medida, atributos estruturados de variação, agrupamento de produto, política de reativação e eventual alteração de código. Moeda e arredondamento precisam ser definidos antes de preços e vendas. Regras de lote, validade e saldo pertencem à Spec de estoque.

## CAM-001 — Preços e custos em duas moedas

O recorte [CAM-001](CURRENCY.md) implementa custo e preço em USD e apresentação em PYG pela taxa vigente. Atualização de preços é exclusiva do MASTER, com versão do SKU e auditoria. A consulta do operador exclui custos. VEN-001 preserva preços e taxa na confirmação.

## CAT-002 — Importação e foto

Autorizado pelo pedido de importação de produtos por planilha e inclusão de imagens após a carga. O MASTER baixa um modelo CSV UTF-8 e importa até 1.000 SKUs por arquivo de até 1 MiB. O formato aceita vírgula ou ponto e vírgula. As colunas seguem os dados descritivos de CAT-001. Código e código de barras devem ser tratados como texto na planilha.

O lote cria registros com as regras e auditoria do cadastro manual. Uma linha inválida ou duplicada cancela a gravação do lote inteiro. A interface informa a linha que precisa de correção. Preços e saldos continuam nos fluxos comerciais existentes.

Na edição do SKU, o MASTER adiciona, troca ou remove uma foto. A aplicação aceita JPEG, PNG ou WebP de até 5 MiB e 20 megapixels, converte para JPEG com lado maior de até 960 pixels e descarta metadados. A foto fica no PostgreSQL e acompanha o backup. Sua leitura exige sessão e segue a visibilidade do SKU. Alterações exigem CSRF, conferem a versão e registram auditoria.

Validar o fluxo em PT/ES, a preservação de zeros à esquerda, o rollback por duplicidade, uploads inválidos, acesso de operador e substituição de foto. O retorno pode usar a versão anterior da aplicação mantendo a migração aditiva e os dados.

## CAT-003 — Planilha Excel para cadastro e atualização

Estado: aprovado pelo usuário e implementado no piloto local. Build, testes PostgreSQL e fluxo Edge verificados. Validação no Microsoft Excel desktop e revisão independente pendentes.

MASTER e DEV podem baixar **Modelo Excel vazio** ou **Exportar produtos do banco** e enviar ambos os arquivos pela tela de importação. O formato é `.xlsx`, com uma tabela de produtos, cabeçalhos em PT ou ES, colunas separadas, filtros e cabeçalho fixo. Uma aba de instruções indica os campos editáveis e explica como adicionar uma linha. Código interno e código de barras usam formato texto para preservar zeros à esquerda.

| Grupo | Colunas |
| --- | --- |
| Identificação | Código interno, descrição, marca, categoria, variação e código de barras |
| Valores editáveis | Custo USD e preço de venda USD |
| Consulta | Custo PYG, preço de venda PYG, status e saldo atual |

A exportação preenche os dados atuais, inclusive produtos inativos. O sistema calcula PYG usando a taxa comercial vigente na exportação e identifica a taxa na aba de instruções. Sem taxa disponível, indica a ausência e deixa as colunas PYG em branco. Na importação, os campos PYG são ignorados. Após salvar, o catálogo calcula a conversão a partir dos valores USD e da taxa vigente. Status, saldo e foto seguem os respectivos fluxos do sistema.

O código interno identifica o SKU e permanece imutável. Para editar um SKU existente, use a linha exportada, com referência e versão protegidas contra edição acidental. O importador valida código, referência e versão no servidor. Uma linha nova usa código ainda inexistente. Omissão de uma linha não exclui produtos. Em linhas existentes, campos opcionais vazios limpam o valor correspondente. Antes de gravar, uma prévia indica criações, atualizações e linhas sem mudanças. O servidor revalida a versão na confirmação para impedir sobrescrita de edição posterior à exportação.

O lote é atômico. Dados inválidos, códigos duplicados ou versões conflitantes impedem qualquer gravação e identificam a linha afetada. Reaproveitar as validações, os limites monetários e a auditoria de catálogo e preços. Preservar a importação CSV existente como alternativa de compatibilidade.

### Implementação e aceite

1. Gerar e ler XLSX com biblioteca avaliada para a stack existente. Limitar linhas e tamanho compactado e descompactado, recusar fórmulas nas células importadas e preservar códigos como texto. Indicar eventual limite de exportação e permitir exportar em lotes quando necessário.
2. Validar no Excel a tabela preenchida e o ciclo baixar → editar → importar, com novo produto e produto existente no mesmo arquivo.
3. Testar zeros à esquerda, preço e custo USD, conversão PYG, limpeza explícita de opcionais, permissões, versão desatualizada, duplicidade e rollback de lote. Conferir que a importação preserva estoque, fotos e vendas históricas.
4. Usar os campos atuais de catálogo, preço e versão. Se a implementação confirmar essa compatibilidade, o retorno consiste em restaurar a versão anterior da aplicação, preservando as alterações válidas já gravadas.
