import os
import json
from typing import Optional
import hashlib
import os as os_mod
import uuid
import datetime
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

import chatbot
import database
from generators.proposal_gen import generate_proposal_pdf
from generators.invoice_gen import generate_invoice_pdf
from generators.contract_gen import generate_contract_pdf
from generators.receipt_gen import generate_receipt_pdf
from email_service import send_reminder_email

app = FastAPI(title="Freelancer Admin Chatbot")

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ─── Models ───

class ChatCommand(BaseModel):
    message: str
    action: Optional[str] = None
    extracted_data: Optional[dict] = None

class RegisterReq(BaseModel):
    name: str
    email: str
    password: str

class LoginReq(BaseModel):
    email: str
    password: str

# ─── Auth Dependency ───

def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()

async def get_current_user(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    user = database.get_user_from_session(session_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return user

async def get_optional_user(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        return database.get_user_from_session(session_id)
    return None

class ClientCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    due_amount: Optional[float] = 0

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    due_amount: Optional[float] = None

class ProjectCreate(BaseModel):
    client_id: int
    name: str
    description: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class EmailDraftRequest(BaseModel):
    client_id: int
    email_type: Optional[str] = "payment_reminder"

class EmailSendRequest(BaseModel):
    to_email: str
    subject: str
    body: str

# ─── Auth & Page Routes ───

def serve_page(filename):
    path = os_mod.path.join(STATIC_DIR, filename)
    with open(path, "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_optional_user(request)
    if user:
        return RedirectResponse(url="/")
    return serve_page("login.html")

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = await get_optional_user(request)
    if user:
        return RedirectResponse(url="/")
    return serve_page("register.html")

@app.post("/api/register")
async def register(req: RegisterReq):
    try:
        salt = uuid.uuid4().hex
        pwd_hash = hash_password(req.password, salt)
        user_id = database.create_user(req.name, req.email, pwd_hash, salt)
        if not user_id:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        session_id = uuid.uuid4().hex
        expires = datetime.datetime.now() + datetime.timedelta(days=7)
        database.create_session(session_id, user_id, expires)
        
        res = JSONResponse({"status": "success"})
        res.set_cookie(key="session_id", value=session_id, httponly=True, max_age=7*24*3600)
        return res
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/login")
async def login(req: LoginReq):
    user = database.get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    pwd_hash = hash_password(req.password, user['salt'])
    if pwd_hash != user['password_hash']:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    session_id = uuid.uuid4().hex
    expires = datetime.datetime.now() + datetime.timedelta(days=7)
    database.create_session(session_id, user['id'], expires)
    
    res = JSONResponse({"status": "success", "user": {"name": user['name']}})
    res.set_cookie(key="session_id", value=session_id, httponly=True, max_age=7*24*3600)
    return res

@app.post("/api/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        database.delete_session(session_id)
    res = JSONResponse({"status": "success"})
    res.delete_cookie("session_id")
    return res

@app.get("/", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    user = await get_optional_user(request)
    if not user: return RedirectResponse(url="/login")
    return serve_page("dashboard.html")

@app.get("/chat", response_class=HTMLResponse)
async def page_chat(request: Request):
    user = await get_optional_user(request)
    if not user: return RedirectResponse(url="/login")
    return serve_page("index.html")

@app.get("/clients", response_class=HTMLResponse)
async def page_clients(request: Request):
    user = await get_optional_user(request)
    if not user: return RedirectResponse(url="/login")
    return serve_page("clients.html")

@app.get("/payments", response_class=HTMLResponse)
async def page_payments(request: Request):
    user = await get_optional_user(request)
    if not user: return RedirectResponse(url="/login")
    return serve_page("payments.html")

@app.get("/invoices", response_class=HTMLResponse)
async def page_invoices(request: Request):
    user = await get_optional_user(request)
    if not user: return RedirectResponse(url="/login")
    return serve_page("invoices.html")

@app.get("/receipts", response_class=HTMLResponse)
async def page_receipts(request: Request):
    user = await get_optional_user(request)
    if not user: return RedirectResponse(url="/login")
    return serve_page("receipts.html")

# ─── Client API ───

@app.get("/api/clients")
async def api_get_clients():
    return JSONResponse(content=database.get_all_clients())

@app.post("/api/clients")
async def api_add_client(client: ClientCreate):
    try:
        cid = database.add_client(client.name, client.email, client.phone,
                                   client.company, client.address, client.notes, client.due_amount)
        return JSONResponse(content={"success": True, "id": cid})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=400)

@app.put("/api/clients/{client_id}")
async def api_update_client(client_id: int, client: ClientUpdate):
    ok = database.update_client(client_id, client.name, client.email, client.phone,
                                 client.company, client.address, client.notes, client.due_amount)
    return JSONResponse(content={"success": ok})

@app.delete("/api/clients/{client_id}")
async def api_delete_client(client_id: int):
    ok = database.delete_client(client_id)
    return JSONResponse(content={"success": ok})

# ─── Project API ───

@app.get("/api/clients/{client_id}/projects")
async def api_get_client_projects(client_id: int):
    projects = database.get_projects_by_client(client_id)
    return JSONResponse(content=projects)

@app.post("/api/projects")
async def api_create_project(project: ProjectCreate):
    try:
        pid = database.create_project(project.client_id, project.name, project.description)
        return JSONResponse(content={"success": True, "id": pid})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=400)

@app.put("/api/projects/{project_id}")
async def api_update_project(project_id: int, project: ProjectUpdate):
    # For now, we only update status via update_project_status if that's all we have, 
    # but I'll implement a general update if needed.
    if project.status:
        database.update_project_status(project_id, project.status)
    # If we need more fields, we'd add update_project to database.py
    return JSONResponse(content={"success": True})

@app.delete("/api/projects/{project_id}")
async def api_delete_project(project_id: int):
    ok = database.delete_project(project_id)
    return JSONResponse(content={"success": ok})

@app.get("/api/projects/{project_id}/invoices")
async def api_get_project_invoices(project_id: int):
    invoices = database.get_invoices_by_project(project_id)
    return JSONResponse(content=invoices)

@app.get("/api/projects/{project_id}/receipts")
async def api_get_project_receipts(project_id: int):
    receipts = database.get_receipts_by_project(project_id)
    return JSONResponse(content=receipts)

# ─── Email API ───

@app.post("/api/draft-email")
async def api_draft_email(req: EmailDraftRequest):
    """AI-drafts an email based on client data and due amount."""
    client = database.get_client_by_id(req.client_id)
    if not client:
        return JSONResponse(content={"success": False, "error": "Client not found"}, status_code=404)

    from openai import OpenAI
    ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    client_name = client.get("name", "Client")
    due = client.get("due_amount", 0)
    email = client.get("email", "")
    company = client.get("company", "")
    notes = client.get("notes", "")

    email_type = req.email_type or "payment_reminder"
    prompt = f"""Draft a professional {email_type.replace('_', ' ')} email for a freelancer to send to their client.

Client Details:
- Name: {client_name}
- Company: {company}
- Email: {email}
- Outstanding Amount Due: ${due:.2f}
- Notes: {notes}

Sender: FreelanceAI Admin (mdshayan90066@gmail.com)

Rules:
- If the due amount is $0, write a friendly check-in email instead of a payment reminder.
- If the due amount is > 0, write a polite but firm payment reminder mentioning the exact amount.
- Keep it professional, concise (under 150 words), and warm.
- Do NOT include a subject line — just the body of the email.
- Sign off as the sender."""

    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        body = response.choices[0].message.content.strip()
        subject = f"Payment Reminder — ${due:.2f} Outstanding" if due > 0 else f"Following Up — {client_name}"
        return JSONResponse(content={
            "success": True,
            "to_email": email,
            "subject": subject,
            "body": body,
            "client_name": client_name,
            "due_amount": due,
        })
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/api/send-email")
async def api_send_email(req: EmailSendRequest):
    """Send an email directly."""
    result = send_reminder_email(req.to_email, req.subject, req.body)
    return JSONResponse(content=result)

# ─── Invoice API ───

@app.get("/api/invoices")
async def api_get_invoices(status: Optional[str] = None):
    invoices = database.get_all_invoices(status)
    return JSONResponse(content=invoices)

@app.put("/api/invoices/{invoice_id}/paid")
async def api_mark_paid(invoice_id: int):
    ok = database.mark_invoice_paid(invoice_id)
    return JSONResponse(content={"success": ok})

# ─── Receipts API ───

@app.get("/api/receipts")
async def api_get_receipts():
    receipts = database.get_all_receipts()
    return JSONResponse(content=receipts)

@app.delete("/api/receipts/{receipt_id}")
async def api_delete_receipt(receipt_id: int):
    ok = database.delete_receipt(receipt_id)
    return JSONResponse(content={"success": ok})

# ─── Stats API ───

@app.get("/api/stats")
async def get_stats():
    try:
        return JSONResponse(content=database.get_stats())
    except Exception as e:
        return JSONResponse(content={"outstanding_revenue": 0, "unpaid_invoices": 0,
                                      "active_projects": 0, "error": str(e)})

# ─── Chat API ───

@app.post("/api/chat")
async def chat_endpoint(cmd: ChatCommand):
    if cmd.action and cmd.extracted_data:
        return handle_action(cmd.action, cmd.extracted_data)
    result = chatbot.process_chat_message(cmd.message)
    intent = result.get("intent", "general_chat")
    ready = result.get("ready_for_execution", False)
    response_data = {
        "intent": intent,
        "response": result.get("response", "I'm not sure how to help with that."),
        "extracted_data": result.get("extracted_data", {}),
        "missing_fields": result.get("missing_fields", []),
        "ready_for_execution": ready,
    }
    if ready and intent in ["proposal", "invoice", "receipt", "contract", "reminder"]:
        response_data["actions"] = get_actions_for_intent(intent)
    return JSONResponse(content=response_data)

def get_actions_for_intent(intent):
    if intent == "proposal":
        return [{"label": "📄 Generate Proposal PDF", "action": "generate_proposal"}]
    elif intent == "invoice":
        return [{"label": "🧾 Generate Invoice PDF", "action": "generate_invoice"}]
    elif intent == "receipt":
        return [{"label": "🧾 Generate Receipt PDF", "action": "generate_receipt"}]
    elif intent == "delete_receipt":
        return [{"label": "🗑️ Delete Receipt", "action": "delete_receipt"}]
    elif intent == "contract":
        return [{"label": "📋 Generate Contract PDF", "action": "generate_contract"}]
    elif intent == "reminder":
        return [{"label": "📧 Send Reminder Email", "action": "send_reminder"}]
    elif intent == "add_client":
        return [{"label": "👥 Add Client", "action": "add_client"}]
    elif intent == "mark_paid":
        return [{"label": "✅ Mark Invoice Paid", "action": "mark_paid"}]
    elif intent == "query":
        return [{"label": "🔍 Run Query", "action": "run_query"}]
    return []

def handle_action(action: str, data: dict):
    try:
        if action == "generate_proposal":
            filepath = generate_proposal_pdf(data)
            filename = os.path.basename(filepath)
            client_name = data.get("client_name", "Client")
            try:
                cid = database.get_or_create_client(client_name)
                # If project_id is in data, use it, else create new
                project_id = data.get("project_id")
                if not project_id:
                    project_id = database.create_project(cid, data.get("project_title", "Project"))
                database.save_proposal(project_id, client_name, data.get("project_title", ""), filepath)
            except Exception as e:
                print(f"DB error: {e}")
            chatbot.reset_chat_state()
            return JSONResponse(content={
                "intent": "proposal_generated",
                "response": f"✅ **Proposal generated!**\nClient: **{client_name}**",
                "download_url": f"/download/{filename}",
                "download_label": f"📥 Download {filename}",
            })

        elif action == "generate_invoice":
            filepath, total = generate_invoice_pdf(data)
            filename = os.path.basename(filepath)
            inv_num = data.get("invoice_number", "INV-0001")
            client_name = data.get("client_name", "Client")
            try:
                database.get_or_create_client(client_name)
                database.save_invoice(
                    inv_num, client_name, data.get("project_name", ""), total, filepath,
                    sender_name=data.get("sender_name", data.get("freelancer_name", "")),
                    sender_address=data.get("sender_address", ""),
                    sender_email=data.get("sender_email", ""),
                    invoice_date=data.get("invoice_date", ""),
                    due_date=data.get("due_date", ""),
                    project_id=data.get("project_id")
                )
            except Exception as e:
                print(f"DB error: {e}")
            chatbot.reset_chat_state()
            return JSONResponse(content={
                "intent": "invoice_generated",
                "response": f"✅ **Invoice #{inv_num} generated!**\nTotal: **${total:.2f}** | Client: **{client_name}**",
                "download_url": f"/download/{filename}",
                "download_label": f"📥 Download {filename}",
            })

        elif action == "generate_receipt":
            filepath, total = generate_receipt_pdf(data)
            filename = os.path.basename(filepath)
            rec_num = data.get("receipt_number", "REC-0001")
            client_name = data.get("client_name", "Client")
            try:
                database.save_receipt(
                    receipt_number=rec_num,
                    client_name=client_name,
                    project_name=data.get("project_name", ""),
                    amount_paid=total,
                    payment_method=data.get("payment_method", "Bank Transfer"),
                    file_path=filepath,
                    receipt_date=data.get("receipt_date", ""),
                    project_id=data.get("project_id")
                )
            except Exception as e:
                print(f"DB error: {e}")
            chatbot.reset_chat_state()
            return JSONResponse(content={
                "intent": "receipt_generated",
                "response": f"✅ **Receipt #{rec_num} generated!**\nAmount: **${total:.2f}** | Client: **{client_name}**",
                "download_url": f"/download/{filename}",
                "download_label": f"📥 Download {filename}",
            })

        elif action == "delete_receipt":
            receipt_id = data.get("receipt_id")
            if receipt_id:
                try:
                    database.delete_receipt(int(receipt_id))
                    chatbot.reset_chat_state()
                    return JSONResponse(content={
                        "intent": "receipt_deleted",
                        "response": f"✅ **Receipt #{receipt_id} deleted successfully!**"
                    })
                except Exception as e:
                    print(f"DB error: {e}")
            return JSONResponse(content={
                "intent": "receipt_delete_failed",
                "response": "❌ Could not delete the receipt. Are you sure you provided a valid receipt ID?"
            })

        elif action == "generate_contract":
            filepath = generate_contract_pdf(data)
            filename = os.path.basename(filepath)
            client_name = data.get("client_name", "Client")
            try:
                cid = database.get_or_create_client(client_name)
                database.create_project(cid, data.get("project_name", "Contract"))
            except Exception as e:
                print(f"DB error: {e}")
            chatbot.reset_chat_state()
            return JSONResponse(content={
                "intent": "contract_generated",
                "response": f"✅ **Contract / SOW generated!**\nParties: **{data.get('freelancer_name','You')}** ↔ **{client_name}**",
                "download_url": f"/download/{filename}",
                "download_label": f"📥 Download {filename}",
            })

        elif action == "send_reminder":
            client_email = data.get("client_email", "")
            if not client_email:
                return JSONResponse(content={"intent": "error",
                    "response": "❌ No client email provided."})
            subject = f"Payment Reminder - Invoice #{data.get('invoice_number', 'N/A')}"
            body = data.get("reminder_text", "Payment reminder.")
            result = send_reminder_email(client_email, subject, body)
            chatbot.reset_chat_state()
            if result["success"]:
                return JSONResponse(content={"intent": "reminder_sent",
                    "response": f"✅ **Reminder sent** to {client_email}!"})
            else:
                return JSONResponse(content={"intent": "error",
                    "response": f"❌ Failed: {result['error']}"})

        elif action == "add_client":
            name = data.get("name")
            if not name:
                return JSONResponse(content={"intent": "error", "response": "Client name is required."})
            try:
                cid = database.add_client(
                    name=name,
                    email=data.get("email"),
                    phone=data.get("phone"),
                    company=data.get("company"),
                    address=data.get("address"),
                    notes=data.get("notes"),
                    due_amount=float(data.get("due_amount", 0))
                )
                chatbot.reset_chat_state()
                return JSONResponse(content={"intent": "client_added", "response": f"✅ **Client Added Successfully!**\nName: {name}"})
            except Exception as e:
                return JSONResponse(content={"intent": "error", "response": f"DB Error: {e}"})

        elif action == "mark_paid":
            inv_num = data.get("invoice_number", "")
            if not inv_num:
                return JSONResponse(content={"intent": "error", "response": "Invoice number required."})
            ok = database.mark_invoice_paid_by_number(inv_num)
            chatbot.reset_chat_state()
            if ok:
                return JSONResponse(content={"intent": "invoice_paid", "response": f"✅ **Invoice #{inv_num} marked as PAID!**"})
            else:
                return JSONResponse(content={"intent": "error", "response": f"❌ Could not find unpaid invoice #{inv_num}."})

        elif action == "run_query":
            q_type = data.get("query_type", "")
            chatbot.reset_chat_state()
            if q_type == "stats":
                st = database.get_stats()
                resp = f"📊 **Dashboard Stats**\n- Outstanding Revenue: ${st['outstanding_revenue']}\n- Total Received: ${st['paid_revenue']}\n- Unpaid Invoices: {st['unpaid_invoices']}\n- Active Projects: {st['active_projects']}"
                return JSONResponse(content={"intent": "query_result", "response": resp})
            elif q_type == "show_unpaid":
                invs = database.get_unpaid_invoices()
                if not invs:
                    return JSONResponse(content={"intent": "query_result", "response": "🎉 Great news! You have **0 unpaid invoices**."})
                lines = [f"- **#{i['invoice_number']}** ({i['client_name']}): ${i['total_amount']}" for i in invs[:5]]
                resp = "📋 **Unpaid Invoices**\n" + "\n".join(lines)
                if len(invs) > 5: resp += f"\n...and {len(invs)-5} more."
                return JSONResponse(content={"intent": "query_result", "response": resp})
            else:
                return JSONResponse(content={"intent": "query_result", "response": f"Query type '{q_type}' is not fully supported yet, but I can see you want info on that!"})

        return JSONResponse(content={"intent": "error", "response": f"Unknown action: {action}"})
    except Exception as e:
        return JSONResponse(content={"intent": "error", "response": f"❌ Error: {str(e)}"}, status_code=500)

# ─── File Download ───

@app.get("/download/{filename}")
async def download_file(filename: str):
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_docs")
    filepath = os.path.join(docs_dir, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, filename=filename, media_type="application/pdf")
    return JSONResponse(content={"error": "File not found"}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
