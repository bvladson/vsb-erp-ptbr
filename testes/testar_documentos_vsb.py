"""
Testes locais do formato "Documentos VSB" (../documentos_vsb.html), sem ERPNext.

O mesmo arquivo é instalado em quatro formatos: Pedido de Venda, Fatura de Venda, Guia de
Remessa e Pedido de Compra. Reaproveita o ambiente de testar_orcamento_vsb.py (sandbox Jinja
igual ao do Frappe v16, DebugUndefined, filtros len/int→cint) e testa cada tipo com os casos
que só ele tem.

Uso (Windows):  set PYTHONIOENCODING=utf-8 && python testes\\testar_documentos_vsb.py
Requer: jinja2 e num2words.
Gera: testes/saida/previa_<documento>.html.
"""
import datetime as dt
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import testar_orcamento_vsb as base  # noqa: E402

TEMPLATE = AQUI.parent / "documentos_vsb.html"

base.ENDERECOS.update({
    "MAG-Entrega": dict(address_line1="Av. Santos Dumont, 3000", address_line2="Galpão 2", city="Fortaleza",
                        state="Ceará", pincode="60150-160", country="Brazil"),
    "Fornecedor-Endereco": dict(address_line1="Rua do Fornecedor, 100", address_line2="Distrito Industrial",
                                city="Maracanaú", state="Ceará", pincode="61939-000", country="Brazil"),
    "VSB-Escritorio": dict(address_line1="Rua jornalista Antonio pontes tavares, 1294", address_line2=None,
                           city="Fortaleza", state="Ceará", pincode="60864-590", country="Brazil"),
})

Registro, FDict = base.Registro, base.FDict

# Nada disto pode sobrar no papel: rótulos em inglês dos formatos oficiais do v16 e
# os defeitos já conhecidos.
INGLES = [r"Customer Name", r"Bill to", r"Supplier Name", r"Supplier Address", r"Invoice Date", r"Invoice Number",
          r"Payment Due Date", r"Order Date", r"Delivery Date", r"Required By", r"Sales Order", r"Purchase Order",
          r"Delivery Note", r"Sales Invoice", r"Sub Total", r"In Words", r"Grand Total", r"\bUnit\b", r"Brazil",
          r"Discount", r"Terms and Conditions", r"DRAFT", r"CANCELLED", r"\bPage\b", r"Quantity", r"\bRate\b",
          r"\bAmount\b", r"Item Code", r" @ ", r"\bNão\b", r"[Aa]penas", r"\bBRL\b", r"[Dd]ezasseis", r"\bStatus\b",
          r"Address:"]

falhas = []


def conferir(nome, condicao, detalhe=""):
    if not condicao:
        falhas.append(f"{nome}: {detalhe}")


def item(**c):
    campos = {"item_code": "0001", "item_name": "0001 - radio comunicador baofeng", "qty": 1, "uom": "Unit",
              "net_rate": 350, "net_amount": 350, "currency": "BRL", "description": None, "image": None}
    campos.update(c)
    return Registro(**campos)


def imposto(**c):
    campos = {"description": "ICMS 19% @ 19.0", "rate": 19, "tax_amount": 66.5, "included_in_print_rate": 0,
              "currency": "BRL"}
    campos.update(c)
    return Registro(**campos)


def parcela(vencimento, valor, descricao=None):
    return Registro(due_date=vencimento, payment_amount=valor, description=descricao, payment_term=None,
                    currency="BRL")


def comum(**c):
    campos = dict(company="vsb segurança", currency="BRL", docstatus=1, discount_amount=0,
                  additional_discount_percentage=0, apply_discount_on="Grand Total", terms=None, tc_name=None,
                  meta=FDict(is_submittable=1), flags=FDict(show_inclusive_tax_in_print=0))
    campos.update(c)
    return campos


def venda(doctype, **c):
    campos = comum(doctype=doctype, customer="MAG MOVEIS CORPORATIVOS", customer_name="MAG MOVEIS CORPORATIVOS",
                   customer_address="MAG-Faturamento", tax_id=None, contact_display="Carlos",
                   contact_mobile="+55 85 90000-0000", contact_email="contato@exemplo.com.br")
    campos.update(c)
    return Registro(**campos)


