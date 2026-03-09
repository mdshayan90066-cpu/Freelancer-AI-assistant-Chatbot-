import os
from fpdf import FPDF
from datetime import datetime

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generated_docs")

def generate_contract_pdf(data: dict) -> str:
    os.makedirs(DOCS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"contract_{data.get('client_name', 'client').replace(' ', '_')}_{timestamp}.pdf"
    filepath = os.path.join(DOCS_DIR, filename)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 15, "STATEMENT OF WORK", ln=True, align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Independent Contractor Agreement", ln=True, align="C")
    pdf.ln(8)

    # Divider
    pdf.set_draw_color(30, 60, 120)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    # Parties
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 8, "1. PARTIES", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 6, f"This Agreement is entered into as of {data.get('date', datetime.now().strftime('%B %d, %Y'))}, by and between:\n\nContractor: {data.get('freelancer_name', 'Freelancer')}\nClient: {data.get('client_name', 'Client')}")
    pdf.ln(6)

    # Scope
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 8, "2. SCOPE OF SERVICES", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 6, f"Project: {data.get('project_name', 'N/A')}\n\n{data.get('services_desc', 'Services to be defined.')}")
    pdf.ln(6)

    # Compensation
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 8, "3. COMPENSATION", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 6, str(data.get("compensation", "To be agreed upon.")))
    pdf.ln(6)

    # Optional clauses
    clause_num = 4
    optional_clauses = [
        ("clause_confidentiality", "CONFIDENTIALITY", "Both parties agree to maintain the confidentiality of any proprietary information shared during the course of this engagement. Neither party shall disclose such information to third parties without prior written consent."),
        ("clause_ip", "INTELLECTUAL PROPERTY", "All work product created by the Contractor under this Agreement shall be the exclusive property of the Client upon full payment. The Contractor retains no rights to the deliverables."),
        ("clause_termination", "TERMINATION", "Either party may terminate this Agreement with 14 days written notice. In the event of termination, the Client shall compensate the Contractor for all work completed to date."),
    ]

    for key, title, default_text in optional_clauses:
        text = data.get(key, default_text)
        if text:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(30, 60, 120)
            pdf.cell(0, 8, f"{clause_num}. {title}", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 6, str(text))
            pdf.ln(6)
            clause_num += 1

    # Signature block
    pdf.ln(12)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 8, "SIGNATURES", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, f"Contractor: {data.get('freelancer_name', '_________________')}")
    pdf.cell(95, 6, f"Client: {data.get('client_name', '_________________')}")
    pdf.ln(10)
    pdf.cell(95, 6, "Signature: _________________")
    pdf.cell(95, 6, "Signature: _________________")
    pdf.ln(8)
    pdf.cell(95, 6, f"Date: {data.get('date', '_________________')}")
    pdf.cell(95, 6, f"Date: {data.get('date', '_________________')}")

    pdf.output(filepath)
    return filepath
