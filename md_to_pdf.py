import sys
import os
import markdown2
from weasyprint import HTML, CSS
from tqdm import tqdm

def convert_md_to_pdf(md_path, pdf_path):
    if not os.path.exists(md_path):
        print(f"Error: {md_path} not found.")
        return

    print(f"Reading {md_path}...")
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Define CSS for professional PDF output
    css_content = """
    @page {
        size: A4;
        margin: 2cm;
        @bottom-right {
            content: counter(page);
        }
    }
    body {
        font-family: "Helvetica Neue", Helvetica, Arial, "PingFang TC", "Microsoft JhengHei", sans-serif;
        line-height: 1.6;
        color: #333;
    }
    h1, h2, h3, h4 {
        color: #2c3e50;
        margin-top: 1.5em;
        page-break-after: avoid;
    }
    code {
        font-family: "Menlo", "Monaco", "Courier New", monospace;
        background-color: #f8f9fa;
        padding: 2px 4px;
        border-radius: 3px;
        font-size: 0.9em;
    }
    pre {
        background-color: #f8f9fa;
        padding: 1em;
        border-radius: 5px;
        border: 1px solid #e9ecef;
        overflow: hidden;
        white-space: pre-wrap;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 1em 0;
    }
    th, td {
        border: 1px solid #dee2e6;
        padding: 8px;
        text-align: left;
    }
    th {
        background-color: #f1f3f5;
    }
    img {
        max-width: 100%;
        height: auto;
    }
    hr {
        border: 0;
        border-top: 1px solid #eee;
        margin: 2em 0;
        page-break-after: always;
    }
    """

    print("Converting Markdown to HTML...")
    # Using 'fenced-code-blocks' and 'tables' extras for high-quality rendering
    html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks", "tables", "break-on-newline"])
    
    # Wrap in a basic HTML structure
    full_html = f"""
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    print(f"Generating PDF: {pdf_path} (this may take a few minutes for 680 pages)...")
    HTML(string=full_html).write_pdf(pdf_path, stylesheets=[CSS(string=css_content)])
    print(f"Success! PDF saved to {pdf_path}")

if __name__ == "__main__":
    input_md = "translated_output.md"
    output_pdf = "translated_micropython_docs.pdf"
    
    if len(sys.argv) > 1:
        input_md = sys.argv[1]
    if len(sys.argv) > 2:
        output_pdf = sys.argv[2]
        
    convert_md_to_pdf(input_md, output_pdf)
