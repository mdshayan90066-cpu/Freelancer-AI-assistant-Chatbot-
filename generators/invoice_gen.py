import os
import math
from fpdf import FPDF
from datetime import datetime

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generated_docs")

class InvoicePDF(FPDF):
    """Custom PDF class for professional invoices with digital stamp support."""

    def draw_digital_stamp(self, x, y, radius, text_top, text_bottom, stamp_color=(30, 60, 120)):
        """Draw a circular digital stamp/seal."""
        r, g, b = stamp_color
        # Outer circle
        self.set_draw_color(r, g, b)
        self.set_line_width(1.2)
        self.ellipse(x - radius, y - radius, radius * 2, radius * 2, style="D")
        # Inner circle
        inner = radius * 0.72
        self.set_line_width(0.4)
        self.ellipse(x - inner, y - inner, inner * 2, inner * 2, style="D")

        # Top text (curved simulation with straight text)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(r, g, b)
        tw = self.get_string_width(text_top)
        self.text(x - tw / 2, y - radius * 0.35, text_top)

        # Center text (large)
        self.set_font("Helvetica", "B", 14)
        tw2 = self.get_string_width(text_bottom)
        self.text(x - tw2 / 2, y + 5, text_bottom)

        # Bottom decorative line
        self.set_line_width(0.3)
        self.line(x - radius * 0.5, y + radius * 0.45, x + radius * 0.5, y + radius * 0.45)

        # Stars
        self.set_font("Helvetica", "", 8)
        self.text(x - radius * 0.6, y + radius * 0.15, "*")
        self.text(x + radius * 0.5, y + radius * 0.15, "*")

    def draw_watermark(self, text, alpha_color=(220, 230, 245)):
        """Draw a diagonal watermark across the page."""
        self.set_font("Helvetica", "B", 50)
        self.set_text_color(*alpha_color)
        # Position diagonally
        self.text(30, 180, text)


