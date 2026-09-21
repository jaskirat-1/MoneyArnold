import os
import json
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.models import (
    FinancialProfile,
    Transaction,
    ActionConfirmationRequest,
    ActionConfirmationResponse
)
from app.foundry_client import FoundryClient

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("financial_buddy.api")

app = FastAPI(
    title="Financial Buddy API",
    description="AI Financial Assistant backend connecting to Microsoft Azure AI Foundry",
    version="1.0.0"
)

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "financial_data.json"
foundry_client = FoundryClient()

def load_stored_data() -> dict:
    if not DATA_FILE.exists():
        raise HTTPException(status_code=500, detail="financial_data.json data store not found")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_stored_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Financial Buddy API",
        "foundry_endpoint": foundry_client.endpoint,
        "mock_fallback_enabled": foundry_client.use_mock_fallback
    }

@app.get("/api/agents/discover")
def discover_agents():
    """Diagnostic endpoint to inspect Azure AI Foundry agents."""
    agents = foundry_client.discover_agents()
    return {
        "discovered_agents": agents,
        "active_config": {
            "workflow_id": foundry_client.workflow_id,
            "analyzer_id": foundry_client.analyzer_id,
            "planner_id": foundry_client.planner_id,
            "action_id": foundry_client.action_id
        }
    }

@app.get("/api/financial-data")
def get_financial_data():
    return load_stored_data()

@app.post("/api/financial-data/profile")
def update_profile(profile: FinancialProfile):
    data = load_stored_data()
    data["profile"] = profile.model_dump()
    save_stored_data(data)
    return {"status": "success", "profile": data["profile"]}

@app.post("/api/financial-data/transactions")
def add_transaction(tx: Transaction):
    data = load_stored_data()
    tx_dict = tx.model_dump()
    if not tx_dict.get("id"):
        tx_dict["id"] = f"tx-{len(data.get('transactions', [])) + 1}"
    data["transactions"].append(tx_dict)
    save_stored_data(data)
    return {"status": "success", "transactions": data["transactions"]}

@app.delete("/api/financial-data/transactions/{tx_id}")
def delete_transaction(tx_id: str):
    data = load_stored_data()
    initial_len = len(data.get("transactions", []))
    data["transactions"] = [t for t in data.get("transactions", []) if t.get("id") != tx_id]
    if len(data["transactions"]) == initial_len:
        raise HTTPException(status_code=404, detail="Transaction not found")
    save_stored_data(data)
    return {"status": "success", "transactions": data["transactions"]}

@app.post("/api/financial-data/reset")
def reset_to_demo_data():
    """Resets the data store to the original verified college demo state."""
    seed_data = {
        "profile": {
            "current_balance": 120000,
            "monthly_income": 60000,
            "monthly_expenses": 30000,
            "upcoming_bills": 5000,
            "savings_goal": 200000,
            "current_savings": 80000,
            "planned_purchase": {
                "item": "Laptop",
                "amount": 50000
            }
        },
        "budgets": [
            {"category": "Food", "amount": 10000},
            {"category": "Transport", "amount": 5000},
            {"category": "Shopping", "amount": 8000},
            {"category": "Entertainment", "amount": 3000}
        ],
        "transactions": [
            {"id": "tx-1", "merchant": "Swiggy", "amount": 2500, "category": "Food", "confidence": "high", "date": "2026-09-02"},
            {"id": "tx-2", "merchant": "Uber", "amount": 1200, "category": "Transport", "confidence": "high", "date": "2026-09-05"},
            {"id": "tx-3", "merchant": "Amazon", "amount": 4500, "category": "Shopping", "confidence": "medium", "date": "2026-09-10"},
            {"id": "tx-4", "merchant": "Netflix", "amount": 649, "category": "Entertainment", "confidence": "high", "date": "2026-09-12"},
            {"id": "tx-5", "merchant": "Electricity", "amount": 2500, "category": "Bills", "confidence": "high", "date": "2026-09-15"},
            {"id": "tx-6", "merchant": "College Books", "amount": 1500, "category": "Shopping", "confidence": "medium", "date": "2026-09-18"}
        ],
        "pending_action": None,
        "action_history": []
    }
