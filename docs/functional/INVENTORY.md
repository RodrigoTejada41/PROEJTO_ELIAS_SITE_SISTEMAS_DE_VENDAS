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

No piloto, MASTER e DEV podem permitir estoque negativo para todos os produtos em **Estoque → Configurações de estoque**. Ao desligar a opção, novas baixas que deixariam saldo negativo são recusadas. Entradas podem recuperar saldos negativos gradualmente.

Em **Importar entradas**, a planilha exportada traz os SKUs ativos e seus saldos. A coluna **Quantidade a adicionar** gera movimentos de entrada após conferência e confirmação. Um arquivo registra um lote, com motivo, autor e histórico por SKU. As regras estão na [Spec EST-002](../../specs/inventory/SPEC.md).
