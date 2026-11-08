from pathlib import Path
from secrets import compare_digest
from urllib.parse import parse_qs

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import identity
from app.finance import format_amount
from app.fx import convert_minor

APP = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=APP / "templates")
NO_STORE = {"Cache-Control": "private, no-store"}
SESSION_COOKIE = "identity_session"
LOGIN_CSRF_COOKIE = "login_csrf"
TEXT = {
    "pt": {
        "dashboard": "Painel administrativo",
        "menu": "Alternar menu",
        "language": "Idioma",
        "notice": "Ambiente de homologação com dados fictícios",
        "sales": "Vendas de exemplo",
        "products": "Produtos de exemplo",
        "skip": "Ir para o conteúdo",
        "login": "Entrar",
        "operators": "Operadores",
        "create_operator": "Cadastrar operador",
        "deactivate": "Desativar",
        "active": "Ativo",
        "inactive": "Inativo",
        "no_operators": "Nenhum operador cadastrado.",
        "operator_invalid": "Use um usuário válido de 3 a 64 caracteres e uma senha de 15 a 128 caracteres.",
        "operator_duplicate": "Esse nome de usuário já existe.",
        "catalog": "Catálogo",
        "code": "Código interno",
        "description": "Descrição",
        "brand": "Marca",
        "category": "Categoria",
        "variation": "Variação",
        "barcode": "Código de barras",
        "search": "Buscar por código ou descrição",
        "create_sku": "Cadastrar SKU",
        "edit_sku": "Editar",
        "save_sku": "Salvar",
        "back_catalog": "Voltar ao catálogo",
        "no_skus": "Nenhum SKU encontrado.",
        "sku_invalid": "Confira os campos e os formatos informados.",
        "sku_duplicate": "O código interno ou o código de barras já está em uso.",
        "sku_stale": "O SKU mudou desde que você abriu o formulário. Reabra a edição antes de salvar.",
        "stock": "Estoque",
        "balance": "Saldo",
        "history": "Histórico",
        "quantity": "Quantidade",
        "reason": "Motivo",
        "movement": "Registrar movimento",
        "entry": "Entrada",
        "exit": "Saída",
        "compensate": "Compensar",
        "stock_invalid": "Informe quantidade inteira de 1 a 1 bilhão e motivo de 3 a 240 caracteres.",
        "stock_conflict": "Movimento recusado. Confira saldo, estado do SKU ou repetição da solicitação.",
        "no_movements": "Nenhuma movimentação registrada.",
        "previous_page": "Anterior",
        "next_page": "Próxima",
        "logout": "Sair",
        "username": "Usuário",
        "password": "Senha",
        "invalid": "Usuário ou senha inválidos.",
        "limited": "Muitas tentativas. Aguarde alguns minutos.",
        "mfa_code": "Código de seis dígitos do aplicativo autenticador",
        "mfa_verify": "Verificar código",
        "mfa_back": "Voltar para o login",
        "mfa_invalid": "Código inválido ou já utilizado.",
        "mfa_expired": "A verificação expirou. Entre novamente.",
        "mfa_enrollment": "Solicite ao responsável um código de ativação do autenticador.",
        "mfa_activation": "Código de ativação",
        "mfa_activation_help": "Use o código de ativação entregue pelo responsável para cadastrar seu autenticador.",
        "mfa_activation_invalid": "Código de ativação inválido.",
        "mfa_activation_issued": "Código de ativação do autenticador emitido",
        "mfa_scan": "No Google Authenticator, toque em + e escaneie o QR Code. Depois, informe o código de seis dígitos.",
        "mfa_qr": "QR Code para configurar o autenticador",
        "mfa_manual": "Mostrar chave para configuração manual",
        "mfa_unavailable": "Verificação indisponível. Entre em contato com o responsável.",
        "mfa_enrolled": "Autenticador cadastrado",
        "mfa_replaced": "Autenticador substituído",
    },
    "es": {
        "dashboard": "Panel administrativo",
        "menu": "Alternar menú",
        "language": "Idioma",
        "notice": "Entorno de pruebas con datos ficticios",
        "sales": "Ventas de ejemplo",
        "products": "Productos de ejemplo",
        "skip": "Ir al contenido",
        "login": "Entrar",
        "operators": "Operadores",
        "create_operator": "Crear operador",
        "deactivate": "Desactivar",
        "active": "Activo",
        "inactive": "Inactivo",
        "no_operators": "No hay operadores registrados.",
        "operator_invalid": "Usa un usuario válido de 3 a 64 caracteres y una contraseña de 15 a 128 caracteres.",
        "operator_duplicate": "Ese nombre de usuario ya existe.",
        "catalog": "Catálogo",
        "code": "Código interno",
        "description": "Descripción",
        "brand": "Marca",
        "category": "Categoría",
        "variation": "Variante",
        "barcode": "Código de barras",
        "search": "Buscar por código o descripción",
        "create_sku": "Crear SKU",
        "edit_sku": "Editar",
        "save_sku": "Guardar",
        "back_catalog": "Volver al catálogo",
        "no_skus": "No se encontraron SKU.",
        "sku_invalid": "Revisa los campos y sus formatos.",
        "sku_duplicate": "El código interno o el código de barras ya está en uso.",
        "sku_stale": "El SKU cambió desde que abriste el formulario. Vuelve a abrirlo antes de guardar.",
        "stock": "Inventario",
        "balance": "Saldo",
        "history": "Historial",
        "quantity": "Cantidad",
        "reason": "Motivo",
        "movement": "Registrar movimiento",
        "entry": "Entrada",
        "exit": "Salida",
        "compensate": "Compensar",
        "stock_invalid": "Indica una cantidad entera de 1 a mil millones y un motivo de 3 a 240 caracteres.",
        "stock_conflict": "Movimiento rechazado. Revisa saldo, estado del SKU o repetición de la solicitud.",
        "no_movements": "No hay movimientos registrados.",
        "previous_page": "Anterior",
        "next_page": "Siguiente",
        "logout": "Cerrar sesión",
        "username": "Usuario",
        "password": "Contraseña",
        "invalid": "Usuario o contraseña no válidos.",
        "limited": "Demasiados intentos. Espera unos minutos.",
        "mfa_code": "Código de seis dígitos de la aplicación autenticadora",
        "mfa_verify": "Verificar código",
        "mfa_back": "Volver al inicio de sesión",
        "mfa_invalid": "Código no válido o ya utilizado.",
        "mfa_expired": "La verificación caducó. Vuelve a iniciar sesión.",
        "mfa_enrollment": "Solicita al responsable un código de activación del autenticador.",
        "mfa_activation": "Código de activación",
        "mfa_activation_help": "Usa el código de activación que te entregó el responsable para configurar tu autenticador.",
        "mfa_activation_invalid": "Código de activación no válido.",
        "mfa_activation_issued": "Código de activación del autenticador emitido",
        "mfa_scan": "En Google Authenticator, toca + y escanea el código QR. Luego, ingresa el código de seis dígitos.",
        "mfa_qr": "Código QR para configurar el autenticador",
        "mfa_manual": "Mostrar clave de configuración manual",
        "mfa_unavailable": "Verificación no disponible. Comunícate con el responsable.",
        "mfa_enrolled": "Autenticador registrado",
        "mfa_replaced": "Autenticador sustituido",
    },
}