@app.get("/api/investments/rates")
def get_investment_rates():
    """
    Returns top verified Indian Fixed Deposit and Government/PSU Bond rates,
    customized for senior citizens and wealth optimization on idle current balance.
    """
    data = load_stored_data()
    profile = data.get("profile", {})
    curr_bal = float(profile.get("current_balance", 120000))
    monthly_expenses = float(profile.get("monthly_expenses", 30000))
    upcoming_bills = float(profile.get("upcoming_bills", 5000))
    
    # Safe reserve buffer = 2 months living expenses + upcoming bills
    safe_reserve = (monthly_expenses * 2) + upcoming_bills
    idle_cash = max(0.0, curr_bal - safe_reserve)
    
    savings_return = round(idle_cash * 0.0275)
    senior_fd_return = round(idle_cash * 0.0850)
    extra_income = max(0, senior_fd_return - savings_return)

    return {
        "summary": {
            "current_balance": curr_bal,
            "recommended_liquid_buffer": safe_reserve,
            "idle_cash": idle_cash,
            "savings_account_return": savings_return,
            "senior_fd_return": senior_fd_return,
            "extra_annual_income": extra_income,
            "has_idle_cash": idle_cash >= 10000
        },
        "government_bonds": [
            {
                "name": "Senior Citizens Savings Scheme (SCSS)",
                "rate": "8.20%",
                "type": "Govt of India Sovereign",
                "payout": "Quarterly Payout",
                "safety": "100% Risk Free",
                "tax_benefit": "Sec 80C & Sec 80TTB eligible",
                "highlight": True
            },
            {
                "name": "RBI Floating Rate Savings Bonds (FRSB)",
                "rate": "8.05%",
                "type": "Reserve Bank of India",
                "payout": "Semi-Annual (Jan & July)",
                "safety": "100% Sovereign Guarantee",
                "tax_benefit": "No upper investment ceiling",
                "highlight": False
            },
            {
                "name": "Post Office Monthly Income Scheme (POMIS)",
                "rate": "7.40%",
                "type": "Govt of India",
                "payout": "Monthly Pension Payout",
                "safety": "100% Risk Free",
                "tax_benefit": "Ideal for regular monthly cash flow",
                "highlight": False
            }
        ],
        "bank_fds": [
            {
                "institution": "Unity Small Finance Bank",
                "senior_rate": "8.75%",
                "regular_rate": "8.25%",
                "tenure": "1001 Days",
                "safety": "RBI / DICGC Insured up to ₹5 Lakhs",
                "highlight": True
            },
            {
                "institution": "Suryoday / Equitas SFB",
                "senior_rate": "8.50%",
                "regular_rate": "8.00%",
                "tenure": "2 to 3 Years",
                "safety": "RBI / DICGC Insured up to ₹5 Lakhs",
                "highlight": True
            },
            {
                "institution": "State Bank of India (SBI Amrit Kalash)",
                "senior_rate": "7.60%",
                "regular_rate": "7.10%",
                "tenure": "400 Days",
                "safety": "India's Largest Public Bank",
                "highlight": False
            },
            {
                "institution": "HDFC / ICICI Bank",
                "senior_rate": "7.75%",
                "regular_rate": "7.25%",
                "tenure": "15 to 18 Months",
                "safety": "Top Tier Private Banks",
                "highlight": False
            }
        ]
    }

@app.post("/api/analyze")
def run_financial_analysis():
    """Runs the 3-agent Foundry workflow on the current financial data."""
    data = load_stored_data()
    result = foundry_client.run_pipeline(data)
    
    # Store any pending mock action for confirmation
    alert_action = result.get("alert_action", {})
    if alert_action.get("requires_confirmation") and alert_action.get("action"):
        data["pending_action"] = alert_action["action"]
        save_stored_data(data)
        
    return result

@app.post("/api/action/confirm", response_model=ActionConfirmationResponse)
def confirm_mock_action(req: ActionConfirmationRequest):
    """
    Executes or cancels the simulated mock financial action.
    No real money is ever transferred or paid.
    """
    data = load_stored_data()
    profile = data.get("profile", {})
    curr_bal = profile.get("current_balance", 0.0)
    curr_sav = profile.get("current_savings", 0.0)
    action_amount = req.amount or 5000.0

    if req.confirmed:
        # Simulate action: reserve funds from current balance into savings/bill reserve
        new_bal = curr_bal - action_amount
        new_sav = curr_sav + action_amount
        profile["current_balance"] = new_bal
        profile["current_savings"] = new_sav
        data["profile"] = profile

        action_record = {
            "type": req.action_type,
            "status": "executed_mock",
            "amount": action_amount,
            "description": req.description or f"Mock reservation of ₹{action_amount:,.2f}",
            "previous_balance": curr_bal,
            "new_balance": new_bal
        }
        data["action_history"].append(action_record)
        data["pending_action"] = None
        save_stored_data(data)

        return ActionConfirmationResponse(
            status="completed",
            message=f"Mock action executed: Reserved ₹{action_amount:,.2f}. Main balance is now ₹{new_bal:,.2f}.",
            action_executed=True,
            updated_balance=new_bal,
            updated_savings=new_sav
        )
    else:
        # User declined or cancelled
        action_record = {
            "type": req.action_type,
            "status": "cancelled_by_user",
            "amount": action_amount,
            "description": req.description or "User declined the action."
        }
        data["action_history"].append(action_record)
        data["pending_action"] = None
        save_stored_data(data)

        return ActionConfirmationResponse(
            status="cancelled",
            message="Mock action was safely cancelled. No balances were modified.",
            action_executed=False,
            updated_balance=curr_bal,
            updated_savings=curr_sav
        )

# Serve Frontend static files directly from root
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
