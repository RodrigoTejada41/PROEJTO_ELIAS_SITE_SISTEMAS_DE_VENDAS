from fastapi import APIRouter, Depends, Request

from app import company, identity
from app.web import (
    TEXT, check_csrf, dev_session, master_session, read_catalog_form, read_form,
    redirect, render,
)

router = APIRouter()


@router.get("/settings/company")
def company_page(request: Request, master=Depends(master_session)):
    return render(request, "company.html", section="company", csrf=master[1],
                  is_master=True, company=company.profile(), fields=company.FIELDS)


@router.post("/settings/company")
def update_company(request: Request, master=Depends(master_session), form=Depends(read_catalog_form)):
    check_csrf(form, master[1])
    values = {key: form.get(key, "").strip() for key in company.FIELDS}
    try:
        company.save_profile(master[0], values)
    except ValueError:
        return render(request, "company.html", 400, section="company", csrf=master[1],
                      is_master=True, company=values, fields=company.FIELDS, error="company_invalid")
    return redirect("/settings/company")


@router.get("/maintenance")
def maintenance(request: Request, dev=Depends(dev_session)):
    return render(request, "maintenance.html", section="maintenance", csrf=dev[1], is_master=True)


@router.post("/maintenance")
def reset_master(request: Request, dev=Depends(dev_session), form=Depends(read_form)):
    check_csrf(form, dev[1])
    address = request.client.host if request.client else "127.0.0.1"
    status, error = identity.reset_master_as_dev(
        dev[0], form.get("dev_password", ""), form.get("password", ""), address,
    )
    if status == 303:
        return redirect("/maintenance?updated=1")
    return render(request, "maintenance.html", status, section="maintenance",
                  csrf=dev[1], is_master=True, error=error)


TEXT["pt"].update({
    "company": "Dados da empresa", "company_save": "Salvar", "receipt_items": "Itens", "receipt_customer": "Cliente",
    "receipt_unit_price": "Preço unitário", "receipt_discount": "Desconto",
    "master_missing": "A conta MASTER ainda não existe.", "trade_name": "Nome comercial", "tax_id": "RUC / identificação empresarial",
    "address": "Endereço", "company_invalid": "Informe o nome da empresa e confira os limites dos campos.",
    "receipt_print": "Imprimir recibo", "receipt_title": "Recibo de venda sem valor fiscal",
    "receipt_company_required": "Preencha os dados da empresa antes de emitir o recibo.",
    "receipt_note": "Este recibo registra a venda. A quitação é registrada no financeiro.",
    "receipt_date": "Data da venda", "receipt_issued": "Recibo de venda emitido",
    "company_updated": "Dados da empresa atualizados", "maintenance": "Manutenção DEV",
    "master_reset": "Redefinir senha do MASTER", "dev_password": "Sua senha DEV",
    "master_new_password": "Nova senha do MASTER", "master_reset_done": "Senha redefinida e sessões do MASTER encerradas.",
    "master_password_reset_by_dev": "Senha do MASTER redefinida pelo DEV", "dev_created": "Conta DEV criada",
    "dev_password_invalid": "Senha DEV inválida.", "master_password_invalid": "Use de 15 a 128 caracteres na nova senha.",
})
TEXT["es"].update({
    "company": "Datos de la empresa", "company_save": "Guardar", "receipt_items": "Artículos", "receipt_customer": "Cliente",
    "receipt_unit_price": "Precio unitario", "receipt_discount": "Descuento",
    "master_missing": "La cuenta MASTER todavía no existe.", "trade_name": "Nombre comercial", "tax_id": "RUC / identificación empresarial",
    "address": "Dirección", "company_invalid": "Indica el nombre de la empresa y revisa los límites de los campos.",
    "receipt_print": "Imprimir recibo", "receipt_title": "Recibo de venta sin valor fiscal",
    "receipt_company_required": "Completa los datos de la empresa antes de emitir el recibo.",
    "receipt_note": "Este recibo registra la venta. El pago se registra en finanzas.",
    "receipt_date": "Fecha de venta", "receipt_issued": "Recibo de venta emitido",
    "company_updated": "Datos de la empresa actualizados", "maintenance": "Mantenimiento DEV",
    "master_reset": "Restablecer contraseña de MASTER", "dev_password": "Tu contraseña DEV",
    "master_new_password": "Nueva contraseña de MASTER", "master_reset_done": "Contraseña restablecida y sesiones de MASTER cerradas.",
    "master_password_reset_by_dev": "Contraseña de MASTER restablecida por DEV", "dev_created": "Cuenta DEV creada",
    "dev_password_invalid": "Contraseña DEV inválida.", "master_password_invalid": "Usa de 15 a 128 caracteres en la nueva contraseña.",
})