def pedido_venda(**c):
    campos = dict(name="SAL-ORD-2026-00001", transaction_date=dt.date(2026, 9, 30), po_no="PC-4471",
                  po_date=dt.date(2026, 9, 29), delivery_date=dt.date(2026, 10, 15),
                  shipping_address_name="MAG-Entrega", items=[item(qty=2, net_amount=700)],
                  taxes=[imposto(tax_amount=133)], total=700, grand_total=833, rounded_total=833,
                  payment_schedule=[parcela(dt.date(2026, 10, 15), 416.5, "Entrada 50%"),
                                    parcela(dt.date(2026, 11, 15), 416.5)])
    campos.update(c)
    return venda("Sales Order", **campos)


def fatura(**c):
    campos = dict(name="ACC-SINV-2026-00001", posting_date=dt.date(2026, 9, 30), due_date=dt.date(2026, 10, 30),
                  shipping_address_name="MAG-Faturamento", items=[item()], taxes=[imposto()], total=350,
                  grand_total=416.5, rounded_total=416.5, is_return=0,
                  payment_schedule=[parcela(dt.date(2026, 10, 30), 416.5)])
    campos.update(c)
    return venda("Sales Invoice", **campos)


def guia(**c):
    campos = dict(name="MAT-DN-2026-00001", posting_date=dt.date(2026, 9, 30), po_no="PC-4471",
                  shipping_address_name="MAG-Entrega", transporter_name="Transportes Ceará Ltda",
                  vehicle_no="PNX-4B21", driver_name="José Almeida", lr_no="CT-e 1234", lr_date=dt.date(2026, 9, 30),
                  items=[item(qty=2, net_amount=700)], taxes=[], total=700, grand_total=700, rounded_total=700,
                  is_return=0)
    campos.update(c)
    return venda("Delivery Note", **campos)


def pedido_compra(**c):
    campos = comum(doctype="Purchase Order", name="PUR-ORD-2026-00001", supplier="Distribuidora Rádios Norte Ltda",
                   supplier_name="Distribuidora Rádios Norte Ltda", supplier_address="Fornecedor-Endereco",
                   contact_display="Marta", contact_mobile="+55 85 9999-0000",
                   contact_email="vendas@radiosnorte.com.br", transaction_date=dt.date(2026, 9, 30),
                   schedule_date=dt.date(2026, 10, 10), shipping_address="VSB-Escritorio",
                   billing_address="VSB-Escritorio",
                   items=[item(item_name="Rádio comunicador Baofeng UV-5R", qty=10, net_rate=180,
                               net_amount=1800, supplier_part_no="BF-UV5R")],
                   taxes=[imposto(tax_amount=342, category="Total", add_deduct_tax="Add"),
                          imposto(description="Frete", rate=0, tax_amount=50, category="Valuation",
                                  add_deduct_tax="Add"),
                          imposto(description="Desconto comercial", rate=0, tax_amount=30, category="Total",
                                  add_deduct_tax="Deduct")],
                   total=1800, grand_total=2112, rounded_total=2112,
                   payment_schedule=[parcela(dt.date(2026, 10, 30), 2112)])
    campos.update(c)
    return Registro(**campos)


def caso(nome, doc, esperados=(), ausentes=(), **opcoes):
    html = base.renderizar(FONTE, doc, **opcoes)
    texto = base.texto_visivel(html)
    conferir(nome, "{{" not in html and "{%" not in html, "sobrou Jinja ou variável indefinida")
    for padrao in INGLES:
        achado = re.search(padrao, texto)
        conferir(nome, not achado,
                 f"inglês {padrao!r}: …{texto[max(0, achado.start() - 30):achado.end() + 30]}…" if achado else "")
    conferir(nome, doc.name not in texto, f"o número {doc.name} já está no papel timbrado e se repetiu no corpo")
    for termo in esperados:
        conferir(nome, termo in texto, f"não encontrou {termo!r} em: {texto}")
    for termo in ausentes:
        conferir(nome, termo not in texto, f"não devia aparecer {termo!r} em: {texto}")
    return html, texto


