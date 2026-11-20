/**
 * SplitTrip Pro — Interactive Frontend Client
 * Powers trip management, custom splits, debt simplification, and visualizations.
 */

const state = {
  trips: [],
  activeTripId: null,
  activeTrip: null,
  currencySymbol: "$",
  categories: [],
  friends: [],
  expenses: [],
  people: [],
  settle: null,
  settlements: [],
  analytics: null,
  editingFriendId: null,
  editingExpenseId: null,
  activeTab: "tab-expenses",
  searchTerm: "",
  categoryFilter: "",
};

// DOM Elements
const tripSelect = document.querySelector("#trip-select");
const btnNewTrip = document.querySelector("#btn-new-trip");
const btnEditTrip = document.querySelector("#btn-edit-trip");
const btnExportCsv = document.querySelector("#btn-export-csv");
const btnShareWhatsapp = document.querySelector("#btn-share-whatsapp");
const themeToggle = document.querySelector("#theme-toggle");

const friendForm = document.querySelector("#friend-form");
const friendName = document.querySelector("#friend-name");
const friendList = document.querySelector("#friend-list");
const friendChecks = document.querySelector("#friend-checks");

const expenseForm = document.querySelector("#expense-form");
const expenseList = document.querySelector("#expense-list");
const expenseSearch = document.querySelector("#expense-search");
const expenseCatFilter = document.querySelector("#expense-cat-filter");
const expenseSubmit = document.querySelector("#expense-submit");
const expenseCancel = document.querySelector("#expense-cancel");
const expensePayer = document.querySelector("#expense-payer");
const expenseCategory = document.querySelector("#expense-category");
const customSplitsContainer = document.querySelector("#custom-splits-container");
const customSplitsFields = document.querySelector("#custom-splits-fields");
const splitDifferenceHint = document.querySelector("#split-difference-hint");

const peopleView = document.querySelector("#people");
const settleResult = document.querySelector("#settle-result");
const settleButton = document.querySelector("#settle-button");
const startOverButton = document.querySelector("#start-over");
const startOverConfirm = document.querySelector("#start-over-confirm");
const confirmClear = document.querySelector("#confirm-clear");
const cancelClear = document.querySelector("#cancel-clear");

const simplifiedDebtsList = document.querySelector("#simplified-debts-list");
const netBalancesTable = document.querySelector("#net-balances-table");
const settlementsHistoryList = document.querySelector("#settlements-history-list");
const btnRecordPayment = document.querySelector("#btn-record-payment");

const modalTrip = document.querySelector("#modal-trip");
const tripForm = document.querySelector("#trip-form");
const tripModalClose = document.querySelector("#trip-modal-close");

const modalPayment = document.querySelector("#modal-payment");
const paymentForm = document.querySelector("#payment-form");
const paymentModalClose = document.querySelector("#payment-modal-close");

// Initialize on page load
document.addEventListener("DOMContentLoaded", initApp);

async function initApp() {
  setupTheme();
  setupEventListeners();
  setupDateDefaults();

  try {
    await loadInitialData();
  } catch (error) {
    showToast("Error loading trip data: " + error.message, "danger");
  }
}

function setupTheme() {
  const saved = localStorage.getItem("splittrip_theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
  themeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("splittrip_theme", next);
  });
}

function setupDateDefaults() {
  const today = new Date().toISOString().split("T")[0];
  const dateInput = document.querySelector("#expense-date");
  if (dateInput && !dateInput.value) {
    dateInput.value = today;
  }
  const paymentDate = document.querySelector("#payment-date");
  if (paymentDate && !paymentDate.value) {
    paymentDate.value = today;
  }
}

function setupEventListeners() {
  // Tabs
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  // Trip selection
  tripSelect.addEventListener("change", (e) => {
    state.activeTripId = parseInt(e.target.value, 10);
    localStorage.setItem("splittrip_active_trip", state.activeTripId);
    loadTripData();
  });

  btnNewTrip.addEventListener("click", openNewTripModal);
  btnEditTrip.addEventListener("click", openEditTripModal);
  tripModalClose.addEventListener("click", () => modalTrip.close());
  tripForm.addEventListener("submit", handleTripSave);

  // Export & Share
  btnExportCsv.addEventListener("click", handleExportCsv);
  btnShareWhatsapp.addEventListener("click", handleShareWhatsapp);

  // Friends & Expenses
  friendForm.addEventListener("submit", handleAddFriend);
  friendList.addEventListener("click", handleFriendAction);

  expenseForm.addEventListener("submit", handleSaveExpense);
  expenseCancel.addEventListener("click", cancelExpenseEdit);
  expenseList.addEventListener("click", handleExpenseAction);

  expenseSearch.addEventListener("input", (e) => {
    state.searchTerm = e.target.value.toLowerCase().trim();
    renderExpenses();
  });

  expenseCatFilter.addEventListener("change", (e) => {
    state.categoryFilter = e.target.value;
    renderExpenses();
  });

  // Split mode change listeners
  document.querySelectorAll('input[name="split_type"]').forEach((radio) => {
    radio.addEventListener("change", updateSplitModeUI);
  });

  // Settle Actions
  settleButton.addEventListener("click", () => loadTripData());
  startOverButton.addEventListener("click", () => {
    clearError("trip-error");
    startOverConfirm.hidden = false;
  });
  cancelClear.addEventListener("click", () => {
    startOverConfirm.hidden = true;
  });
  confirmClear.addEventListener("click", handleClearTrip);

  // Payment Recording
  btnRecordPayment.addEventListener("click", openRecordPaymentModal);
  paymentModalClose.addEventListener("click", () => modalPayment.close());
  paymentForm.addEventListener("submit", handleSavePayment);
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-panel").forEach((p) => {
    p.classList.toggle("active", p.id === tabId);
  });

  if (tabId === "tab-analytics") {
    loadAnalytics();
  } else if (tabId === "tab-settle") {
    loadTripData();
  }
}

