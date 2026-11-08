# Estoque

Estado: VALIDATED no piloto Docker em 05/11/2026. Continuação após Docker autorizada pelo usuário. Evidências no checkpoint.

[Regras funcionais](../../docs/functional/INVENTORY.md)

## EST-001 — Movimentação local por SKU

O catálogo CAT-001 identifica cada apresentação comercial. O primeiro recorte de estoque propõe registrar entradas e saídas administrativas com motivo, histórico e saldo conciliável para Esther Beauty 777.

### Regras propostas para o piloto

- Uma empresa e um local de estoque. Quantidades inteiras por unidade comercial do SKU.
- MASTER registra entradas e saídas administrativas. Operador consulta saldos e histórico.
- Cada movimento referencia SKU, tipo, quantidade positiva, motivo obrigatório de 3 a 240 caracteres, ator e horário do servidor.
- O saldo inicial é zero e resulta do histórico. Entradas acrescentam unidades e saídas subtraem. Limites do piloto: 1 bilhão por movimento e saldo máximo de 2 bilhões de unidades.
- Saída que causaria saldo negativo é rejeitada, inclusive sob concorrência.
- SKU inativo conserva saldo e histórico consultáveis pelo MASTER e não aceita novos movimentos.
- Movimentos confirmados são imutáveis. Correção exige novo movimento compensatório com motivo e referência ao original, sujeito às mesmas regras de saldo e acesso.
- Cada movimento aceita uma compensação direta, com quantidade inversa determinada pelo servidor. A compensação também fica no histórico.
- Cada submissão recebe uma chave única. Repetir a mesma chave com o mesmo conteúdo retorna o resultado original. Reutilizar a chave com conteúdo diferente informa conflito.

### Contratos e segurança

Listagem e histórico requerem sessão ativa. Operador vê apenas SKUs ativos, sem controles de escrita. Escrita exige MASTER e POST com CSRF. O servidor valida quantidade, SKU, motivo e chave de submissão. A interface usa AdminLTE 3, identidade Esther Beauty 777 e português/espanhol.

Transação PostgreSQL coordena o bloqueio do SKU, a verificação de estado e saldo, o registro do movimento e a idempotência. O bloqueio precisa ser compatível com a inativação do catálogo. Índices e restrições garantem referências e unicidade de chave. Usar números inteiros com limites explícitos e rejeitar valores acima da capacidade do banco. Queries parametrizadas e histórico com paginação de 50 registros.

### Escopo reservado a entregas posteriores

Saída automática por venda, reserva, compras, devolução de venda, múltiplos locais, quantidades fracionárias, lotes, validade, custo e estoque mínimo dependem de seus contratos específicos. Esta proposta precisa confirmar que a unidade comercial inteira atende ao piloto.

### Critérios de aceite

1. Entrada de 10 unidades e saída de 3 deixam saldo 7, conciliável pelo histórico e com causa registrada.
2. Duas saídas simultâneas de 6 sobre saldo 10 permitem apenas uma e deixam saldo 4.
3. Duas submissões concorrentes com mesma chave e conteúdo criam um movimento. Mesma chave e outro conteúdo produzem conflito.
4. Falha de persistência reverte toda a operação. Saldo, histórico e idempotência permanecem consistentes.
5. Operador consulta saldo e histórico, recebe 403 ao escrever por URL direta e não consulta SKU inativo. Sessão inválida redireciona ao login e CSRF inválido impede gravação.
6. Quantidades zero, negativas, fracionárias ou acima do limite são rejeitadas. Motivo vazio é rejeitado.
7. Inativação concorrente com movimentação preserva um resultado serializado. Após a inativação, novos movimentos são recusados.
8. Uma compensação preserva o movimento original e referencia sua causa. Uma saída compensatória que tornaria saldo negativo é rejeitada.
9. Formulários e mensagens funcionam em português e espanhol a 390 e 1280 px, com teclado e foco visível.

### Implementação, retorno e validação

