"""
Compile docs/technical_report.md into docs/technical_report.pdf
using Headless Chrome PDF printing.
"""
import os
import subprocess
import re

MD_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "technical_report.md")
HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "technical_report.html")
PDF_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "technical_report.pdf")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

with open(MD_PATH, "r", encoding="utf-8") as f:
    text = f.read()

try:
    import markdown
    html_body = markdown.markdown(text, extensions=["tables", "fenced_code"])
except ImportError:
    # simple markdown fallback
    html_body = f"<pre>{text}</pre>"

html_content = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>FloodLens AI Technical Report</title>
<style>
  @page {
    size: letter;
    margin: 14mm 16mm 14mm 16mm;
  }
  body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 8.8pt;
    line-height: 1.4;
    color: #111827;
  }
  h1 { font-size: 15pt; color: #0f172a; margin-top: 0; margin-bottom: 4px; line-height: 1.2; text-align: center; }
  .authors { text-align: center; font-size: 8.5pt; color: #475569; margin-bottom: 12px; }
  h2 { font-size: 11pt; color: #1e3a8a; border-bottom: 1px solid #cbd5e1; padding-bottom: 2px; margin-top: 10px; margin-bottom: 4px; page-break-after: avoid; }
  h3 { font-size: 9.5pt; color: #0f172a; margin-top: 8px; margin-bottom: 3px; page-break-after: avoid; }
  p { margin-bottom: 5px; text-align: justify; }
  table { width: 100%; border-collapse: collapse; margin: 6px 0; font-size: 8pt; page-break-inside: avoid; }
  th, td { border: 1px solid #cbd5e1; padding: 3px 5px; text-align: left; }
  th { background-color: #f1f5f9; font-weight: 600; color: #0f172a; }
  code { font-family: Consolas, Monaco, monospace; font-size: 8pt; background: #f1f5f9; padding: 1px 3px; border-radius: 2px; }
  pre { background: #f8fafc; border: 1px solid #e2e8f0; padding: 5px; font-size: 7.5pt; overflow-x: auto; page-break-inside: avoid; margin-bottom: 6px; }
  ul, ol { margin-top: 2px; margin-bottom: 5px; padding-left: 18px; }
  li { margin-bottom: 1.5px; }
  blockquote { border-left: 3px solid #3b82f6; margin: 5px 0; padding-left: 8px; color: #4b5563; font-style: italic; font-size: 8.5pt; }
  hr { border: none; border-top: 1px solid #e2e8f0; margin: 10px 0; }
</style>
</head>
<body>
""" + html_body + """
</body>
</html>"""

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html_content)

abs_html = os.path.abspath(HTML_PATH)
abs_pdf = os.path.abspath(PDF_PATH)

cmd = [
    CHROME,
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--run-all-compositor-stages-before-draw",
    f"--print-to-pdf={abs_pdf}",
    "--no-pdf-header-footer",
    f"file:///{abs_html.replace(os.sep, '/')}"
]

res = subprocess.run(cmd, capture_output=True, text=True)
print("Chrome return code:", res.returncode)
if os.path.exists(abs_pdf):
    print("PDF generated successfully:", abs_pdf)
    print("PDF Size:", os.path.getsize(abs_pdf), "bytes")
