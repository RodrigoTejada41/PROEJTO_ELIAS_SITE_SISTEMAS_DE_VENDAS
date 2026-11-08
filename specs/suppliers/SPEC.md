# FOR-001 — Fornecedores

Estado: VALIDATED no piloto local Docker em 05/11/2026. Evidências no checkpoint. Revisão independente pendente.

MASTER cadastra, consulta, edita e inativa fornecedores. Operador recebe acesso negado. Nome obrigatório de até 160 caracteres; referência externa, contato, telefone e e-mail opcionais. Referência normalizada e única entre fornecedores, inclusive inativos. O mesmo código pode identificar um cliente e um fornecedor. Nomes iguais são permitidos. Referência externa não representa documento fiscal.

Identidade estável, edição com versão, busca, paginação e inativação lógica seguem o contrato de clientes. Toda mudança registra ator, alvo e horário na mesma transação. Inativação preserva referências futuras de compras e contas a pagar.

Aceite inclui unicidade por tipo, dados opcionais, confirmação visual de inativação, concorrência de edição, CSRF, escrita por MASTER, acesso direto negado ao operador e auditoria. Compras, tributação e pagamento ficam nas respectivas Specs. Migração aditiva e retorno com dados preservados.
