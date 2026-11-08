# 9. REGRAS FUNCIONAIS DO CONTROL_DE_VENTAS

Criar documentação inicial para cada área abaixo.

As regras ainda não aprovadas deverão aparecer como propostas ou pendências.

## 9.1 Usuário MASTER

Definir:

- Cadastro de administradores.
- Cadastro de operadores.
- Cadastro de vendedores.
- Perfis e permissões.
- Ativação e desativação.
- Revogação de sessões.
- Redefinição segura de credenciais.
- Histórico de acesso.
- Auditoria administrativa.

Definir explicitamente quais ações são exclusivas do MASTER.

Não implementar conta de administração com senha fixa no código.

## 9.2 Cadastro de produtos

Especificar:

- Código interno.
- Código de barras, quando aplicável.
- Descrição.
- Marca.
- Categoria.
- Fornecedor.
- Volume ou peso.
- Variação.
- Custo.
- Preço de venda.
- Estoque.
- Estoque mínimo.
- Lote.
- Validade.
- Status do produto.

Produtos cosméticos podem ter variações de fragrância, cor, tonalidade, apresentação e volume.

Não presumir que todos os produtos exigem controle de lote e validade; definir obrigatoriedade conforme a operação.

## 9.3 Estoque

Documentar:

- Entrada.
- Saída por venda.
- Devolução.
- Ajuste.
- Inventário.
- Perda.
- Avaria.
- Produto vencido.
- Histórico de movimentação.
- Alertas de estoque mínimo.
- Controle opcional por lote.
- Rastreabilidade das operações.

Nenhuma movimentação de estoque poderá ocorrer sem causa registrada.

## 9.4 Vendas

Documentar:

- Criação da venda.
- Seleção de cliente.
- Seleção de vendedor.
- Inclusão de produtos.
- Quantidade.
- Valor unitário.
- Desconto.
- Total.
- Forma e condição de pagamento.
- Status da venda.
- Confirmação.
- Cancelamento.
- Devolução.
- Histórico.

A venda deverá preservar um registro dos preços e condições aplicados no momento da operação, independentemente de alterações futuras no cadastro de produtos.

Definir quando o estoque será reservado ou baixado.

## 9.5 Comissões

Especificar mecanismos configuráveis de comissão:

- Por vendedor.
- Por produto.
- Por categoria.
- Percentual.
- Valor fixo.
- Metas, se aprovadas.
- Período de apuração.
- Aprovação.
- Pagamento.
- Estorno.
- Ajustes autorizados.

Não presumir percentuais.

Não presumir comissão sobre vendas simplesmente cadastradas.

Definir expressamente o evento que gera o direito à comissão.

O sistema deverá impedir pagamento duplicado da mesma comissão.

## 9.6 Financeiro

Documentar:

- Contas a receber.
- Contas a pagar.
- Recebimentos parciais.
- Pagamentos parciais.
- Despesas.
- Receitas.
- Fluxo de caixa.
- Saldos.
- Vencimentos.
- Inadimplência.
- Relatórios.
- Histórico de operações.

Separar claramente:

- Venda registrada.
- Receita reconhecida.
- Valor recebido.
- Comissão apurada.
- Comissão efetivamente paga.

Esses conceitos não são equivalentes.

## 9.7 Relatórios

Especificar:

- Vendas por período.
- Vendas por vendedor.
- Vendas por produto.
- Produtos mais vendidos.
- Estoque disponível.
- Produtos abaixo do mínimo.
- Produtos próximos do vencimento.
- Comissões por vendedor.
- Comissões pendentes.
- Comissões pagas.
- Contas a receber.
- Contas a pagar.
- Fluxo financeiro.
- Histórico de operações.

Cada relatório deverá definir origem dos dados, filtros, regras de cálculo e permissões.

---

# 10. INTERNACIONALIZAÇÃO

Idiomas obrigatórios:

- Português.
- Espanhol.

O idioma deverá ser configurável individualmente por usuário.

Não duplicar telas para cada idioma.

Utilizar o mecanismo de internacionalização compatível com a tecnologia existente.

Centralizar traduções de:

- Menus.
- Botões.
- Formulários.
- Mensagens.
- Erros.
- Status.
- Confirmações.
- Relatórios.
- Notificações.

Não traduzir identificadores internos nem alterar dados comerciais armazenados por causa do idioma selecionado.

Definir formatos de data, hora, números e moeda independentemente da tradução de interface.

---

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