Migração aditiva em PostgreSQL e reutilização dos IDs do catálogo. Preservar FastAPI e templates Jinja2. Validar migração, transações, concorrência e HTTP em banco descartável e o fluxo visual em navegador.

Se houver retorno da aplicação após gravar movimentos, preservar tabelas e histórico para correção. Aprovar este recorte antes da implementação conforme o AGENTS.md do projeto.

## Integração VEN-001

A confirmação de venda baixa o estoque e cria o título a receber em transação única. Movimentos vinculados à venda não aceitam compensação administrativa direta. Cancelamento autorizado da venda repõe o estoque original, inclusive para SKU inativado posteriormente, coordenando a reversão com o financeiro.

## EST-002 — Permissão global de estoque negativo e entradas por Excel

Estado: aprovado pelo usuário e validado no piloto local. Excel desktop e revisão independente pendentes.

### Permitir estoque negativo

Em **Estoque → Configurações**, MASTER ou DEV pode marcar **Permitir estoque negativo para todos os produtos**. A configuração é única para a empresa, começa desmarcada e fica registrada com ator e horário. A interface identifica quando está ativa e destaca saldos negativos. Operador continua com acesso de consulta.

Quando marcada, saídas manuais, compensações e confirmação de vendas podem deixar saldo abaixo de zero, até o limite de −2 bilhões de unidades. Permanecem as validações de SKU ativo, quantidade, motivo e idempotência, e a exceção existente de reposição ao cancelar venda de SKU inativado.

Ao desmarcar, saldos negativos existentes são preservados. Nenhum movimento que reduza o saldo pode deixá-lo negativo. Entradas e demais reposições podem reduzir a dívida de estoque aos poucos, inclusive quando uma reposição ainda deixa saldo negativo. A mudança de configuração e os movimentos concorrentes devem observar uma ordem consistente de bloqueio.

### Entrada em lote por Excel

Em **Estoque → Importar entradas**, MASTER ou DEV baixa uma tabela `.xlsx` preenchida com os produtos ativos do banco. Colunas de consulta mostram código interno, descrição, código de barras e saldo na exportação. A coluna editável **Quantidade a adicionar** começa em branco. O sistema preserva códigos como texto e oferece exportação em lotes de até 1.000 produtos. O saldo exibido é uma referência e o servidor aplica a entrada sobre o saldo corrente.

Por exemplo, se o saldo está em −3 e a planilha informa uma entrada de 10, o novo saldo é 7. Linhas vazias ou com zero são ignoradas. Números negativos, fracionários, códigos duplicados ou desconhecidos e produtos inativados após a exportação bloqueiam o lote. É obrigatório informar o motivo da entrada, uma vez por lote.

A prévia mostra produtos, saldo atual, quantidade a adicionar e saldo projetado. Na confirmação, revalidar os SKUs e os limites, recalcular sobre os saldos efetivos sob bloqueio e mostrar os saldos gravados. Gravar todas as entradas e sua trilha de auditoria em uma transação. Clique repetido ou reenvio da mesma confirmação retorna o resultado original. Para impedir duplicação acidental, cada arquivo exportado só pode confirmar um lote. Para nova entrada, baixar outro arquivo. Preservar o histórico, o catálogo e o fluxo de importação de produtos.

### Implementação e aceite

1. Usar migração aditiva para a política global e o controle idempotente dos lotes, reaproveitando o histórico e os controles de acesso atuais.
2. Testar opção desligada e ligada, saídas e vendas simultâneas, saldo negativo preexistente após desligamento, reposição parcial, cancelamento e limite inferior.
3. Testar download, prévia e confirmação em PT/ES, bloqueio a operador, CSRF, zeros à esquerda, inativação concorrente, gravação atômica e reenvio da confirmação.
4. Para retorno, preservar tabelas e movimentos. Havendo saldo negativo, validar a capacidade de reposição antes de voltar à versão anterior, que exige saldo final não negativo.
