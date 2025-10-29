"""
Test della formattazione Markdown → HTML
"""

from html_templates import format_text_to_html

# Test con vari formati
test_text = """# Riassunto Analisi WhatsApp

Questo è un paragrafo introduttivo con **testo in grassetto** e *testo in corsivo*.

## Partecipanti e Struttura del Gruppo

Il gruppo include i seguenti partecipanti:
- Mario Rossi
- Luigi Bianchi
- **Giuseppe Verdi** (amministratore)

### Dettagli Conversazione

Le conversazioni analizzate coprono il periodo dal 01/01/2025 al 14/10/2025.

#### Eventi Principali

1. Primo messaggio il 01/01/2025
2. Aggiunta di nuovi membri il 15/01/2025
3. Cambio nome gruppo il 20/02/2025

## Contenuti Rilevanti

I messaggi contengono riferimenti a:

* Numeri di telefono: +39 123 456 7890
* Indirizzi email: esempio@test.com
* Link esterni

**Nota importante**: Le informazioni sono state estratte automaticamente.
"""

print("=== TEST CONVERSIONE MARKDOWN -> HTML ===\n")
print("INPUT (Markdown):")
print("-" * 60)
print(test_text)
print("\n" + "=" * 60 + "\n")

print("OUTPUT (HTML):")
print("-" * 60)
html_output = format_text_to_html(test_text)
print(html_output)
print("\n" + "=" * 60)

# Salva un esempio HTML completo
html_full = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Test Formattazione</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #075E54; border-bottom: 3px solid #25D366; padding-bottom: 10px; }}
        h2 {{ color: #128C7E; border-left: 5px solid #25D366; padding-left: 15px; }}
        h3 {{ color: #34B7F1; }}
        h4 {{ color: #666; }}
        p {{ line-height: 1.6; margin-bottom: 15px; }}
        ul, ol {{ margin: 15px 0; padding-left: 30px; }}
        li {{ margin-bottom: 8px; }}
        strong {{ color: #075E54; font-weight: 600; }}
    </style>
</head>
<body>
    {html_output}
</body>
</html>"""

with open("test_output.html", "w", encoding="utf-8") as f:
    f.write(html_full)

print("\n✓ File di test creato: test_output.html")
print("  Apri il file nel browser per vedere il risultato formattato!")
