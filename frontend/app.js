// Financial Buddy - Frontend Controller
const API_BASE = window.location.origin.includes(':8000') 
  ? window.location.origin 
  : 'http://localhost:8000';

let currentPendingAction = null;
let currentProfile = null;

document.addEventListener('DOMContentLoaded', () => {
  checkBackendHealth();
  loadFinancialData();
  setupEventListeners();
});

function setupEventListeners() {
  // Main Run Workflow button
  const runBtn = document.getElementById('run-analysis-btn');
  if (runBtn) {
    runBtn.addEventListener('click', runAIAnalysis);
  }

  // Confirmation actions
  const confirmBtn = document.getElementById('btn-confirm-action');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => handleActionDecision(true));
  }

  const cancelBtn = document.getElementById('btn-cancel-action');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => handleActionDecision(false));
  }

  // Reset Demo button
  const resetBtn = document.getElementById('btn-reset-demo');
  if (resetBtn) {
    resetBtn.addEventListener('click', handleResetDemo);
  }

  // Add Expense Modal
  const openAddTxBtn = document.getElementById('btn-open-add-tx');
  const modalAddTx = document.getElementById('modal-add-tx');
  const closeAddTxBtn = document.getElementById('btn-close-add-tx');
  const cancelAddTxBtn = document.getElementById('btn-cancel-add-tx');
  const formAddTx = document.getElementById('form-add-tx');

  if (openAddTxBtn && modalAddTx) {
    openAddTxBtn.addEventListener('click', () => {
      formAddTx.reset();
      document.getElementById('tx-date').value = new Date().toISOString().split('T')[0];
      modalAddTx.classList.remove('hidden');
    });

    const closeAddModal = () => modalAddTx.classList.add('hidden');
    if (closeAddTxBtn) closeAddTxBtn.addEventListener('click', closeAddModal);
    if (cancelAddTxBtn) cancelAddTxBtn.addEventListener('click', closeAddModal);
    modalAddTx.addEventListener('click', (e) => {
      if (e.target === modalAddTx) closeAddModal();
    });

    if (formAddTx) {
      formAddTx.addEventListener('submit', handleAddTransaction);
    }
  }

  // Edit Profile Modal
  const openProfileBtn = document.getElementById('btn-open-edit-profile');
  const modalProfile = document.getElementById('modal-edit-profile');
  const closeProfileBtn = document.getElementById('btn-close-profile');
  const cancelProfileBtn = document.getElementById('btn-cancel-profile');
  const formProfile = document.getElementById('form-edit-profile');

  if (openProfileBtn && modalProfile) {
    openProfileBtn.addEventListener('click', () => {
      if (currentProfile) {
        document.getElementById('prof-balance').value = currentProfile.current_balance || 120000;
        document.getElementById('prof-income').value = currentProfile.monthly_income || 60000;
        document.getElementById('prof-expenses').value = currentProfile.monthly_expenses || 30000;
        document.getElementById('prof-bills').value = currentProfile.upcoming_bills || 5000;
        document.getElementById('prof-savings').value = currentProfile.current_savings || 80000;
        document.getElementById('prof-savings-goal').value = currentProfile.savings_goal || 200000;
        
        const purchase = currentProfile.planned_purchase || { item: 'Laptop', amount: 50000 };
        document.getElementById('prof-item').value = purchase.item || 'Laptop';
        document.getElementById('prof-item-amount').value = purchase.amount || 50000;
      }
      modalProfile.classList.remove('hidden');
    });

    const closeProfileModal = () => modalProfile.classList.add('hidden');
    if (closeProfileBtn) closeProfileBtn.addEventListener('click', closeProfileModal);
    if (cancelProfileBtn) cancelProfileBtn.addEventListener('click', closeProfileModal);
    modalProfile.addEventListener('click', (e) => {
      if (e.target === modalProfile) closeProfileModal();
    });

    if (formProfile) {
      formProfile.addEventListener('submit', handleUpdateProfile);
    }
  }
}

// 1. Check API Health & Connection
async function checkBackendHealth() {
  const statusBadge = document.getElementById('backend-status');
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error('Backend responded with error');
    const data = await res.json();
    
    if (data.mock_fallback_enabled) {
      statusBadge.textContent = '● Simulation Engine Active';
      statusBadge.className = 'badge badge-accent';
      statusBadge.title = 'Using dynamic multi-agent calculation engine';
    } else {
      statusBadge.textContent = '● Connected to Azure Foundry';
      statusBadge.className = 'badge badge-success';
    }
  } catch (err) {
    statusBadge.textContent = '● Backend Offline (Start FastAPI)';
    statusBadge.className = 'badge badge-danger';
  }
}

