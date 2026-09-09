import re
import logging

_logger = logging.getLogger(__name__)

try:
    import markdown
except ImportError:
    markdown = None
    _logger.warning("Libreria 'markdown' no instalada. La conversion de texto usara fallback.")

try:
    from markdownify import markdownify as md
except ImportError:
    md = None
    _logger.warning("Libreria 'markdownify' no instalada. La conversion de texto usara fallback.")


def trello_markdown_to_html(text):
    if not text:
        return ""
    if markdown:
        html = markdown.markdown(text, extensions=['fenced_code', 'nl2br', 'tables'])
        return html
    else:
        from odoo.tools import plaintext2html
        return plaintext2html(text)


def html_to_trello_markdown(html_content):
    if not html_content:
        return ""
    if md:
        text = md(html_content, heading_style="ATX", default_title=True)
        return text.replace('  \n', '\n').strip()
    else:
        text = html_content
        # Bloques de codigo (manejar con o sin <code> anidado)
        text = re.sub(r'<pre.*?>(?:<code.*?>)?(.*?)(?:</code>)?</pre>', r'\n```\n\1\n```\n', text, flags=re.DOTALL)
        # Codigo en linea
        text = re.sub(r'<code.*?>(.*?)</code>', r'`\1`', text, flags=re.DOTALL)
        # Negritas y Cursivas
        text = re.sub(r'<b.*?>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
        text = re.sub(r'<strong.*?>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
        text = re.sub(r'<i.*?>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)
        text = re.sub(r'<em.*?>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
        
        # Citas (Blockquotes)
        text = re.sub(r'<blockquote.*?>(.*?)</blockquote>', r'\n> \1\n', text, flags=re.DOTALL)
        
        # Listas (Ordenadas y Desordenadas)
        def replace_ol(m):
            return '\n\n' + re.sub(r'<li.*?>(.*?)</li>', r'1. \1\n', m.group(1), flags=re.DOTALL) + '\n'
            
        def replace_ul(m):
            return '\n\n' + re.sub(r'<li.*?>(.*?)</li>', r'- \1\n', m.group(1), flags=re.DOTALL) + '\n'

        text = re.sub(r'<ol.*?>(.*?)</ol>', replace_ol, text, flags=re.DOTALL)
        text = re.sub(r'<ul.*?>(.*?)</ul>', replace_ul, text, flags=re.DOTALL)
        
        # Huerfanos
        text = re.sub(r'<li.*?>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL)
        
        # Saltos de linea y parrafos
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = text.replace('</p>', '\n\n')
        text = text.replace('</div>', '\n')
        
        # Quitar el resto de etiquetas HTML
        text = re.sub(r'<.*?>', ' ', text)
        
        # Limpiar multiples espacios (pero no si están dentro de código)
        # Una limpieza simple está bien para el fallback
        return text.strip()
