#!/usr/bin/env python3
"""
Standalone diagnostic & test script to verify Microsoft Azure AI Foundry connection.
Usage:
    python test_foundry.py
"""

import os
import sys
import json
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ENDPOINT = os.getenv(
    "AZURE_AI_PROJECT_ENDPOINT",
    "https://MoneyArnold-01.services.ai.azure.com/api/projects/MoneyArnold-01"
)

def test_connection_and_list_agents():
    print("=" * 60)
    print("FINANCIAL BUDDY - AZURE AI FOUNDRY CONNECTION TEST")
    print("=" * 60)
    print(f"Connecting to Endpoint: {ENDPOINT}")

    try:
        from azure.identity import DefaultAzureCredential
        from azure.ai.projects import AIProjectClient
    except ImportError:
        print("\n[ERROR] Missing required packages!")
        print("Please install them with: pip install azure-ai-projects azure-identity python-dotenv")
        sys.exit(1)

    print("\n[1/3] Authenticating with DefaultAzureCredential...")
    credential = DefaultAzureCredential()

    try:
        project_client = AIProjectClient(
            endpoint=ENDPOINT,
            credential=credential,
            allow_preview=True
        )
        print("Successfully initialized AIProjectClient.")
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize AIProjectClient: {e}")
        return

    print("\n[2/3] Querying Agents and Workflows in MoneyArnold-01...")
    agents_found = []
    
    # Method 1: Check project_client.agents (Foundry Hosted / Workflow Agents)
    try:
        if hasattr(project_client.agents, "list"):
            for a in project_client.agents.list():
                agents_found.append({"name": getattr(a, "name", "Unnamed"), "id": getattr(a, "id", "")})
        elif hasattr(project_client.agents, "list_agents"):
            for a in project_client.agents.list_agents().data:
                agents_found.append({"name": getattr(a, "name", "Unnamed"), "id": getattr(a, "id", "")})
    except Exception as e:
        print(f"[NOTE] project_client.agents.list check: {e}")

    # Method 2: Check OpenAI Assistants API (Azure AI Foundry Agents)
    try:
        openai_client = project_client.get_openai_client()
        asst_list = openai_client.beta.assistants.list()
        for asst in asst_list.data:
            if not any(x["id"] == asst.id for x in agents_found):
                agents_found.append({"name": asst.name or "Unnamed", "id": asst.id})
    except Exception as e:
        print(f"[NOTE] openai_client.beta.assistants check: {e}")

    if not agents_found:
        print("No agents returned yet.")
        print("Tip: If your Azure account needs RBAC, assign 'Azure AI Developer' or 'Cognitive Services OpenAI User' in Azure Portal.")
    else:
        print(f"✓ Found {len(agents_found)} Agent(s) in MoneyArnold-01:")
        for idx, a in enumerate(agents_found, start=1):
            print(f"  {idx}. Name: {a['name']:<25} | ID: {a['id']}")

    print("\n[3/3] Testing Agent Execution...")
    if agents_found:
        test_agent = agents_found[0]
        print(f"Testing execution on agent: '{test_agent['name']}' (ID: {test_agent['id']})...")
        try:
            openai_client = project_client.get_openai_client()
            thread = openai_client.beta.threads.create()
            openai_client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content="Hello! Please confirm you are ready to process financial data."
            )
            run = openai_client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=test_agent['id']
            )
            print(f"✓ Run completed with status: {run.status}")

            messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
            for msg in messages.data:
                if msg.role == "assistant" and msg.content:
                    print(f"Agent Response: {msg.content[0].text.value[:200]}...")
                    break
        except Exception as e:
            print(f"[Execution Note] {e}")
    else:
        print("Skipping execution test as no agents were listed.")

    print("\n" + "=" * 60)
    print("Test finished! Copy any Agent IDs printed above into your backend/.env file.")
    print("=" * 60)

if __name__ == "__main__":
    test_connection_and_list_agents()
