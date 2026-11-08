# users

Estado do IDN-001: VALIDATED no piloto local Docker em 05/11/2026. Aprovação de identidade em 04/11/2026 e continuidade em 05/11/2026.

[Regras funcionais](../../docs/functional/USERS.md)

## Aceite do piloto

Desativar operador revoga suas sessões. Operador recebe acesso negado ao tentar administrar privilégios via requisição direta.

## Decisões adotadas

Uma empresa, bootstrap e recuperação por terminal administrativo, perfis MASTER e OPERATOR. Matriz vigente em [ACE-001](../access-control/SPEC.md).

## IDN-001 — Piloto local

Piloto para uma empresa, Esther Beauty 777. A instalação inicial cria uma conta MASTER por comando administrativo local com senha solicitada sem eco. Nenhuma senha padrão. O bootstrap só funciona enquanto não houver MASTER, com integridade garantida também sob concorrência. Recuperação local auditável exige acesso administrativo autorizado e revoga todas as sessões da conta.

Login com identificador e senha, hash Argon2id, resposta genérica para falha e limitação de tentativas. Sessão opaca revogável no servidor, com cookie HttpOnly, SameSite e Secure em HTTPS. Login renova a sessão. Logout e ações administrativas usam POST com proteção CSRF. Eventos críticos registram ator, ação, alvo, resultado e horário sem credenciais.

## Aceite de IDN-001

- Duas tentativas concorrentes de bootstrap resultam em uma única conta MASTER.
- Usuário inexistente e senha incorreta exibem a mesma mensagem. Tentativas repetidas são limitadas.
- Sessão expirada, desativada ou encerrada deixa de acessar o painel mesmo quando reapresentada.
- Rotas protegidas recusam acesso direto sem sessão válida e formulários administrativos recusam token CSRF inválido.
- O MASTER cria e desativa operadores. Operador não altera perfis e o único MASTER não pode ser desativado pelo painel.
- Login, logout e gestão de usuários funcionam em português e espanhol. O registro de auditoria permite rastrear as ações.

## Sequência de entrega

Continuação autorizada em 04/11/2026. Premissa de implementação local: uma instalação para Esther Beauty 777. O primeiro incremento cobre somente migração PostgreSQL, criação local do MASTER e registro do evento. Login, recuperação e gestão de operadores serão entregues em incrementos próprios.

## Recuperação local do MASTER

Autorizada em 04/11/2026. Operador autorizado do ambiente executa o comando local com um papel PostgreSQL administrativo e digita a nova senha duas vezes em terminal sem eco. O comando atua sobre a conta MASTER existente, preserva seu estado ativo e recusa a operação se a conta não existir. A troca por hash Argon2id, a remoção de todas as sessões da conta e o evento de sucesso com papel PostgreSQL e horário são atômicos. Um login simultâneo com a senha antiga não pode deixar uma sessão válida após a recuperação.

## Validação atual

Bootstrap concorrente, login, sessão, operadores e recuperação no PostgreSQL Docker. Recuperação também executada em terminal real sem eco em banco separado. Evidências no checkpoint. Revisão independente pendente.

## IDN-002 — Perfil DEV para manutenção

Estado: aprovado pelo usuário e validado no piloto local em 07/11/2026. Revisão independente pendente.

O DEV é uma conta separada, com acesso aos recursos disponíveis ao MASTER e a uma área exclusiva de manutenção. O primeiro recurso exclusivo proposto é redefinir a senha do MASTER com reautenticação do DEV, revogação das sessões do MASTER e registro de auditoria. Melhorias futuras podem incluir recursos nessa área mediante escopo próprio. O perfil opera dentro da aplicação. Alterações de código, banco e implantação continuam pelos processos administrativos do projeto.

Provisionar um único DEV por comando local autorizado, com senha informada sem eco e hash Argon2id. MASTER e operadores não podem criar, editar, desativar ou assumir o perfil DEV. Aplicar autorização no servidor e proteção CSRF nas escritas. O histórico deve identificar a conta e o papel reais do autor.

### Implementação e aceite

1. Ampliar a restrição de papéis em migração aditiva e garantir unicidade do DEV, preservando contas e a unicidade do MASTER.
2. Centralizar a hierarquia DEV → MASTER → OPERATOR nos controles pertinentes e revisar também os filtros de consultas, navegação e auditoria que verificam papéis diretamente.
3. Validar provisionamento concorrente, acesso do DEV aos módulos do MASTER, bloqueio por acesso direto aos recursos exclusivos, tentativa de elevação, reautenticação, revogação e trilha de auditoria. Verificar regressão das contas existentes e telas em PT/ES.
4. Planejar retorno à versão anterior com revogação das sessões DEV e bloqueio da conta DEV antes de reabrir o acesso. Preservar a conta e seus registros de auditoria.