// 2. Load Stored Financial Profile & Transactions
async function loadFinancialData() {
  try {
    const res = await fetch(`${API_BASE}/api/financial-data`);
    if (!res.ok) return;
    const data = await res.json();
    
    currentProfile = data.profile;
    updateOverviewCards(data.profile);
    renderInitialBudgets(data.budgets);
    renderTransactions(data.transactions);
  } catch (err) {
    console.error('Failed to load initial data:', err);
  }
}

function updateOverviewCards(profile) {
  if (!profile) return;
  
  document.getElementById('val-balance').textContent = `₹${Number(profile.current_balance).toLocaleString()}`;
  document.getElementById('val-income').textContent = `₹${Number(profile.monthly_income).toLocaleString()}`;
  
  const surplus = profile.monthly_income - profile.monthly_expenses;
  const surplusEl = document.getElementById('val-surplus');
  if (surplus >= 0) {
    surplusEl.textContent = `Net Surplus: +₹${surplus.toLocaleString()}/mo`;
    surplusEl.className = 'metric-sub text-success';
  } else {
    surplusEl.textContent = `Net Deficit: -₹${Math.abs(surplus).toLocaleString()}/mo`;
    surplusEl.className = 'metric-sub text-warning';
  }
  
  const savingsPct = Math.min(100, Math.max(0, Math.round((profile.current_savings / profile.savings_goal) * 100)));
  document.getElementById('val-savings').innerHTML = `₹${Number(profile.current_savings).toLocaleString()} <small class="text-muted">/ ₹${Number(profile.savings_goal).toLocaleString()}</small>`;
  document.getElementById('savings-progress-bar').style.width = `${savingsPct}%`;
  
  const shortfall = Math.max(0, profile.savings_goal - profile.current_savings);
  const months = surplus > 0 ? Math.ceil(shortfall / surplus) : '∞';
  document.getElementById('savings-gap-text').textContent = `Goal Shortfall: ₹${shortfall.toLocaleString()} (~${months} months away)`;
  
  if (profile.planned_purchase) {
    document.getElementById('val-purchase').textContent = `${profile.planned_purchase.item}: ₹${Number(profile.planned_purchase.amount).toLocaleString()}`;
  }
  document.getElementById('val-bills').textContent = `Upcoming Bills: ₹${Number(profile.upcoming_bills || 5000).toLocaleString()}`;
}

// 3. Trigger Full 3-Agent Workflow
async function runAIAnalysis() {
  const runBtn = document.getElementById('run-analysis-btn');
  const originalHtml = runBtn.innerHTML;
  runBtn.disabled = true;
  runBtn.innerHTML = `<span class="btn-icon">⏳</span> Analyzing via AI...`;

  try {
    const res = await fetch(`${API_BASE}/api/analyze`, { method: 'POST' });
    if (!res.ok) throw new Error('Analysis request failed');
    const result = await res.json();

    // Render outputs from all 3 agents
    renderAgent1(result.analyzer);
    renderAgent2(result.planner);
    renderAgent3(result.alert_action);
  } catch (err) {
    alert('Error running AI workflow. Please verify FastAPI backend is running.');
    console.error(err);
  } finally {
    runBtn.disabled = false;
    runBtn.innerHTML = originalHtml;
  }
}

// Render Agent 1 Output
function renderAgent1(analyzer) {
  if (!analyzer) return;

  // Render Budget Utilization
  const budgetList = document.getElementById('budget-bars-list');
  budgetList.innerHTML = '';
  (analyzer.budget_analysis || []).forEach(b => {
    const pct = Math.round(b.percentage_used);
    const isExceeded = pct >= 100;
    const isWarning = pct >= 75 && !isExceeded;
    
    let fillClass = 'progress-fill';
    let badgeHtml = '';
    if (isExceeded) {
      fillClass += ' danger';
      badgeHtml = '<span class="badge badge-danger">Exceeded</span>';
    } else if (isWarning) {
      fillClass += ' warning';
      badgeHtml = '<span class="badge badge-warning">Warning</span>';
    }

    const item = document.createElement('div');
    item.className = 'budget-bar-item';
    item.innerHTML = `
      <div class="budget-bar-header">
        <span>${b.budget_name} ${badgeHtml}</span>
        <span>₹${b.spending.toLocaleString()} / ₹${b.budget_amount.toLocaleString()} (${pct}%)</span>
      </div>
      <div class="progress-track">
        <div class="${fillClass}" style="width: ${Math.min(100, pct)}%"></div>
      </div>
    `;
    budgetList.appendChild(item);
  });

  // Render Categorized Transactions
  if (analyzer.categorized_transactions) {
    renderTransactions(analyzer.categorized_transactions);
  }
}