// -----------------------------------------------------------------
// DATA LOADING
// -----------------------------------------------------------------
async function loadInitialData() {
  const [tripsRes, catsRes] = await Promise.all([
    api("/api/trips"),
    api("/api/categories"),
  ]);

  state.trips = tripsRes.trips || [];
  state.categories = catsRes.categories || [];

  // Determine active trip
  const savedTripId = parseInt(localStorage.getItem("splittrip_active_trip"), 10);
  if (savedTripId && state.trips.some((t) => t.id === savedTripId)) {
    state.activeTripId = savedTripId;
  } else if (state.trips.length > 0) {
    state.activeTripId = state.trips[0].id;
  }

  renderTripDropdown();
  renderCategoryDropdowns();
  await loadTripData();
}

async function loadTripData() {
  if (!state.activeTripId) return;

  try {
    const tripUrl = `/api/trips/${state.activeTripId}`;
    const friendsUrl = `/api/friends?trip_id=${state.activeTripId}`;
    const expensesUrl = `/api/expenses?trip_id=${state.activeTripId}`;
    const peopleUrl = `/api/people?trip_id=${state.activeTripId}`;
    const settleUrl = `/api/settle?trip_id=${state.activeTripId}`;
    const settlementsUrl = `/api/settlements?trip_id=${state.activeTripId}`;

    const [trip, friendsRes, expensesRes, peopleRes, settleRes, settlementsRes] = await Promise.all([
      api(tripUrl),
      api(friendsUrl),
      api(expensesUrl),
      api(peopleUrl),
      api(settleUrl),
      api(settlementsUrl),
    ]);

    state.activeTrip = trip;
    state.currencySymbol = trip.currency_symbol || "$";
    state.friends = friendsRes.friends || [];
    state.expenses = expensesRes.expenses || [];
    state.people = peopleRes.friends || [];
    state.settle = settleRes;
    state.settlements = settlementsRes.settlements || [];

    updateCurrencySymbols();
    renderAll();
  } catch (err) {
    console.error("Failed to load trip details:", err);
  }
}

function updateCurrencySymbols() {
  document.querySelectorAll(".currency-symbol").forEach((el) => {
    el.textContent = state.currencySymbol;
  });
}

function renderAll() {
  renderStats();
  renderFriends();
  renderExpensePayerDropdown();
  renderFriendChecks();
  renderExpenses();
  renderPeopleView();
  renderSettle();
  if (state.activeTab === "tab-analytics") {
    loadAnalytics();
  }
}

// -----------------------------------------------------------------
// RENDERING
// -----------------------------------------------------------------
function renderTripDropdown() {
  tripSelect.innerHTML = state.trips
    .map((t) => `<option value="${t.id}" ${t.id === state.activeTripId ? "selected" : ""}>${escapeHtml(t.name)} (${t.currency_symbol})</option>`)
    .join("");
}

function renderCategoryDropdowns() {
  const catOptions = state.categories
    .map((c) => `<option value="${c.id}">${c.icon} ${escapeHtml(c.name)}</option>`)
    .join("");

  expenseCategory.innerHTML = catOptions;
  expenseCatFilter.innerHTML = '<option value="">All Categories</option>' + catOptions;
}

