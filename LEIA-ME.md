# Orçamento VSB em português — instalado no ERP

Formato de impressão do Orçamento em português, com a logo e a identidade da VSB, mais as
correções do papel timbrado. **Instalado e ativo** em `portal.vsbseguranca.com.br` desde
30/09/2026.

- Formato: **Orçamento VSB** (`/app/print-format/Orçamento VSB`) — é o **padrão** do
  Orçamento, então o botão Imprimir, o PDF e o e-mail já usam ele.
- Papel timbrado: **VSB TEMPLET - PERSONALIZADO** (`/app/letter-head`) — cabeçalho e
  rodapé corrigidos; cópia do original em `timbrado/backup-20260930/`.
- Ambiente: ERPNext 16.36.0 / Frappe 16.35.0 em Docker (`/opt/vsb-erpnext`), app próprio `vsb_core`.

- Pedido de Venda, Fatura de Venda, Guia de Remessa e Pedido de Compra: formatos
  **Pedido de Venda VSB**, **Fatura de Venda VSB**, **Guia de Remessa VSB** e **Pedido de
  Compra VSB**, padrão de cada documento desde 30/09/2026 (seção própria abaixo).

## Arquivos

| Arquivo | O que é |
|---|---|
| `orcamento_vsb.html` | O formato de impressão do Orçamento (Jinja) |
| `documentos_vsb.html` | O formato dos outros quatro documentos (um arquivo só, instalado nos quatro) |
| `testes/testar_documentos_vsb.py` | Testes dos quatro documentos |
| `timbrado/cabecalho.html` | Cabeçalho do papel timbrado (campo Content) |
| `timbrado/rodape.html` | Rodapé do papel timbrado (campo Footer) |
| `timbrado/backup-20260930/` | Como estavam antes, para restaurar |
| `testes/testar_orcamento_vsb.py` | Testes do formato |
| `testes/testar_timbrado.py` | Testes do papel timbrado |
| `testes/saida/orcamento_vsb_PDF_servidor.pdf` | PDF gerado no servidor |

## Por que os orçamentos saíam em inglês

Não era configuração de idioma — o ERP já está em pt-BR. O defeito estava no formato
padrão **"Quotation with Item Image"**, que vem com o ERPNext v16:

| O que aparecia | Causa |
|---|---|
| `Customer Name:`, `Bill to:` | Texto fixo em inglês no template, sem passar pelo tradutor. |
| `Quotation:`, `Posting Date:`, `Valid Till:`, `Sub Total:`, `In Words:`, `Grand Total:` | Passam pelo tradutor, mas com os dois-pontos dentro da chave. O pt-BR do ERPNext só tem "Posting Date", sem os dois-pontos. |
| Coluna `Não` | O template usa "No" (número), que o pt-BR traduz como negação. |
| `1 Unit`, `Brazil` | Dados do cadastro, impressos sem tradução. |
| `ICMS 19% @ 19.0 (19%)` | A descrição do imposto já traz "@ 19.0" e o template ainda acrescentava "(19%)". |
| `BRL Quatrocentos E Dezasseis apenas.` | O Frappe passa "pt-BR" ao num2words, que não reconhece o código e usa o português de Portugal. E descrevia o **total arredondado** (R$ 416,00), não o total impresso (R$ 416,50). |

Os outros formatos novos do v16 têm o mesmo defeito: "Quotation Standard" e os
"Standard"/"with Item Image" de Pedido de Venda, Fatura de Venda e Guia de Remessa.

## O que o formato novo faz

O papel timbrado **"VSB TEMPLET - PERSONALIZADO"** já imprime a logo, a empresa, o
endereço, o rótulo "ORÇAMENTO", o número, a emissão, a validade, a barra de contatos e,
no rodapé, a paginação. O formato antigo **repetia** número, emissão e validade no corpo.

O corpo novo não repete nada disso. Ele começa no cliente e traz:

- **Cliente**: nome, CNPJ/CPF (quando cadastrado) e endereço;
- **Contato**: nome, telefone e e-mail — que antes não saíam no papel;
- **Itens**: nº, nome, código (só quando o nome ainda não o mostra), descrição (só quando
  acrescenta algo), quantidade com a unidade em sigla brasileira, preço unitário e total;