def redirect(path):
    return RedirectResponse(path, status_code=303, headers=NO_STORE)


def set_cookie(response, request, name, value, max_age):
    response.set_cookie(
        name, value, max_age=max_age, httponly=True, samesite="lax",
        secure=request.url.scheme == "https",
    )


def change_language(request, path, lang):
    response = redirect(path)
    set_cookie(response, request, "locale", lang if lang in TEXT else "pt", 365 * 24 * 60 * 60)
    return response


def render(request, template, status=200, **context):
    locale = request.cookies.get("locale", "pt")
    if locale not in TEXT:
        locale = "pt"
    return templates.TemplateResponse(
        request, template, {"locale": locale, "t": TEXT[locale], "money": format_amount, "convert": convert_minor, **context},
        status_code=status, headers=NO_STORE,
    )


async def read_form(request: Request):
    return await parse_form(request, 4096, 3)


async def read_catalog_form(request: Request):
    return await parse_form(request, 8192, 7)


async def parse_form(request, max_bytes, max_fields):
    if request.headers.get("content-type", "").split(";")[0] != "application/x-www-form-urlencoded":
        raise HTTPException(415)
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > max_bytes:
            raise HTTPException(413)
        body.extend(chunk)
    try:
        fields = parse_qs(body.decode("ascii"), keep_blank_values=True, max_num_fields=max_fields)
    except ValueError as error:
        raise HTTPException(400) from error
    if any(len(values) != 1 for values in fields.values()):
        raise HTTPException(400)
    return {key: values[0] for key, values in fields.items()}