function renderStats() {
  if (!state.settle) return;
  const sym = state.currencySymbol;

  document.querySelector("#stat-total-spend").textContent = `${sym}${state.settle.tripTotal || "0.00"}`;
  document.querySelector("#stat-expense-count").textContent = `${state.expenses.length} expenses recorded`;

  // Organizer Net
  const orgBalance = state.settle.balances ? state.settle.balances.find((b) => b.is_organizer) : null;
  const statUserBalance = document.querySelector("#stat-user-balance");
  const statUserStatus = document.querySelector("#stat-user-status");

  if (orgBalance) {
    const netCents = orgBalance.net_cents;
    if (netCents > 0) {
      statUserBalance.textContent = `+${sym}${orgBalance.net}`;
      statUserBalance.style.color = "var(--success)";
      statUserStatus.textContent = "You are owed by the group";
    } else if (netCents < 0) {
      statUserBalance.textContent = `-${sym}${orgBalance.net.replace("-", "")}`;
      statUserBalance.style.color = "var(--danger)";
      statUserStatus.textContent = "You owe the group";
    } else {
      statUserBalance.textContent = `${sym}0.00`;
      statUserBalance.style.color = "var(--text-main)";
      statUserStatus.textContent = "All settled up";
    }
  }

  document.querySelector("#stat-people-count").textContent = state.friends.length + 1;

  const statSettleStatus = document.querySelector("#stat-settle-status");
  const statPendingDebts = document.querySelector("#stat-pending-debts");
  const pendingCount = (state.settle.simplifiedDebts || []).length;

  if (pendingCount === 0) {
    statSettleStatus.textContent = "✅ Fully Settled";
    statPendingDebts.textContent = "No debts pending";
  } else {
    statSettleStatus.textContent = `⏳ ${pendingCount} Debt${pendingCount > 1 ? "s" : ""}`;
    statPendingDebts.textContent = "Payments remaining";
  }
}

function renderFriends() {
  friendList.innerHTML = state.friends
    .map((f) => {
      const initial = f.name.charAt(0).toUpperCase();
      const color = f.color || "#4F46E5";
      return `
        <li class="friend-item" data-id="${f.id}">
          <div class="friend-identity">
            <span class="friend-avatar" style="background-color: ${color}">${initial}</span>
            <span class="friend-name-text">${escapeHtml(f.name)}</span>
          </div>
          <div class="row">
            <button type="button" class="btn btn-sm btn-outline edit-friend" data-id="${f.id}">Rename</button>
            <button type="button" class="btn btn-sm btn-danger remove-friend" data-id="${f.id}">Remove</button>
          </div>
        </li>
      `;
    })
    .join("");
}

function renderExpensePayerDropdown() {
  const orgName = (state.activeTrip && state.activeTrip.organizer_name) || "You (Organizer)";
  let html = `<option value="0">${escapeHtml(orgName)}</option>`;
  html += state.friends
    .map((f) => `<option value="${f.id}">${escapeHtml(f.name)}</option>`)
    .join("");
  expensePayer.innerHTML = html;
}

function renderFriendChecks() {
  friendChecks.innerHTML = state.friends
    .map((f) => {
      return `
        <label class="check-label">
          <input type="checkbox" value="${f.id}" checked>
          <span>${escapeHtml(f.name)}</span>
        </label>
      `;
    })
    .join("");

  // Re-attach listeners to update split inputs when checked friends change
  friendChecks.querySelectorAll("input").forEach((box) => {
    box.addEventListener("change", updateSplitModeUI);
  });
}

function updateSplitModeUI() {
  const splitType = document.querySelector('input[name="split_type"]:checked').value;
  if (splitType === "equal") {
    customSplitsContainer.hidden = true;
    return;
  }

  customSplitsContainer.hidden = false;
  const selectedFids = Array.from(friendChecks.querySelectorAll("input:checked")).map((cb) => parseInt(cb.value, 10));
  const participants = [{ id: 0, name: (state.activeTrip && state.activeTrip.organizer_name) || "You (Organizer)" }];
  state.friends.forEach((f) => {
    if (selectedFids.includes(f.id)) {
      participants.push({ id: f.id, name: f.name });
    }
  });

  let labelUnit = splitType === "exact" ? state.currencySymbol : (splitType === "percent" ? "%" : "shares");
  let placeholder = splitType === "exact" ? "0.00" : (splitType === "percent" ? "50" : "1");

  customSplitsFields.innerHTML = participants
    .map((p) => `
      <div class="form-group">
        <label for="split-val-${p.id}">${escapeHtml(p.name)} (${labelUnit})</label>
        <input type="text" id="split-val-${p.id}" data-pid="${p.id}" class="custom-split-input" placeholder="${placeholder}" autocomplete="off">
      </div>
    `)
    .join("");

  calculateSplitDifferenceHint();
  document.querySelectorAll(".custom-split-input").forEach((inp) => {
    inp.addEventListener("input", calculateSplitDifferenceHint);
  });
}

