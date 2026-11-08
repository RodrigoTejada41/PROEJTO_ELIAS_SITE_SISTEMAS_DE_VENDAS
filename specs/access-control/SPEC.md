# ACE-001 — Acesso do piloto

Estado: VALIDATED no piloto local em 05/11/2026. Matriz aprovada pela continuidade de 05/11/2026.

Uma empresa, Esther Beauty 777. Cada requisição verifica sessão válida e conta ativa. Desativação de operador revoga suas sessões. O único MASTER não pode ser desativado pela gestão de operadores.

| Recurso | MASTER | Operador |
| --- | --- | --- |
| Painel | Consulta | Consulta |
| Catálogo e preços de SKUs ativos | Consulta e gestão | Consulta sem custos |
| SKUs inativos e custos | Consulta e gestão | Negado |
| Estoque | Consulta e movimentação | Consulta de ativos |
| Clientes | Gestão | Consulta de ativos |
| Fornecedores | Gestão | Negado |
| Vendas e financeiro | Gestão | Negado |
| Câmbio comercial e comissões | Gestão | Negado |
| Relatório de estoque | Consulta e CSV | Ativos e CSV |
| Relatórios monetários e auditoria | Consulta | Negado |
| Idioma da própria conta | Alteração com CSRF | Alteração com CSRF |
| Operadores | Cadastro e desativação | Negado |

A interface aplica a mesma matriz na navegação. A autorização ocorre novamente no servidor em acesso direto. Escritas administrativas são POST com CSRF. Perfis delegados e múltiplas empresas dependem de um recorte próprio.

## Extensões aprovadas em 07/11/2026

- O DEV herda os acessos do MASTER e pode acessar a manutenção exclusiva do [IDN-002](../users/SPEC.md).
- DEV e MASTER podem editar os dados da empresa e emitir recibo para vendas confirmadas no [VEN-002](../sales/SPEC.md). O operador recebe acesso negado.

## ACE-002 — Verificação em duas etapas

Implementação autorizada em 08/11/2026. Em produção, DEV, MASTER e operadores precisam de senha e código TOTP de aplicativo autenticador. Contas existentes mantêm seus dados e devem ser cadastradas por terminal autorizado antes do primeiro acesso. O piloto aceita contas sem cadastro para preservar o ambiente de demonstração. Contas cadastradas exigem o segundo fator também no piloto.

Validar a senha antes de criar um desafio sem acesso a recursos. O desafio vence em cinco minutos e permite cinco tentativas por conta, mesmo com novo desafio ou IP. A confirmação consome o desafio e impede reutilização do mesmo código. Cadastro e substituição exigem confirmação de um código do novo autenticador, revogam sessões e registram auditoria. A troca de senha preserva o fator e invalida desafios anteriores.

Guardar o segredo TOTP cifrado com chave externa exclusiva da aplicação. A migração é aditiva. Preserve a imagem anterior, o backup e a chave protegida para recuperação. Após ativar o segundo fator em produção, qualquer retorno exige versão que mantenha a exigência. O aceite cobre expiração, repetição, bloqueio, sessão anterior, recuperação por terminal e interface PT/ES.

### Cadastro no primeiro acesso

Extensão autorizada para configurar Google Authenticator pelo navegador. O responsável emite um código de ativação em terminal privado para conta ainda sem fator e entrega por canal separado da senha. O código expira em 24 horas. Após validar a senha e o código de ativação, o desafio mostra um QR Code gerado na aplicação e uma chave manual para quem usa o mesmo dispositivo. O primeiro TOTP confirma o cadastro, consome o código de ativação e abre a sessão na mesma transação. Um desafio novo exige novamente o código de ativação e gera outro QR Code. Contas com autenticador continuam com o fluxo normal e recuperação assistida.
