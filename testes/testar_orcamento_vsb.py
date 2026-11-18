"""
Testes locais do formato de impressão "Orçamento VSB" (../orcamento_vsb.html), sem ERPNext.

O template é renderizado num jinja2 SandboxedEnvironment com DebugUndefined — o mesmo tipo
de ambiente que o Frappe usa nos formatos Jinja — com um Orçamento simulado igual ao da
tela de 30/09/2026 (SAL-QTN-2026-00001, MAG MOVEIS CORPORATIVOS, R$ 416,50).

Uso (Windows):  set PYTHONIOENCODING=utf-8 && python testes\\testar_orcamento_vsb.py
Requer: jinja2 e num2words (usado como referência do valor por extenso).
Gera: testes/saida/previa_*.html para conferência visual.
"""
import datetime as dt
import html as htmlmod
import json
import random
import re
import sys
from decimal import Decimal
from pathlib import Path

from jinja2 import DebugUndefined
from jinja2.sandbox import SandboxedEnvironment
from num2words import num2words

AQUI = Path(__file__).resolve().parent
TEMPLATE = AQUI.parent / "orcamento_vsb.html"
OFICIAL = AQUI / "referencia" / "quotation_with_item_image_v16.json"
SAIDA = AQUI / "saida"

# Traduções pt-BR alcançadas pelo template oficial (erpnext/frappe locale/pt_BR.po, branch
# version-16, 30/09/2026). As chaves com dois-pontos ("Posting Date:", "Grand Total:"...)
# não existem lá e ficam em inglês.
PT_BR = {
    "CANCELLED": "CANCELADO", "DRAFT": "RASCUNHO", "No": "Não", "Item Code": "Código do Item",
    "Quantity": "Quantidade", "Rate": "Preço Unitário", "Amount": "Valor Total",
    "Discount": "Desconto", "Terms and Conditions": "Termos e Condições",
    "Page {0} of {1}": "Página {0} de {1}",
}

ENDERECOS = {
    "MAG-Faturamento": dict(address_line1="Rua travessa sargento portugal 64", address_line2="Av dom manuel, 1180",
                            city="Fortaleza", state="Ceará", pincode="60850-520", country="Brazil"),
    "Cliente-Exterior": dict(address_line1="100 Main St", address_line2=None, city="Miami", state="FL",
                             pincode="33101", country="United States"),
}

MOEDAS = {"BRL": ("R$", ".", ","), "USD": ("$", ",", ".")}
CAMPOS_MOEDA = {"total", "discount_amount", "grand_total", "rounded_total", "net_rate", "net_amount", "tax_amount",
                "payment_amount"}
CAMPOS_FLOAT = {"qty", "rate", "additional_discount_percentage"}


class FDict(dict):
    """Como o frappe._dict: acesso por atributo, None quando a chave falta."""

    def __getattr__(self, chave):
        return self.get(chave)


class Registro:
    """Documento ou linha de tabela filha, com get_formatted no estilo do Frappe."""

    def __init__(self, **campos):
        self.__dict__.update(campos)

    def __getattr__(self, chave):  # só é chamado para campos ausentes
        return None

    def get(self, chave, padrao=None):
        return self.__dict__.get(chave, padrao)

    def get_formatted(self, campo, doc=None, currency=None, **_):
        valor = self.__dict__.get(campo)
        if campo in CAMPOS_MOEDA:
            moeda = currency or (doc.currency if doc else None) or self.__dict__.get("currency") or "BRL"
            return formatar_moeda(valor, moeda)
        if campo in CAMPOS_FLOAT:
            return formatar_float(valor)
        return "" if valor is None else str(valor)


def formatar_numero(valor, casas, milhar, decimal):
    texto = f"{abs(valor):,.{casas}f}".replace(",", "\0").replace(".", decimal).replace("\0", milhar)
    return ("-" if valor < 0 else "") + texto


def formatar_moeda(valor, moeda):
    simbolo, milhar, decimal = MOEDAS[moeda]
    return f"{simbolo} {formatar_numero(float(valor or 0), 2, milhar, decimal)}"


def formatar_float(valor):
    valor = float(valor or 0)
    # o Frappe mostra Float inteiro sem casas ("19"), senão usa a precisão padrão (3)
    return str(int(valor)) if valor == int(valor) else formatar_numero(valor, 3, ".", ",")