- **Totais**: subtotal, desconto (só quando existe), impostos com a descrição limpa,
  **Total geral** em destaque e, quando o arredondamento está ligado e muda o valor,
  a linha "Total a pagar (arredondado)";
- **Valor total por extenso**, em reais, calculado do Total geral impresso;
- **Condições de pagamento** com as parcelas, quando houver;
- **Termos e condições**, quando houver;
- **Aceite** com duas assinaturas (só no orçamento válido, nunca em rascunho ou cancelado).

Mesma paleta do timbrado: azul `#063c51`, cobre `#b0774c`, fundo `#f4f7f8`.

## Correções no papel timbrado (30/09/2026)

Sete defeitos no cabeçalho e cinco no rodapé. Os dois primeiros só apareciam no PDF, que
é justamente o que o cliente recebe:

1. **A moldura e a faixa azul do topo não saíam no PDF.** O bloco misturava
   `border-top: 5px` com `border: 1px` e `border-radius`, e o wkhtmltopdf descarta a borda
   inteira nessa combinação — no PDF o cabeçalho saía sem moldura e sem a faixa. Agora a
   borda é uniforme e a faixa é um elemento próprio, recortado pelo canto arredondado.
   Comprovado com três variantes renderizadas pelo próprio gerador.
2. **O PDF terminava com uma página em branco.** A classe `page-break` do ERPNext é
   `page-break-after: always`; aplicada também no último bloco, forçava mais uma página só
   com timbrado e rodapé. Agora ela só entra entre blocos.
3. **"PÁGINA /" aparecia vazio na tela.** Quem escreve os números é o wkhtmltopdf, e só ao
   gerar o PDF. O bloco agora é `.visible-pdf`: oculto na tela, revelado no PDF.
4. **Rótulo do documento em inglês.** O timbrado só conhecia Orçamento, Pedido e Fatura;
   uma Guia de Remessa saía "Delivery Note". Agora há treze tipos em português e o último
   recurso passa pelo tradutor.
5. **Nome da empresa e endereço da logo sem tratamento.** O Jinja do Frappe não tem
   autoescape: aspas no nome da empresa quebravam o atributo `alt`. E o arquivo da logo tem
   espaços no nome ("LOGO PRINCIPAL OTIMIZADO.png"), agora convertidos para `%20`.
6. **Endereço mal montado.** Sem cidade, saía " - Ceará" com um traço solto e sem quebra de
   linha. Cidade, UF e CEP passaram a ser montados juntos.
7. **Sem logo, a coluna de 28% ficava vazia.** Agora ela some e as outras crescem.
8. **Faixa cobre do rodapé** saiu de `position: absolute` para células de tabela, que o
   wkhtmltopdf trata de forma previsível no rodapé.
9. **Classes genéricas da paginação** (`vsb-page-label`, `vsb-page-number`) ganharam prefixo
   do rodapé, para o formato de impressão não as redefinir sem querer.
10. Saiu o CSS morto (uma regra que anulava uma sombra inexistente) e a barra de contatos
    passou a não aparecer quando não há nenhum contato cadastrado.
11. **Rótulo colado no valor.** Ao compactar o HTML eu removi os espaços e a separação
    passou a vir só de uma margem de CSS: na tela parecia certo, mas ao copiar saía
    `SITEvsbseguranca.com.br`, e o mesmo acontecia ao extrair o texto do PDF. Agora há um
    `&nbsp;` de verdade entre o rótulo e o valor, no cabeçalho e no rodapé.
12. **Minilogo no rodapé** no lugar do nome "vsb segurança" escrito. Limite de 26px de
    altura: abaixo disso a assinatura "SOLUÇÕES TÉCNICAS" do arquivo vira um borrão; acima,
    o rodapé cresce e come área do documento. Sem logo cadastrada, volta o nome escrito.

