# Freelancer AI Assistant Chatbot 🤖💼

Welcome to the **Freelancer AI Assistant Chatbot** – the ultimate all-in-one, AI-powered command center designed specifically for freelancers, consultants, and independent contractors. 

## 🌟 Why is this project unique and amazing?

Most freelancer tools force you to navigate through endless menus, tabs, and forms just to create a simple invoice or log a payment. **This project flips that paradigm on its head by bringing an advanced AI-powered conversational interface to the forefront.** 

Instead of clicking through tedious UI forms, you simply **chat** with your assistant:
> *"Generate an invoice for Acme Corp for the Website Redesign project, total $1,500."*
> *"Draft a friendly payment reminder for John Doe."*
> *"Create a receipt for $500 paid via Bank Transfer."*

### 🔥 Key Features & Capabilities:
- **🧠 Natural Language AI Chatbot:** Powered by OpenAI under the hood, the system understands your intent and extracts key data (like client names, dollar amounts, dates, and project details) directly from your conversational prompts.
- **📄 Automated Document Generation:** Automatically generates rich, professional **PDFs** for Contracts, Proposals, Invoices, and Receipts on the fly based purely on your chat commands.
- **📧 AI Email Drafting & Reminders:** Analyzes your client's outstanding balance and automatically drafts a contextual, professional payment reminder (or a friendly check-in if their balance is $0), which can be sent directly from the app.
- **📊 Real-Time Financial Dashboard:** Get instant insights into your outstanding revenue, total received, active projects, and unpaid invoices.
- **🔒 Secure Authentication:** Fully integrated user authentication system using secure password hashing and session management, ensuring your business data stays private.
- **🗂 Client & Project Management:** A robust backend that meticulously tracks all of your clients, their contact information, ongoing projects, and financial histories.

## 🚀 Tech Stack
- **Backend:** FastAPI (Python)
- **AI Processing:** OpenAI GPT Models
- **Database:** SQLite for local, fast, reliable data storage
- **Frontend:** HTML / JS / CSS dynamic dashboard
- **PDF Generation:** Custom Python generators for Pixel-Perfect Business Documents

## ⚙️ Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mdshayan90066-cpu/Freelancer-AI-assistant-Chatbot-.git
   cd Freelancer-AI-assistant-Chatbot-
   ```

2. **Set up a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment:**
   - Copy `.env.example` to `.env`
   - Copy `API_example.txt` to `API.txt`
   - Open them and add your real `OPENAI_API_KEY` to both files.

5. **Run the application:**
   ```bash
   uvicorn main:app --reload
   ```

6. **Access the Dashboard:** 
   Open `http://localhost:8000` in your web browser, register a new admin account, and start chatting with your new AI assistant!

---
*Built to empower freelancers to spend less time on admin, and more time on what they do best.*