function renderInitialBudgets(budgets) {
  if (!budgets) return;
  const budgetList = document.getElementById('budget-bars-list');
  budgetList.innerHTML = '';
  budgets.forEach(b => {
    const item = document.createElement('div');
    item.className = 'budget-bar-item';
    item.innerHTML = `
      <div class="budget-bar-header">
        <span>${b.category}</span>
        <span>Limit: ₹${Number(b.amount).toLocaleString()}</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" style="width: 0%"></div>
      </div>
    `;
    budgetList.appendChild(item);
  });
}

function renderTransactions(txList) {
  const tbody = document.getElementById('transactions-table-body');
  tbody.innerHTML = '';
  (txList || []).forEach(tx => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${tx.merchant}</strong></td>
      <td><span class="badge badge-info">${tx.category || 'Pending'}</span></td>
      <td>₹${Number(tx.amount).toLocaleString()}</td>
      <td><span class="badge ${tx.confidence === 'high' ? 'badge-success' : 'badge-neutral'}">${tx.confidence || 'medium'}</span></td>
      <td style="text-align: center;">
        <button class="btn-delete-tx" onclick="handleDeleteTransaction('${tx.id}')" title="Delete transaction">🗑️</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Render Agent 2 Output
function renderAgent2(planner) {
  if (!planner) return;

  // Affordability Verdict Box
  const verdictTag = document.getElementById('verdict-tag');
  const verdictDesc = document.getElementById('verdict-details');

  if (planner.affordability_analysis) {
    const aff = planner.affordability_analysis;
    const isAffordable = aff.affordable;
    verdictTag.textContent = isAffordable ? 'Decision: Affordable with Caution' : 'Decision: High Liquidity Risk';
    verdictTag.className = isAffordable ? 'verdict-tag text-warning' : 'verdict-tag text-danger';
    verdictDesc.textContent = aff.verdict;
  }

  // Cash Flow Projections
  const forecastGrid = document.getElementById('forecast-grid');
  forecastGrid.innerHTML = '';
  if (planner.cash_flow) {
    const cf = planner.cash_flow;
    const cards = [
      { days: '30 Days', before: cf.forecast_30_days_before, after: cf.forecast_30_days_after },
      { days: '60 Days', before: cf.forecast_60_days_before, after: cf.forecast_60_days_after },
      { days: '90 Days', before: cf.forecast_90_days_before, after: cf.forecast_90_days_after }
    ];

    cards.forEach(c => {
      const col = document.createElement('div');
      col.className = 'forecast-col';
      const afterClass = (c.after || 0) < 0 ? 'text-danger' : 'forecast-after';
      col.innerHTML = `
        <h4>${c.days}</h4>
        <div class="forecast-before">₹${Number(c.before || 0).toLocaleString()}</div>
        <div class="${afterClass}">After Buy: ₹${Number(c.after || 0).toLocaleString()}</div>
      `;
      forecastGrid.appendChild(col);
    });
  }

  // Recommendations
  const recList = document.getElementById('recommendations-list');
  recList.innerHTML = '';
  (planner.recommendations || []).forEach(r => {
    const li = document.createElement('li');
    li.textContent = r;
    recList.appendChild(li);
  });
}

// Render Agent 3 Output & Action Confirmation UI
function renderAgent3(alertAction) {
  if (!alertAction) return;

  // Render Alerts
  const alertsContainer = document.getElementById('alerts-container');
  alertsContainer.innerHTML = '';
  
  (alertAction.alerts || []).forEach(a => {
    const alertDiv = document.createElement('div');
    const level = typeof a === 'string' ? 'warning' : (a.level || 'warning');
    const title = typeof a === 'string' ? 'Financial Alert' : a.title;
    const msg = typeof a === 'string' ? a : a.message;

    alertDiv.className = `alert-item ${level}`;
    alertDiv.innerHTML = `
      <div class="alert-icon">⚠️</div>
      <div class="alert-content">
        <strong>${title}</strong>
        <p>${msg}</p>
      </div>
    `;
    alertsContainer.appendChild(alertDiv);
  });

  // Handle Mock Action Confirmation Box
  const confirmBox = document.getElementById('confirmation-box');
  const banner = document.getElementById('action-status-banner');
  banner.className = 'status-banner hidden';

  if (alertAction.requires_confirmation && alertAction.action) {
    currentPendingAction = alertAction.action;
    document.getElementById('confirm-action-title').textContent = 'Action Required: Reserve Funds';
    document.getElementById('confirm-action-desc').textContent = 
      alertAction.user_message || alertAction.action.description || 'Simulate reserving funds for upcoming expenses.';
    confirmBox.classList.remove('hidden');
  } else {
    confirmBox.classList.add('hidden');
  }
}

// 4. Handle Mock Action Confirmation (Confirm vs Dismiss)
async function handleActionDecision(confirmed) {
  if (!currentPendingAction) return;

  const payload = {
    action_type: currentPendingAction.type || 'reserve_bill_funds',
    confirmed: confirmed,
    amount: currentPendingAction.amount || 5000,
    description: currentPendingAction.description
  };

  try {
    const res = await fetch(`${API_BASE}/api/action/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Action confirmation request failed');
    const result = await res.json();

    // Hide confirmation box and show status banner
    document.getElementById('confirmation-box').classList.add('hidden');
    const banner = document.getElementById('action-status-banner');
    banner.classList.remove('hidden');

    if (result.action_executed) {
      banner.className = 'status-banner success';
      banner.innerHTML = `✓ <strong>Mock Action Successful:</strong> ${result.message}`;
      // Update UI balance & reload data
      document.getElementById('val-balance').textContent = `₹${result.updated_balance.toLocaleString()}`;
      loadFinancialData();
    } else {
      banner.className = 'status-banner cancelled';
      banner.innerHTML = `ℹ️ <strong>Dismissed:</strong> ${result.message}`;
    }

    currentPendingAction = null;
  } catch (err) {
    alert('Error processing mock action.');
    console.error(err);
  }
}

// 5. Dynamic Handlers: Add Expense, Edit Profile, Delete Expense, Reset Demo
async function handleAddTransaction(e) {
  e.preventDefault();
  const merchant = document.getElementById('tx-merchant').value.trim();
  const amount = parseFloat(document.getElementById('tx-amount').value);
  const category = document.getElementById('tx-category').value;
  const date = document.getElementById('tx-date').value;

  if (!merchant || isNaN(amount)) return;

  try {
    const res = await fetch(`${API_BASE}/api/financial-data/transactions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        merchant: merchant,
        amount: amount,
        category: category || null,
        date: date || null
      })
    });

    if (!res.ok) throw new Error('Failed to add transaction');
    
    document.getElementById('modal-add-tx').classList.add('hidden');
    await loadFinancialData();
    // Automatically trigger AI re-analysis on the new data
    runAIAnalysis();
  } catch (err) {
    alert('Error saving new expense.');
    console.error(err);
  }
}

