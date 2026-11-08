"""Help topics with translated steps tied to controls in the administrative UI."""

GUIDES = (
    ("home", "all", "/", "Usar o painel e alterar o idioma", "Usar el panel y cambiar el idioma", (
        ("#menu-toggle", "Use o botão do menu para encontrar os módulos disponíveis para sua conta.",
         "Usa el botón del menú para encontrar los módulos disponibles para tu cuenta."),
        (".brand-header nav", "Alterne entre Português e Español. As telas e o manual acompanham a preferência da sua conta.",
         "Cambia entre Português y Español. Las pantallas y el manual siguen la preferencia de tu cuenta."),
        (".brand-header form[action$='/logout'] button", "Ao terminar, use Sair para encerrar sua sessão.",
         "Al terminar, usa Salir para cerrar tu sesión."),
    )),
    ("catalog", "all", "/catalog", "Consultar produtos e preços", "Consultar productos y precios", (
        ("#q", "Busque pelo código, descrição ou código de barras do produto.",
         "Busca por código, descripción o código de barras del producto."),
        ("#content .list-group", "Confira a descrição e o preço de venda. O preço em PYG depende da cotação cadastrada.",
         "Revisa la descripción y el precio de venta. El precio en PYG depende de la cotización registrada."),
    )),
    ("stock", "all", "/stock", "Consultar saldo e histórico", "Consultar saldo e historial", (
        ("#content .list-group", "Localize o produto e confira o saldo disponível.",
         "Localiza el producto y revisa el saldo disponible."),
        ("#content .list-group a[href*='/stock/']", "Abra o histórico do produto para consultar as movimentações.",
         "Abre el historial del producto para consultar los movimientos."),
    )),
    ("customers", "all", "/contacts/customers", "Localizar um cliente", "Buscar un cliente", (
        ("#q", "Digite o nome ou outro dado do cliente no campo de busca.",
         "Escribe el nombre u otro dato del cliente en el campo de búsqueda."),
        ("#content .list-group", "Consulte os dados exibidos nos resultados.",
         "Consulta los datos que aparecen en los resultados."),
    )),
    ("inventory-report", "all", "/reports", "Consultar e exportar estoque", "Consultar y exportar inventario", (
        ("#balance", "Escolha todos os saldos ou filtre por positivo, zero ou negativo.",
         "Elige todos los saldos o filtra por positivo, cero o negativo."),
        ("#content form button", "Aplique os filtros e, se precisar de uma planilha, use a opção de exportação CSV.",
         "Aplica los filtros y, si necesitas una planilla, usa la opción de exportación CSV."),
    )),
    ("sale", "admin", "/sales/new", "Registrar uma venda", "Registrar una venta", (
        ("#customer_id", "Escolha o cliente, o vendedor e a data de vencimento. Informe o desconto em USD, se houver.",
         "Selecciona el cliente, el vendedor y la fecha de vencimiento. Indica el descuento en USD, si corresponde."),
        ("#product-search", "Busque pelo código ou descrição e adicione os itens. Duas unidades de USD 10, por exemplo, somam USD 20 antes do desconto.",
         "Busca por código o descripción y agrega los artículos. Dos unidades de USD 10, por ejemplo, suman USD 20 antes del descuento."),
        ("#sale-totals", "Confira quantidades, estoque e total antes de salvar.",
         "Revisa cantidades, inventario y total antes de guardar."),
        ("#sale-cart button[value='confirm']", "Salve um rascunho para continuar depois ou confirme para registrar a venda.",
         "Guarda un borrador para continuar después o confirma para registrar la venta."),
    )),
    ("receipt", "admin", "/sales", "Emitir recibo ou cancelar venda", "Emitir recibo o cancelar venta", (
        ("#content .list-group", "Abra a venda confirmada pelo número na lista.",
         "Abre la venta confirmada por su número en la lista."),
        (None, "No detalhe, emita ou imprima o recibo. Para cancelar, confira antes os efeitos no estoque, no financeiro e na comissão.",
         "En el detalle, emite o imprime el recibo. Para cancelar, revisa antes los efectos sobre inventario, finanzas y comisión."),
    )),
    ("product", "admin", "/catalog/new", "Cadastrar e editar um produto", "Crear y editar un producto", (
        ("#content [name='code']", "Informe um código interno único e a descrição. Preencha marca, categoria e código de barras quando disponíveis.",
         "Indica un código interno único y la descripción. Completa marca, categoría y código de barras cuando estén disponibles."),
        ("#content form button", "Salve o produto. Volte ao catálogo para editar dados, incluir uma foto ou inativar o item.",
         "Guarda el producto. Vuelve al catálogo para editar datos, agregar una foto o desactivar el artículo."),
        (None, "Configure o preço em Preços e custos. Registre as unidades iniciais em Estoque.",
         "Configura el precio en Precios y costos. Registra las unidades iniciales en Inventario."),
    )),
    ("import-products", "admin", "/catalog/import", "Importar produtos em massa", "Importar productos en lote", (
        ("#content a[href$='/xlsx/template']", "Baixe o modelo XLSX vazio. Preencha uma linha por produto, com código interno único e descrição, sem mudar os cabeçalhos.",
         "Descarga el modelo XLSX vacío. Completa una fila por producto, con código interno único y descripción, sin cambiar los encabezados."),
        ("#catalog-workbook", "Selecione o XLSX e gere a prévia. Confira as linhas marcadas como novas.",
         "Selecciona el XLSX y genera la vista previa. Revisa las filas marcadas como nuevas."),
        (None, "Confirme o lote quando os dados estiverem corretos. O catálogo é salvo na confirmação.",
         "Confirma el lote cuando los datos sean correctos. El catálogo se guarda al confirmar."),
    )),
    ("update-products", "admin", "/catalog/import", "Alterar produtos em massa", "Actualizar productos en lote", (
        ("#export-page", "Escolha o lote e exporte o catálogo preenchido. Cada lote contém até mil produtos.",
         "Elige el lote y exporta el catálogo completo. Cada lote contiene hasta mil productos."),
        ("#catalog-workbook", "Edite descrição, marca, categoria, variação, código de barras, custo ou preço em USD. Preserve o código interno e a referência da linha.",
         "Edita descripción, marca, categoría, variación, código de barras, costo o precio en USD. Conserva el código interno y la referencia de la fila."),
        (None, "Envie o arquivo e revise a prévia antes de confirmar. Se uma linha mudou depois da exportação, baixe um lote atualizado.",
         "Envía el archivo y revisa la vista previa antes de confirmar. Si una fila cambió después de exportar, descarga un lote actualizado."),
    )),
    ("stock-adjustment", "admin", "/stock", "Movimentar estoque e configurar saldo", "Mover inventario y configurar saldo", (
        ("#content .list-group", "Abra o histórico do produto. Registre uma entrada ou saída com quantidade e motivo.",
         "Abre el historial del producto. Registra una entrada o salida con cantidad y motivo."),
        ("#content a[href$='/stock/settings']", "Em Configurações do estoque, confira se a loja permite saldo negativo antes de registrar saídas.",
         "En Configuración de inventario, revisa si la tienda permite saldo negativo antes de registrar salidas."),
        (None, "Se lançar uma movimentação incorreta, use a compensação no histórico para manter o registro da correção.",
         "Si registras un movimiento incorrecto, usa la compensación en el historial para conservar el registro de la corrección."),
    )),
    ("stock-import", "admin", "/stock/import", "Dar entrada no estoque em massa", "Registrar entradas de inventario en lote", (
        ("#stock-export-page", "Baixe a planilha do lote de estoque. Preencha as quantidades de entrada dos itens, sem alterar os códigos.",
         "Descarga la planilla del lote de inventario. Completa las cantidades de entrada sin alterar los códigos."),
        ("#stock-reason", "Informe o motivo, selecione o XLSX e gere a prévia. Com saldo de 5 e entrada de 3, o novo saldo será 8.",
         "Indica el motivo, selecciona el XLSX y genera la vista previa. Con saldo de 5 y entrada de 3, el nuevo saldo será 8."),
        (None, "Confira o saldo projetado antes de confirmar o lote.",
         "Revisa el saldo proyectado antes de confirmar el lote."),
    )),
    ("pricing", "admin", "/pricing", "Configurar preços, custos e câmbio", "Configurar precios, costos y cambio", (
        ("#content .list-group", "Localize o produto e abra a edição. Salve o custo e o preço de venda em USD.",
         "Localiza el producto y abre la edición. Guarda el costo y el precio de venta en USD."),
        ("#content a[href$='/fx']", "Abra Câmbio para atualizar a referência do Banco Central do Paraguai ou registrar uma taxa manual com motivo.",
         "Abre Cambio para actualizar la referencia del Banco Central del Paraguay o registrar una tasa manual con motivo."),
    )),
    ("contacts", "admin", "/contacts/customers/new", "Cadastrar clientes e fornecedores", "Crear clientes y proveedores", (
        ("#content [name='name']", "No cadastro de cliente, informe nome e os dados de contato disponíveis. Revise e salve.",
         "En el registro de cliente, indica el nombre y los datos de contacto disponibles. Revisa y guarda."),
        (None, "Para um fornecedor, abra Fornecedores no menu e escolha a opção de novo cadastro. Use a lista para editar ou inativar contatos.",
         "Para un proveedor, abre Proveedores en el menú y elige la opción de nuevo registro. Usa la lista para editar o desactivar contactos."),
    )),
    ("finance", "admin", "/finance", "Lançar, baixar ou estornar títulos", "Registrar, liquidar o revertir títulos", (
        ("#content a[href$='/finance/settings']", "Confira a configuração financeira antes de criar o primeiro título.",
         "Revisa la configuración financiera antes de crear el primer título."),
        ("#kind", "Escolha contas a receber ou a pagar e crie um título. Informe valor e vencimento.",
         "Elige cuentas por cobrar o por pagar y crea un título. Indica el importe y el vencimiento."),
        ("#content .list-group", "Abra o título para registrar uma baixa parcial ou total. No histórico, confira as opções de estorno ou cancelamento.",
         "Abre el título para registrar una liquidación parcial o total. En el historial, revisa las opciones de reversión o anulación."),
    )),
    ("commissions", "admin", "/commissions", "Configurar e pagar comissões", "Configurar y pagar comisiones", (
        ("#seller_id", "Selecione o vendedor e informe o percentual aplicado à confirmação da venda.",
         "Selecciona al vendedor e indica el porcentaje aplicado al confirmar la venta."),
        ("#content .list-group", "Abra o vendedor para conferir valores gerados, pagos e saldo antes de registrar um pagamento.",
         "Abre el vendedor para revisar valores generados, pagados y saldo antes de registrar un pago."),
    )),
    ("reports", "admin", "/reports/sales", "Analisar vendas, ranking e caixa", "Analizar ventas, clasificación y caja", (
        ("#content .btn-group, #content nav", "Escolha o relatório de vendas, produtos mais vendidos ou fluxo financeiro.",
         "Elige el informe de ventas, productos más vendidos o flujo financiero."),
        ("#start", "Informe período e demais filtros da tela. Compare os valores por moeda e exporte CSV quando disponível.",
         "Indica el período y los demás filtros de la pantalla. Compara valores por moneda y exporta CSV cuando esté disponible."),
    )),
    ("company", "admin", "/settings/company", "Cadastrar os dados do recibo", "Registrar los datos del recibo", (
        ("#content form", "Preencha o nome da empresa e os dados comerciais que devem aparecer no recibo.",
         "Completa el nombre de la empresa y los datos comerciales que deben aparecer en el recibo."),
        ("#content form button", "Salve os dados antes de emitir o recibo de uma venda confirmada.",
         "Guarda los datos antes de emitir el recibo de una venta confirmada."),
    )),
    ("operators", "admin", "/operators", "Cadastrar e desativar operadores", "Crear y desactivar operadores", (
        ("#content [name='username']", "Crie um usuário individual e informe uma senha inicial. Na produção, entregue o código de ativação do autenticador pelo processo de cadastro.",
         "Crea un usuario individual e indica una contraseña inicial. En producción, entrega el código de activación del autenticador mediante el proceso de registro."),
        ("#content .list-group", "Confira as contas cadastradas. Desative o acesso quando a pessoa deixar de operar o sistema.",
         "Revisa las cuentas registradas. Desactiva el acceso cuando la persona deje de operar el sistema."),
    )),
    ("audit", "admin", "/audit", "Consultar a auditoria", "Consultar la auditoría", (
        ("#source", "Selecione o módulo e o período para localizar o evento.",
         "Selecciona el módulo y el período para localizar el evento."),
        ("#content .list-group", "Confira a ação, a pessoa ou serviço responsável e o horário registrado.",
         "Revisa la acción, la persona o servicio responsable y la hora registrada."),
    )),
    ("maintenance", "dev", "/maintenance", "Redefinir a senha do MASTER", "Restablecer la contraseña de MASTER", (
        ("#content [name='dev_password']", "Confirme sua senha DEV e informe a nova senha do MASTER.",
         "Confirma tu contraseña DEV e indica la nueva contraseña de MASTER."),
        ("#content form button", "Ao confirmar, as sessões do MASTER são encerradas. O autenticador permanece cadastrado.",
         "Al confirmar, se cierran las sesiones de MASTER. El autenticador permanece registrado."),
    )),
)


def help_topics(locale, role):
    if role not in ("DEV", "MASTER", "OPERATOR"):
        return []
    spanish = locale == "es"
    allowed = {"all"}
    if role in ("DEV", "MASTER"):
        allowed.add("admin")
    if role == "DEV":
        allowed.add("dev")
    return [
        (key, path, es if spanish else pt,
         [(target, step_es if spanish else step_pt) for target, step_pt, step_es in steps])
        for key, access, path, pt, es, steps in GUIDES if access in allowed
    ]