function calculateSplitDifferenceHint() {
  const splitType = document.querySelector('input[name="split_type"]:checked').value;
  const totalAmount = parseFloat(document.querySelector("#expense-amount").value) || 0;
  const inputs = Array.from(document.querySelectorAll(".custom-split-input"));

  if (splitType === "exact") {
    const currentSum = inputs.reduce((acc, inp) => acc + (parseFloat(inp.value) || 0), 0);
    const diff = totalAmount - currentSum;
    if (Math.abs(diff) < 0.001) {
      splitDifferenceHint.textContent = `✅ Shares match total: ${state.currencySymbol}${totalAmount.toFixed(2)}`;
      splitDifferenceHint.style.color = "var(--success)";
    } else {
      splitDifferenceHint.textContent = `Remaining to allocate: ${state.currencySymbol}${diff.toFixed(2)} of ${state.currencySymbol}${totalAmount.toFixed(2)}`;
      splitDifferenceHint.style.color = "var(--danger)";
    }
  } else if (splitType === "percent") {
    const currentSum = inputs.reduce((acc, inp) => acc + (parseFloat(inp.value) || 0), 0);
    const diff = 100 - currentSum;
    if (Math.abs(diff) < 0.05) {
      splitDifferenceHint.textContent = "✅ Percentages sum to 100%";
      splitDifferenceHint.style.color = "var(--success)";
    } else {
      splitDifferenceHint.textContent = `Remaining percentage: ${diff.toFixed(1)}%`;
      splitDifferenceHint.style.color = "var(--danger)";
    }
  } else {
    splitDifferenceHint.textContent = "Shares will be allocated proportionally based on given weights.";
    splitDifferenceHint.style.color = "var(--text-muted)";
  }
}

function renderExpenses() {
  let list = state.expenses;

  // Filter category
  if (state.categoryFilter) {
    const cid = parseInt(state.categoryFilter, 10);
    list = list.filter((e) => e.category_id === cid);
  }

  // Filter search
  if (state.searchTerm) {
    list = list.filter((e) =>
      e.description.toLowerCase().includes(state.searchTerm) ||
      (e.notes && e.notes.toLowerCase().includes(state.searchTerm))
    );
  }

  document.querySelector("#expense-filter-stats").textContent = `${list.length} shown`;

  if (list.length === 0) {
    expenseList.innerHTML = "";
    document.querySelector("#no-expenses-message").hidden = false;
    return;
  }

  document.querySelector("#no-expenses-message").hidden = true;
  const sym = state.currencySymbol;

  expenseList.innerHTML = list
    .map((e) => {
      const catIcon = e.category_icon || "💡";
      const payerName = e.payer_name || "You (Organizer)";
      const friendShare = e.friendShare || "0.00";

      return `
        <li class="expense-item" data-id="${e.id}">
          <div class="expense-main">
            <div class="expense-cat-icon">${catIcon}</div>
            <div>
              <div class="expense-desc">${escapeHtml(e.description)}</div>
              <div class="expense-meta">
                <span>📅 ${e.date}</span>
                <span class="expense-payer-tag">Paid by ${escapeHtml(payerName)}</span>
                <span>Split: ${e.split_type || "equal"}</span>
              </div>
            </div>
          </div>
          <div class="expense-right">
            <div class="expense-amount-box">
              <div class="expense-total">${sym}${e.amount}</div>
              <div class="expense-user-share">${sym}${friendShare} / share</div>
            </div>
            <div class="expense-actions">
              <button type="button" class="btn btn-sm btn-outline edit-expense" data-id="${e.id}">Edit</button>
              <button type="button" class="btn btn-sm btn-danger remove-expense" data-id="${e.id}">Delete</button>
            </div>
          </div>
        </li>
      `;
    })
    .join("");
}

function renderPeopleView() {
  const sym = state.currencySymbol;
  if (!state.people || state.people.length === 0) {
    peopleView.innerHTML = '<p class="hint">Add friends and expenses to view the spending breakdown.</p>';
    return;
  }

  peopleView.innerHTML = state.people
    .map((p) => {
      const expItems = (p.expenses || [])
        .map((x) => `
          <li class="person-expense-row">
            <span>${x.date} — ${escapeHtml(x.description)}</span>
            <strong>${sym}${x.share}</strong>
          </li>
        `)
        .join("");

      return `
        <div class="person-card">
          <div class="person-card-header">
            <span>👤 ${escapeHtml(p.name)}</span>
            <span class="badge">Owes total: ${sym}${p.total}</span>
          </div>
          <ul class="person-expense-sublist">
            ${expItems || '<li class="hint">No shared expenses</li>'}
          </ul>
        </div>
      `;
    })
    .join("");
}