Uma armadilha ficou documentada dentro do `orcamento_vsb.html`: a regra `.print-format`
também define as margens do PDF, porque o Frappe lê `margin-top/bottom/left/right` dela.
Não declare `margin-top` nem `margin-bottom` ali — sem elas o wkhtmltopdf mede o timbrado e
reserva o espaço exato; com elas, o mesmo CSS é copiado para dentro do documento do
cabeçalho e empurra o timbrado para fora da página.

## Pedido de Venda, Fatura, Guia de Remessa e Pedido de Compra (30/09/2026)

Os formatos padrão do ERPNext v16 para esses documentos ("... with Item Image") tinham os
mesmos defeitos do orçamento: rótulos em inglês ("Customer Name:", "Invoice Date:",
"Required By:"…), "Não" na coluna de número e o valor por extenso em português de Portugal.

`documentos_vsb.html` é um arquivo só, instalado nos quatro formatos, que se adapta ao tipo
de documento. É a mesma família visual do Orçamento VSB (mesmos blocos, cores, extenso e
faixa "Rascunho — sujeito a alteração"), com a linha dos itens igual à do orçamento.

O que muda por documento (cada item só aparece quando o campo está preenchido):

| Documento | Particularidades |
|---|---|
| Pedido de Venda | Pedido do cliente e data; entrega prevista; local de entrega quando é diferente do endereço de cobrança; parcelas; assinaturas da VSB e "De acordo" do cliente |
| Fatura de Venda | Parcelas; faixa "Devolução — referente a…" nas devoluções; sem assinaturas. O vencimento já sai no papel timbrado |
| Guia de Remessa | Local de entrega; transportadora, veículo, motorista e conhecimento de transporte; "Recebido por — nome e documento" e "Data e assinatura"; faixa de devolução |
| Pedido de Compra | "Fornecedor" em vez de "Cliente"; entrega prevista e "Entregar em" (endereço da VSB); código do produto no fornecedor; assinaturas da VSB e "De acordo" do fornecedor |

Nos impostos de compra, duas correções em relação ao formato oficial, conferidas com o
cálculo do próprio ERPNext:

- imposto marcado como **só para custo do estoque** ("Valuation") não entra no total do
  pedido e **não aparece** no papel;
- imposto **deduzido** ("Deduct") sai com sinal de menos.

No formato oficial, os dois apareciam como se somassem, e as linhas não fechavam com o total.
Exemplo testado: R$ 1.800,00 + ICMS R$ 342,00 − desconto R$ 30,00 = **R$ 2.112,00**, com um
frete de R$ 50,00 que foi só para o custo do estoque.

