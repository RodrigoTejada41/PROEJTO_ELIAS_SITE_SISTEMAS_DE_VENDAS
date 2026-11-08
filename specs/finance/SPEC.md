# FIN-001 — Títulos e baixas parciais

Estado: VALIDATED no piloto local Docker em 05/11/2026. Evidências no checkpoint. Revisão independente pendente.

Conforme a definição do usuário em 05/11/2026, o piloto usa USD com duas casas decimais e PYG inteiro. Cada título preserva sua moeda. O padrão inicial de apresentação monetária é USD; o padrão fica protegido após o primeiro título ou rascunho de venda.

MASTER cria contas a receber e a pagar com descrição, valor positivo, vencimento e vínculo opcional ao cliente ou fornecedor ativo correspondente. O valor e os dados de origem ficam preservados. Correção usa cancelamento e novo título. Cancelamento só é permitido com saldo líquido recebido/pago igual a zero.

Baixa parcial inclui valor, moeda efetivamente recebida ou paga e meio de pagamento explícito. Pagamento em outra moeda usa a taxa vigente e preserva valor original, equivalente e taxa conforme [CAM-001](../products/CURRENCY.md). Recebimentos e pagamentos não ultrapassam o saldo em aberto. Cada submissão usa chave de idempotência e bloqueio do título para serializar concorrência. Repetição igual retorna o lançamento original; conteúdo diferente na mesma chave informa conflito.

Estorno preserva a baixa original e registra motivo, ator e horário, tornando seu valor disponível no saldo. Estorno único por baixa, idempotente. Criação, baixa, estorno e cancelamento têm auditoria atômica. Operador recebe 403 em todo o módulo financeiro.

Cálculos em unidades monetárias inteiras, sem ponto flutuante. Valores com mais casas que a configuração são rejeitados sem arredondamento implícito. Limite do piloto: 999.999.999.999 unidades monetárias mínimas por título. Formulários aceitam vírgula ou ponto decimal, sem separador de milhar.

Consulta paginada com títulos em aberto, quitados ou cancelados, saldos e identificação dos vencidos pela data UTC. O histórico distingue valor do título, baixas e estornos. Datas e moeda da operação são preservadas.

Aceite inclui obrigatoriedade da configuração, precisão decimal, baixas parciais, recebimentos concorrentes, repetição, estorno, cancelamento com restrição, CSRF, autorização e rollback. Parcelamento, encargos, conciliação bancária, reconhecimento contábil e integrações de pagamento dependem de contratos próprios. Venda e comissão utilizam vínculos específicos em seus recortes.