function renderSettle() {
  if (!state.settle) return;
  const sym = state.currencySymbol;

  // PRD Worked Table
  let prdHtml = `
    <div class="balances-table-container">
      <table class="balances-table">
        <thead>
          <tr>
            <th>Friend</th>
            <th>Amount Owed (${sym})</th>
          </tr>
        </thead>
        <tbody>
  `;
  (state.settle.friends || []).forEach((f) => {
    prdHtml += `
      <tr>
        <td><strong>${escapeHtml(f.name)}</strong></td>
        <td>${sym}${f.owes}</td>
      </tr>
    `;
  });
  prdHtml += `
        <tr>
          <td><em>Your Own Share (not a debt)</em></td>
          <td>${sym}${state.settle.organizerShare}</td>
        </tr>
        <tr style="font-weight: 800; background: var(--bg-subtle);">
          <td>Trip Total</td>
          <td>${sym}${state.settle.tripTotal}</td>
        </tr>
      </tbody>
    </table>
  </div>
  `;
  settleResult.innerHTML = prdHtml;

  // Simplified Debts Cards
  const debts = state.settle.simplifiedDebts || [];
  if (debts.length === 0) {
    simplifiedDebtsList.innerHTML = '<p class="hint">🎉 Everyone is fully settled up! No payments owed.</p>';
  } else {
    simplifiedDebtsList.innerHTML = debts
      .map((d) => `
        <div class="debt-card">
          <div class="debt-transfer">
            <span class="debt-person">👤 ${escapeHtml(d.from_name)}</span>
            <span class="debt-arrow">➔ pays ➔</span>
            <span class="debt-person">👤 ${escapeHtml(d.to_name)}</span>
          </div>
          <div class="debt-amount">${sym}${d.amount}</div>
          <button type="button" class="btn btn-sm btn-primary btn-quick-settle"
                  data-from="${d.from_id}" data-to="${d.to_id}" data-amount="${d.amount}">
            Mark as Paid
          </button>
        </div>
      `)
      .join("");

    simplifiedDebtsList.querySelectorAll(".btn-quick-settle").forEach((btn) => {
      btn.addEventListener("click", () => {
        openRecordPaymentModal({
          from_id: btn.dataset.from,
          to_id: btn.dataset.to,
          amount: btn.dataset.amount,
        });
      });
    });
  }

  // Complete Net Balances Table
  if (state.settle.balances) {
    let bHtml = `
      <table class="balances-table">
        <thead>
          <tr>
            <th>Person</th>
            <th>Total Paid</th>
            <th>Total Share</th>
            <th>Net Balance</th>
          </tr>
        </thead>
        <tbody>
    `;
    state.settle.balances.forEach((b) => {
      let netClass = "net-zero";
      let prefix = "";
      if (b.net_cents > 0) {
        netClass = "net-positive";
        prefix = "+";
      } else if (b.net_cents < 0) {
        netClass = "net-negative";
      }
      bHtml += `
        <tr>
          <td><strong>${escapeHtml(b.name)}</strong></td>
          <td>${sym}${b.paid}</td>
          <td>${sym}${b.share}</td>
          <td class="${netClass}">${prefix}${sym}${b.net.replace("-", "")}</td>
        </tr>
      `;
    });
    bHtml += "</tbody></table>";
    netBalancesTable.innerHTML = bHtml;
  }

  // Settlement Payments History
  if (state.settlements.length === 0) {
    settlementsHistoryList.innerHTML = '<p class="hint">No settlements recorded yet.</p>';
  } else {
    settlementsHistoryList.innerHTML = state.settlements
      .map((s) => `
        <div class="settlement-history-item">
          <div>
            <strong>${escapeHtml(s.from_name)}</strong> paid <strong>${escapeHtml(s.to_name)}</strong>
            <span style="color: var(--success); font-weight: 700; margin-left: 0.5rem;">${sym}${s.amount}</span>
            <div class="hint" style="margin-bottom:0">${s.date} ${s.note ? "• " + escapeHtml(s.note) : ""}</div>
          </div>
          <button type="button" class="btn btn-sm btn-outline delete-settlement" data-id="${s.id}">Delete</button>
        </div>
      `)
      .join("");

    settlementsHistoryList.querySelectorAll(".delete-settlement").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this payment record?")) return;
        try {
          await api(`/api/settlements/${btn.dataset.id}`, { method: "DELETE" });
          showToast("Settlement payment removed.", "info");
          await loadTripData();
        } catch (err) {
          showToast(err.message, "danger");
        }
      });
    });
  }
}

// -----------------------------------------------------------------
// ANALYTICS & CHARTS
// -----------------------------------------------------------------
async function loadAnalytics() {
  if (!state.activeTripId) return;
  try {
    const stats = await api(`/api/analytics?trip_id=${state.activeTripId}`);
    state.analytics = stats;
    renderAnalyticsCharts();
  } catch (err) {
    console.error("Failed to load analytics:", err);
  }
}

