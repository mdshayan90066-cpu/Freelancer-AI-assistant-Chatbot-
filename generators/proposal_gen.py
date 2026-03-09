import os
from fpdf import FPDF
from datetime import datetime

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generated_docs")

def generate_proposal_pdf(data: dict) -> str:
    os.makedirs(DOCS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"proposal_{data.get('client_name', 'client').replace(' ', '_')}_{timestamp}.pdf"
    filepath = os.path.join(DOCS_DIR, filename)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 15, "Project Proposal", ln=True, align="C")
    pdf.ln(5)

    # Project Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 10, data.get("project_title", "Untitled Project"), ln=True, align="C")
    pdf.ln(5)

    # Meta info
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Prepared for: {data.get('client_name', 'Client')}", ln=True)
    pdf.cell(0, 6, f"Prepared by: {data.get('freelancer_name', 'Freelancer')}", ln=True)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%B %d, %Y')}", ln=True)
    pdf.ln(8)

    # Divider
    pdf.set_draw_color(30, 60, 120)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    sections = [
        ("Introduction", data.get("introduction", "")),
        ("Project Understanding", data.get("project_understanding", "")),
        ("Proposed Approach", data.get("proposed_approach", "")),
        ("Deliverables", data.get("deliverables", "")),
        ("Timeline", data.get("timeline", "")),
        ("Pricing", data.get("pricing", data.get("rate", data.get("budget", "To be discussed")))),
        ("Terms & Conditions", data.get("terms", "Standard terms apply.")),
        ("Closing", data.get("closing", "Looking forward to working with you.")),
    ]

    for title, content in sections:
        if not content:
            continue
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 60, 120)
        pdf.cell(0, 10, title, ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 6, str(content))
        pdf.ln(4)

    pdf.output(filepath)
    return filepath