def check_csrf(form, expected):
    supplied = form.get("csrf", "")
    if not expected or not compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(403)


def session_csrf(token):
    return identity.digest("csrf:" + token).hex()


def active_session(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    account = identity.session_account(token) if token else None
    if account is None:
        raise HTTPException(303, headers={**NO_STORE, "Location": "/login"})
    request.state.role = account[1]
    return account[0], account[1], session_csrf(token)


def is_admin_role(role):
    return role in ("MASTER", "DEV")


def dev_session(account=Depends(active_session)):
    if account[1] != "DEV":
        raise HTTPException(403, headers=NO_STORE)
    return account[0], account[2]


def master_session(account=Depends(active_session)):
    if not is_admin_role(account[1]):
        raise HTTPException(403, headers=NO_STORE)
    return account[0], account[2]



TEXT["pt"].update({
    "customers": "Clientes", "suppliers": "Fornecedores", "name": "Nome",
    "external_ref": "Referência externa", "contact": "Contato", "phone": "Telefone", "email": "E-mail",
    "new_contact": "Cadastrar", "search_contact": "Buscar por nome ou referência",
    "no_contacts": "Nenhum cadastro encontrado.", "confirm_deactivate": "Confirmar desativação",
    "contact_invalid": "Confira nome, limites dos campos, referência e formato do e-mail.",
    "contact_duplicate": "A referência externa já existe nesse cadastro.",
    "back": "Voltar", "reports": "Relatórios", "audit": "Auditoria",
})
TEXT["es"].update({
    "customers": "Clientes", "suppliers": "Proveedores", "name": "Nombre",
    "external_ref": "Referencia externa", "contact": "Contacto", "phone": "Teléfono", "email": "Correo electrónico",
    "new_contact": "Crear", "search_contact": "Buscar por nombre o referencia",
    "no_contacts": "No hay registros.", "confirm_deactivate": "Confirmar desactivación",
    "contact_invalid": "Revisa nombre, límites de los campos, referencia y formato del correo.",
    "contact_duplicate": "La referencia externa ya existe en este registro.",
    "back": "Volver", "reports": "Informes", "audit": "Auditoría",
})

TEXT["pt"].update({
    "status": "Estado", "all": "Todos", "export_csv": "Exportar CSV",
    "stock_units": "Unidades em estoque", "filtered_skus": "SKUs encontrados",
    "export_limit": "A exportação admite até 10 mil SKUs. Refine a busca.",
    "source": "Origem", "actor": "Responsável", "action": "Ação", "entity": "Entidade",
    "start_date": "Data inicial (UTC)", "end_date": "Data final (UTC)",
    "invalid_period": "Informe um período de datas válido.", "filter": "Filtrar",
    "no_events": "Nenhum evento encontrado.", "target": "Identificador", "when": "Horário",
    "identity": "Identidade", "inventory": "Estoque", "contacts": "Clientes e fornecedores",
    "created": "Cadastro", "edited": "Edição", "deactivated": "Desativação",
    "compensation": "Compensação", "login_event": "Entrada na conta", "logout_event": "Saída da conta",
})
TEXT["es"].update({
    "status": "Estado", "all": "Todos", "export_csv": "Exportar CSV",
    "stock_units": "Unidades en inventario", "filtered_skus": "SKU encontrados",
    "export_limit": "La exportación admite hasta 10 mil SKU. Refina la búsqueda.",
    "source": "Origen", "actor": "Responsable", "action": "Acción", "entity": "Entidad",
    "start_date": "Fecha inicial (UTC)", "end_date": "Fecha final (UTC)",
    "invalid_period": "Indica un período de fechas válido.", "filter": "Filtrar",
    "no_events": "No hay eventos.", "target": "Identificador", "when": "Fecha y hora",
    "identity": "Identidad", "inventory": "Inventario", "contacts": "Clientes y proveedores",
    "created": "Creación", "edited": "Edición", "deactivated": "Desactivación",
    "compensation": "Compensación", "login_event": "Acceso a la cuenta", "logout_event": "Salida de la cuenta",
})

TEXT["pt"].update({
    "finance": "Financeiro", "currency": "Moeda (código de 3 letras)", "scale": "Casas decimais",
    "finance_settings": "Configurar moeda", "currency_required": "Configure a moeda antes do primeiro lançamento.",
    "currency_locked": "A moeda fica protegida após o primeiro título.",
    "finance_invalid": "Confira os dados, o valor e as casas decimais. Use ponto ou vírgula decimal, sem separador de milhar.",
    "finance_conflict": "Operação recusada. Confira saldo, estado do título, moeda e repetição da solicitação.",
    "receivable": "Contas a receber", "payable": "Contas a pagar", "new_title": "Novo título",
    "amount": "Valor", "due_date": "Vencimento", "remaining": "Em aberto", "paid": "Quitado",
    "settled_amount": "Valor recebido ou pago", "open": "Em aberto", "canceled": "Cancelado",
    "overdue": "Vencido", "settle": "Registrar baixa", "cancel": "Cancelar",
    "reverse": "Estornar", "method": "Meio de pagamento", "cash": "Dinheiro",
    "transfer": "Transferência", "card": "Cartão", "other": "Outro", "party": "Cliente ou fornecedor (ID opcional)",
    "no_titles": "Nenhum título encontrado.", "no_settlements": "Nenhuma baixa registrada.",
    "reversed": "Estornado", "configured": "Configuração", "settled": "Baixa", "title": "Título",
})
TEXT["es"].update({
    "finance": "Finanzas", "currency": "Moneda (código de 3 letras)", "scale": "Decimales",
    "finance_settings": "Configurar moneda", "currency_required": "Configura la moneda antes del primer registro.",
    "currency_locked": "La moneda queda protegida después del primer título.",
    "finance_invalid": "Revisa los datos, el importe y los decimales. Usa punto o coma decimal, sin separador de miles.",
    "finance_conflict": "Operación rechazada. Revisa saldo, estado del título, moneda y repetición de la solicitud.",
    "receivable": "Cuentas por cobrar", "payable": "Cuentas por pagar", "new_title": "Nuevo título",
    "amount": "Importe", "due_date": "Vencimiento", "remaining": "Pendiente", "paid": "Liquidado",
    "settled_amount": "Importe cobrado o pagado", "open": "Pendiente", "canceled": "Cancelado",
    "overdue": "Vencido", "settle": "Registrar pago", "cancel": "Cancelar",
    "reverse": "Revertir", "method": "Medio de pago", "cash": "Efectivo",
    "transfer": "Transferencia", "card": "Tarjeta", "other": "Otro", "party": "Cliente o proveedor (ID opcional)",
    "no_titles": "No hay títulos.", "no_settlements": "No hay pagos registrados.",
    "reversed": "Revertido", "configured": "Configuración", "settled": "Pago", "title": "Título",
})

TEXT["pt"].update({
    "pricing": "Preços e custos", "cost": "Custo", "selling_price": "Preço de venda",
    "fx": "Câmbio USD/PYG", "fx_manual": "Cotação da empresa", "fx_automatic": "Referência automática",
    "fx_mode": "Cotação usada nas operações", "fx_rate": "Guaranis por dólar (1 USD)",
    "fx_invalid": "Confira a cotação, o motivo e a disponibilidade da referência.",
    "fx_missing": "Cotação comercial ainda não configurada.", "fx_reference": "Referência consultada",
    "fx_refresh": "Verificar referência", "fx_failure": "A consulta falhou. Confira a data do último valor.",
    "fx_checked": "Última verificação", "fx_published": "Publicação", "fx_equivalent": "Equivalente indicativo",
    "fx_daily": "O BCP publica a referência em dias úteis. O sistema consulta a tabela a cada hora.",
    "not_priced": "Preço ainda não cadastrado.", "payment_currency": "Moeda do pagamento",
    "fx_manual_note": "O valor da empresa é aplicado às operações no modo manual.",
})
TEXT["es"].update({
    "pricing": "Precios y costos", "cost": "Costo", "selling_price": "Precio de venta",
    "fx": "Cambio USD/PYG", "fx_manual": "Cotización de la empresa", "fx_automatic": "Referencia automática",
    "fx_mode": "Cotización aplicada a las operaciones", "fx_rate": "Guaraníes por dólar (1 USD)",
    "fx_invalid": "Revisa cotización, motivo y disponibilidad de la referencia.",
    "fx_missing": "La cotización comercial aún no está configurada.", "fx_reference": "Referencia consultada",
    "fx_refresh": "Verificar referencia", "fx_failure": "La consulta falló. Revisa la fecha del último valor.",
    "fx_checked": "Última consulta", "fx_published": "Publicación", "fx_equivalent": "Equivalente indicativo",
    "fx_daily": "El BCP publica la referencia en días hábiles. El sistema consulta la tabla cada hora.",
    "not_priced": "Precio aún no registrado.", "payment_currency": "Moneda del pago",
    "fx_manual_note": "El valor de la empresa se aplica a las operaciones en modo manual.",
})

TEXT["pt"].update({
    "sales": "Vendas", "new_sale": "Nova venda", "seller": "Vendedor", "customer": "Cliente (ID opcional)",
    "discount": "Desconto · USD", "draft": "Rascunho", "confirmed": "Confirmada", "confirm_sale": "Confirmar venda",
    "sale_conflict": "Operação recusada. Confira a versão, os dados ativos, o estoque, a cotação e os recebimentos.",
    "unit_price": "Preço unitário USD (vazio usa o cadastro)", "add_item": "Incluir ou atualizar item",
    "remove_item": "Remover", "total": "Total", "subtotal": "Subtotal", "no_sales": "Nenhuma venda encontrada.",
    "item_set": "Item atualizado", "item_removed": "Item removido", "sale": "Venda",
})
TEXT["es"].update({
    "sales": "Ventas", "new_sale": "Nueva venta", "seller": "Vendedor", "customer": "Cliente (ID opcional)",
    "discount": "Descuento · USD", "draft": "Borrador", "confirmed": "Confirmada", "confirm_sale": "Confirmar venta",
    "sale_conflict": "Operación rechazada. Revisa versión, datos activos, inventario, cotización y cobros.",
    "unit_price": "Precio unitario USD (vacío usa el catálogo)", "add_item": "Agregar o actualizar producto",
    "remove_item": "Quitar", "total": "Total", "subtotal": "Subtotal", "no_sales": "No hay ventas.",
    "item_set": "Producto actualizado", "item_removed": "Producto quitado", "sale": "Venta",
})

TEXT["pt"].update({
    "commissions": "Comissões", "percent": "Percentual (%)", "commission_event": "Quando apurar",
    "received": "Em cada recebimento", "commission_confirmed": "Na confirmação da venda",
    "commission_invalid": "Informe vendedor, percentual de 0 a 100, evento e dados de pagamento válidos.",
    "commission_conflict": "Confira o saldo disponível, a cotação e a repetição do pagamento.",
    "commission_rules": "Regras para novas vendas", "commission_no_rule": "Configure a comissão do vendedor antes de confirmar.",
    "commission_earned": "Comissão apurada", "commission_paid": "Comissão paga",
    "commission_balance": "Saldo de comissão", "commission_payout": "Pagar comissão",
    "commission_base": "Base de cálculo", "recent_history": "Últimos 50 registros",
    "rule_configured": "Regra de comissão", "accrued": "Comissão apurada",
    "accrual_reversed": "Apuração estornada", "payout": "Comissão paga", "payout_reversed": "Pagamento estornado",
    "sale_conflict": "Operação recusada. Confira versão, dados ativos, estoque, câmbio, regra de comissão e recebimentos.",
})
TEXT["es"].update({
    "commissions": "Comisiones", "percent": "Porcentaje (%)", "commission_event": "Cuándo calcular",
    "received": "En cada cobro", "commission_confirmed": "Al confirmar la venta",
    "commission_invalid": "Indica vendedor, porcentaje de 0 a 100, evento y datos de pago válidos.",
    "commission_conflict": "Revisa saldo disponible, cotización y repetición del pago.",
    "commission_rules": "Reglas para nuevas ventas", "commission_no_rule": "Configura la comisión del vendedor antes de confirmar.",
    "commission_earned": "Comisión calculada", "commission_paid": "Comisión pagada",
    "commission_balance": "Saldo de comisión", "commission_payout": "Pagar comisión",
    "commission_base": "Base de cálculo", "recent_history": "Últimos 50 registros",
    "rule_configured": "Regla de comisión", "accrued": "Comisión calculada",
    "accrual_reversed": "Comisión revertida", "payout": "Comisión pagada", "payout_reversed": "Pago revertido",
    "sale_conflict": "Operación rechazada. Revisa versión, datos activos, inventario, cambio, regla de comisión y cobros.",
})

TEXT["pt"].update({
    "cash_flow": "Fluxo financeiro", "sales_report": "Vendas confirmadas",
    "top_products": "Produtos mais vendidos por quantidade", "export_limit": "A exportação admite até 10 mil registros. Refine os filtros.",
})
TEXT["es"].update({
    "cash_flow": "Flujo financiero", "sales_report": "Ventas confirmadas",
    "top_products": "Productos más vendidos por cantidad", "export_limit": "La exportación admite hasta 10 mil registros. Refina los filtros.",
})

TEXT["pt"].update({
    "access_denied": "Acesso negado para esta conta.", "not_found": "Página ou registro não encontrado.",
    "request_invalid": "Solicitação inválida. Confira os campos e tente novamente.",
    "database_unavailable": "Banco temporariamente indisponível. Tente novamente.",
    "master_created": "MASTER cadastrado", "master_password_recovered": "Senha do MASTER recuperada",
    "operator_created": "Operador cadastrado", "operator_deactivated": "Operador desativado",
    "currency": "Moeda", "prices": "Preços",
})
TEXT["es"].update({
    "access_denied": "Acceso denegado para esta cuenta.", "not_found": "Página o registro no encontrado.",
    "request_invalid": "Solicitud no válida. Revisa los campos e inténtalo de nuevo.",
    "database_unavailable": "Base de datos temporalmente no disponible. Inténtalo de nuevo.",
    "master_created": "MASTER creado", "master_password_recovered": "Contraseña del MASTER recuperada",
    "operator_created": "Operador creado", "operator_deactivated": "Operador desactivado",
    "currency": "Moneda", "prices": "Precios",
})

TEXT["pt"]["search_button"] = "Buscar"
TEXT["es"]["search_button"] = "Buscar"

TEXT["pt"].update({
    "import_skus": "Importar produtos", "import_template": "Baixar modelo CSV",
    "csv_file": "Planilha CSV", "import_line": "Linha", "import_success": "Produtos importados:",
    "import_help": "Preencha o modelo e salve em CSV UTF-8 (até 1.000 produtos e 1 MiB). Formate o código interno e o código de barras como texto para preservar zeros à esquerda. Após importar, abra a edição de um produto para adicionar sua foto.",
    "import_header": "Use as colunas do modelo. Código e descrição são obrigatórios.",
    "import_row": "Confira a codificação UTF-8, as colunas e os dados do produto.",
    "import_limit": "O arquivo ultrapassa 1.000 produtos.", "import_empty": "Inclua pelo menos um produto.",
    "product_photo": "Foto do produto", "choose_photo": "Selecionar foto (JPEG, PNG ou WebP, até 5 MiB)",
    "save_photo": "Salvar foto", "remove_photo": "Remover foto",
    "photo_invalid": "Envie uma imagem válida com até 20 megapixels e sem animação.",
})
TEXT["es"].update({
    "import_skus": "Importar productos", "import_template": "Descargar plantilla CSV",
    "csv_file": "Hoja CSV", "import_line": "Fila", "import_success": "Productos importados:",
    "import_help": "Completa la plantilla y guárdala en CSV UTF-8 (hasta 1.000 productos y 1 MiB). Formatea el código interno y el código de barras como texto para conservar los ceros iniciales. Tras importar, abre la edición de un producto para agregar su foto.",
    "import_header": "Usa las columnas de la plantilla. El código y la descripción son obligatorios.",
    "import_row": "Revisa la codificación UTF-8, las columnas y los datos del producto.",
    "import_limit": "El archivo supera los 1.000 productos.", "import_empty": "Incluye al menos un producto.",
    "product_photo": "Foto del producto", "choose_photo": "Seleccionar foto (JPEG, PNG o WebP, hasta 5 MiB)",
    "save_photo": "Guardar foto", "remove_photo": "Quitar foto",
    "photo_invalid": "Sube una imagen válida de hasta 20 megapíxeles y sin animación.",
})