function renderAnalyticsCharts() {
  if (!state.analytics) return;

  const cats = state.analytics.categories || [];
  const donutContainer = document.querySelector("#category-donut-chart");
  const legendContainer = document.querySelector("#category-legend");

  if (cats.length === 0) {
    donutContainer.innerHTML = '<div class="hint" style="text-align:center; padding-top:60px;">No expense data</div>';
    legendContainer.innerHTML = "";
    return;
  }

  // Build SVG Donut Chart
  let cumulativePercent = 0;
  let paths = "";
  let legendHtml = "";

  cats.forEach((cat) => {
    const percent = cat.percentage / 100;
    const [startX, startY] = getCoordinatesForPercent(cumulativePercent);
    cumulativePercent += percent;
    const [endX, endY] = getCoordinatesForPercent(cumulativePercent);
    const largeArcFlag = percent > 0.5 ? 1 : 0;
    const pathData = [
      `M ${startX} ${startY}`,
      `A 1 1 0 ${largeArcFlag} 1 ${endX} ${endY}`,
      `L 0 0`,
    ].join(" ");

    paths += `<path d="${pathData}" fill="${cat.color}"></path>`;
    legendHtml += `
      <div class="legend-item">
        <span class="legend-color-dot" style="background-color: ${cat.color}"></span>
        <span>${cat.icon} ${escapeHtml(cat.name)}: <strong>${cat.percentage}%</strong> (${state.currencySymbol}${cat.amount})</span>
      </div>
    `;
  });

  donutContainer.innerHTML = `
    <svg viewBox="-1.2 -1.2 2.4 2.4" style="transform: rotate(-90deg); width: 100%; height: 100%;">
      ${paths}
      <circle cx="0" cy="0" r="0.65" fill="var(--bg-card)"></circle>
    </svg>
  `;
  legendContainer.innerHTML = legendHtml;

  // Timeline Daily Bar Chart
  const timeline = state.analytics.timeline || [];
  const timelineContainer = document.querySelector("#timeline-chart");

  if (timeline.length === 0) {
    timelineContainer.innerHTML = '<p class="hint" style="margin:auto">No timeline data available.</p>';
    return;
  }

  const maxAmount = Math.max(...timeline.map((t) => t.amount_cents), 1);
  timelineContainer.innerHTML = timeline
    .map((t) => {
      const heightPercent = Math.max(10, (t.amount_cents / maxAmount) * 100);
      const shortDate = t.date.slice(5); // MM-DD
      return `
        <div class="timeline-bar-column">
          <div class="timeline-bar" style="height: ${heightPercent}%;" title="${t.date}: ${state.currencySymbol}${t.amount}"></div>
          <span class="timeline-date-label">${shortDate}</span>
        </div>
      `;
    })
    .join("");
}

function getCoordinatesForPercent(percent) {
  const x = Math.cos(2 * Math.PI * percent);
  const y = Math.sin(2 * Math.PI * percent);
  return [x, y];
}

// -----------------------------------------------------------------
// EVENT HANDLERS
// -----------------------------------------------------------------
async function handleAddFriend(e) {
  e.preventDefault();
  clearError("friend-error");
  const name = friendName.value.trim();

  try {
    await api("/api/friends", {
      method: "POST",
      body: JSON.stringify({
        trip_id: state.activeTripId,
        name,
      }),
    });
    friendName.value = "";
    showToast(`Added ${name} to group!`, "success");
    await loadTripData();
  } catch (err) {
    showError("friend-error", err.message);
  }
}

async function handleFriendAction(e) {
  const friendId = parseInt(e.target.dataset.id, 10);
  if (!friendId) return;

  if (e.target.classList.contains("remove-friend")) {
    if (!confirm("Are you sure you want to remove this friend?")) return;
    try {
      await api(`/api/friends/${friendId}`, { method: "DELETE" });
      showToast("Friend removed.", "info");
      await loadTripData();
    } catch (err) {
      alert(err.message);
    }
  } else if (e.target.classList.contains("edit-friend")) {
    const friend = state.friends.find((f) => f.id === friendId);
    if (!friend) return;
    const newName = prompt("Rename friend:", friend.name);
    if (!newName || newName.trim() === "" || newName.trim() === friend.name) return;

    try {
      await api(`/api/friends/${friendId}`, {
        method: "PATCH",
        body: JSON.stringify({ name: newName.trim() }),
      });
      showToast("Friend renamed.", "success");
      await loadTripData();
    } catch (err) {
      alert(err.message);
    }
  }
}

