"""
Testes locais do papel timbrado VSB (../timbrado/cabecalho.html e ../timbrado/rodape.html).

O Frappe renderiza o papel timbrado com apenas {"doc": doc.as_dict()}, ou seja `doc` é um
dicionário (frappe._dict) — nunca um Document. Estes testes usam o mesmo contexto e o mesmo
tipo de ambiente Jinja do Frappe v16 (sandbox, DebugUndefined, filtros len/int→cint).

Uso (Windows):  set PYTHONIOENCODING=utf-8 && python testes\\testar_timbrado.py
Requer: jinja2.
"""
import datetime as dt
import html as htmlmod
import re
import sys
from pathlib import Path

from jinja2 import DebugUndefined
from jinja2.sandbox import SandboxedEnvironment

AQUI = Path(__file__).resolve().parent
CABECALHO = AQUI.parent / "timbrado" / "cabecalho.html"
RODAPE = AQUI.parent / "timbrado" / "rodape.html"

# Traduções pt-BR que o Frappe tem para nomes de DocType (erpnext/frappe locale/pt_BR.po).
PT_BR = {
    "Quotation": "Orçamento", "Sales Order": "Pedido de Venda", "Sales Invoice": "Fatura de Venda",
    "Delivery Note": "Guia de Remessa", "Payment Entry": "Lançamento de Pagamento",
    "Timesheet": "Registro de Horas", "United States": "Estados Unidos",
}

EMPRESA = {
    "vsb segurança": dict(company_logo="/files/LOGO PRINCIPAL OTIMIZADO.png", website="vsbseguranca.com.br",
                          email="contato@vsbseguranca.com.br", phone_no="85987102000", tax_id=None),
    "Empresa \"Aspas\" S/A": dict(company_logo="/files/logo.png", website=None, email=None, phone_no=None,
                                  tax_id="07.452.335/0001-90"),
    "Sem Logo ME": dict(company_logo=None, website="x.com.br", email=None, phone_no=None, tax_id=None),
}

ENDERECOS = {
    "Escritório-Faturamento": dict(address_line1="Rua jornalista Antonio pontes tavares, 1294", address_line2=None,
                                   city="Fortaleza", state="Ceará", pincode="60864-590", country="Brazil"),
    "Sem-Cidade": dict(address_line1="Rodovia BR-116, km 12", address_line2=None, city=None, state="Ceará",
                       pincode=None, country="Brazil"),
    "So-CEP": dict(address_line1="Av. Central, 1", address_line2=None, city=None, state=None, pincode="60000-000",
                   country="Brazil"),
    "Exterior": dict(address_line1="100 Main St", address_line2="Suite 4", city="Miami", state="FL",
                     pincode="33101", country="United States"),
}


class FDict(dict):
    """Como frappe._dict: acesso por atributo, None quando a chave falta."""

    def __getattr__(self, chave):
        return self.get(chave)


ATRIBUTOS_PROIBIDOS = {"gi_frame", "gi_code", "gi_yieldfrom", "cr_frame", "cr_code", "cr_origin", "cr_await",
                       "ag_code", "ag_frame", "tb_frame", "tb_next", "f_back", "f_builtins", "f_code", "f_globals",
                       "f_locals", "f_trace"}


class FrappeSandboxedEnvironment(SandboxedEnvironment):
    """Cópia de frappe.utils.jinja._get_jenv (v16)."""

    def is_safe_attribute(self, obj, attr, *args, **kwargs):
        if attr in ATRIBUTOS_PROIBIDOS:
            return False
        return super().is_safe_attribute(obj, attr, *args, **kwargs)


def cint(valor, padrao=0):
    try:
        return int(float(valor))
    except Exception:
        return padrao


def ambiente():
    env = FrappeSandboxedEnvironment(undefined=DebugUndefined)
    env.filters.update({"len": len, "int": cint, "str": lambda v: "" if v is None else str(v)})

    def get_value(doctype, nome, campos=None, as_dict=False):
        tabela = {"Company": EMPRESA, "Address": ENDERECOS}.get(doctype, {})
        dados = tabela.get(nome)
        return FDict(dados) if dados else None

    frappe = FDict(
        db=FDict(get_value=get_value),
        utils=FDict(
            formatdate=lambda data, fmt=None: data.strftime("%d/%m/%Y") if data else "",
            get_url=lambda caminho: f"https://portal.vsbseguranca.com.br{caminho}",
        ),
    )
    env.globals.update(frappe=frappe, _=lambda m, **k: PT_BR.get(m, m))
    return env