def money_in_words_frappe(valor, moeda="BRL", lang="pt-BR"):
    """Réplica de frappe.utils.money_in_words (v16): é o texto que o ERPNext grava em in_words."""

    def in_words(numero):
        try:
            return num2words(int(numero), lang=lang).replace("-", " ")
        except NotImplementedError:
            return num2words(int(numero), lang="en").replace("-", " ")

    inteiro, fracao = f"{float(valor):.2f}".split(".")
    texto = f"{moeda} {in_words(inteiro).title()}"
    if int(fracao):
        texto += f" e {in_words(int(fracao)).title()} Centavo"
    return f"{texto} apenas."


def orcamento(**alteracoes):
    """
    Cópia do SAL-QTN-2026-00001 lido na VPS em 30/09/2026: 1 rádio a R$ 350,00 + ICMS 19%
    = R$ 416,50, com arredondamento ligado (rounded_total R$ 416,00) e uma parcela.
    """
    itens = [Registro(item_code="0001", item_name="0001 - radio comunicador baofeng", qty=1, uom="Unit",
                      net_rate=350, net_amount=350, image=None, currency="BRL", description=None)]
    impostos = [Registro(description="ICMS 19% @ 19.0", rate=19, tax_amount=66.5, included_in_print_rate=0,
                         currency="BRL")]
    parcelas = [Registro(due_date=dt.date(2026, 9, 30), invoice_portion=100, payment_amount=416, description=None,
                         payment_term=None, currency="BRL")]
    campos = dict(
        doctype="Quotation", name="SAL-QTN-2026-00001", customer_name="MAG MOVEIS CORPORATIVOS",
        party_name="MAG MOVEIS CORPORATIVOS", customer_address="MAG-Faturamento", tax_id=None,
        address_display="Rua travessa sargento portugal 64<br>Fortaleza<br>",
        contact_display="Carlos", contact_mobile="+55 85 90000-0000", contact_phone=None,
        contact_email="contato@exemplo.com.br", company="vsb segurança",
        transaction_date=dt.date(2026, 9, 30), valid_till=dt.date(2026, 10, 30),
        currency="BRL", total=350, discount_amount=0, additional_discount_percentage=0,
        apply_discount_on="Grand Total", grand_total=416.5, rounded_total=416,
        in_words=money_in_words_frappe(416, "BRL"), terms=None, tc_name=None, payment_terms_template=None,
        docstatus=1, items=itens, taxes=impostos, payment_schedule=parcelas,
        meta=FDict(is_submittable=1), flags=FDict(show_inclusive_tax_in_print=0),
    )
    campos.update(alteracoes)
    return Registro(**campos)


def cint(valor, padrao=0):
    """frappe.utils.cint — o Frappe troca o filtro Jinja "int" por esta função."""
    try:
        return int(float(valor))
    except Exception:
        return padrao


def flt(valor, precisao=None):
    try:
        numero = float(valor)
    except Exception:
        return 0.0
    return round(numero, precisao) if precisao is not None else numero


ATRIBUTOS_PROIBIDOS = {"gi_frame", "gi_code", "gi_yieldfrom", "cr_frame", "cr_code", "cr_origin", "cr_await", "ag_code",
                       "ag_frame", "tb_frame", "tb_next", "f_back", "f_builtins", "f_code", "f_globals", "f_locals",
                       "f_trace"}


class FrappeSandboxedEnvironment(SandboxedEnvironment):
    """Cópia de frappe.utils.jinja._get_jenv (v16): sandbox + UNSAFE_ATTRIBUTES sem format/format_map."""

    def is_safe_attribute(self, obj, attr, *args, **kwargs):
        if attr in ATRIBUTOS_PROIBIDOS:
            return False
        return super().is_safe_attribute(obj, attr, *args, **kwargs)


def ambiente(item_naming_by="Item Code"):
    env = FrappeSandboxedEnvironment(undefined=DebugUndefined)
    # mesmos filtros de frappe.utils.jinja.set_filters
    env.filters.update({"json": json.dumps, "len": len, "int": cint, "str": lambda v: "" if v is None else str(v),
                        "flt": flt})

    def traduzir(msg, lang=None, context=None):
        return PT_BR.get(msg, msg)

    def get_value(doctype, nome, campos=None, as_dict=False):
        if doctype == "Address" and nome in ENDERECOS:
            return FDict(ENDERECOS[nome])
        return None

    frappe = FDict(
        utils=FDict(format_date=lambda data: data.strftime("%d/%m/%Y") if data else ""),
        db=FDict(get_value=get_value, get_single_value=lambda doctype, campo: item_naming_by),
        render_template=lambda fonte, ctx: env.from_string(fonte).render(ctx),
    )
    env.globals.update(frappe=frappe, _=traduzir)
    return env


