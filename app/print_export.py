"""High-fidelity browser print export for Streamlit pages.

The browser is the authoritative renderer for page-replica PDF export. This helper
opens the browser print dialog so the PDF preserves the same cards, Plotly charts,
tables and typography as the live Streamlit page. Print-specific CSS lives in
app.ui_theme.apply_professional_theme().
"""
from __future__ import annotations

import html

import streamlit.components.v1 as components


def page_pdf_button(label: str = "Exportar página a PDF") -> None:
    """Render a compact button that prints the parent Streamlit page.

    The user can choose "Guardar como PDF" in the browser print dialog. This avoids
    maintaining a second visual renderer that can drift from the web product.
    """
    safe_label = html.escape(label)
    components.html(
        f"""
        <div style="display:flex;justify-content:flex-end;width:100%;padding:0;margin:0;">
          <button id="fps-print-page" onclick="window.parent.print()" style="
              width:100%;
              min-height:38px;
              border:1px solid #D8E1E8;
              border-radius:9px;
              background:#FFFFFF;
              color:#172B3A;
              font:600 14px 'Segoe UI',Arial,sans-serif;
              cursor:pointer;
              padding:8px 14px;
          ">{safe_label}</button>
        </div>
        """,
        height=46,
        scrolling=False,
    )
