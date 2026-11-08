# AUD-001 — Consulta administrativa

Estado: VALIDATED no piloto local Docker em 05/11/2026. Evidências no checkpoint. Revisão independente pendente.

MASTER consulta eventos de identidade, catálogo, estoque, clientes/fornecedores, financeiro, câmbio, vendas e comissões. Operador e visitante não acessam o histórico administrativo. Exibir ator, ação, tipo de entidade, identificador do alvo e horário. Nunca retornar senhas, hashes de credencial, tokens ou conteúdo dos secrets.

Filtros por origem e período inclusivo de datas em UTC. Paginação de 50 eventos, ordenação determinística por horário e origem/ID. O livro de estoque é a fonte de seus eventos. Os eventos dos outros módulos derivam das tabelas de auditoria já gravadas na mesma transação das operações.

Aceite inclui eventos após cadastro e inativação, filtros de datas/origem, autorização direta e ausência dos campos sensíveis nas respostas. Retenção continua preservada durante o piloto, com remoção condicionada à futura política aprovada. A consulta não concede permissão de alterar eventos.
