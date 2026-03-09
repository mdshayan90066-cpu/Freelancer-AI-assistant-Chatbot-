import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generators.invoice_gen import generate_invoice_pdf

data = {
    "client_name": "AlphaVoice",
    "project_name": "Voice Backend",
    "invoice_number": "INV-004",
    "line_items": [{"description": "Setup", "hours": 1, "rate": 1200}],
    "tax_percentage": 5
}

try:
    generate_invoice_pdf(data)
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
