import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "freelancer.db")

@contextmanager
def get_db_conn():
    # check_same_thread=False is important for async apps like FastAPI
    # busy_timeout (ms) helps handle concurrent writes in WAL mode
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_db():
    # Deprecated: use with get_db_conn() as conn instead
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_conn() as conn:
        c = conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            company TEXT,
            address TEXT,
            notes TEXT,
            due_amount REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            client_name TEXT,
            project_title TEXT,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE,
            client_name TEXT,
            project_name TEXT,
            project_id INTEGER,
            total_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'unpaid',
            file_path TEXT,
            sender_name TEXT,
            sender_address TEXT,
            sender_email TEXT,
            invoice_date TEXT,
            due_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            client_name TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'sent',
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_number TEXT UNIQUE,
            client_name TEXT,
            project_name TEXT,
            project_id INTEGER,
            amount_paid REAL DEFAULT 0,
            payment_method TEXT,
            file_path TEXT,
            receipt_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            salt TEXT
        );
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER,
            expires_at TIMESTAMP
        );
        """)
        conn.commit()

# ─── Client CRUD ───

def get_all_clients():
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM clients ORDER BY created_at DESC")
        return [dict(r) for r in c.fetchall()]

def get_client_by_id(client_id):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        row = c.fetchone()
        return dict(row) if row else None

def add_client(name, email=None, phone=None, company=None, address=None, notes=None, due_amount=0):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO clients (name, email, phone, company, address, notes, due_amount) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (name, email, phone, company, address, notes, due_amount))
        conn.commit()
        return c.lastrowid

def update_client(client_id, name=None, email=None, phone=None, company=None, address=None, notes=None, due_amount=None):
    with get_db_conn() as conn:
        c = conn.cursor()
        fields = []
        values = []
        for col, val in [("name", name), ("email", email), ("phone", phone),
                         ("company", company), ("address", address), ("notes", notes), ("due_amount", due_amount)]:
            if val is not None:
                fields.append(f"{col} = ?")
                values.append(val)
        if not fields:
            return False
        values.append(client_id)
        c.execute(f"UPDATE clients SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        return c.rowcount > 0

def delete_client(client_id):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        conn.commit()
        return c.rowcount > 0

def get_or_create_client(name, email=None, company=None):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM clients WHERE name = ?", (name,))
        row = c.fetchone()
        if row:
            return row["id"]
        else:
            c.execute("INSERT INTO clients (name, email, company) VALUES (?, ?, ?)", (name, email, company))
            conn.commit()
            return c.lastrowid

# ─── Project ───

def create_project(client_id, name, description=None):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO projects (client_id, name, description) VALUES (?, ?, ?)", (client_id, name, description))
        conn.commit()
        return c.lastrowid

def get_projects_by_client(client_id):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM projects WHERE client_id = ? ORDER BY created_at DESC", (client_id,))
        return [dict(r) for r in c.fetchall()]

def delete_project(project_id):
    with get_db_conn() as conn:
        c = conn.cursor()
        # Cascade: delete invoices/receipts or move to unlinked? 
        # For now, just delete the project. 
        c.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        return c.rowcount > 0

def update_project_status(project_id, status):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE projects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, project_id))
        conn.commit()
        return c.rowcount > 0

def get_invoices_by_project(project_id):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM invoices WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
        return [dict(r) for r in c.fetchall()]

def get_receipts_by_project(project_id):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM receipts WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
        return [dict(r) for r in c.fetchall()]

# ─── Proposal ───

def save_proposal(project_id, client_name, project_title, file_path):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO proposals (project_id, client_name, project_title, file_path) VALUES (?, ?, ?, ?)",
                  (project_id, client_name, project_title, file_path))
        conn.commit()

# ─── Invoice CRUD ───

def save_invoice(invoice_number, client_name, project_name, total_amount, file_path,
                 sender_name="", sender_address="", sender_email="", invoice_date="", due_date="", project_id=None):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO invoices
            (invoice_number, client_name, project_name, project_id, total_amount, file_path,
             sender_name, sender_address, sender_email, invoice_date, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (invoice_number, client_name, project_name, project_id, total_amount, file_path,
             sender_name, sender_address, sender_email, invoice_date, due_date))
        conn.commit()

def get_all_invoices(status_filter=None):
    with get_db_conn() as conn:
        c = conn.cursor()
        if status_filter and status_filter != "all":
            c.execute("SELECT * FROM invoices WHERE status = ? ORDER BY created_at DESC", (status_filter,))
        else:
            c.execute("SELECT * FROM invoices ORDER BY created_at DESC")
        return [dict(r) for r in c.fetchall()]

def get_unpaid_invoices():
    return get_all_invoices("unpaid")

def mark_invoice_paid(invoice_id):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (invoice_id,))
        conn.commit()
        return c.rowcount > 0

def mark_invoice_paid_by_number(invoice_number):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE invoices SET status = 'paid' WHERE invoice_number = ?", (invoice_number,))
        conn.commit()
        return c.rowcount > 0

# ─── Stats ───

def get_stats():
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT COALESCE(SUM(total_amount), 0) as total FROM invoices WHERE status = 'unpaid'")
        outstanding = c.fetchone()["total"]
        c.execute("SELECT COALESCE(SUM(total_amount), 0) as total FROM invoices WHERE status = 'paid'")
        paid_total = c.fetchone()["total"]
        c.execute("SELECT COUNT(*) as cnt FROM invoices WHERE status = 'unpaid'")
        unpaid_count = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) as cnt FROM invoices")
        total_invoices = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) as cnt FROM projects WHERE status = 'active'")
        active_projects = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) as cnt FROM clients")
        total_clients = c.fetchone()["cnt"]
        return {
            "outstanding_revenue": round(outstanding, 2),
            "paid_revenue": round(paid_total, 2),
            "total_revenue": round(outstanding + paid_total, 2),
            "unpaid_invoices": unpaid_count,
            "total_invoices": total_invoices,
            "active_projects": active_projects,
            "total_clients": total_clients
        }

# ─── Receipts CRUD ───

def save_receipt(receipt_number, client_name, project_name, amount_paid, payment_method, file_path, receipt_date, project_id=None):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO receipts (receipt_number, client_name, project_name, project_id, amount_paid, payment_method, file_path, receipt_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (receipt_number, client_name, project_name, project_id, amount_paid, payment_method, file_path, receipt_date))
        conn.commit()
        return c.lastrowid

def get_all_receipts():
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM receipts ORDER BY created_at DESC")
        return [dict(r) for r in c.fetchall()]

def delete_receipt(receipt_id):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM receipts WHERE id = ?", (receipt_id,))
        conn.commit()
        return c.rowcount > 0

# ─── Auth Functions ───

def create_user(name, email, password_hash, salt):
    try:
        with get_db_conn() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (name, email, password_hash, salt) VALUES (?, ?, ?, ?)", 
                      (name, email, password_hash, salt))
            conn.commit()
            return c.lastrowid
    except sqlite3.IntegrityError:
        return None # User exists

def get_user_by_email(email):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = c.fetchone()
        return dict(row) if row else None

def create_session(session_id, user_id, expires_at):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO sessions (session_id, user_id, expires_at) VALUES (?, ?, ?)", 
                  (session_id, user_id, expires_at))
        conn.commit()

def get_user_from_session(session_id):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT users.id, users.name, users.email 
            FROM sessions 
            JOIN users ON sessions.user_id = users.id 
            WHERE sessions.session_id = ? AND sessions.expires_at > CURRENT_TIMESTAMP
        ''', (session_id,))
        row = c.fetchone()
        return dict(row) if row else None

def delete_session(session_id):
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()

# Initialize on import
init_db()
