import os
from datetime import datetime
from fpdf import FPDF

def generate_receipt_pdf(data: dict) -> tuple:
    """Gets extracted data and returns (filepath, total_amount)."""
    
    receipt_number = data.get("receipt_number", f"REC-{datetime.now().strftime('%Y%m%d%H%M')}")
    client_name = data.get("client_name", "Client")
    project_name = data.get("project_name", "")
    amount_paid = float(data.get("amount_paid", 0))
    payment_method = data.get("payment_method", "Bank Transfer")
    receipt_date = data.get("receipt_date", datetime.now().strftime("%Y-%m-%d"))
    
    # Freelancer Details
    sender_name = data.get("sender_name", data.get("freelancer_name", "Your Name"))
    sender_address = data.get("sender_address", "Your Address")
    sender_email = data.get("sender_email", "your@email.com")

    # Look up client in DB to auto-fill details if missing
    import database
    
    clients = database.get_all_clients()
    
    client_address = ""
    client_email = ""
    
    if client_name and clients:
        for c in clients:
            if c["name"].lower() == client_name.lower():
                client_name = c["name"]
                client_address = c.get("address", "") or ""
                client_email = c.get("email", "") or ""
                break

    class PDF(FPDF):
        def header(self):
            # Sleek dark header
            self.set_fill_color(31, 41, 55)
            self.rect(0, 0, 210, 24, 'F')
            self.set_font('Arial', 'B', 24)
            self.set_text_color(255, 255, 255)
            self.set_y(5)
            self.cell(0, 10, 'OFFICIAL RECEIPT', 0, 1, 'R')
            self.ln(12)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, 'Thank you for your business. This is a computer-generated receipt.', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    
    # Sender details
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(100, 8, sender_name, ln=0)
    
    # Receipt Info
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(90, 8, f"Receipt #: {receipt_number}", ln=1, align='R')
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(100, 5, sender_address, ln=0)
    pdf.cell(90, 5, f"Date: {receipt_date}", ln=1, align='R')
    pdf.cell(100, 5, sender_email, ln=1)
    
    pdf.ln(10)
    
    # Billed To
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 8, "Received From:", ln=1)
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, client_name, ln=1)
    if client_address:
        pdf.cell(0, 6, client_address, ln=1)
    if client_email:
        pdf.cell(0, 6, client_email, ln=1)
        
    pdf.ln(15)
    
    # Payment Box
    pdf.set_fill_color(245, 245, 250)
    pdf.set_draw_color(220, 220, 220)
    pdf.cell(0, 40, "", border=1, fill=True, ln=1)
    pdf.set_y(pdf.get_y() - 35)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(60, 8, " Project:", ln=0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, project_name or "General Services", ln=1)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(60, 8, " Payment Method:", ln=0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, payment_method, ln=1)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(60, 8, " Amount Received:", ln=0)
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(16, 185, 129) # Green
    pdf.cell(0, 8, f"${amount_paid:,.2f}", ln=1)
    
    pdf.ln(20)
    
    # Digital Stamp
    self_y = pdf.get_y()
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(16, 185, 129)
    # create a stamp style
    pdf.cell(0, 15, "*** PAID IN FULL ***", align="C", ln=1)
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, f"Payment recorded on {datetime.now().strftime('%B %d, %Y')}", align="C", ln=1)

    # Save
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_docs")
    os.makedirs(docs_dir, exist_ok=True)
    
    filename = f"{receipt_number}.pdf"
    filepath = os.path.join(docs_dir, filename)
    pdf.output(filepath)
    
    # update data with resolved client data
    data["client_name"] = client_name
    data["receipt_number"] = receipt_number
    data["amount_paid"] = amount_paid
    data["payment_method"] = payment_method
    data["receipt_date"] = receipt_date
    data["project_name"] = project_name
    
    return filepath, amount_paid