def testar():
    cliente = "Cliente MAG MOVEIS CORPORATIVOS Rua travessa sargento portugal 64 Av dom manuel, 1180 Fortaleza - Ceará • CEP 60850-520"
    contato = "Contato Nome Exemplo Telefone +55 85 90000-0000 E-mail contato@exemplo.com.br"
    entrega_mag = "Av. Santos Dumont, 3000 Galpão 2 Fortaleza - Ceará • CEP 60150-160"

    # ---------------- Pedido de Venda ----------------
    html, texto = caso("pedido de venda", pedido_venda(), [
        cliente, contato,
        "Pedido do cliente PC-4471 de 29/09/2026", "Entrega prevista 15/10/2026", "Local de entrega " + entrega_mag,
        "Nº Descrição Qtd. Preço unit. Total",
        "1 0001 - radio comunicador baofeng 2 UN R$ 350,00 R$ 700,00",
        "Subtotal R$ 700,00", "ICMS 19% R$ 133,00", "Total geral R$ 833,00",
        "Valor total por extenso Oitocentos e trinta e três reais",
        "Condições de pagamento", "Entrada 50% 15/10/2026 R$ 416,50", "Parcela 2 15/11/2026 R$ 416,50",
        "vsb segurança", "De acordo — MAG MOVEIS CORPORATIVOS"],
        ["Rascunho", "cancelad", "Devolução", "Recebido por", "Fornecedor", "arredondado"])
    base.SAIDA.mkdir(exist_ok=True)
    (base.SAIDA / "previa_pedido_venda.html").write_text(base.pagina(html), encoding="utf-8")
    caso("pedido de venda em rascunho", pedido_venda(docstatus=0), ["Rascunho — sujeito a alteração"], ["De acordo"])
    caso("pedido de venda cancelado", pedido_venda(docstatus=2), ["Pedido de venda cancelado"], ["De acordo"])
    caso("pedido de venda sem entrega diferente nem pedido do cliente",
         pedido_venda(po_no=None, delivery_date=None, shipping_address_name="MAG-Faturamento"),
         ausentes=["Pedido do cliente", "Entrega prevista", "Local de entrega"])
    caso("pedido de venda arredondado", pedido_venda(rounded_total=833.5, grand_total=833.3),
         ["Total a pagar (arredondado) R$ 833,50", "Oitocentos e trinta e três reais e trinta centavos"])

    # ---------------- Fatura de Venda ----------------
    html, texto = caso("fatura", fatura(), [
        cliente, contato, "1 0001 - radio comunicador baofeng 1 UN R$ 350,00 R$ 350,00",
        "Subtotal R$ 350,00", "ICMS 19% R$ 66,50", "Total geral R$ 416,50",
        "Valor total por extenso Quatrocentos e dezesseis reais e cinquenta centavos",
        "Condições de pagamento", "Parcela 1 30/10/2026 R$ 416,50"],
        # a fatura não tem assinatura; entrega igual à cobrança não é repetida;
        # o vencimento já está no papel timbrado
        ["De acordo", "Recebido por", "Local de entrega", "Pedido do cliente", "Entrega prevista", "Devolução"])
    (base.SAIDA / "previa_fatura.html").write_text(base.pagina(html), encoding="utf-8")
    caso("fatura cancelada", fatura(docstatus=2), ["Fatura cancelada"])
    caso("fatura com CNPJ do cliente", fatura(tax_id="07.452.335/0001-90"), ["CNPJ/CPF: 07.452.335/0001-90"])
    caso("fatura de devolução", fatura(is_return=1, return_against="ACC-SINV-2026-00009",
                                      items=[item(qty=-1, net_amount=-350)], taxes=[imposto(tax_amount=-66.5)],
                                      total=-350, grand_total=-416.5, rounded_total=-416.5,
                                      payment_schedule=[]),
         ["Devolução — referente a ACC-SINV-2026-00009",
          "Valor total por extenso Quatrocentos e dezesseis reais e cinquenta centavos"])

    # ---------------- Guia de Remessa ----------------
    html, texto = caso("guia de remessa", guia(), [
        cliente, contato,
        "Pedido do cliente PC-4471", "Local de entrega " + entrega_mag,
        "Transportadora Transportes Ceará Ltda", "Veículo PNX-4B21", "Motorista José Almeida",
        "Conhecimento de transporte CT-e 1234 de 30/09/2026",
        "1 0001 - radio comunicador baofeng 2 UN R$ 350,00 R$ 700,00", "Total geral R$ 700,00",
        "Valor total por extenso Setecentos reais",
        "Recebido por — nome e documento", "Data e assinatura"],
        ["Condições de pagamento", "De acordo", "Entrega prevista", "Devolução"])
    (base.SAIDA / "previa_guia_remessa.html").write_text(base.pagina(html), encoding="utf-8")
    conferir("guia de remessa", html.count('class="vsb-section-label">Transportadora') == 1,
             "seis detalhes devem sair em duas linhas de três, sem repetir")
    caso("guia de remessa cancelada", guia(docstatus=2), ["Guia de remessa cancelada"], ["Recebido por"])
    caso("guia de remessa em rascunho", guia(docstatus=0), ["Rascunho — sujeito a alteração"], ["Recebido por"])
    caso("guia de devolução", guia(is_return=1, return_against="MAT-DN-2026-00009"),
         ["Devolução — referente a MAT-DN-2026-00009"], ["Recebido por"])
    caso("guia sem transporte", guia(transporter_name=None, vehicle_no=None, driver_name=None, lr_no=None),
         ["Local de entrega"], ["Transportadora", "Veículo", "Motorista", "Conhecimento"])

    # ---------------- Pedido de Compra ----------------
    html, texto = caso("pedido de compra", pedido_compra(), [
        "Fornecedor Distribuidora Rádios Norte Ltda Rua do Fornecedor, 100 Distrito Industrial Maracanaú - Ceará • CEP 61939-000",
        "Contato Nome Marta Telefone +55 85 9999-0000 E-mail vendas@radiosnorte.com.br",
        "Entrega prevista 10/10/2026",
        "Entregar em Rua jornalista Antonio pontes tavares, 1294 Fortaleza - Ceará • CEP 60864-590",
        "1 Rádio comunicador Baofeng UV-5R Cód. 0001 Cód. fornecedor BF-UV5R 10 UN R$ 180,00 R$ 1.800,00",
        "Subtotal R$ 1.800,00 ICMS 19% R$ 342,00 Desconto comercial − R$ 30,00 Total geral R$ 2.112,00",
        "Valor total por extenso Dois mil, cento e doze reais",
        "Condições de pagamento", "Parcela 1 30/10/2026 R$ 2.112,00",
        "vsb segurança", "De acordo — Distribuidora Rádios Norte Ltda"],
        # "Frete" é só custo de estoque (Valuation): não soma no total, não pode aparecer
        ["Cliente", "Frete", "CNPJ/CPF", "Pedido do cliente", "Recebido por"])
    (base.SAIDA / "previa_pedido_compra.html").write_text(base.pagina(html), encoding="utf-8")
    caso("pedido de compra cancelado", pedido_compra(docstatus=2), ["Pedido de compra cancelado"], ["De acordo"])
    caso("pedido de compra em rascunho", pedido_compra(docstatus=0), ["Rascunho — sujeito a alteração"],
         ["De acordo"])
    caso("pedido de compra sem endereço de entrega", pedido_compra(shipping_address=None),
         ["Entrega prevista 10/10/2026"], ["Entregar em"])


def main():
    global FONTE
    FONTE = TEMPLATE.read_text(encoding="utf-8")
    base.ambiente().from_string(FONTE)  # erro de sintaxe falharia aqui, como no validate_template ao salvar
    conferir("render_template", ".__" not in FONTE, "o Frappe recusa templates com '.__' (Illegal template)")
    for classe in (".vsb-page-number", ".vsb-page-label", ".vsb-footer-page"):
        conferir("classes do timbrado", classe not in FONTE, f"{classe} é do rodapé do papel timbrado")
    testar()
    print()
    if falhas:
        print(f"FALHOU ({len(falhas)}):")
        for f in falhas:
            print(" -", f)
        sys.exit(1)
    print("OK: Pedido de Venda, Fatura, Guia de Remessa e Pedido de Compra passaram. Prévias em", base.SAIDA)


if __name__ == "__main__":
    main()