def renderizar(fonte, doc, item_naming_by="Item Code", **ajustes_impressao):
    impressao = FDict(repeat_header_footer=0, add_draft_heading=1, print_taxes_with_zero_amount=0)
    impressao.update(ajustes_impressao)
    return ambiente(item_naming_by).from_string(fonte).render(
        doc=doc, layout=[[]], letter_head='<div class="lh">[papel timbrado VSB]</div>', no_letterhead=0,
        footer=None, print_settings=impressao,
    )


def texto_visivel(html):
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", htmlmod.unescape(html)).strip()


INGLES = [r"Customer Name", r"Bill to", r"Quotation", r"Posting Date", r"Valid Till", r"Sub Total", r"In Words",
          r"Grand Total", r"\bUnit\b", r"Brazil", r"Discount", r"Terms and Conditions", r"DRAFT", r"CANCELLED",
          r"\bPage\b", r"Quantity", r"\bRate\b", r"\bAmount\b", r"Item Code", r" @ ", r"\bNão\b", r"[Aa]penas",
          r"\bBRL\b", r"[Dd]ezasseis"]

falhas = []


def conferir(nome, condicao, detalhe=""):
    if not condicao:
        falhas.append(f"{nome}: {detalhe}")


FRONTEIRA_DE_CLASSE = re.compile(r"\b(mil|milhão|milhões|bilhão|bilhões)(?:,| e) ")


def testar_extenso(fonte):
    """
    Compara vsb_extenso_reais com o num2words pt_BR ('catorze' → 'quatorze', sem 'zero reais e').

    O conectivo entre classes (milhões/mil) é estilo e o num2words é incoerente nele
    ("dois bilhões, quinhentos milhões" mas "mil e cem"), então na comparação em massa ele é
    neutralizado; a regra do template é conferida à parte com casos escritos à mão.
    """
    modulo = ambiente().from_string(fonte).make_module({"layout": []})
    macro = modulo.vsb_extenso_reais

    for n in range(1, 1000):
        obtido = str(modulo.vsb_extenso_ate_999(n))
        esperado = num2words(n, lang="pt_BR").replace("catorze", "quatorze")
        conferir("extenso 1–999", obtido == esperado, f"{n}: {obtido!r} ≠ {esperado!r}")

    regra = {
        "1050": "mil e cinquenta reais", "1100": "mil e cem reais", "1116": "mil, cento e dezesseis reais",
        "2500": "dois mil e quinhentos reais", "1000001": "um milhão e um reais", "1000100": "um milhão e cem reais",
        "1001000": "um milhão e mil reais", "1200000": "um milhão e duzentos mil reais",
        "3050000": "três milhões e cinquenta mil reais", "2500000000": "dois bilhões e quinhentos milhões de reais",
        "677033709": "seiscentos e setenta e sete milhões, trinta e três mil, setecentos e nove reais",
        "1234567.89": "um milhão, duzentos e trinta e quatro mil, quinhentos e sessenta e sete reais e oitenta e nove centavos",
        "1000000": "um milhão de reais", "2000000000": "dois bilhões de reais", "0": "zero reais",
        "0.5": "cinquenta centavos", "1.01": "um real e um centavo", "0.29": "vinte e nove centavos",
        "416.5": "quatrocentos e dezesseis reais e cinquenta centavos",
    }
    for valor, esperado in regra.items():
        obtido = str(macro(float(valor)))
        conferir("extenso regra", obtido == esperado, f"{valor}: {obtido!r} ≠ {esperado!r}")

    def referencia(valor):
        texto = num2words(valor, lang="pt_BR", to="currency").replace("catorze", "quatorze")
        return FRONTEIRA_DE_CLASSE.sub(r"\1 · ", re.sub(r"^zero reais e ", "", texto))

    valores = [Decimal(c) / 100 for c in range(0, 100)]
    valores += [Decimal(n) + Decimal(c) / 100 for n in range(0, 2101) for c in (0, 1, 50)]
    valores += [Decimal(v) for v in ("2416", "10000", "10001", "10100", "10116", "100000", "100100", "101000",
                                     "110000", "116000", "999999", "1000000", "1000001", "1000100", "1001000",
                                     "1100000", "1200000", "1234567.89", "2000000", "1000000000", "1000000001",
                                     "1001000000", "2500000000", "999999999999.99")]
    sorteio = random.Random(20260930)
    valores += [Decimal(sorteio.randrange(0, 10**9)) + Decimal(sorteio.randrange(0, 100)) / 100 for _ in range(4000)]
    valores += [Decimal(sorteio.randrange(0, 10**5)) + Decimal(sorteio.randrange(0, 100)) / 100 for _ in range(4000)]

    divergencias = []
    for valor in valores:
        obtido, esperado = FRONTEIRA_DE_CLASSE.sub(r"\1 · ", str(macro(float(valor)))), referencia(valor)
        if obtido != esperado:
            divergencias.append((valor, obtido, esperado))
    for valor, obtido, esperado in divergencias[:15]:
        print(f"  DIVERGE {valor}: obtido={obtido!r}\n{'':>10}esperado={esperado!r}")
    conferir("extenso", not divergencias, f"{len(divergencias)} divergências em {len(valores)} valores")
    print(f"extenso: {len(valores)} valores comparados, {len(divergencias)} divergências")
    for amostra in ("416.50", "0.01", "1.00", "1100.00", "2416.00", "1000000.00", "1200000.00", "1234567.89"):
        print(f"  {amostra:>13} -> {macro(float(amostra))}")


