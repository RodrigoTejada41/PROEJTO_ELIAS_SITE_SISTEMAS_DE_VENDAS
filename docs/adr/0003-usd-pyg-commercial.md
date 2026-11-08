# 0003 — USD/PYG e transações comerciais do piloto

Data: 05/11/2026. Aprovação funcional pela definição do usuário de dólar, guarani, custo variável com a cotação e comissão percentual ajustável.

Valores monetários são inteiros na menor unidade da moeda. USD usa centavos e PYG inteiro no piloto. Taxas e percentuais usam Decimal/numeric. Rejeitar precisão excedente em entradas e aplicar HALF_UP somente em conversões e apurações expressamente definidas.

Produtos mantêm custo e preço em USD. PYG é equivalente pela taxa comercial escolhida. Confirmação preserva preços, cliente, vendedor, percentual/evento da comissão e cotação. Baixa guarda moeda/valor do pagamento, taxa e equivalente no título. Relatórios de caixa agrupam moedas distintas e usam a data de cada baixa ou estorno.

Alternativa considerada: guardar todos os valores em numeric com escala dinâmica. Inteiros por moeda facilitam provar limites, idempotência e ausência de ponto flutuante nas baixas. Taxas e percentuais continuam em numeric, preservando sua precisão.

A referência aberta integrada é ExchangeRate-API, identificada nas telas. BCP é referência oficial consultada, mas seu endpoint respondeu HTTP 403 ao cliente automatizado. Um worker Compose respeita a próxima publicação da fonte diária, mantém histórico e preserva o último valor em falhas. A política comercial tem escolha explícita entre taxa manual e referência automática. Estado inicial manual sem taxa comercial inventada.

Venda confirma baixa de estoque, título a receber e comissão do evento configurado na mesma transação PostgreSQL. Cancelamento e estornos preservam os registros originais. Pagamento de comissão cria conta a pagar e baixa vinculadas. Reverter apuração já paga pode deixar saldo negativo do vendedor, preservando pagamentos e futuras compensações.

Helpers HTTP existentes foram compartilhados em app/web.py para reutilizar sessão, autorização, CSRF, idioma e renderização entre routers. PostgreSQL, FastAPI, Jinja2 e AdminLTE 3 foram preservados.

Validação por testes PostgreSQL em esquemas descartáveis e fluxo no Edge em banco de homologação separado. Retorno por imagem anterior compatível e dados preservados. Implantação pública e permissões definitivas de banco pertencem à operação da VPS.

## Ajuste aprovado em 05/11/2026

O usuário definiu referência oficial automática e comissão na confirmação. A consulta direta ao BCP foi validada dentro do Docker, com identificação da linha USD e da data na tabela diária. A migração 014 ativa a política automática e limpa os apontadores da fonte anterior. Registros históricos de taxa, venda e baixa são preservados. Novas regras de comissão registradas pela interface usam confirmação. O percentual permanece informado pelo MASTER.
