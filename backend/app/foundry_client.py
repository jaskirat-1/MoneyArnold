import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("financial_buddy.foundry")

class FoundryClient:
    def __init__(self):
        self.endpoint = os.getenv(
            "AZURE_AI_PROJECT_ENDPOINT",
            "https://MoneyArnold-01.services.ai.azure.com/api/projects/MoneyArnold-01"
        )
        self.workflow_id = os.getenv("FOUNDRY_WORKFLOW_ID")
        self.analyzer_id = os.getenv("AGENT_ANALYZER_ID")
        self.planner_id = os.getenv("AGENT_PLANNER_ID")
        self.action_id = os.getenv("AGENT_ACTION_ID")
        self.use_mock_fallback = os.getenv("USE_MOCK_FALLBACK", "false").lower() == "true"
        
        self._project_client = None

    def get_client(self):
        """Initializes and returns the Azure AIProjectClient with DefaultAzureCredential."""
        if self._project_client is None:
            try:
                from azure.identity import DefaultAzureCredential
                from azure.ai.projects import AIProjectClient

                # allow_preview=True enables workflow and agent endpoint features
                self._project_client = AIProjectClient(
                    endpoint=self.endpoint,
                    credential=DefaultAzureCredential(),
                    allow_preview=True
                )
            except Exception as e:
                logger.warning(f"Could not initialize Azure AIProjectClient: {e}")
                return None
        return self._project_client

    def discover_agents(self) -> Dict[str, str]:
        """Auto-discovers Agent IDs from Azure AI Foundry if not manually specified in .env."""
        client = self.get_client()
        if not client:
            return {}

        discovered = {}
        # Try Foundry Hosted / Workflow Agents
        try:
            if hasattr(client.agents, "list"):
                for agent in client.agents.list():
                    name = getattr(agent, "name", "")
                    aid = getattr(agent, "id", "")
                    if name and aid:
                        discovered[name] = aid
        except Exception as e:
            logger.debug(f"client.agents.list check: {e}")

        # Try Azure OpenAI Assistants API
        try:
            openai_client = client.get_openai_client()
            assts = openai_client.beta.assistants.list()
            for asst in assts.data:
                name = asst.name or ""
                aid = asst.id
                if name and aid and name not in discovered:
                    discovered[name] = aid
        except Exception as e:
            logger.debug(f"openai_client.beta.assistants check: {e}")

        for name, aid in discovered.items():
            name_lower = name.lower()
            if not self.analyzer_id and ("analyzer" in name_lower or "categor" in name_lower):
                self.analyzer_id = aid
            elif not self.planner_id and ("planner" in name_lower or "forecast" in name_lower):
                self.planner_id = aid
            elif not self.action_id and ("action" in name_lower or "alert" in name_lower):
                self.action_id = aid
            elif not self.workflow_id and ("workflow" in name_lower or "buddy" in name_lower):
                self.workflow_id = aid

        logger.info(f"Discovered Azure Foundry Agents: {discovered}")
        return discovered

    def _execute_agent(self, agent_id: str, prompt_content: str) -> Optional[Dict[str, Any]]:
        """Sends a message to an agent on a dedicated thread and returns its parsed JSON response."""
        client = self.get_client()
        if not client:
            return None

        try:
            openai_client = client.get_openai_client()
            thread = openai_client.beta.threads.create()
            openai_client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt_content
            )
            run = openai_client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=agent_id
            )

            if run.status != "completed":
                logger.error(f"Run ended with status: {run.status}")
                return None

            messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
            for msg in messages.data:
                if msg.role == "assistant" and msg.content:
                    raw_text = msg.content[0].text.value
                    cleaned = self._clean_json_string(raw_text)
                    return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Error executing agent {agent_id}: {e}")
            return None

    def _clean_json_string(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def run_pipeline(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the Financial Buddy workflow:
        Option 1: If a workflow agent ID is configured, invokes the workflow directly.
        Option 2: Sequentially chains Agent 1 (Analyzer) -> Agent 2 (Planner) -> Agent 3 (Alert & Action).
        Option 3: Falls back to verified test data if offline or not logged into Azure.
        """
        client = self.get_client()

        if client and not self.use_mock_fallback:
            self.discover_agents()

            # Path A: Single Workflow Agent invocation
            if self.workflow_id:
                logger.info(f"Invoking Foundry Workflow Agent: {self.workflow_id}")
                result = self._execute_agent(self.workflow_id, json.dumps(financial_data))
                if result:
                    return {
                        "execution_mode": "foundry_workflow_agent",
                        "analyzer": result.get("analyzer", {}),
                        "planner": result.get("planner", {}),
                        "alert_action": result if "agent" in result and result["agent"] == "alert_action" else result.get("alert_action", result),
                        "status": "success"
                    }

            # Path B: Sequential Agent Chaining
            if self.analyzer_id and self.planner_id and self.action_id:
                logger.info("Executing 3-Agent Sequential Pipeline in Azure AI Foundry...")
                
                # Step 1: Agent 1 - Financial Analyzer
                analyzer_input = {
                    "transactions": financial_data.get("transactions", []),
                    "budgets": financial_data.get("budgets", []),
                    "instructions": "Categorize transactions, monitor budget utilization, and identify subscriptions/unbudgeted expenses."
                }
                analyzer_res = self._execute_agent(self.analyzer_id, json.dumps(analyzer_input))

                # Step 2: Agent 2 - Financial Planner
                if analyzer_res:
                    planner_input = {
                        "analyzer_results": analyzer_res,
                        "profile": financial_data.get("profile", {}),
                        "instructions": "Perform cash-flow forecasting (30/60/90 days), calculate savings goal gap, and assess affordability of planned purchase."
                    }
                    planner_res = self._execute_agent(self.planner_id, json.dumps(planner_input))

                    # Step 3: Agent 3 - Alert & Action
                    if planner_res:
                        action_input = {
                            "analyzer_results": analyzer_res,
                            "planner_results": planner_res,
                            "profile": financial_data.get("profile", {}),
                            "instructions": "Generate proactive alerts, highlight budget and emergency shortfalls, and create confirmation-based mock financial action."
                        }
                        action_res = self._execute_agent(self.action_id, json.dumps(action_input))

                        if action_res:
                            return {
                                "execution_mode": "foundry_live_chain",
                                "analyzer": analyzer_res,
                                "planner": planner_res,
                                "alert_action": action_res,
                                "status": "success"
                            }

        # Path C: Verified Simulation Fallback
        logger.info("Using verified local test outputs (USE_MOCK_FALLBACK or Foundry unavailable).")
        return self.get_verified_mock_output(financial_data)

    def get_verified_mock_output(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dynamically calculates multi-agent outputs from user's current financial_data store.
        Matches the exact logic and schema of the 3 Foundry agents.
        """
        profile = financial_data.get("profile", {})
        curr_bal = float(profile.get("current_balance", 120000))
        income = float(profile.get("monthly_income", 60000))
        expenses = float(profile.get("monthly_expenses", 30000))
        surplus = max(0.0, income - expenses)
        bills_amt = float(profile.get("upcoming_bills", 5000))
        curr_savings = float(profile.get("current_savings", 80000))
        savings_goal = float(profile.get("savings_goal", 200000))
        
        planned_purchase = profile.get("planned_purchase") or {"item": "Laptop", "amount": 50000}
        item_name = planned_purchase.get("item", "Laptop")
        purchase_amt = float(planned_purchase.get("amount", 50000))

        raw_txs = financial_data.get("transactions", [])
        budgets_config = financial_data.get("budgets", [
            {"category": "Food", "amount": 10000},
            {"category": "Transport", "amount": 5000},
            {"category": "Shopping", "amount": 8000},
            {"category": "Entertainment", "amount": 3000}
        ])

        # -------------------------------------------------------------
        # 1. Agent 1 Simulation: Categorization & Budget Analysis
        # -------------------------------------------------------------
        categorized_txs = []
        spending_by_category = {b["category"]: 0.0 for b in budgets_config}
        spending_by_category["Bills"] = 0.0
        spending_by_category["Other"] = 0.0

        subscriptions = []
        unbudgeted_items = []

        for tx in raw_txs:
            merchant = tx.get("merchant", "Unknown")
            amt = float(tx.get("amount", 0))
            cat = tx.get("category")
            conf = tx.get("confidence", "high")
            date = tx.get("date")

            m_lower = merchant.lower()
            if not cat or cat == "Pending":
                if any(k in m_lower for k in ["swiggy", "zomato", "restaurant", "cafe", "food", "grocer", "mcdonald"]):
                    cat = "Food"
                    conf = "high"
                elif any(k in m_lower for k in ["uber", "ola", "metro", "fuel", "petrol", "transport", "train"]):
                    cat = "Transport"
                    conf = "high"
                elif any(k in m_lower for k in ["amazon", "flipkart", "myntra", "shopping", "clothes", "book"]):
                    cat = "Shopping"
                    conf = "medium"
                elif any(k in m_lower for k in ["netflix", "spotify", "prime", "movie", "hotstar", "cinema"]):
                    cat = "Entertainment"
                    conf = "high"
                elif any(k in m_lower for k in ["electricity", "power", "water", "wifi", "bill", "recharge", "utility"]):
                    cat = "Bills"
                    conf = "high"
                else:
                    cat = "Other"
                    conf = "medium"

            categorized_txs.append({
                "id": tx.get("id"),
                "merchant": merchant,
                "amount": amt,
                "date": date,
                "category": cat,
                "confidence": conf
            })

            # Check for subscriptions
            if any(k in m_lower for k in ["netflix", "spotify", "prime", "hotstar", "youtube"]):
                subscriptions.append({"service": merchant, "amount": amt, "type": "recurring_subscription", "confidence": "high"})
            
            # Check for unbudgeted essentials
            if cat == "Bills":
                unbudgeted_items.append({"item": f"{merchant} Bill", "amount": amt, "status": "unbudgeted_expense", "note": "Utility expense"})

            spending_by_category[cat] = spending_by_category.get(cat, 0.0) + amt

        # Build budget analysis
        budget_analysis = []
        alerts_agent1 = []
        for b in budgets_config:
            b_name = b["category"]
            b_limit = float(b["amount"])
            spent = spending_by_category.get(b_name, 0.0)
            pct = (spent / b_limit * 100.0) if b_limit > 0 else 0.0
            
            if pct >= 100.0:
                status = "exceeded"
                alerts_agent1.append(f"{b_name} budget exceeded! Spent ₹{spent:,.0f} of ₹{b_limit:,.0f} ({pct:.1f}%).")
            elif pct >= 75.0:
                status = "warning"
                alerts_agent1.append(f"{b_name} budget warning: {pct:.1f}% utilized (₹{spent:,.0f} of ₹{b_limit:,.0f}).")
            else:
                status = "normal"

            budget_analysis.append({
                "budget_name": b_name,
                "budget_amount": b_limit,
                "spending": spent,
                "percentage_used": pct,
                "status": status,
                "remaining": max(0.0, b_limit - spent)
            })

        analyzer_output = {
            "agent": "financial_analyzer",
            "status": "success",
            "categorized_transactions": categorized_txs,
            "budget_analysis": budget_analysis,
            "bills_analysis": unbudgeted_items,
            "subscription_analysis": subscriptions,
            "spending_patterns": [
                {"insight": f"{b['budget_name']} is at {b['percentage_used']:.1f}% of limit."} for b in budget_analysis if b["percentage_used"] > 20
            ],
            "alerts": alerts_agent1,
            "data_needed": []
        }

        # -------------------------------------------------------------
        # 2. Agent 2 Simulation: Financial Planner & Forecasting
        # -------------------------------------------------------------
        balance_after_purchase = curr_bal - purchase_amt
        fc_30_before = curr_bal + surplus - bills_amt
        fc_30_after = balance_after_purchase + surplus - bills_amt
        fc_60_before = curr_bal + (2 * surplus) - bills_amt
        fc_60_after = balance_after_purchase + (2 * surplus) - bills_amt
        fc_90_before = curr_bal + (3 * surplus) - bills_amt
        fc_90_after = balance_after_purchase + (3 * surplus) - bills_amt

        goal_gap = max(0.0, savings_goal - curr_savings)
        months_to_goal = round(goal_gap / surplus, 1) if surplus > 0 else 999.0

        # Affordability verdict
        remaining_liquidity_after_all = balance_after_purchase - bills_amt
        if remaining_liquidity_after_all >= expenses:
            affordable = True
            verdict = f"Affordable: Purchasing {item_name} leaves ₹{balance_after_purchase:,.0f} liquid (₹{remaining_liquidity_after_all:,.0f} after reserving ₹{bills_amt:,.0f} bills), which comfortably covers your ₹{expenses:,.0f}/mo expenses."
        elif remaining_liquidity_after_all >= 0:
            affordable = True
            verdict = f"Affordable with caution: Leaves ₹{balance_after_purchase:,.0f} liquid, or ₹{remaining_liquidity_after_all:,.0f} after reserving ₹{bills_amt:,.0f} bills. Cushion for emergency living expenses is tight."
        else:
            affordable = False
            verdict = f"Not recommended: Purchasing {item_name} (₹{purchase_amt:,.0f}) would cause a liquidity deficit of ₹{abs(remaining_liquidity_after_all):,.0f} once upcoming bills are paid."

        planner_output = {
            "agent": "financial_planner",
            "status": "success",
            "cash_flow": {
                "monthly_income": income,
                "monthly_expenses": expenses,
                "monthly_surplus": surplus,
                "balance_after_purchase": balance_after_purchase,
                "forecast_30_days_before": fc_30_before,
                "forecast_30_days_after": fc_30_after,
                "forecast_60_days_before": fc_60_before,
                "forecast_60_days_after": fc_60_after,
                "forecast_90_days_before": fc_90_before,
                "forecast_90_days_after": fc_90_after
            },
            "budget_plan": {
                "recommended_savings_rate": round((surplus / income * 100), 1) if income > 0 else 0,
                "recommended_emergency_buffer": expenses * 2
            },
            "savings_plan": {
                "target_goal": savings_goal,
                "current_savings": curr_savings,
                "goal_gap": goal_gap,
                "months_to_reach_at_surplus": months_to_goal,
                "scenario_with_purchase_from_savings": {
                    "resulting_savings": max(0.0, curr_savings - purchase_amt),
                    "new_gap": goal_gap + purchase_amt,
                    "months_to_goal": round((goal_gap + purchase_amt) / surplus, 1) if surplus > 0 else 999.0
                }
            },
            "goal_analysis": [
                {"goal": "Emergency Savings Goal", "target": savings_goal, "current": curr_savings, "progress_pct": round((curr_savings / savings_goal * 100), 1) if savings_goal > 0 else 0}
            ],
            "affordability_analysis": {
                "item": item_name,
                "cost": purchase_amt,
                "affordable": affordable,
                "verdict": verdict
            },
            "recommendations": [
                f"Reserve ₹{bills_amt:,.0f} for upcoming bills prior to purchasing {item_name}.",
                f"Allocate monthly surplus of ₹{surplus:,.0f} toward the ₹{goal_gap:,.0f} emergency goal gap ({months_to_goal} months)."
            ],
            "data_needed": []
        }

        # -------------------------------------------------------------
        # 3. Agent 3 Simulation: Alerts & Interactive Confirmation
        # -------------------------------------------------------------
        all_alerts = []
        for b_alert in alerts_agent1:
            all_alerts.append({"level": "warning", "title": "Budget Alert", "message": b_alert})

        if bills_amt > 0:
            all_alerts.append({"level": "info", "title": "Upcoming Bills", "message": f"₹{bills_amt:,.0f} in upcoming bills require reservation."})

        if goal_gap > 0:
            all_alerts.append({"level": "warning", "title": "Emergency Fund Shortfall", "message": f"Emergency fund gap is ₹{goal_gap:,.0f} (~{months_to_goal} months at surplus)."})

        if not affordable:
            all_alerts.append({"level": "danger", "title": "Liquidity Risk", "message": f"High risk: buying {item_name} creates a negative balance of ₹{abs(remaining_liquidity_after_all):,.0f} after bills."})
        else:
            all_alerts.append({"level": "attention", "title": "Post-Purchase Liquidity", "message": f"After {item_name} (₹{purchase_amt:,.0f}) and bills (₹{bills_amt:,.0f}), net liquidity will be ₹{remaining_liquidity_after_all:,.0f}."})

        action_amt = bills_amt if bills_amt > 0 else purchase_amt
        action_type = "reserve_bill_funds" if bills_amt > 0 else "reserve_purchase_funds"
        action_desc = f"Reserve ₹{action_amt:,.0f} from main balance to safeguard upcoming expenses."

        action_output = {
            "agent": "alert_action",
            "status": "success",
            "alerts": all_alerts,
            "user_message": f"Your balance is ₹{curr_bal:,.0f}. To ensure you maintain stability, would you like to reserve ₹{action_amt:,.0f} now?",
            "requires_confirmation": True,
            "action": {
                "type": action_type,
                "description": action_desc,
                "amount": action_amt,
                "status": "pending_confirmation"
            }
        }

        return {
            "execution_mode": "dynamic_simulation",
            "analyzer": analyzer_output,
            "planner": planner_output,
            "alert_action": action_output,
            "status": "success"
        }