def testar_tela(fonte, fonte_oficial):
    doc = orcamento()
    if fonte_oficial:
        oficial = texto_visivel(renderizar(fonte_oficial, doc))
        print("\n[oficial] " + oficial)
        for termo in ("Customer Name:", "Bill to:", "Quotation:", "Posting Date:", "Valid Till:", "Não Item",
                      "1 Unit", "Sub Total:", "ICMS 19% @ 19.0 (19%):", "Desconto (0%):", "In Words:",
                      "BRL Quatrocentos E Dezasseis apenas.", "Grand Total:", "Brazil"):
            conferir("oficial reproduz a tela", termo in oficial, f"não encontrou {termo!r}")
        (SAIDA / "previa_oficial.html").write_text(pagina(renderizar(fonte_oficial, doc)), encoding="utf-8")

    html = renderizar(fonte, doc)
    texto = texto_visivel(html)
    print("\n[novo]    " + texto)
    (SAIDA / "previa_nova.html").write_text(pagina(html), encoding="utf-8")
    for padrao in INGLES:
        achado = re.search(padrao, texto)
        conferir("sem inglês", not achado, f"{padrao!r} ainda aparece: …{texto[max(0, achado.start() - 30):achado.end() + 30]}…" if achado else "")
    for termo in ("Cliente MAG MOVEIS CORPORATIVOS",
                  "Rua travessa sargento portugal 64 Av dom manuel, 1180 Fortaleza - Ceará • CEP 60850-520",
                  "Contato Nome Exemplo", "Telefone +55 85 90000-0000",
                  "E-mail contato@exemplo.com.br",
                  "Nº Descrição Qtd. Preço unit. Total",
                  "1 0001 - radio comunicador baofeng 1 UN R$ 350,00 R$ 350,00",
                  "Subtotal R$ 350,00", "ICMS 19% R$ 66,50",
                  "Valor total por extenso Quatrocentos e dezesseis reais e cinquenta centavos",
                  "Total geral R$ 416,50", "Total a pagar (arredondado) R$ 416,00",
                  "Condições de pagamento", "Parcela Vencimento Valor", "Parcela 1 30/09/2026 R$ 416,00",
                  "vsb segurança", "De acordo — MAG MOVEIS CORPORATIVOS"):
        conferir("tela nova", termo in texto, f"não encontrou {termo!r}")
    conferir("tela nova", "Desconto" not in texto, "linha de desconto zerada apareceu")
    conferir("tela nova", "{{" not in html, "variável indefinida impressa")
    # o corpo não deve repetir o que o papel timbrado já imprime
    for repetido in ("SAL-QTN-2026-00001", "30/10/2026", "Emissão", "Validade", "Orçamento:"):
        conferir("sem repetir o timbrado", repetido not in texto, f"{repetido!r} já está no papel timbrado")