**Como desfazer:** em `/app/print-format`, abra o formato antigo de cada documento
("Sales Order with Item Image", "Sales Invoice with Item Image", "Delivery Note with Item
Image" e "Purchase Order with Item Image") e clique em **Definir como padrão**.

**Rodapé do timbrado:** em 30/09/2026, às 14:16, o rodapé do "VSB TEMPLET - PERSONALIZADO"
foi removido pela tela do ERP (usuário `vsbfortaleza@gmail.com`). Todos os formatos
imprimem o rodapé quando o timbrado tem um. Sem ele, os PDFs de mais de uma página ficam
sem numeração, porque quem pagina é o rodapé. Se quiser de volta, o conteúdo está em
`timbrado/rodape.html` (campo Footer do timbrado).

## Como conferir

Abra o orçamento `SAL-QTN-2026-00001` → **Imprimir**. Confira:

- [ ] Nenhum texto em inglês
- [ ] "Por extenso: Quatrocentos e dezesseis reais e cinquenta centavos" (e não "Dezasseis")
- [ ] "1 UN" em vez de "1 Unit"
- [ ] "ICMS 19%" sem o "@ 19.0", e sem linha "Desconto (0%)"
- [ ] O número, a emissão e a validade aparecem **uma vez só**, no cabeçalho
- [ ] Botão **PDF**: sai igual à tela, com a logo

O PDF gerado no servidor está em `testes/saida/orcamento_vsb_PDF_servidor.pdf`.

## Como desfazer

Pela interface, em `/app/print-format`: abra "Quotation with Item Image" e clique em
**Definir como padrão**. Nenhum dado de orçamento é alterado.

O estado anterior era: `default_print_format` do Quotation = `Quotation with Item Image`
(Property Setter `Quotation-main-default_print_format`).

## Decisões suas, ainda em aberto

1. **Arredondamento (recomendo desligar).** Está **ligado**: R$ 416,50 gera um Total
   Arredondado de R$ 416,00, e a parcela do orçamento está em R$ 416,00 — R$ 0,50 a menos
   que a soma dos itens. Por isso o formato mostra a linha "Total a pagar (arredondado)":
   esconder isso deixaria o documento mentindo. Para resolver na origem, marque
   **Desativar Arredondamento** em **Padrões Gerais**. A linha desaparece sozinha, e vale
   só para documentos novos.
2. **Descrição do imposto.** Em **Modelo de Encargos e Impostos Sobre Vendas**
   ("Brazil ICMS 19% - VSB"), troque "ICMS 19% @ 19.0" por "ICMS". Os orçamentos novos
   passam a sair "ICMS (19%)". O formato já limpa os antigos.
3. **CNPJ do cliente e da VSB.** Os dois cadastros estão sem CNPJ, então as linhas não
   saem — nem no corpo (cliente), nem no cabeçalho e no rodapé (VSB). Preenchendo o campo
   Tax Id em **Empresa** e no **Cliente**, elas aparecem sozinhas. Para um orçamento
   brasileiro, o CNPJ da VSB no papel é o que mais pesa.
4. **Série de numeração** `SAL-QTN-2026-…`. Se preferir `ORC-2026-…`, mude em
   **Configurações de Nomenclatura de Documentos**. Só vale para os novos.
5. **Outros documentos.** Pedido de Venda, Fatura de Venda e Guia de Remessa têm o mesmo
   defeito. Posso preparar os equivalentes.
6. **Levar para o `vsb_core`.** Hoje o formato está no banco (persiste a reinícios e
   atualizações, e é editável pela interface). Se quiser versionado em código junto com as
   traduções, ele pode virar um arquivo do app — exige rebuild da imagem Docker.
7. **O papel timbrado "Company Letterhead"** continua com o cabeçalho antigo e **sem
   rodapé**. Não é o padrão, então não afeta nada hoje, mas é uma armadilha: se alguém o
   selecionar num documento, perde o rodapé e volta os defeitos do PDF. Posso aplicar o
   mesmo conteúdo nele ou marcá-lo como Desativado — diga qual prefere.
8. **Margem lateral de ~3mm.** O formato mantém as margens laterais do PDF em zero (como o
   template oficial do ERPNext) e o recuo vem do próprio timbrado. Fica bom em tela e por
   e-mail; se for imprimir em papel com frequência, vale subir para ~8mm.

## Testes

```
python -m venv venv
venv\Scripts\python -m pip install jinja2 num2words
set PYTHONIOENCODING=utf-8
venv\Scripts\python testes\testar_orcamento_vsb.py
```

Os testes renderizam o template no mesmo tipo de ambiente Jinja do Frappe v16 (sandbox,
`DebugUndefined`, filtros `len`/`int`→`cint`) e cobrem:

- que o template oficial, com as traduções pt-BR reais, reproduz a tela com defeito;
- que o formato novo não tem nenhum texto em inglês nem repete o papel timbrado;
- 30 variações: desconto, rascunho, cancelado, moeda estrangeira, sem endereço, sem
  contato, com CNPJ, código do item, impostos zerados/inclusos/de valor fixo, parcelas,
  termos, unidades e outras;
- o extenso: 19 casos de regra escritos à mão e 14.427 valores comparados com o
  num2words pt_BR.

Além disso, foi verificado no próprio servidor: o orçamento real pelo fluxo oficial de
impressão, o PDF (1 página) e um caso forçado com 40 itens e imagem (4 páginas), com o
timbrado e o cabeçalho da tabela repetindo e a paginação correta. Nada foi gravado no
orçamento nesse teste.

Na junção entre classes (milhões e milhares), o extenso usa vírgula e só coloca "e" antes
do último grupo quando ele é menor que 100 ou centena redonda: "mil e cem",
"mil, cento e dezesseis", "dois bilhões e quinhentos milhões".
