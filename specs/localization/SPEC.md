# LOC-001 — Português e espanhol

Estado: VALIDATED no piloto local Docker em 05/11/2026. Evidências no checkpoint. Revisão independente pendente.

Interface, formulários e erros controlados em português e espanhol. Login permite selecionar idioma no navegador. Após autenticação, a seleção pela interface grava a preferência da conta com POST e CSRF e mantém cookie de apresentação. Login em navegador sem cookie reaplica a preferência armazenada. Links legados de idioma continuam atualizando a apresentação local.

Moeda é independente do idioma: USD com duas casas e PYG inteiro conforme CAM-001. Formulários monetários aceitam ponto ou vírgula decimal sem milhar e rejeitam precisão excedente. Datas operacionais têm dia/mês/ano e eventos de auditoria indicam UTC/offset explicitamente. Troca de idioma não modifica valores financeiros.

Aceite inclui persistência após recarga e novo login, igualdade de mensagens de credencial inválida, recusa de CSRF, fallback português, navegação por teclado e erros 403/404/422 localizados. Variantes regionais adicionais dependem de recorte próprio.