def testar_variacoes(fonte):
    def caso(nome, doc, esperados=(), ausentes=(), **opcoes):
        html = renderizar(fonte, doc, **opcoes)
        texto = texto_visivel(html)
        conferir(nome, "{{" not in html, "variável indefinida impressa")
        for termo in esperados:
            conferir(nome, termo in texto, f"não encontrou {termo!r} em: {texto}")
        for termo in ausentes:
            conferir(nome, termo not in texto, f"não devia aparecer {termo!r} em: {texto}")
        return html

    imposto = lambda **c: Registro(**{"description": "ICMS 19% @ 19.0", "rate": 19, "tax_amount": 66.5,
                                      "included_in_print_rate": 0, "currency": "BRL", **c})
    item = lambda **c: Registro(**{"item_code": "A", "item_name": "Câmera", "qty": 1, "uom": "Unit", "net_rate": 10,
                                   "net_amount": 10, "currency": "BRL", "description": None, "image": None, **c})
    caso("desconto % sobre o total líquido",
         orcamento(apply_discount_on="Net Total", additional_discount_percentage=10, discount_amount=35),
         ["Subtotal R$ 350,00 Desconto (10%) − R$ 35,00 ICMS 19% R$ 66,50"])
    caso("desconto em valor sobre o total geral", orcamento(discount_amount=20),
         ["ICMS 19% R$ 66,50 Desconto − R$ 20,00"], ["(0%)"])
    caso("rascunho", orcamento(docstatus=0), ["Rascunho — sujeito a alteração"], ["De acordo"])
    caso("rascunho sem cabeçalho", orcamento(docstatus=0), ausentes=["Rascunho —"], add_draft_heading=0)
    caso("cancelado", orcamento(docstatus=2), ["Orçamento cancelado"], ["De acordo"])
    caso("moeda estrangeira usa o extenso do ERPNext",
         orcamento(currency="USD", in_words="USD Four Hundred And Sixteen only.", rounded_total=0),
         ["por extenso USD Four Hundred And Sixteen only.", "Total geral $ 416.50"])
    caso("sem arredondamento", orcamento(rounded_total=0), ["Total geral R$ 416,50"], ["arredondado"])
    caso("arredondado igual ao total", orcamento(grand_total=416, rounded_total=416),
         ["Total geral R$ 416,00"], ["arredondado"])
    caso("sem endereço nem contato",
         orcamento(customer_address=None, address_display=None, contact_display=None, contact_mobile=None,
                   contact_email=None),
         ["Cliente MAG MOVEIS CORPORATIVOS"], ["Contato", "CEP"])
    caso("sem endereço usa o texto do ERP", orcamento(customer_address=None),
         ["Rua travessa sargento portugal 64 Fortaleza"])
    caso("com CNPJ", orcamento(tax_id="07.452.335/0001-90"), ["CNPJ/CPF: 07.452.335/0001-90"])
    caso("código do item", orcamento(items=[item(item_code="CAM-01", item_name="Câmera")]), ["Cód. CAM-01"],
         item_naming_by="Item Code")
    caso("código já presente no nome é omitido", orcamento(), ausentes=["Cód."], item_naming_by="Item Code")
    caso("sem código quando a numeração é série", orcamento(items=[item(item_code="CAM-01", item_name="Câmera")]),
         ausentes=["Cód."], item_naming_by="Naming Series")
    caso("imposto com descrição limpa", orcamento(taxes=[imposto(description="ICMS")]), ["ICMS (19%) R$ 66,50"])
    caso("taxa de valor fixo", orcamento(taxes=[imposto(description="Frete", rate=0, tax_amount=50)]),
         ["Frete R$ 50,00"], ["(0%)"])
    caso("imposto zerado oculto", orcamento(taxes=[imposto(tax_amount=0)]), ausentes=["ICMS"])
    caso("imposto zerado com opção marcada", orcamento(taxes=[imposto(tax_amount=0)]), ["ICMS 19% R$ 0,00"],
         print_taxes_with_zero_amount=1)
    caso("imposto incluso no preço", orcamento(taxes=[imposto(included_in_print_rate=1)]), ausentes=["ICMS"])
    caso("endereço no exterior", orcamento(customer_address="Cliente-Exterior"),
         ["100 Main St Miami - FL • CEP 33101 United States"])
    caso("termos", orcamento(terms="<p>Pagamento em 30 dias.</p>", tc_name="Padrão VSB"),
         ["Termos e condições — Padrão VSB Pagamento em 30 dias."])
    caso("parcelas com descrição", orcamento(payment_schedule=[
        Registro(due_date=dt.date(2026, 10, 10), payment_amount=208.25, description="Entrada 50%", currency="BRL"),
        Registro(due_date=dt.date(2026, 11, 10), payment_amount=208.25, description=None, payment_term="30 dias",
                 currency="BRL"),
    ], payment_terms_template="50/50"), ["Condições de pagamento — 50/50",
                                         "Entrada 50% 10/10/2026 R$ 208,25", "30 dias 10/11/2026 R$ 208,25"])
    caso("sem parcelas", orcamento(payment_schedule=[]), ausentes=["Condições de pagamento"])
    # a paginação é do rodapé do papel timbrado; o formato não pode criar outra nem
    # redefinir as classes .vsb-page-number / .vsb-page-label que o rodapé usa
    html = caso("cabeçalho repetido no PDF", orcamento(), ausentes=["Página"], repeat_header_footer=1)
    conferir("paginação", 'id="footer-html"' in html, "sem o bloco de rodapé do PDF")
    for classe in (".vsb-page-number", ".vsb-page-label"):
        conferir("classes do timbrado", classe not in fonte, f"{classe} é do rodapé do papel timbrado")
    caso("unidades", orcamento(items=[
        item(item_name="Câmera", qty=2, uom="Nos", net_amount=20),
        item(item_name="Instalação", qty=3, uom="Hour", net_amount=30),
        item(item_name="Visita", qty=1, uom="Serviço"),
    ]), ["1 Câmera", "2 UN", "2 Instalação", "3 H", "3 Visita", "1 Serviço"])
    caso("descrição que repete o nome é omitida", orcamento(items=[item(description="<p>Câmera</p>")]),
         ausentes=["Câmera Câmera"])
    caso("descrição que acrescenta aparece",
         orcamento(items=[item(description="<p>Full HD, infravermelho 30 m</p>")]),
         ["Full HD, infravermelho 30 m"])
    html = caso("imagem escapada", orcamento(items=[item(image="/files/cam&1.png")]))
    conferir("imagem escapada", 'src="/files/cam&amp;1.png"' in html, "src da imagem sem escape")
    caso("um milhão", orcamento(grand_total=1000000, rounded_total=1000000), ["por extenso Um milhão de reais"])
    caso("total inteiro", orcamento(grand_total=350, rounded_total=350), ["por extenso Trezentos e cinquenta reais"])


