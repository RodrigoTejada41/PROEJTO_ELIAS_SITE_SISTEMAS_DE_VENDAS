# 11. SEGURANÇA E CONTROLE DE ACESSO

Toda operação protegida deverá ser validada no servidor.

Criar matriz de permissões por módulo e ação.

Operações previstas:

- Visualizar.
- Criar.
- Editar.
- Desativar.
- Excluir, quando permitido.
- Aprovar.
- Cancelar.
- Exportar.
- Administrar.

Requisitos obrigatórios de análise:

- Senhas com hash adequado.
- Proteção de sessão.
- Autorização por recurso.
- Proteção contra acesso horizontal indevido.
- Validação de entrada.
- Proteção de dados sensíveis.
- Auditoria de ações críticas.
- Tratamento seguro de exceções.
- Proteção contra requisições indevidas.
- Gestão segura de segredos.
- Backup e recuperação.

As regras de segurança devem ser implementadas conforme a arquitetura efetivamente aprovada.