async function handleSaveExpense(e) {
  e.preventDefault();
  clearError("expense-error");

  const date = document.querySelector("#expense-date").value;
  const description = document.querySelector("#expense-description").value.trim();
  const amount = document.querySelector("#expense-amount").value.trim();
  const payer_id = parseInt(expensePayer.value, 10);
  const category_id = parseInt(expenseCategory.value, 10);
  const split_type = document.querySelector('input[name="split_type"]:checked').value;

  const friendIds = Array.from(friendChecks.querySelectorAll("input:checked")).map((cb) => parseInt(cb.value, 10));

  let custom_splits = null;
  if (split_type !== "equal") {
    custom_splits = {};
    document.querySelectorAll(".custom-split-input").forEach((inp) => {
      custom_splits[inp.dataset.pid] = inp.value.trim();
    });
  }

  const payload = {
    trip_id: state.activeTripId,
    date,
    description,
    amount,
    payer_id,
    category_id,
    split_type,
    custom_splits,
    friendIds,
  };

  const editingId = state.editingExpenseId;
  try {
    await api(editingId ? `/api/expenses/${editingId}` : "/api/expenses", {
      method: editingId ? "PATCH" : "POST",
      body: JSON.stringify(payload),
    });

    cancelExpenseEdit();
    showToast(editingId ? "Expense updated!" : "Expense recorded!", "success");
    await loadTripData();
  } catch (err) {
    showError("expense-error", err.message);
  }
}

function handleExpenseAction(e) {
  const expenseId = parseInt(e.target.dataset.id, 10);
  if (!expenseId) return;

  if (e.target.classList.contains("remove-expense")) {
    if (!confirm("Are you sure you want to delete this expense?")) return;
    api(`/api/expenses/${expenseId}`, { method: "DELETE" })
      .then(() => {
        showToast("Expense deleted.", "info");
        return loadTripData();
      })
      .catch((err) => alert(err.message));
  } else if (e.target.classList.contains("edit-expense")) {
    startEditExpense(expenseId);
  }
}

function startEditExpense(expenseId) {
  const exp = state.expenses.find((x) => x.id === expenseId);
  if (!exp) return;

  state.editingExpenseId = expenseId;
  document.querySelector("#expense-date").value = exp.date;
  document.querySelector("#expense-description").value = exp.description;
  document.querySelector("#expense-amount").value = exp.amount;
  expensePayer.value = exp.payer_id;
  if (exp.category_id) {
    expenseCategory.value = exp.category_id;
  }

  const splitRadio = document.querySelector(`input[name="split_type"][value="${exp.split_type || "equal"}"]`);
  if (splitRadio) splitRadio.checked = true;

  friendChecks.querySelectorAll("input").forEach((cb) => {
    cb.checked = (exp.friendIds || []).includes(parseInt(cb.value, 10));
  });

  updateSplitModeUI();

  expenseSubmit.textContent = "Save changes";
  expenseCancel.hidden = false;
  document.querySelector("#expenses-heading").textContent = "Edit Expense";
  document.querySelector("#quick-expense-section").scrollIntoView({ behavior: "smooth" });
}

function cancelExpenseEdit() {
  state.editingExpenseId = null;
  expenseForm.reset();
  setupDateDefaults();
  expenseSubmit.textContent = "Add expense";
  expenseCancel.hidden = true;
  document.querySelector("#expenses-heading").textContent = "Add Expense";
  document.querySelector('input[name="split_type"][value="equal"]').checked = true;
  customSplitsContainer.hidden = true;
  friendChecks.querySelectorAll("input").forEach((cb) => (cb.checked = true));
  clearError("expense-error");
}

async function handleClearTrip() {
  clearError("trip-error");
  try {
    await api(`/api/trips/${state.activeTripId}/clear`, { method: "POST" });
    startOverConfirm.hidden = true;
    showToast("Trip cleared back to empty.", "info");
    await loadTripData();
  } catch (err) {
    showError("trip-error", err.message);
  }
}

// -----------------------------------------------------------------
// TRIP MODAL & SETTINGS
// -----------------------------------------------------------------
function openNewTripModal() {
  document.querySelector("#modal-trip-title").textContent = "Create New Trip";
  document.querySelector("#trip-name").value = "";
  document.querySelector("#trip-currency-symbol").value = "$";
  document.querySelector("#trip-currency-code").value = "USD";
  document.querySelector("#trip-organizer-name").value = "You (Organizer)";
  document.querySelector("#trip-notes").value = "";
  modalTrip.dataset.mode = "create";
  modalTrip.showModal();
}

function openEditTripModal() {
  if (!state.activeTrip) return;
  document.querySelector("#modal-trip-title").textContent = "Edit Trip Settings";
  document.querySelector("#trip-name").value = state.activeTrip.name;
  document.querySelector("#trip-currency-symbol").value = state.activeTrip.currency_symbol || "$";
  document.querySelector("#trip-currency-code").value = state.activeTrip.currency_code || "USD";
  document.querySelector("#trip-organizer-name").value = state.activeTrip.organizer_name || "You (Organizer)";
  document.querySelector("#trip-notes").value = state.activeTrip.notes || "";
  modalTrip.dataset.mode = "edit";
  modalTrip.showModal();
}

