import os
import json
from openai import OpenAI
from dotenv import load_dotenv

def get_ai_client():
    load_dotenv(override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY environment variable not set.")
        return None
    return OpenAI(api_key=api_key)

# Global memory
conversation_history = []
current_intent = None
extracted_data = {}

def analyze_intent_and_extract(message: str, current_state: dict = None):
    client = get_ai_client()
    if not client:
        return {"intent": "unknown", "response": "API Key not configured. Please check your .env file."}

    system_instruction = """
    The freelancer can perform actions to control the entire application architecture:
    1. 'proposal' - Generate a project proposal.
       Required fields to extract over time: client_name, project_title, project_description, deliverables, timeline, freelancer_name.
       Optional: budget, rate, skills, introduction, project_understanding, proposed_approach, pricing, terms, closing, project_id.
    2. 'invoice' - Generate an invoice.
       Required fields: client_name, project_name, invoice_number, invoice_date, due_date, line_items (list of objects with description, hours, rate), freelancer_payment_details.
       Optional: tax_percentage, notes, project_id.
    3. 'receipt' - Generate a payment receipt.
       Required fields: client_name, amount_paid.
       Optional fields: project_name, receipt_number, payment_method, receipt_date, freelancer_name, project_id.
    4. 'reminder' - Generate and send a payment reminder.
       Required fields: client_name, invoice_number, amount_outstanding, original_due_date, overdue_days, freelancer_name, contact_details.
       Optional: project_id.
    5. 'contract' - Generate a formal legal statement of work or independent contractor agreement.
       Required fields: client_name, project_name, date, services_desc, compensation, freelancer_name.
       Optional: clause_confidentiality, clause_ip, clause_termination.
    6. 'add_client' - Add a new client to the system.
       Required fields: name. Optional fields: email, phone, company, address, notes, due_amount (default 0).
    7. 'mark_paid' - Mark an invoice as paid.
       Required fields: invoice_number.
    8. 'query' - Query database (e.g. "show unpaid invoices", "mark invoice 1042 as paid").
       Required fields: query_type (e.g., 'show_unpaid', 'mark_paid', 'client_history', 'stats'), target_id (e.g., invoice number or client name).
    9. 'delete_receipt' - Delete a generated receipt.
       Required fields: receipt_id (the numeric ID of the receipt).

    You will be provided with the current state (ongoing intent and previously extracted data).
    If the user's input is part of the ongoing intent, update the extracted data.
    If it's a new request, determine the new intent.
    If information is missing for the intent, formulate a natural conversational response asking for it. If everything is present, set ready_for_execution to true.

    OUTPUT FORMAT MUST BE VALID JSON:
    {
        "intent": "proposal" | "invoice" | "receipt" | "reminder" | "contract" | "add_client" | "mark_paid" | "query" | "delete_receipt" | "general_chat",
        "extracted_data": { ... dict of extracted fields ... },
        "missing_fields": ["list", "of", "missing", "required", "fields"],
        "ready_for_execution": boolean,
        "response": "Your conversational response to the user"
    }
    """

    prompt = f"""
    Current State: {json.dumps(current_state if current_state else {})}
    User Message: {message}

    Process the user message and output the requested JSON structure.
    For line_items in invoices, try to parse text like "12 hours at $80 for design" into {{"description": "design", "hours": 12, "rate": 80}}.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return {
            "intent": "error",
            "extracted_data": {},
            "missing_fields": [],
            "ready_for_execution": False,
            "response": f"Sorry, I encountered an error analyzing your request: {str(e)}"
        }

def generate_reminder_text(data: dict) -> str:
    client = get_ai_client()
    if not client:
        return "Warning: AI client not configured. Cannot generate reminder text."

    overdue_days = int(data.get("overdue_days", 0))
    tone = "gentle" if overdue_days <= 7 else "firm" if overdue_days <= 21 else "urgent"

    tone_instructions = {
        "gentle": "Friendly reminder assuming the client forgot. 1-7 days overdue.",
        "firm": "Direct but professional message requesting prompt payment. 8-21 days overdue.",
        "urgent": "Professional but strict reminder mentioning possible consequences such as late fees or work pause. 22+ days overdue."
    }

    prompt = f"""
    Write a payment reminder email for a freelancer to send to their client.
    Client Name: {data.get("client_name")}
    Invoice Number: {data.get("invoice_number")}
    Amount Outstanding: {data.get("amount_outstanding")}
    Original Due Date: {data.get("original_due_date")}
    Overdue Days: {overdue_days}
    Freelancer Name: {data.get("freelancer_name")}
    Contact Details: {data.get("contact_details")}

    Tone: {tone.upper()} - {tone_instructions[tone]}

    Write ONLY the body of the email. No Subject lines. Be professional.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating reminder text: {e}")
        return f"Dear {data.get('client_name')},\n\nThis is a reminder that invoice #{data.get('invoice_number')} for {data.get('amount_outstanding')} was due on {data.get('original_due_date')} and is now {overdue_days} days overdue.\n\nPlease process this payment as soon as possible.\n\nBest,\n{data.get('freelancer_name')}"

def generate_proposal_sections(data: dict) -> dict:
    client = get_ai_client()
    if not client:
        return data

    prompt = f"""
    You are an expert proposal writer for freelancers.
    Given the rough data provided, generate professional, natural-sounding content for the standard proposal sections.

    Input:
    Client Name: {data.get('client_name', 'Client')}
    Project Title: {data.get('project_title', 'Project')}
    Project Description: {data.get('project_description', '')}
    Deliverables: {data.get('deliverables', '')}
    Timeline: {data.get('timeline', '')}
    Pricing/Rate: {data.get('rate', '')} {data.get('budget', '')}
    Freelancer Name: {data.get('freelancer_name', 'Freelancer')}
    Skills/Background: {data.get('skills', '')}

    Generate a JSON object with string keys:
    - introduction
    - project_understanding
    - proposed_approach
    - deliverables_formatted
    - timeline_formatted
    - pricing_formatted
    - terms
    - closing

    OUTPUT MUST BE VALID JSON.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.5,
        )
        sections = json.loads(response.choices[0].message.content)
        data['introduction'] = sections.get('introduction', '')
        data['project_understanding'] = sections.get('project_understanding', '')
        data['proposed_approach'] = sections.get('proposed_approach', '')
        if 'deliverables' not in data or len(str(data.get('deliverables', ''))) < 10:
            data['deliverables'] = sections.get('deliverables_formatted', data.get('deliverables', ''))
        data['terms'] = sections.get('terms', "Standard payment terms apply. 50% upfront, 50% upon completion.")
        data['closing'] = sections.get('closing', "Looking forward to working with you.")
        return data
    except Exception as e:
        print(f"Error generating proposal sections: {e}")
        return data

def process_chat_message(message: str) -> dict:
    global current_intent, extracted_data

    current_state = {
        "intent": current_intent,
        "extracted_data": extracted_data
    }

    ai_response = analyze_intent_and_extract(message, current_state)

    current_intent = ai_response.get("intent", "general_chat")

    new_data = ai_response.get("extracted_data", {})
    if isinstance(new_data, dict):
        for k, v in new_data.items():
            if v:
                extracted_data[k] = v

    ai_response["extracted_data"] = extracted_data

    if ai_response.get("ready_for_execution", False):
        if current_intent == "proposal":
            ai_response["extracted_data"] = generate_proposal_sections(extracted_data)
        elif current_intent == "reminder":
            reminder_text = generate_reminder_text(extracted_data)
            ai_response["extracted_data"]["reminder_text"] = reminder_text
            ai_response["response"] = f"Here is a draft of the reminder email. Would you like me to send it?\n\n---\n{reminder_text}\n---"

    return ai_response

def reset_chat_state():
    global current_intent, extracted_data
    current_intent = None
    extracted_data = {}