def pagina(corpo):
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Prévia</title>
<style>
  body {{ background: #eee; margin: 0; padding: 24px; font-family: Inter, "Segoe UI", sans-serif; }}
  .print-format {{ background: #fff; width: 210mm; margin: 0 auto; padding: 15mm; box-sizing: border-box;
                   font-size: 14px; line-height: 21px; }}
  .lh {{ border: 1px dashed #bbb; color: #999; text-align: center; padding: 28px 0; }}
  table {{ border-collapse: collapse; }}
</style></head><body><div class="print-format">{corpo}</div></body></html>"""


def main():
    SAIDA.mkdir(exist_ok=True)
    fonte = TEMPLATE.read_text(encoding="utf-8")
    ambiente().from_string(fonte)  # erro de sintaxe falharia aqui, como no validate_template ao salvar
    conferir("render_template", ".__" not in fonte, "o Frappe recusa templates com '.__' (Illegal template)")
    fonte_oficial = json.loads(OFICIAL.read_text(encoding="utf-8"))["html"] if OFICIAL.exists() else None

    testar_extenso(fonte)
    testar_tela(fonte, fonte_oficial)
    testar_variacoes(fonte)

    print()
    if falhas:
        print(f"FALHOU ({len(falhas)}):")
        for falha in falhas:
            print(" -", falha)
        sys.exit(1)
    print("OK: todos os testes passaram. Prévias em", SAIDA)


if __name__ == "__main__":
    main()
