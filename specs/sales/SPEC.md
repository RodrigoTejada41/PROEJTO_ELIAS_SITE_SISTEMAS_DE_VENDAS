# VEN-001 — Venda administrativa do piloto

Estado: VALIDATED no piloto local Docker em 05/11/2026. Evidências no checkpoint. Revisão independente pendente.

MASTER cria rascunho, define cliente opcional ativo, vendedor ativo, vencimento e desconto em valor. Adiciona vários SKUs ativos com quantidades inteiras e preços unitários explícitos na moeda configurada. Edição exige a versão atual do rascunho. Operadores recebem acesso negado ao módulo de vendas neste recorte, mantendo suas consultas de catálogo, clientes e estoque.

Rascunho não movimenta estoque nem cria título. Confirmação exige itens, total líquido positivo e estoque disponível para todos os SKUs. Preços, descrições, códigos, cliente, vendedor, moeda e condições ficam preservados. A confirmação baixa estoque e cria uma conta a receber pelo total líquido, em uma transação PostgreSQL. A venda registrada e o recebimento permanecem eventos distintos.

Confirmar novamente uma venda confirmada retorna seu estado sem repetir estoque ou financeiro. Concorrência entre vendas não gera saldo negativo. Movimentos de venda são protegidos contra compensação manual: o cancelamento da venda coordena suas reversões.

Cancelamento de rascunho preserva seu histórico. Cancelamento de venda confirmada é permitido somente sem recebimento líquido pendente de estorno. Repõe as quantidades originais, inclusive se o SKU foi inativado depois da venda, cancela o título e registra auditoria em uma transação. Repetição não duplica efeitos. A interface pede confirmação antes de confirmar ou cancelar.

Moeda e precisão vêm da configuração obrigatória. Quantidade e valores obedecem aos limites do estoque e financeiro. Desconto é explícito, sem percentual presumido; o total é soma dos itens menos desconto. Não há arredondamento implícito. Comissão depende de regra comercial configurada ou aprovada em sua Spec e não é criada por cadastro de rascunho.

Aceite inclui múltiplos itens, snapshots, versão, saldo insuficiente, confirmação concorrente e repetida, recebimento separado, restrição de cancelamento, reversões atômicas, SKU inativo, autorização e CSRF. Parcelamento, devolução parcial, fiscal e PDV dependem de recortes próprios.

## VEN-002 — Dados da empresa e recibo simples de venda

Estado: aprovado pelo usuário e validado no piloto local em 07/11/2026. O usuário confirmou o escopo de recibo simples sem emissão fiscal. Revisão independente pendente.

O piloto tem uma empresa. Em **Dados da empresa**, no menu administrativo, MASTER e DEV editam o nome que sai no recibo, nome comercial, identificação empresarial (RUC no Paraguai), endereço e telefone. O nome é obrigatório. A edição usa a sessão e a proteção CSRF existentes e registra a alteração em auditoria.

Na venda confirmada, MASTER e DEV usam **Imprimir recibo** para abrir uma página em português ou espanhol, conforme o idioma da conta. O navegador permite imprimir ou salvar em PDF. O recibo mostra identificação da empresa, número e data da venda, cliente quando informado, itens, quantidades, preços, desconto, total e moeda. Exibe a indicação **Recibo de venda sem valor fiscal**. O recibo registra a venda. A confirmação da venda e a quitação financeira continuam sendo eventos distintos.

Cada venda confirmada pode ter um único registro de emissão, vinculado ao ID existente. A primeira emissão guarda uma cópia dos dados da empresa. Reimpressões reutilizam esse registro e os valores preservados na venda. Isso permite emitir para vendas confirmadas antes da migração e mantém a identificação original após futuras edições da ficha. Sem o nome da empresa, a tela orienta a preencher a ficha. Rascunhos e vendas canceladas ficam sem opção de emissão. A emissão usa POST com CSRF e unicidade no PostgreSQL para tratar cliques repetidos ou simultâneos.

### Implementação e aceite

1. Criar migração aditiva para a ficha e o registro de emissão. Em caso de retorno, executar a versão anterior da aplicação e manter os dados das novas tabelas.
2. Implementar a ficha no padrão AdminLTE 3 e o recibo imprimível na tela de detalhes da venda, reutilizando os dados preservados na confirmação e os controles de acesso existentes.
3. Validar acesso direto, CSRF, persistência, emissão concorrente, reimpressão após edição da ficha, venda anterior à migração, bloqueio de rascunho e cancelada, totais em USD/PYG e impressão em português e espanhol.

## VEN-003 — Venda em tela única e recibo tabular

Estado: aprovado pelo usuário, implementado e validado no piloto local. Impressora física e revisão independente pendentes.

MASTER e DEV montam a venda na tela **Nova venda**, com cliente opcional selecionado pelo nome, vendedor, vencimento e desconto. Uma busca de produtos ativos por descrição, código interno ou código de barras apresenta foto quando cadastrada, saldo disponível e preço do catálogo em USD e equivalente em PYG. A busca retorna um conjunto limitado de resultados e o servidor valida a seleção. Para produtos sem preço cadastrado, a tela solicita preço unitário.

A lista de itens fica visível enquanto o usuário adiciona produtos, altera quantidades ou preços e remove linhas. Adicionar o mesmo SKU soma a quantidade mantendo um único item. A tela permite até 200 SKUs distintos por envio, recalcula subtotal, desconto e total e identifica o equivalente PYG como estimativa até a confirmação. O servidor valida os valores e fixa a cotação comercial na confirmação conforme VEN-001. O usuário pode salvar e retomar o rascunho ou confirmar a venda. Em caso de erro, preservam-se os dados editados e a interface informa a ação necessária, como conferir saldo, selecionar vendedor ativo ou configurar cotação ou comissão. A confirmação mantém a transação de estoque, financeiro, comissão e auditoria do fluxo atual.

Depois da confirmação, a opção **Imprimir recibo** abre o diálogo do navegador, que permite selecionar impressora local ou salvar em PDF. Se a ficha da empresa estiver incompleta, a venda confirmada é preservada e o sistema indica como completar a ficha e voltar para emitir.

O recibo toma como referência apenas a disposição visual do PDF enviado. O cabeçalho fica dividido entre dados da empresa e identificação do recibo. Abaixo vêm data e cliente, grade com quantidade, descrição, preço unitário e valor da linha, e bloco de subtotal, desconto e total destacado. Usar dados do sistema e manter a indicação **Recibo de venda sem valor fiscal**. A referência serve somente para a organização visual. O recibo não incorpora logotipo, dados de terceiros, timbrado ou colunas fiscais do PDF. Reimpressões preservam os dados originais da emissão.

O cabeçalho exibe o logotipo próprio da Esther Beauty 777 ao lado do nome da empresa preservado na emissão. A tabela, os dados da venda e os totais usam bordas e espaçamentos consistentes na tela e em A4.

### Implementação e aceite

1. Reutilizar rascunho, versão, idempotência, permissões, snapshots e regras de confirmação existentes. Evitar migração se os contratos atuais comportarem o fluxo.
2. Validar pesquisa, foto e ausência de foto, inclusão repetida, alteração, remoção, recuperação de rascunho e confirmação. Testar concorrência, estoque insuficiente e outros bloqueios, com mensagens específicas e preservação dos dados.
3. Verificar PT/ES, teclado, celular e desktop. Validar impressão em PDF A4 com uma e várias páginas, repetição de cabeçalho da tabela e valores legíveis. Impressora física depende de dispositivo disponível.