async function handleTripSave(e) {
  e.preventDefault();
  clearError("trip-modal-error");

  const name = document.querySelector("#trip-name").value.trim();
  const currency_symbol = document.querySelector("#trip-currency-symbol").value.trim() || "$";
  const currency_code = document.querySelector("#trip-currency-code").value.trim() || "USD";
  const organizer_name = document.querySelector("#trip-organizer-name").value.trim() || "You (Organizer)";
  const notes = document.querySelector("#trip-notes").value.trim();

  const isEdit = modalTrip.dataset.mode === "edit";

  try {
    if (isEdit) {
      await api(`/api/trips/${state.activeTripId}`, {
        method: "PATCH",
        body: JSON.stringify({ name, currency_symbol, currency_code, organizer_name, notes }),
      });
      showToast("Trip settings saved!", "success");
    } else {
      const created = await api("/api/trips", {
        method: "POST",
        body: JSON.stringify({ name, currency_symbol, currency_code, organizer_name, notes }),
      });
      state.activeTripId = created.id;
      localStorage.setItem("splittrip_active_trip", created.id);
      showToast(`Created trip: ${name}`, "success");
    }
    modalTrip.close();
    await loadInitialData();
  } catch (err) {
    showError("trip-modal-error", err.message);
  }
}

// -----------------------------------------------------------------
// RECORD PAYMENT MODAL
// -----------------------------------------------------------------
function openRecordPaymentModal(prefill = null) {
  const orgName = (state.activeTrip && state.activeTrip.organizer_name) || "You (Organizer)";
  const participants = [{ id: 0, name: orgName }, ...state.friends];

  const fromSelect = document.querySelector("#payment-from");
  const toSelect = document.querySelector("#payment-to");

  fromSelect.innerHTML = participants.map((p) => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join("");
  toSelect.innerHTML = participants.map((p) => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join("");

  if (prefill) {
    fromSelect.value = prefill.from_id;
    toSelect.value = prefill.to_id;
    document.querySelector("#payment-amount").value = prefill.amount;
  } else {
    document.querySelector("#payment-amount").value = "";
  }

  setupDateDefaults();
  modalPayment.showModal();
}

async function handleSavePayment(e) {
  e.preventDefault();
  clearError("payment-modal-error");

  const from_id = parseInt(document.querySelector("#payment-from").value, 10);
  const to_id = parseInt(document.querySelector("#payment-to").value, 10);
  const amount = document.querySelector("#payment-amount").value.trim();
  const date = document.querySelector("#payment-date").value;
  const note = document.querySelector("#payment-note").value.trim();

  try {
    await api("/api/settlements", {
      method: "POST",
      body: JSON.stringify({
        trip_id: state.activeTripId,
        from_id,
        to_id,
        amount,
        date,
        note,
      }),
    });
    modalPayment.close();
    showToast("Settlement payment recorded!", "success");
    await loadTripData();
  } catch (err) {
    showError("payment-modal-error", err.message);
  }
}

// -----------------------------------------------------------------
// EXPORT & WHATSAPP SHARING
// -----------------------------------------------------------------
function handleExportCsv() {
  if (!state.activeTripId) return;
  window.location.href = `/api/trips/${state.activeTripId}/export/csv`;
}

function handleShareWhatsapp() {
  if (!state.settle || !state.activeTrip) return;
  const sym = state.currencySymbol;

  let text = `✈️ *Trip Settle Summary: ${state.activeTrip.name}*\n`;
  text += `💰 Total Trip Spend: ${sym}${state.settle.tripTotal}\n\n`;

  text += `📋 *What Each Person Owes:*\n`;
  (state.settle.friends || []).forEach((f) => {
    text += `• ${f.name}: ${sym}${f.owes}\n`;
  });
  text += `• Organizer Share: ${sym}${state.settle.organizerShare}\n\n`;

  const simplified = state.settle.simplifiedDebts || [];
  if (simplified.length > 0) {
    text += `⚡ *Simplified Payments:*\n`;
    simplified.forEach((d) => {
      text += `👉 ${d.from_name} pays ${d.to_name}: ${sym}${d.amount}\n`;
    });
  } else {
    text += `🎉 All balances are settled!\n`;
  }

  navigator.clipboard.writeText(text).then(() => {
    showToast("Copied settle summary to clipboard!", "success");
  }).catch(() => {});

  const encoded = encodeURIComponent(text);
  window.open(`https://api.whatsapp.com/send?text=${encoded}`, "_blank");
}

// -----------------------------------------------------------------
// UTILITIES
// -----------------------------------------------------------------
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Request failed with status ${res.status}`);
  }
  return data;
}

function escapeHtml(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function showError(elementId, message) {
  const el = document.getElementById(elementId);
  if (el) {
    el.textContent = message;
    el.hidden = false;
  }
}

function clearError(elementId) {
  const el = document.getElementById(elementId);
  if (el) {
    el.textContent = "";
    el.hidden = true;
  }
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