def generate_invoice_pdf(data: dict) -> tuple:
    os.makedirs(DOCS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    inv_num = data.get("invoice_number", "INV-0001")
    filename = f"invoice_{inv_num}_{timestamp}.pdf"
    filepath = os.path.join(DOCS_DIR, filename)

    pdf = InvoicePDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ─── Watermark ───
    pdf.draw_watermark("ORIGINAL")

    # ─── Header Banner ───
    # A sleek, deep indigo color
    pdf.set_fill_color(31, 41, 55)
    pdf.rect(0, 0, 210, 42, style="F")

    pdf.set_font("Helvetica", "B", 30)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(10)
    pdf.cell(0, 12, "INVOICE", ln=True, align="L", new_x="LMARGIN")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(156, 163, 175)
    pdf.cell(0, 6, f"{inv_num}", ln=True, align="L")

    # Invoice number on right side of banner
    pdf.set_y(10)
    pdf.set_font("Helvetica", "", 10)
    invoice_date = data.get("invoice_date", datetime.now().strftime("%B %d, %Y"))
    due_date = data.get("due_date", "Upon Receipt")
    pdf.cell(0, 6, f"Date: {invoice_date}", ln=True, align="R")
    pdf.set_y(16)
    pdf.cell(0, 6, f"Due: {due_date}", ln=True, align="R")

    pdf.ln(20)

    # ─── Sender (FROM) Block ───
    pdf.set_text_color(30, 60, 120)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(95, 5, "FROM", ln=False)
    pdf.cell(95, 5, "BILL TO", ln=True)

    pdf.set_text_color(50, 50, 50)
    pdf.set_font("Helvetica", "B", 11)
    # Auto-fetch client from DB if available
    client_name_input = data.get("client_name", "Client")
    client_address_input = data.get("client_address", "")
    client_email_input = data.get("client_email", "")
    
    try:
        import database
        clients = database.get_all_clients()
        for c in clients:
            if c["name"].lower() == client_name_input.lower():
                client_name_input = c["name"]
                client_address_input = c.get("address") or client_address_input
                client_email_input = c.get("email") or client_email_input
                break
    except Exception as e:
        print("Could not fetch client data from DB:", e)

    sender_name = data.get("sender_name", data.get("freelancer_name", "Freelancer"))
    pdf.cell(95, 6, sender_name, ln=False)
    pdf.cell(95, 6, client_name_input, ln=True)

    pdf.set_font("Helvetica", "", 9)
    sender_address = data.get("sender_address", "")
    client_address = client_address_input
    sender_email = data.get("sender_email", "")
    client_email = client_email_input

    for s_line, c_line in [
        (sender_address, client_address),
        (sender_email, client_email),
    ]:
        pdf.cell(95, 5, str(s_line), ln=False)
        pdf.cell(95, 5, str(c_line), ln=True)

    pdf.ln(10)

    # ─── Invoice Details Bar ───
    pdf.set_fill_color(240, 243, 250)
    pdf.set_draw_color(30, 60, 120)
    y_bar = pdf.get_y()
    pdf.rect(10, y_bar, 190, 12, style="DF")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(30, 60, 120)
    pdf.set_y(y_bar + 2)
    pdf.cell(47, 8, f"  Invoice #: {inv_num}", align="L")
    pdf.cell(47, 8, f"Date: {invoice_date}", align="C")
    pdf.cell(47, 8, f"Due: {due_date}", align="C")
    project = data.get("project_name", "N/A")
    pdf.cell(49, 8, f"Project: {project}", align="R")
    pdf.ln(14)

    # ─── Line Items Table ───
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(30, 60, 120)
    pdf.set_text_color(255, 255, 255)
    col_widths = [80, 28, 35, 22, 25]
    headers = ["Description", "Hours", "Rate", "Tax%", "Amount"]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 9, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(50, 50, 50)
    subtotal = 0
    tax_pct = float(data.get("tax_percentage", 0))

    line_items = data.get("line_items", [])
    if isinstance(line_items, list):
        for idx, item in enumerate(line_items):
            if isinstance(item, dict):
                desc = str(item.get("description", "Service"))
                hours = float(item.get("hours", 0))
                rate = float(item.get("rate", 0))
                amount = hours * rate
                subtotal += amount

                # Alternate row color
                if idx % 2 == 0:
                    pdf.set_fill_color(248, 249, 252)
                else:
                    pdf.set_fill_color(255, 255, 255)

                pdf.cell(col_widths[0], 8, desc, border=1, fill=True)
                pdf.cell(col_widths[1], 8, f"{hours:.1f}", border=1, align="C", fill=True)
                pdf.cell(col_widths[2], 8, f"${rate:.2f}", border=1, align="C", fill=True)
                pdf.cell(col_widths[3], 8, f"{tax_pct}%", border=1, align="C", fill=True)
                pdf.cell(col_widths[4], 8, f"${amount:.2f}", border=1, align="C", fill=True)
                pdf.ln()

    pdf.ln(6)

    # ─── Totals Block ───
    tax_amount = subtotal * (tax_pct / 100)
    total = subtotal + tax_amount

    x_totals = 120
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(x_totals)
    pdf.cell(45, 7, "Subtotal:", align="R")
    pdf.cell(25, 7, f"${subtotal:.2f}", align="R")
    pdf.ln()

    if tax_pct > 0:
        pdf.set_x(x_totals)
        pdf.cell(45, 7, f"Tax ({tax_pct}%):", align="R")
        pdf.cell(25, 7, f"${tax_amount:.2f}", align="R")
        pdf.ln()

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 60, 120)
    pdf.set_x(x_totals)
    pdf.cell(45, 10, "TOTAL DUE:", align="R")
    pdf.cell(25, 10, f"${total:.2f}", align="R")
    pdf.ln(14)

    # ─── Payment Details ───
    payment_details = data.get("freelancer_payment_details", "")
    if payment_details:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(30, 60, 120)
        pdf.cell(0, 6, "PAYMENT DETAILS", ln=True)
        pdf.set_draw_color(30, 60, 120)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 100, pdf.get_y())
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 5, str(payment_details))
        pdf.ln(4)

    # ─── Notes ───
    notes = data.get("notes", "")
    if notes:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 5, f"Notes: {notes}")
        pdf.ln(4)

    # ─── Digital Stamp ───
    stamp_y = pdf.get_y() + 5
    if stamp_y > 248:
        pdf.add_page()
        stamp_y = 50
    pdf.draw_digital_stamp(
        x=170, y=stamp_y, radius=22,
        text_top=str(sender_name).upper(),
        text_bottom="ORIGINAL",
        stamp_color=(31, 41, 55)
    )

    # ─── Footer ───
    pdf.set_y(-30)
    pdf.set_draw_color(30, 60, 120)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 4, f"Generated by FreelanceAI on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", align="C", ln=True)
    pdf.cell(0, 4, "Thank you for your business!", align="C")

    pdf.output(filepath)
    return filepath, total
