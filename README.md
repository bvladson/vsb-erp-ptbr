# ERPNext em português de verdade — formatos de impressão da VSB

Formatos de impressão em pt-BR para **ERPNext v16** (Frappe 16), instalados e ativos em
`portal.vsbseguranca.com.br` desde **30/09/2026**: Orçamento, Pedido de Venda, Fatura de
Venda, Guia de Remessa e Pedido de Compra, mais o papel timbrado da empresa.

> O relato técnico completo — defeito por defeito, com a causa de cada um — está em
> **[LEIA-ME.md](LEIA-ME.md)**.

## O problema

Os orçamentos saíam em inglês. A reação natural é procurar a configuração de idioma — mas o
ERP já estava em pt-BR. O defeito estava nos próprios formatos que vêm com o v16, e cada
palavra em inglês tinha uma causa diferente:

| O que aparecia | Por quê |
| --- | --- |
| `Customer Name:`, `Bill to:` | Texto fixo no template, sem passar pelo tradutor |
| `Quotation:`, `Valid Till:`, `Grand Total:` | Passam pelo tradutor, mas com os dois-pontos **dentro** da chave — e o pt-BR só tem a chave sem eles |
| Coluna `Não` | O template usa "No" de *número*; o pt-BR traduz como negação |
| `BRL Quatrocentos E Dezasseis apenas.` | O Frappe passa `pt-BR` ao `num2words`, que não reconhece o código e cai no português de Portugal — e ainda descrevia o total **arredondado**, não o impresso |
| `ICMS 19% @ 19.0 (19%)` | A descrição do imposto já traz `@ 19.0` e o template acrescentava `(19%)` |

Diagnosticar isso exigiu ler o template, o dicionário de tradução e o comportamento do
`num2words` — não bastava traduzir strings.

## O papel timbrado

Sete defeitos no cabeçalho e cinco no rodapé. Os dois piores só apareciam **no PDF**, que é
exatamente o que o cliente recebe:

- **A moldura e a faixa azul sumiam no PDF.** O bloco misturava `border-top: 5px` com
  `border: 1px` e `border-radius`; o wkhtmltopdf descarta a borda inteira nessa combinação.
  Corrigido com borda uniforme e faixa como elemento próprio — comprovado com três variantes
  renderizadas pelo gerador real, não pelo navegador.
- **O PDF terminava com uma página em branco.** A classe `page-break` do ERPNext é
  `page-break-after: always`; aplicada ao último bloco, forçava mais uma página só com
  timbrado e rodapé.
- **`Jinja do Frappe não tem autoescape`**: aspas no nome da empresa quebravam o atributo
  `alt` da logo. E o arquivo da logo tem espaços no nome, agora convertidos para `%20`.

## O que há aqui

| Arquivo | Conteúdo |
| --- | --- |
| `orcamento_vsb.html` | Formato de impressão do Orçamento (Jinja) |
| `documentos_vsb.html` | Formato dos outros quatro documentos, em arquivo único |
| `timbrado/cabecalho.html`, `timbrado/rodape.html` | Papel timbrado corrigido |
| `timbrado/backup-20260930/` | Como estava antes, para restaurar |
| `testes/` | Testes dos formatos e do timbrado, com saída de referência e PDF gerado no servidor |

Os testes comparam a saída renderizada contra referências guardadas, inclusive o PDF gerado
pelo próprio servidor — é a única forma de pegar defeito que só existe no PDF.

## Sobre esta cópia pública

Os dados que aparecem nas saídas de teste são fictícios. O contato de exemplo foi
substituído por `contato@exemplo.com.br`.
