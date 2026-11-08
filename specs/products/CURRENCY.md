# CAM-001 — USD, PYG e custos do catálogo

Estado: VALIDATED no piloto local Docker em 05/11/2026. Evidências no checkpoint.

Produtos têm custo e preço base em USD. Exibir também o equivalente em PYG, recalculado pela cotação vigente, mantendo o USD armazenado. USD usa duas casas e PYG unidades inteiras no piloto. Conversão em Decimal com arredondamento HALF_UP explícito para a unidade de destino.

MASTER altera custo e preço com versão do SKU e auditoria. Operadores consultam preços de SKUs ativos e não recebem custos. Cada venda confirmada preserva preços e cotação; atualizações futuras não reescrevem vendas.

A aplicação mantém histórico de taxas USD/PYG, origem, data de referência e consulta. O modo automático é o padrão e consulta a publicação diária oficial do Banco Central do Paraguai a cada hora. Se a consulta falhar ou a referência for inválida, usa a ExchangeRate-API, identificada como fonte alternativa na tela de câmbio. A referência alternativa precisa ter sido publicada nas últimas 48 horas. Na próxima consulta com referência válida do BCP, o sistema volta a usá-la. Se ambas as fontes falharem, o sistema mantém a última cotação e mostra um aviso. O MASTER pode registrar uma taxa manual identificada, que permanece ativa enquanto o modo manual estiver selecionado.

Fonte oficial: https://www.bcp.gov.py/webapps/web/cotizacion/monedas . O servidor Docker lê a linha USD e a data da tabela diária. A data de referência do BCP é armazenada à meia-noite UTC. A fonte alternativa publica diariamente em https://open.er-api.com/v6/latest/USD e fornece o horário de publicação. As taxas anteriores permanecem vinculadas ao histórico.

Financeiro admite títulos em USD e PYG, com moeda preservada por título. Baixas em outra moeda registram o valor efetivamente informado, a taxa escolhida vigente e o equivalente que reduz o saldo do título. Repetição após mudança de cotação retorna o lançamento original. Não somar valores de moedas diferentes como se fossem equivalentes.

Aceite inclui troca de referência, falha de rede, origem/data, custo protegido, arredondamento, precisão por moeda, versão, baixas cruzadas e preservação histórica. Implantação não exige conta paga nem chave de API.
