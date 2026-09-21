from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PlannedPurchase(BaseModel):
    item: str = "Laptop"
    amount: float = 50000.0

class FinancialProfile(BaseModel):
    current_balance: float = 120000.0
    monthly_income: float = 60000.0
    monthly_expenses: float = 30000.0
    upcoming_bills: float = 5000.0
    savings_goal: float = 200000.0
    current_savings: float = 80000.0
    planned_purchase: Optional[PlannedPurchase] = None

class Budget(BaseModel):
    category: str
    amount: float

class Transaction(BaseModel):
    id: Optional[str] = None
    merchant: str
    amount: float
    category: Optional[str] = None
    confidence: Optional[str] = "high"
    date: Optional[str] = None

class FinancialDataStore(BaseModel):
    profile: FinancialProfile
    budgets: List[Budget] = []
    transactions: List[Transaction] = []
    pending_action: Optional[Dict[str, Any]] = None
    action_history: List[Dict[str, Any]] = []

class ActionConfirmationRequest(BaseModel):
    action_type: str = Field(..., description="e.g. reserve_funds, transfer_to_savings, pay_bill")
    confirmed: bool = Field(..., description="True to execute mock action, False to cancel")
    amount: Optional[float] = None
    description: Optional[str] = None

class ActionConfirmationResponse(BaseModel):
    status: str
    message: str
    action_executed: bool
    updated_balance: float
    updated_savings: float
