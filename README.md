# Financial Buddy 💰

> An AI Financial Assistant prototype built with **Microsoft Azure AI Foundry** and **FastAPI**.

Designed as a college-project prototype to demonstrate multi-agent financial reasoning, cash-flow forecasting, budget alerts, and confirmation-driven mock actions without modifying real bank accounts.

---

## 🏗️ Architecture

```
Browser (Frontend UI)
       │
       ▼
FastAPI Backend (/api/analyze)
       │
       ▼
Microsoft Azure AI Foundry (MoneyArnold-01)
       │
       ├── Agent 1: Financial Analyzer (Categorization, Budgets, Subscriptions)
       │     ▼
       ├── Agent 2: Financial Planner (Cash Flow Forecast, Affordability, Goal Gap)
       │     ▼
       └── Agent 3: Alert & Action (Proactive Alerts, Simulation Action with Confirmation)
       │
       ▼
Unified JSON Response ──► Interactive Dashboard
```

---

## 📁 Project Structure

```
MoneyArnold/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI REST API & static file serving
│   │   ├── foundry_client.py   # Azure AI Foundry SDK integration & fallback
│   │   └── models.py           # Pydantic data schemas
│   ├── data/
│   │   └── financial_data.json # File-based financial store (No database needed)
│   ├── .env                    # Environment variables (Azure endpoint & IDs)
│   ├── .env.example            # Environment template
│   ├── requirements.txt        # Python dependencies
│   └── test_foundry.py         # Standalone diagnostic test script
│
├── frontend/
│   ├── index.html              # Interactive Dashboard UI
│   ├── style.css               # Clean responsive styling
│   └── app.js                  # Frontend controller & API bridge
│
├── .gitignore
└── README.md
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python 3.10+**
- **Azure CLI** installed ([Download Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli))

### 2. Local Azure Authentication (Windows / macOS)
Open your terminal (PowerShell or Command Prompt on Windows, Terminal on Mac) and sign in:
```bash
az login
```
*Make sure to log in with the Azure account that has access to your project `MoneyArnold-01`.*

### 3. Install Dependencies
```bash
# Navigate to backend directory
cd backend

# Create and activate a virtual environment
# On Windows:
python -m venv venv
venv\Scripts\activate

# On Mac/Linux:
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 4. Test the Foundry Connection
Run the diagnostic script to inspect your Azure AI Foundry project and agents:
```bash
python test_foundry.py
```
This script will:
1. Verify authentication via `DefaultAzureCredential`.
2. Connect to `https://MoneyArnold-01.services.ai.azure.com/api/projects/MoneyArnold-01`.
3. Print all Agent Names and IDs discovered in your Foundry project.

*(Optional)* You can copy the printed Agent IDs into `backend/.env` to pin specific agents, though the client automatically auto-discovers them by name!

### 5. Run the Financial Buddy Web App
```bash
uvicorn app.main:app --reload --port 8000
```
Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

Click **"Run AI Workflow"** to see all three agents process the financial information, generate forecasts, and present simulated actions!

---

## ☁️ Deploying to Azure App Service

For a clean college demo, you can deploy the complete app (FastAPI + Frontend) directly to **Azure App Service (Linux)**:

```bash
# 1. Log in and set your subscription
az login
az account set --subscription "<YOUR_SUBSCRIPTION_ID_OR_NAME>"

# 2. Deploy from the backend folder
cd backend
az webapp up --runtime "PYTHON:3.11" --sku B1 --name financial-buddy-prototype

# 3. Configure the Foundry endpoint on App Service
az webapp config appsettings set \
  --name financial-buddy-prototype \
  --settings AZURE_AI_PROJECT_ENDPOINT="https://MoneyArnold-01.services.ai.azure.com/api/projects/MoneyArnold-01"

# 4. Enable Managed Identity for passwordless Azure auth
az webapp identity assign --name financial-buddy-prototype
```

Then in the Azure Portal:
1. Go to your **Azure AI Services / Foundry** resource (`MoneyArnold-01`).
2. Open **Access Control (IAM)** -> **Add role assignment**.
3. Select role **Azure AI Developer** (or **Cognitive Services OpenAI User**).
4. Assign access to **Managed Identity** -> Select your `financial-buddy-prototype` App Service.
5. Save. Your deployed web app now securely authenticates to Azure Foundry without storing secrets!

---

## 🛡️ Prototype Safety Note
This application executes **only simulated actions**. When a user confirms a fund reservation or payment action in the UI, it updates the session state and audit log within `financial_data.json`. No real bank accounts, cards, or payment gateways are accessed.