def documento(**alteracoes):
    """Orçamento SAL-QTN-2026-00001 como dicionário, igual ao que o Frappe entrega."""
    campos = dict(doctype="Quotation", name="SAL-QTN-2026-00001", company="vsb segurança",
                  company_address="Escritório-Faturamento", transaction_date=dt.date(2026, 9, 30),
                  valid_till=dt.date(2026, 10, 30))
    campos.update(alteracoes)
    return FDict(campos)


def renderizar(fonte, doc):
    return ambiente().from_string(fonte).render(doc=doc)


def texto(h):
    h = re.sub(r"<style.*?</style>", " ", h, flags=re.S)
    h = re.sub(r"<!--.*?-->", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


falhas = []


def conferir(nome, condicao, detalhe=""):
    if not condicao:
        falhas.append(f"{nome}: {detalhe}")


def testar_cabecalho(fonte):
    html = renderizar(fonte, documento())
    t = texto(html)
    print("[cabeçalho]", t)
    conferir("cabeçalho", "{{" not in html and "{%" not in html, "sobrou Jinja")
    for termo in ("vsb segurança", "Rua jornalista Antonio pontes tavares, 1294",
                  "Fortaleza - Ceará • CEP 60864-590", "Orçamento", "SAL-QTN-2026-00001",
                  "Emissão: 30/09/2026", "Validade: 30/10/2026",
                  "SITE vsbseguranca.com.br", "E-MAIL contato@vsbseguranca.com.br", "CONTATO 85987102000"):
        conferir("cabeçalho", termo in t, f"não encontrou {termo!r}")
    conferir("cabeçalho", "CNPJ" not in t, "mostrou CNPJ sem o dado cadastrado")

    # correção 1: a faixa azul é um elemento, e a borda do bloco é uniforme.
    # Larguras diferentes + border-radius fazem o wkhtmltopdf descartar a borda no PDF.
    conferir("faixa azul no PDF", 'class="vsb-header-bar"' in html, "a faixa azul não é um elemento próprio")
    bloco = re.search(r"\.vsb-header\s*\{(.*?)\}", fonte, re.S)
    conferir("faixa azul no PDF", bloco and "border-top" not in bloco.group(1),
             "border-top junto com border-radius em .vsb-header zera a borda no PDF")
    conferir("faixa azul no PDF", bloco and "overflow: hidden" in bloco.group(1),
             "sem overflow:hidden a faixa não é recortada pelo canto arredondado")

    # correção 2: rótulo em português, nunca o nome cru em inglês
    for doctype, esperado in [("Sales Order", "Pedido de venda"), ("Sales Invoice", "Nota / Fatura"),
                              ("Delivery Note", "Guia de remessa"), ("Purchase Order", "Pedido de compra"),
                              ("Payment Entry", "Comprovante de pagamento")]:
        t2 = texto(renderizar(fonte, documento(doctype=doctype, valid_till=None)))
        conferir("rótulo pt-BR", esperado in t2, f"{doctype}: esperava {esperado!r} em: {t2[:110]}")
        conferir("rótulo pt-BR", doctype not in t2, f"{doctype}: vazou o nome em inglês")
    # doctype fora da tabela passa pelo tradutor
    t3 = texto(renderizar(fonte, documento(doctype="Timesheet", valid_till=None)))
    conferir("rótulo pt-BR", "Registro de Horas" in t3, f"Timesheet não foi traduzido: {t3[:110]}")

    # correção 3 e 4: alt escapado e espaços no endereço da logo
    h4 = renderizar(fonte, documento(company='Empresa "Aspas" S/A', company_address=None))
    conferir("alt escapado", 'alt="Empresa &#34;Aspas&#34; S/A"' in h4 or 'alt="Empresa &quot;Aspas&quot; S/A"' in h4,
             "aspas no nome da empresa quebram o atributo alt")
    conferir("alt escapado", 'alt="Empresa "Aspas" S/A"' not in h4, "atributo alt quebrado")
    conferir("CNPJ", "CNPJ: 07.452.335/0001-90" in texto(h4), "não mostrou o CNPJ cadastrado")
    conferir("logo com espaço", "LOGO%20PRINCIPAL%20OTIMIZADO.png" in html, "espaços na URL da logo não foram trocados")
    conferir("logo com espaço", "LOGO PRINCIPAL OTIMIZADO.png" not in html, "sobrou espaço cru na URL da logo")

    # correção 5: endereço sem cidade não deixa traço solto
    t5 = texto(renderizar(fonte, documento(company_address="Sem-Cidade")))
    conferir("endereço", "Rodovia BR-116, km 12 Ceará" in t5, f"cidade ausente montou errado: {t5}")
    conferir("endereço", " - Ceará" not in t5, f"traço solto sem cidade: {t5}")
    t6 = texto(renderizar(fonte, documento(company_address="So-CEP")))
    conferir("endereço", "Av. Central, 1 CEP 60000-000" in t6, f"só CEP montou errado: {t6}")
    conferir("endereço", "•" not in t6, f"marcador solto com só o CEP: {t6}")
    t7 = texto(renderizar(fonte, documento(company_address="Exterior")))
    conferir("endereço", "Miami - FL • CEP 33101 Estados Unidos" in t7, f"exterior montou errado: {t7}")
    conferir("endereço", "Brazil" not in texto(html), "imprimiu Brazil")

    # correção 6: sem logo, a coluna não fica vazia
    h8 = renderizar(fonte, documento(company="Sem Logo ME"))
    conferir("sem logo", "<img" not in h8, "renderizou img sem logo cadastrada")
    conferir("sem logo", "vsb-company-cell-sem-logo" in h8, "não usou a coluna larga sem logo")
    conferir("sem logo", 'class="vsb-logo-cell"' not in h8, "manteve a célula da logo vazia")
    conferir("com logo", 'class="vsb-logo-cell"' in html, "não renderizou a célula da logo")

    # correção 7: sem CSS morto
    conferir("CSS morto", "box-shadow:" not in fonte, "sobrou a regra de box-shadow")
    conferir("CSS morto", "@media print" not in fonte, "sobrou o bloco @media print inútil")

    # fatura mostra vencimento
    t9 = texto(renderizar(fonte, documento(doctype="Sales Invoice", valid_till=None,
                                           posting_date=dt.date(2026, 9, 30), transaction_date=None,
                                           due_date=dt.date(2026, 10, 30))))
    conferir("fatura", "Emissão: 30/09/2026" in t9 and "Vencimento: 30/10/2026" in t9, f"fatura: {t9[:150]}")

    # sem contatos a barra não aparece (o seletor CSS fica sempre no <style>; olhar o atributo)
    h10 = renderizar(fonte, documento(company="Empresa \"Aspas\" S/A"))
    conferir("barra de contatos", 'class="vsb-contact-bar"' not in h10, "barra de contatos vazia apareceu")
    conferir("barra de contatos", 'class="vsb-contact-bar"' in html, "barra de contatos não apareceu com dados")

    # Rótulo e valor precisam de espaço DE VERDADE no HTML, não só a margem do CSS: com
    # margem sozinha o texto copiado sai colado ("SITEvsbseguranca.com.br"), e o mesmo
    # acontece ao extrair o texto do PDF.
    # A conferência é no HTML cru, e não no texto visível, porque texto() troca cada tag
    # por um espaço — ali o caso colado passaria sem ser notado.
    colados = re.findall(r'class="vsb-contact-label">[^<]+</span>(?!&nbsp;|\s)', html)
    conferir("espaço rótulo/valor", not colados, f"faltou o &nbsp; depois do rótulo: {colados}")


def testar_rodape(fonte):
    html = renderizar(fonte, documento())
    t = texto(html)
    print("[rodapé]  ", t)
    conferir("rodapé", "{{" not in html and "{%" not in html, "sobrou Jinja")
    for termo in ("WEB vsbseguranca.com.br", "E-MAIL contato@vsbseguranca.com.br",
                  "TEL 85987102000", "Documento gerado eletronicamente"):
        conferir("rodapé", termo in t, f"não encontrou {termo!r}")
    # espaço de verdade entre rótulo e valor (ver explicação em testar_cabecalho)
    colados = re.findall(r'class="vsb-footer-contact-label">[^<]+</span>(?!&nbsp;|\s)', html)
    conferir("espaço rótulo/valor", not colados, f"faltou o &nbsp; depois do rótulo: {colados}")

    # minilogo no lugar do nome escrito, com recuo para o nome quando não há logo
    conferir("minilogo", 'class="vsb-footer-logo"' in html, "o rodapé não usa o minilogo")
    conferir("minilogo", "vsb segurança" not in t, "o nome escrito ainda aparece no lugar do logo")
    conferir("minilogo", "LOGO%20PRINCIPAL%20OTIMIZADO.png" in html, "logo do rodapé sem %20 nos espaços")
    h_sem = renderizar(fonte, documento(company="Sem Logo ME"))
    conferir("minilogo", 'class="vsb-footer-logo"' not in h_sem, "renderizou img sem logo cadastrada")
    conferir("minilogo", "Sem Logo ME" in texto(h_sem), "sem logo, faltou o nome da empresa")

    # correção 1: a paginação fica oculta na tela e é revelada no PDF
    bloco = re.search(r'<div class="visible-pdf">(.*?)</div>\s*</td>', html, re.S)
    conferir("paginação só no PDF", bloco is not None, "o bloco de paginação não está em .visible-pdf")
    if bloco:
        conferir("paginação só no PDF", "Página" in bloco.group(1), "o rótulo Página ficou fora do .visible-pdf")
        conferir("paginação só no PDF", 'class="page"' in bloco.group(1) and 'class="topage"' in bloco.group(1),
                 "os contadores ficaram fora do .visible-pdf")
    # as classes que o wkhtmltopdf procura precisam existir exatamente assim
    conferir("contadores", '<span class="page"></span>' in html, "faltou o span class=page")
    conferir("contadores", '<span class="topage"></span>' in html, "faltou o span class=topage")

    # correção 2: faixa em tabela, não em position:absolute
    conferir("faixa do rodapé", "position: absolute" not in fonte, "position:absolute é instável no rodapé do PDF")
    conferir("faixa do rodapé", "vsb-footer-line-accent" in html and "vsb-footer-line-rest" in html,
             "a faixa não virou células de tabela")

    # correção 3: nomes genéricos passaram a ter prefixo do rodapé.
    # Os genéricos são procurados como seletor CSS ("{seletor} {") para não confundir
    # com o nome prefixado, que os contém como sufixo.
    for generico in ("vsb-page-label", "vsb-page-number"):
        conferir("classes com prefixo", not re.search(rf"\.{generico}\s*[{{,]", fonte),
                 f".{generico} é genérico e pode colidir com o formato de impressão")
        conferir("classes com prefixo", f'class="{generico}"' not in fonte,
                 f"ainda usa class={generico!r} no HTML")
    for prefixado in (".vsb-footer-page-label", ".vsb-footer-page-number"):
        conferir("classes com prefixo", prefixado in fonte, f"faltou {prefixado}")

    # correção 4 e 5
    h4 = renderizar(fonte, documento(company='Empresa "Aspas" S/A'))
    conferir("escape", "&#34;" in h4 or "&quot;" in h4, "nome da empresa não escapado no rodapé")
    conferir("CSS morto", "box-shadow:" not in fonte, "sobrou a regra de box-shadow")
    conferir("CSS morto", "@media print" not in fonte, "sobrou o bloco @media print inútil")
    conferir("CNPJ", "CNPJ: 07.452.335/0001-90" in texto(h4), "não mostrou o CNPJ cadastrado")
    conferir("CNPJ", "CNPJ" not in t, "mostrou CNPJ sem o dado cadastrado")


def main():
    cab = CABECALHO.read_text(encoding="utf-8")
    rod = RODAPE.read_text(encoding="utf-8")
    for nome, fonte in (("cabeçalho", cab), ("rodapé", rod)):
        ambiente().from_string(fonte)  # erro de sintaxe falharia aqui, como no salvar
        conferir("render_template", ".__" not in fonte, f"{nome}: o Frappe recusa templates com '.__'")

    testar_cabecalho(cab)
    testar_rodape(rod)

    print()
    if falhas:
        print(f"FALHOU ({len(falhas)}):")
        for f in falhas:
            print(" -", f)
        sys.exit(1)
    print("OK: papel timbrado passou em todos os testes.")


if __name__ == "__main__":
    main()
