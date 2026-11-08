# COM-001 — Comissão percentual por vendedor

Estado: VALIDATED no piloto. Em 05/11/2026, o usuário definiu a confirmação da venda como evento das novas regras.

MASTER define percentual de 0 a 100 por vendedor, com até quatro casas decimais. Novas regras apuram comissão na confirmação da venda, sobre o total líquido em USD. Zero por cento é uma escolha explícita. Vendas anteriores preservam o evento e o percentual registrados.

Cada alteração cria nova versão da regra. A confirmação de venda exige regra explícita para o vendedor e preserva seu percentual e evento. Alterações posteriores afetam novas vendas, mantendo a apuração das anteriores. As apurações usam HALF_UP para centavos de USD. As regras históricas de recebimento continuam vinculadas às vendas que as utilizaram.

Apuração e pagamento são registros diferentes. A confirmação ou baixa financeira gera a apuração na mesma transação do evento. Estorno do recebimento ou cancelamento da venda reverte a apuração correspondente com histórico. Se a comissão já foi paga, a reversão pode deixar saldo negativo do vendedor; não apagar pagamentos nem pagar novamente a mesma apuração.

MASTER registra pagamento de comissão, limitado ao saldo disponível, com chave de idempotência. O pagamento cria título a pagar e baixa financeira na mesma transação. Estorno dessa baixa devolve o valor ao saldo da comissão. Repetição de pagamento preserva um único efeito, inclusive sob concorrência.

Comissões são apuradas em USD. Pagamento admite USD ou PYG com preservação da taxa e do valor efetivo. Operador não consulta custos, regra de outros vendedores nem administração de comissões neste piloto.

Aceite inclui percentual variável, versão, evento explícito, recebimento parcial, snapshot, duplicidade, saldo, reversão antes e depois do pagamento, concorrência e vínculo financeiro. Metas, regras por produto/categoria e aprovação multinível dependem de recortes próprios.
