# CLI-001 — Clientes

Estado: VALIDATED no piloto local Docker em 05/11/2026. Evidências no checkpoint. Revisão independente pendente.

MASTER cadastra, consulta, edita e inativa clientes. Operador consulta clientes ativos. Nome obrigatório de até 160 caracteres, referência externa opcional de até 64 caracteres, contato, telefone e e-mail opcionais. A referência externa é normalizada para maiúsculas e única entre clientes, inclusive inativos. Nomes iguais são permitidos. A referência não representa documento fiscal.

Cadastro preserva ID. Edição usa versão para recusar sobrescrita concorrente. Inativação lógica idempotente preserva histórico e impede seleção em operações novas. Cadastro, edição e inativação têm auditoria atômica de ator, alvo e horário.

Busca por nome ou referência e paginação de 50 registros. Escrita exclusiva do MASTER com POST e CSRF. Operador não acessa inativos nem escrita direta. A interface oferece português e espanhol no layout da marca.

Aceite inclui cadastro, duplicidade de referência, edição desatualizada, inativação repetida, autorização, CSRF, preservação de referências e rollback da auditoria. Integração fiscal, documentos nacionais e retenção legal dependem de definição própria. O piloto usa dados fictícios. Migração aditiva e retorno com tabelas preservadas.