async function handleUpdateProfile(e) {
  e.preventDefault();
  const balance = parseFloat(document.getElementById('prof-balance').value);
  const income = parseFloat(document.getElementById('prof-income').value);
  const expenses = parseFloat(document.getElementById('prof-expenses').value);
  const bills = parseFloat(document.getElementById('prof-bills').value);
  const savings = parseFloat(document.getElementById('prof-savings').value);
  const goal = parseFloat(document.getElementById('prof-savings-goal').value);
  const item = document.getElementById('prof-item').value.trim();
  const itemAmount = parseFloat(document.getElementById('prof-item-amount').value);

  const updatedProfile = {
    current_balance: balance,
    monthly_income: income,
    monthly_expenses: expenses,
    upcoming_bills: bills,
    current_savings: savings,
    savings_goal: goal,
    planned_purchase: {
      item: item || 'Laptop',
      amount: itemAmount || 50000
    }
  };

  try {
    const res = await fetch(`${API_BASE}/api/financial-data/profile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedProfile)
    });

    if (!res.ok) throw new Error('Failed to update profile');
    
    document.getElementById('modal-edit-profile').classList.add('hidden');
    await loadFinancialData();
    // Automatically trigger AI re-analysis on the new profile
    runAIAnalysis();
  } catch (err) {
    alert('Error updating profile.');
    console.error(err);
  }
}

async function handleDeleteTransaction(txId) {
  if (!confirm('Are you sure you want to remove this transaction?')) return;

  try {
    const res = await fetch(`${API_BASE}/api/financial-data/transactions/${txId}`, {
      method: 'DELETE'
    });

    if (!res.ok) throw new Error('Failed to delete transaction');
    
    await loadFinancialData();
    runAIAnalysis();
  } catch (err) {
    alert('Error deleting transaction.');
    console.error(err);
  }
}

async function handleResetDemo() {
  if (!confirm('Reset all financial data back to the original demo values?')) return;

  try {
    const res = await fetch(`${API_BASE}/api/financial-data/reset`, {
      method: 'POST'
    });

    if (!res.ok) throw new Error('Failed to reset demo data');
    
    await loadFinancialData();
    runAIAnalysis();
  } catch (err) {
    alert('Error resetting demo data.');
    console.error(err);
  }
}
