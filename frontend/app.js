/* ============================================================
   Fish Distribution Manager — Frontend
   Uses ONLY the documented FastAPI endpoints.
   Persists view / filters / open trip across page refreshes.
   ============================================================ */

// ===== API Client =====
const API_BASE = '';

async function apiFetch(path, options = {}) {
  const config = {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  };

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, config);
  } catch (networkError) {
    throw new Error(`Network error: ${networkError.message}`);
  }

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body && body.detail) {
        if (Array.isArray(body.detail)) {
          message = body.detail.map(e => e.msg || JSON.stringify(e)).join('; ');
        } else if (typeof body.detail === 'string') {
          message = body.detail;
        } else {
          message = JSON.stringify(body.detail);
        }
      }
    } catch (_) { /* non-JSON error body */ }
    throw new Error(message);
  }

  if (response.status === 204) return null;
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

// ===== Helpers =====
const $ = (id) => document.getElementById(id);

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function isActive(record) {
  return record && record.is_active === true;
}

function debounce(fn, waitMs) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), waitMs);
  };
}

// ===== Persistent UI state =====
const PERSIST_KEY = 'fdm.ui-state.v1';

const persist = {
  load() {
    try {
      const raw = localStorage.getItem(PERSIST_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (_) { return null; }
  },
  save(patch) {
    try {
      const current = this.load() || {};
      const next = {
        ...current,
        ...patch,
        filters: { ...(current.filters || {}), ...(patch.filters || {}) },
      };
      localStorage.setItem(PERSIST_KEY, JSON.stringify(next));
    } catch (_) { /* storage disabled */ }
  },
  clearTrip() {
    try {
      const current = this.load() || {};
      delete current.tripId;
      localStorage.setItem(PERSIST_KEY, JSON.stringify(current));
    } catch (_) { /* noop */ }
  },
};

// ===== DOM refs =====
const healthButton = $('health-button');
const healthBadge  = $('health-badge');
const healthLabel  = $('health-label');

const views = {
  trips:        $('view-trips'),
  customers:    $('view-customers'),
  'fish-types': $('view-fish-types'),
  suppliers:    $('view-suppliers'),
};
const navLinks = document.querySelectorAll('.sidebar nav a');

// Trips
const tripsListContainer   = $('trips-list-container');
const tripsList            = $('trips-list');
const tripsLoading         = $('trips-loading');
const tripsEmpty           = $('trips-empty');
const createTripBtn        = $('create-trip-btn');
const tripWorkspace        = $('trip-workspace');
const tripTitle            = $('trip-title');
const tripMeta             = $('trip-meta');
const backToTripsBtn       = $('back-to-trips-btn');
const addCustomerToTripBtn = $('add-customer-to-trip-btn');
const addFishToTripBtn     = $('add-fish-to-trip-btn');
const copyCustomersBtn     = $('copy-customers-btn');

// Requirements
const reqLoading      = $('requirements-loading');
const reqError        = $('requirements-error');
const reqThead        = $('requirements-thead');
const reqTbody        = $('requirements-tbody');
const reqTfoot        = $('requirements-tfoot');
const reqEmpty        = $('requirements-empty');
const reqNoFish       = $('requirements-no-fish');
const shortfallWarn   = $('shortfall-warning');
const emptyAddCustomerBtn = $('empty-add-customer-btn');
const emptyAddFishBtn     = $('empty-add-fish-btn');

// Customers
const customersList      = $('customers-list');
const customersLoading   = $('customers-loading');
const customersEmpty     = $('customers-empty');
const createCustomerBtn  = $('create-customer-btn');
const customerSearch     = $('customer-search');
const customerSortBy     = $('customer-sort-by');
const customerSortOrder  = $('customer-sort-order');
const customerRefreshBtn = $('customer-refresh-btn');

// Fish types
const fishTypesList      = $('fish-types-list');
const fishTypesLoading   = $('fish-types-loading');
const fishTypesEmpty     = $('fish-types-empty');
const createFishTypeBtn  = $('create-fish-type-btn');
const fishTypeSearch     = $('fish-type-search');
const fishTypeSortBy     = $('fish-type-sort-by');
const fishTypeSortOrder  = $('fish-type-sort-order');
const fishTypeRefreshBtn = $('fish-type-refresh-btn');

// Suppliers
const suppliersList      = $('suppliers-list');
const suppliersLoading   = $('suppliers-loading');
const suppliersEmpty     = $('suppliers-empty');
const createSupplierBtn  = $('create-supplier-btn');
const supplierSearch     = $('supplier-search');
const supplierSortBy     = $('supplier-sort-by');
const supplierSortOrder  = $('supplier-sort-order');
const supplierRefreshBtn = $('supplier-refresh-btn');

// Modal
const modalOverlay = $('modal-overlay');
const modalTitle   = $('modal-title');
const modalBody    = $('modal-body');
const modalFooter  = $('modal-footer');
const modalClose   = $('modal-close');

// ===== State =====
const state = {
  currentTripId: null,
  customersCache: [],
  fishTypesCache: [],
  suppliersCache: [],
};

// ===== Query string builder =====
function buildListQuery({ search, sortBy, sortOrder }) {
  const params = new URLSearchParams();
  if (search && search.trim()) params.set('search', search.trim());
  if (sortBy)                  params.set('sort_by', sortBy);
  if (sortOrder)               params.set('sort_order', sortOrder);
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

// ===== Filter persistence helpers =====
function captureCustomerFilters() {
  return { search: customerSearch.value, sortBy: customerSortBy.value, sortOrder: customerSortOrder.value };
}
function captureFishTypeFilters() {
  return { search: fishTypeSearch.value, sortBy: fishTypeSortBy.value, sortOrder: fishTypeSortOrder.value };
}
function captureSupplierFilters() {
  return { search: supplierSearch.value, sortBy: supplierSortBy.value, sortOrder: supplierSortOrder.value };
}
function saveFiltersFor(viewName) {
  const filters = persist.load()?.filters || {};
  if (viewName === 'customers')  filters.customers = captureCustomerFilters();
  if (viewName === 'fish-types') filters.fishTypes = captureFishTypeFilters();
  if (viewName === 'suppliers')  filters.suppliers = captureSupplierFilters();
  persist.save({ filters });
}
function restoreFiltersFor(viewName) {
  const filters = persist.load()?.filters || {};
  if (viewName === 'customers' && filters.customers) {
    customerSearch.value    = filters.customers.search    || '';
    customerSortBy.value    = filters.customers.sortBy    || '';
    customerSortOrder.value = filters.customers.sortOrder || 'asc';
  }
  if (viewName === 'fish-types' && filters.fishTypes) {
    fishTypeSearch.value    = filters.fishTypes.search    || '';
    fishTypeSortBy.value    = filters.fishTypes.sortBy    || '';
    fishTypeSortOrder.value = filters.fishTypes.sortOrder || 'asc';
  }
  if (viewName === 'suppliers' && filters.suppliers) {
    supplierSearch.value    = filters.suppliers.search    || '';
    supplierSortBy.value    = filters.suppliers.sortBy    || '';
    supplierSortOrder.value = filters.suppliers.sortOrder || 'asc';
  }
}

// ===== Navigation =====
function switchView(name) {
  Object.entries(views).forEach(([key, el]) => {
    el.classList.toggle('active', key === name);
  });
  navLinks.forEach(link => {
    link.classList.toggle('active', link.dataset.view === name);
  });

  persist.save({ view: name });
  restoreFiltersFor(name);

  if (name === 'customers')  loadCustomers();
  if (name === 'fish-types') loadFishTypes();
  if (name === 'suppliers')  loadSuppliers();
  if (name === 'trips')      loadTrips();
}

navLinks.forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    if (link.dataset.view !== 'trips') persist.clearTrip();
    switchView(link.dataset.view);
  });
});

// ===== Health check (badge, not JSON) =====
function setHealthBadge(stateName, labelText) {
  healthBadge.classList.remove('ok', 'err', 'checking');
  if (stateName) healthBadge.classList.add(stateName);
  healthLabel.textContent = labelText;
}

async function runHealthCheck() {
  setHealthBadge('checking', 'Checking…');
  try {
    const data = await apiFetch('/api/health');
    // Backend returns {"status":"Ok"} — we don't display the raw JSON,
    // only a friendly badge.
    const ok = data && typeof data === 'object' && String(data.status || '').toLowerCase() === 'ok';
    if (ok) {
      setHealthBadge('ok', 'Online');
    } else {
      setHealthBadge('ok', 'Reachable');
    }
  } catch (err) {
    setHealthBadge('err', `Offline`);
    // Optional: log to console for debugging
    console.warn('Health check failed:', err.message);
  }
}

healthButton.addEventListener('click', runHealthCheck);

// ===== Confirm dialog =====
function confirmDialog({ title, message, confirmText, confirmClass = 'btn-danger' }) {
  return new Promise((resolve) => {
    const html = `<p>${escapeHtml(message)}</p>`;
    openModal(title, html, [
      { text: 'Cancel', class: 'btn-outline', action: () => { closeModal(); resolve(false); } },
      { text: confirmText, class: confirmClass, action: () => { closeModal(); resolve(true); } },
    ]);
  });
}

// ============================================================
// TRIPS
// ============================================================

async function loadTrips() {
  tripsLoading.classList.remove('hidden');
  tripsEmpty.classList.add('hidden');
  tripsList.innerHTML = '';
  tripsListContainer.classList.remove('hidden');

  try {
    const [trips, suppliers] = await Promise.all([
      apiFetch('/api/trips/'),
      apiFetch('/api/suppliers/').catch(() => []),
    ]);
    state.suppliersCache = suppliers || [];
    tripsLoading.classList.add('hidden');

    if (!Array.isArray(trips) || trips.length === 0) {
      tripsEmpty.classList.remove('hidden');
      return;
    }

    const supplierNameById = new Map(state.suppliersCache.map(s => [s.id, s.name]));

    tripsList.innerHTML = trips.map(trip => {
      const supplierName =
        supplierNameById.get(trip.supplier_id) ||
        (trip.supplier_id ? `Supplier #${trip.supplier_id}` : 'No supplier');
      const date   = trip.trip_date || 'No date';
      const status = trip.status || '—';

      return `
        <li data-trip-id="${trip.id}">
          <div class="trip-info">
            <h4>Trip #${trip.id}</h4>
            <p>${escapeHtml(String(date))} · ${escapeHtml(supplierName)}</p>
          </div>
          <span class="trip-status">${escapeHtml(status)}</span>
        </li>
      `;
    }).join('');

    tripsList.querySelectorAll('li').forEach(li => {
      li.addEventListener('click', () => openTrip(li.dataset.tripId));
    });
  } catch (err) {
    tripsLoading.classList.add('hidden');
    tripsListContainer.innerHTML =
      `<div class="error">Failed to load trips: ${escapeHtml(err.message)}</div>`;
  }
}

async function openTrip(tripId) {
  state.currentTripId = tripId;
  persist.save({ view: 'trips', tripId: String(tripId) });

  tripsListContainer.classList.add('hidden');
  tripWorkspace.classList.remove('hidden');
  tripTitle.textContent = `Trip #${tripId}`;
  tripMeta.textContent = 'Loading…';

  try {
    const trip = await apiFetch(`/api/trips/${tripId}`);
    let supplierName = trip.supplier_id ? `Supplier #${trip.supplier_id}` : 'No supplier';
    if (trip.supplier_id) {
      try {
        const supplier = await apiFetch(`/api/suppliers/${trip.supplier_id}`);
        supplierName = supplier.name;
      } catch (_) { /* fallback */ }
    }

    tripTitle.textContent = `Trip #${trip.id}`;
    tripMeta.textContent =
      `Date: ${trip.trip_date || 'N/A'} · Supplier: ${supplierName} · Status: ${trip.status || '—'}`;

    await loadRequirementsTable(tripId);
  } catch (err) {
    tripMeta.textContent = `Error: ${err.message}`;
    reqError.textContent = `Failed to load trip: ${err.message}`;
    reqError.classList.remove('hidden');
  }
}

backToTripsBtn.addEventListener('click', () => {
  state.currentTripId = null;
  persist.clearTrip();
  tripWorkspace.classList.add('hidden');
  tripsListContainer.classList.remove('hidden');
  loadTrips();
});

// ============================================================
// REQUIREMENTS TABLE
// Response schema (confirmed):
// {
//   trip_id,
//   fish_types: [{ id, name }],
//   customers: [{
//     trip_customer_id, customer_id, name, phone, address,
//     quantities: [{ fish_type_id, quantity_bags }],
//     total_bags
//   }],
//   fish_totals: [{
//     fish_type_id, quantity_bags,
//     planned_quantity_bags, effective_planned_quantity_bags,
//     shortfall_bags, shortfall_exists
//   }],
//   grand_total_bags
// }
// ============================================================

async function loadRequirementsTable(tripId) {
  reqLoading.classList.remove('hidden');
  reqError.classList.add('hidden');
  reqEmpty.classList.add('hidden');
  reqNoFish.classList.add('hidden');
  shortfallWarn.classList.add('hidden');
  reqThead.innerHTML = '';
  reqTbody.innerHTML = '';
  reqTfoot.innerHTML = '';

  try {
    const data = await apiFetch(`/api/trips/${tripId}/requirements-table`);
    reqLoading.classList.add('hidden');

    const fishTypes  = Array.isArray(data.fish_types)  ? data.fish_types  : [];
    const customers  = Array.isArray(data.customers)   ? data.customers   : [];
    const fishTotals = Array.isArray(data.fish_totals) ? data.fish_totals : [];

    if (customers.length === 0) { reqEmpty.classList.remove('hidden'); return; }
    if (fishTypes.length === 0) { reqNoFish.classList.remove('hidden'); return; }

    // Build a fast lookup for fish totals
    const totalsByFishId = new Map();
    fishTotals.forEach(ft => totalsByFishId.set(ft.fish_type_id, ft));

    // HEADER — fixed 3 + dynamic fish + total + actions
    let headHtml = `<tr><th>Customer</th><th>Mobile</th><th>Address</th>`;
    fishTypes.forEach(ft => {
      headHtml += `
        <th>
          <span class="fish-header">
            <span>${escapeHtml(ft.name)}</span>
            <button class="planned-edit-btn"
                    title="Edit planned quantity for ${escapeHtml(ft.name)}"
                    data-fish-type-id="${ft.id}"
                    data-fish-type-name="${escapeHtml(ft.name)}">✎</button>
          </span>
        </th>`;
    });
    headHtml += `<th>Customer Total</th><th>Actions</th></tr>`;
    reqThead.innerHTML = headHtml;

    // BODY
    let bodyHtml = '';
    customers.forEach(cust => {
      const customerId     = cust.customer_id;
      const tripCustomerId = cust.trip_customer_id;
      const name    = cust.name    || 'N/A';
      const phone   = cust.phone   || '—';
      const address = cust.address || '—';
      const total   = cust.total_bags ?? 0;

      bodyHtml += '<tr>';
      bodyHtml += `
        <td>
          <span class="customer-link"
                data-customer-id="${customerId}"
                data-trip-customer-id="${tripCustomerId}">
            ${escapeHtml(String(name))}
          </span>
        </td>`;
      bodyHtml += `<td>${escapeHtml(String(phone))}</td>`;
      bodyHtml += `<td>${escapeHtml(String(address))}</td>`;

      fishTypes.forEach(ft => {
        const qtyEntry = (cust.quantities || []).find(q => q.fish_type_id === ft.id);
        const qty = qtyEntry ? (qtyEntry.quantity_bags ?? 0) : 0;
        bodyHtml += `<td>${qty}</td>`;
      });

      bodyHtml += `<td><strong>${total}</strong></td>`;
      bodyHtml += `
        <td>
          <button class="btn btn-sm btn-outline edit-req-btn"
                  data-customer-id="${customerId}">
            Edit
          </button>
        </td>`;
      bodyHtml += '</tr>';
    });
    reqTbody.innerHTML = bodyHtml;

    // FOOTER — 3 rows:
    //  1) "Planned" (only if any planned > 0)
    //  2) "Fish Totals" (actuals)
    //  3) "Shortfall" (only if any shortfall_exists)
    const anyPlanned = fishTotals.some(t => (t.planned_quantity_bags ?? 0) > 0);
    const anyShortfall = fishTotals.some(t => t.shortfall_exists === true);

    let footHtml = '';

    if (anyPlanned) {
      footHtml += `<tr class="planned-row"><td colspan="3">Planned</td>`;
      fishTypes.forEach(ft => {
        const t = totalsByFishId.get(ft.id);
        const planned = t ? (t.effective_planned_quantity_bags ?? t.planned_quantity_bags ?? 0) : 0;
        footHtml += `<td>${planned}</td>`;
      });
      // Grand planned = sum of planned (we can compute; the API doesn't expose a total)
      const grandPlanned = fishTypes.reduce((sum, ft) => {
        const t = totalsByFishId.get(ft.id);
        return sum + (t ? (t.effective_planned_quantity_bags ?? t.planned_quantity_bags ?? 0) : 0);
      }, 0);
      footHtml += `<td>${grandPlanned}</td><td></td></tr>`;
    }

    footHtml += `<tr><td colspan="3" class="totals-label">Fish Totals</td>`;
    fishTypes.forEach(ft => {
      const t = totalsByFishId.get(ft.id);
      footHtml += `<td>${t ? (t.quantity_bags ?? 0) : 0}</td>`;
    });
    footHtml += `<td>${data.grand_total_bags ?? 0}</td><td></td></tr>`;

    if (anyShortfall) {
      footHtml += `<tr class="shortfall-row"><td colspan="3">Shortfall</td>`;
      fishTypes.forEach(ft => {
        const t = totalsByFishId.get(ft.id);
        const shortfall = t && t.shortfall_exists ? (t.shortfall_bags ?? 0) : 0;
        footHtml += `<td>${shortfall > 0 ? shortfall : '—'}</td>`;
      });
      const grandShortfall = fishTypes.reduce((sum, ft) => {
        const t = totalsByFishId.get(ft.id);
        return sum + (t && t.shortfall_exists ? (t.shortfall_bags ?? 0) : 0);
      }, 0);
      footHtml += `<td>${grandShortfall}</td><td></td></tr>`;
    }

    reqTfoot.innerHTML = footHtml;

    // Shortfall warning banner above the table
    if (anyShortfall) {
      const totalShortfall = fishTypes.reduce((sum, ft) => {
        const t = totalsByFishId.get(ft.id);
        return sum + (t && t.shortfall_exists ? (t.shortfall_bags ?? 0) : 0);
      }, 0);
      shortfallWarn.textContent =
        `⚠ Shortfall detected: ${totalShortfall} bag(s) below planned quantities.`;
      shortfallWarn.classList.remove('hidden');
    }

    // Handlers: customer name / edit requirements
    document.querySelectorAll('.customer-link').forEach(el => {
      el.addEventListener('click', () => openRequirementsModal(tripId, el.dataset.customerId));
    });
    document.querySelectorAll('.edit-req-btn').forEach(btn => {
      btn.addEventListener('click', () => openRequirementsModal(tripId, btn.dataset.customerId));
    });

    // Handlers: planned-quantity edit (pencil in header)
    document.querySelectorAll('.planned-edit-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const fishTypeId   = parseInt(btn.dataset.fishTypeId, 10);
        const fishTypeName = btn.dataset.fishTypeName;
        const t = totalsByFishId.get(fishTypeId);
        const currentPlanned = t ? (t.planned_quantity_bags ?? 0) : 0;
        openPlannedQuantityModal(tripId, fishTypeId, fishTypeName, currentPlanned);
      });
    });

  } catch (err) {
    reqLoading.classList.add('hidden');
    reqError.textContent = `Failed to load requirements: ${err.message}`;
    reqError.classList.remove('hidden');
  }
}

// ============================================================
// PLANNED QUANTITY EDITOR
// PATCH /api/trips/{trip_id}/fish-types/{fish_type_id}/planned-quantity
// Body: { planned_quantity_bags: <int> }
// ============================================================

function openPlannedQuantityModal(tripId, fishTypeId, fishTypeName, currentValue) {
  const html = `
    <p class="muted" style="margin-bottom:16px;">
      Set the planned quantity for <strong>${escapeHtml(fishTypeName)}</strong> on this trip.
    </p>
    <div class="form-group">
      <label>Planned quantity (bags)</label>
      <input type="number" min="0" step="1" id="planned-qty" value="${currentValue}">
      <div class="help-text">Set to 0 to clear the planned quantity.</div>
    </div>
    <div id="planned-qty-error" class="error hidden"></div>
  `;

  openModal(`Planned quantity — ${fishTypeName}`, html, [
    { text: 'Cancel', class: 'btn-outline', action: closeModal },
    {
      text: 'Save',
      class: 'btn-primary',
      action: async () => {
        const raw     = parseInt(document.getElementById('planned-qty').value, 10);
        const errorEl = document.getElementById('planned-qty-error');
        if (isNaN(raw) || raw < 0) {
          errorEl.textContent = 'Planned quantity must be a non-negative integer.';
          errorEl.classList.remove('hidden');
          return;
        }
        try {
          await apiFetch(
            `/api/trips/${tripId}/fish-types/${fishTypeId}/planned-quantity`,
            {
              method: 'PATCH',
              body: JSON.stringify({ planned_quantity_bags: raw }),
            }
          );
          closeModal();
          await loadRequirementsTable(tripId);
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.classList.remove('hidden');
        }
      },
    },
  ]);
}

// ============================================================
// REQUIREMENTS MODAL
// ============================================================

async function openRequirementsModal(tripId, customerId) {
  try {
    const [requirements, tableData] = await Promise.all([
      apiFetch(`/api/trips/${tripId}/customers/${customerId}/requirements`),
      apiFetch(`/api/trips/${tripId}/requirements-table`),
    ]);

    const tripFishTypes = Array.isArray(tableData.fish_types) ? tableData.fish_types : [];

    let html = '<form id="requirements-form">';
    if (tripFishTypes.length === 0) {
      html += '<p class="muted">No fish types are configured on this trip.</p>';
    } else {
      tripFishTypes.forEach(ft => {
        const existing = (requirements || []).find(r => r.fish_type_id === ft.id);
        const qty      = existing ? (existing.quantity_bags ?? 0) : 0;
        const reqId    = existing ? existing.id : '';
        html += `
          <div class="form-group">
            <label>${escapeHtml(ft.name)}</label>
            <input type="number" min="1" step="1"
                   name="fish_${ft.id}"
                   value="${qty}"
                   data-fish-type-id="${ft.id}"
                   data-requirement-id="${reqId}">
            <div class="help-text">Leave blank or 0 to skip.</div>
          </div>
        `;
      });
    }
    html += '</form>';
    html += '<div id="req-modal-error" class="error hidden"></div>';

    openModal('Edit Requirements', html, [
      { text: 'Cancel', class: 'btn-outline', action: closeModal },
      {
        text: 'Save',
        class: 'btn-primary',
        action: async () => {
          const form    = document.getElementById('requirements-form');
          const errorEl = document.getElementById('req-modal-error');
          errorEl.classList.add('hidden');

          const inputs = form.querySelectorAll('input[data-fish-type-id]');
          const tasks  = [];

          inputs.forEach(input => {
            const fishTypeId    = parseInt(input.dataset.fishTypeId, 10);
            const requirementId = input.dataset.requirementId;
            const raw           = parseInt(input.value, 10);
            const quantity      = isNaN(raw) ? 0 : raw;
            if (quantity <= 0) return;

            if (requirementId) {
              tasks.push(
                apiFetch(`/api/trips/${tripId}/customers/${customerId}/requirements/${requirementId}`, {
                  method: 'PATCH',
                  body: JSON.stringify({ quantity_bags: quantity }),
                })
              );
            } else {
              tasks.push(
                apiFetch(`/api/trips/${tripId}/customers/${customerId}/requirements`, {
                  method: 'POST',
                  body: JSON.stringify({ fish_type_id: fishTypeId, quantity_bags: quantity }),
                })
              );
            }
          });

          try {
            await Promise.all(tasks);
            closeModal();
            await loadRequirementsTable(tripId);
          } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
          }
        },
      },
    ]);
  } catch (err) {
    alert(`Failed to load requirements: ${err.message}`);
  }
}

// ============================================================
// ADD CUSTOMER TO TRIP
// ============================================================

addCustomerToTripBtn.addEventListener('click', addCustomerFlow);
emptyAddCustomerBtn.addEventListener('click', addCustomerFlow);

async function addCustomerFlow() {
  if (!state.currentTripId) return;
  try {
    const customers = await apiFetch('/api/customers/');
    state.customersCache = customers || [];
    if (!customers || customers.length === 0) {
      alert('No customers available. Create a customer first.');
      return;
    }

    const html = `
      <div class="form-group">
        <label>Search</label>
        <input type="text" id="add-cust-search" placeholder="Type to filter…">
      </div>
      <div class="form-group">
        <label>Select Customer</label>
        <select id="customer-select" size="8" style="height:auto;">
          ${customers.map(c => `
            <option value="${c.id}">
              ${escapeHtml(c.name)}${c.phone ? ' · ' + escapeHtml(c.phone) : ''}
              ${isActive(c) ? '' : ' (inactive)'}
            </option>
          `).join('')}
        </select>
      </div>
      <div id="add-customer-error" class="error hidden"></div>
    `;

    openModal('Add Customer to Trip', html, [
      { text: 'Cancel', class: 'btn-outline', action: closeModal },
      {
        text: 'Add to Trip',
        class: 'btn-primary',
        action: async () => {
          const select  = document.getElementById('customer-select');
          const errorEl = document.getElementById('add-customer-error');
          if (!select.value) {
            errorEl.textContent = 'Please select a customer.';
            errorEl.classList.remove('hidden');
            return;
          }
          try {
            await apiFetch(`/api/trips/${state.currentTripId}/customers`, {
              method: 'POST',
              body: JSON.stringify({ customer_id: parseInt(select.value, 10) }),
            });
            closeModal();
            await loadRequirementsTable(state.currentTripId);
          } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
          }
        },
      },
    ]);

    const searchInput = document.getElementById('add-cust-search');
    const selectEl    = document.getElementById('customer-select');
    searchInput.addEventListener('input', () => {
      const term = searchInput.value.toLowerCase();
      Array.from(selectEl.options).forEach(opt => {
        opt.style.display = opt.text.toLowerCase().includes(term) ? '' : 'none';
      });
    });
  } catch (err) {
    alert(`Failed to load customers: ${err.message}`);
  }
}

// ============================================================
// COPY CUSTOMERS FROM ANOTHER TRIP
// ============================================================

copyCustomersBtn.addEventListener('click', async () => {
  if (!state.currentTripId) return;
  try {
    const trips = await apiFetch('/api/trips/');
    const others = (trips || []).filter(t => String(t.id) !== String(state.currentTripId));
    if (others.length === 0) {
      alert('No other trips available to copy from.');
      return;
    }

    const html = `
      <div class="form-group">
        <label>Source Trip</label>
        <select id="copy-source-trip">
          ${others.map(t => `
            <option value="${t.id}">
              Trip #${t.id} · ${escapeHtml(String(t.trip_date || 'no date'))}
            </option>
          `).join('')}
        </select>
      </div>
      <p class="muted">All customers from the selected trip will be added. Duplicates are skipped by the backend.</p>
      <div id="copy-customers-error" class="error hidden"></div>
    `;

    openModal('Copy Customers From Trip', html, [
      { text: 'Cancel', class: 'btn-outline', action: closeModal },
      {
        text: 'Copy',
        class: 'btn-primary',
        action: async () => {
          const select  = document.getElementById('copy-source-trip');
          const errorEl = document.getElementById('copy-customers-error');
          try {
            await apiFetch(
              `/api/trips/${state.currentTripId}/customers/copy-from/${parseInt(select.value, 10)}`,
              { method: 'POST' }
            );
            closeModal();
            await loadRequirementsTable(state.currentTripId);
          } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
          }
        },
      },
    ]);
  } catch (err) {
    alert(`Failed to load trips: ${err.message}`);
  }
});

// ============================================================
// ADD FISH TYPE TO TRIP
// ============================================================

addFishToTripBtn.addEventListener('click', addFishTypeFlow);
emptyAddFishBtn.addEventListener('click', addFishTypeFlow);

async function addFishTypeFlow() {
  if (!state.currentTripId) return;
  try {
    const fishTypes = await apiFetch('/api/fish-types/');
    state.fishTypesCache = fishTypes || [];
    const activeFishTypes = (fishTypes || []).filter(isActive);
    if (activeFishTypes.length === 0) {
      alert('No active fish types available. Create one first.');
      return;
    }

    const html = `
      <div class="form-group">
        <label>Select Fish Type</label>
        <select id="fish-type-select">
          ${activeFishTypes.map(ft => `<option value="${ft.id}">${escapeHtml(ft.name)}</option>`).join('')}
        </select>
      </div>
      <div id="add-fish-error" class="error hidden"></div>
    `;

    openModal('Add Fish Type to Trip', html, [
      { text: 'Cancel', class: 'btn-outline', action: closeModal },
      {
        text: 'Add',
        class: 'btn-primary',
        action: async () => {
          const select  = document.getElementById('fish-type-select');
          const errorEl = document.getElementById('add-fish-error');
          try {
            await apiFetch(`/api/trips/${state.currentTripId}/fish-types`, {
              method: 'POST',
              body: JSON.stringify({ fish_type_id: parseInt(select.value, 10) }),
            });
            closeModal();
            await loadRequirementsTable(state.currentTripId);
          } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
          }
        },
      },
    ]);
  } catch (err) {
    alert(`Failed to load fish types: ${err.message}`);
  }
}

// ============================================================
// CREATE TRIP
// ============================================================

createTripBtn.addEventListener('click', async () => {
  try {
    const [suppliers, fishTypes] = await Promise.all([
      apiFetch('/api/suppliers/'),
      apiFetch('/api/fish-types/'),
    ]);
    state.suppliersCache = suppliers || [];
    state.fishTypesCache = fishTypes || [];

    const activeSuppliers = state.suppliersCache.filter(isActive);
    const activeFishTypes = state.fishTypesCache.filter(isActive);

    const html = `
      <div class="form-group"><label>Trip Date *</label><input type="date" id="trip-date" required></div>
      <div class="form-group">
        <label>Supplier *</label>
        <select id="trip-supplier" required>
          <option value="">Select supplier…</option>
          ${activeSuppliers.map(s => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label>Fish Types * <span class="muted">(select at least one)</span></label>
        <div class="checkbox-group">
          ${activeFishTypes.length === 0
            ? '<span class="muted">No active fish types available.</span>'
            : activeFishTypes.map(ft => `
                <label><input type="checkbox" value="${ft.id}" class="trip-fish-checkbox"> ${escapeHtml(ft.name)}</label>
              `).join('')}
        </div>
      </div>
      <div id="create-trip-error" class="error hidden"></div>
    `;

    openModal('Create New Trip', html, [
      { text: 'Cancel', class: 'btn-outline', action: closeModal },
      {
        text: 'Create Trip',
        class: 'btn-primary',
        action: async () => {
          const date         = document.getElementById('trip-date').value;
          const supplierVal  = document.getElementById('trip-supplier').value;
          const selectedFish = Array.from(document.querySelectorAll('.trip-fish-checkbox:checked'))
            .map(cb => parseInt(cb.value, 10));
          const errorEl      = document.getElementById('create-trip-error');

          if (!date)                     { errorEl.textContent = 'Trip date is required.'; errorEl.classList.remove('hidden'); return; }
          if (!supplierVal)              { errorEl.textContent = 'Supplier is required.'; errorEl.classList.remove('hidden'); return; }
          if (selectedFish.length === 0) { errorEl.textContent = 'Select at least one fish type.'; errorEl.classList.remove('hidden'); return; }

          try {
            await apiFetch('/api/trips/', {
              method: 'POST',
              body: JSON.stringify({
                trip_date: date,
                supplier_id: parseInt(supplierVal, 10),
                fish_type_ids: selectedFish,
              }),
            });
            closeModal();
            await loadTrips();
          } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
          }
        },
      },
    ]);
  } catch (err) {
    alert(`Failed to load form data: ${err.message}`);
  }
});

// ============================================================
// CUSTOMERS
// ============================================================

async function loadCustomers() {
  customersLoading.classList.remove('hidden');
  customersEmpty.classList.add('hidden');
  customersList.innerHTML = '';

  try {
    const qs = buildListQuery({
      search:    customerSearch.value,
      sortBy:    customerSortBy.value,
      sortOrder: customerSortOrder.value,
    });
    const customers = await apiFetch(`/api/customers/${qs}`);
    state.customersCache = customers || [];
    customersLoading.classList.add('hidden');

    if (!customers || customers.length === 0) {
      customersEmpty.classList.remove('hidden');
      return;
    }
    renderCustomers(customers);
  } catch (err) {
    customersLoading.classList.add('hidden');
    customersList.innerHTML =
      `<div class="error">Failed to load customers: ${escapeHtml(err.message)}</div>`;
  }
}

function renderCustomers(customers) {
  if (!customers || customers.length === 0) {
    customersEmpty.classList.remove('hidden');
    customersList.innerHTML = '';
    return;
  }
  customersEmpty.classList.add('hidden');

  customersList.innerHTML = customers.map(c => `
    <li class="${isActive(c) ? '' : 'list-item-inactive'}" data-customer-id="${c.id}">
      <div class="customer-info">
        <h4>${escapeHtml(c.name || 'Unnamed')}</h4>
        <p>${escapeHtml(c.phone || 'No phone')} · ${escapeHtml(c.address || 'No address')}</p>
      </div>
      <div class="row-actions">
        <span class="badge ${isActive(c) ? 'badge-active' : 'badge-inactive'}">
          ${isActive(c) ? 'Active' : 'Inactive'}
        </span>
        <button class="btn btn-sm btn-outline edit-customer-btn" data-id="${c.id}">Edit</button>
        <button class="btn btn-sm btn-outline toggle-customer-btn" data-id="${c.id}" data-active="${isActive(c)}">
          ${isActive(c) ? 'Deactivate' : 'Activate'}
        </button>
        <button class="btn btn-sm btn-danger delete-customer-btn" data-id="${c.id}">Delete</button>
      </div>
    </li>
  `).join('');

  customersList.querySelectorAll('.edit-customer-btn').forEach(btn => {
    btn.addEventListener('click', () => openEditCustomer(parseInt(btn.dataset.id, 10)));
  });
  customersList.querySelectorAll('.toggle-customer-btn').forEach(btn => {
    btn.addEventListener('click', () => toggleCustomerActive(
      parseInt(btn.dataset.id, 10), btn.dataset.active === 'true'
    ));
  });
  customersList.querySelectorAll('.delete-customer-btn').forEach(btn => {
    btn.addEventListener('click', () => deleteCustomer(parseInt(btn.dataset.id, 10)));
  });
}

const debouncedCustomerSearch = debounce(() => {
  saveFiltersFor('customers');
  loadCustomers();
}, 300);
customerSearch.addEventListener('input', debouncedCustomerSearch);
customerSortBy.addEventListener('change', () => { saveFiltersFor('customers'); loadCustomers(); });
customerSortOrder.addEventListener('change', () => { saveFiltersFor('customers'); loadCustomers(); });
customerRefreshBtn.addEventListener('click', () => loadCustomers());

createCustomerBtn.addEventListener('click', () => {
  const html = `
    <div class="form-group"><label>Name *</label><input type="text" id="cust-name" maxlength="100"></div>
    <div class="form-group"><label>Phone *</label><input type="text" id="cust-phone" maxlength="20"></div>
    <div class="form-group"><label>Address *</label><textarea id="cust-address" rows="2" maxlength="255"></textarea></div>
    <div id="create-customer-error" class="error hidden"></div>
  `;

  openModal('New Customer', html, [
    { text: 'Cancel', class: 'btn-outline', action: closeModal },
    {
      text: 'Create',
      class: 'btn-primary',
      action: async () => {
        const name    = document.getElementById('cust-name').value.trim();
        const phone   = document.getElementById('cust-phone').value.trim();
        const address = document.getElementById('cust-address').value.trim();
        const errorEl = document.getElementById('create-customer-error');
        if (!name || !phone || !address) {
          errorEl.textContent = 'Name, phone, and address are all required.';
          errorEl.classList.remove('hidden');
          return;
        }
        try {
          await apiFetch('/api/customers/', {
            method: 'POST',
            body: JSON.stringify({ name, phone, address }),
          });
          closeModal();
          await loadCustomers();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.classList.remove('hidden');
        }
      },
    },
  ]);
});

async function openEditCustomer(customerId) {
  try {
    const customer = await apiFetch(`/api/customers/${customerId}`);
    const html = `
      <div class="form-group"><label>Name *</label><input type="text" id="edit-cust-name" value="${escapeHtml(customer.name)}" maxlength="100"></div>
      <div class="form-group"><label>Phone *</label><input type="text" id="edit-cust-phone" value="${escapeHtml(customer.phone)}" maxlength="20"></div>
      <div class="form-group"><label>Address *</label><textarea id="edit-cust-address" rows="2" maxlength="255">${escapeHtml(customer.address)}</textarea></div>
      <div id="edit-customer-error" class="error hidden"></div>
    `;

    openModal('Edit Customer', html, [
      { text: 'Cancel', class: 'btn-outline', action: closeModal },
      {
        text: 'Save',
        class: 'btn-primary',
        action: async () => {
          const name    = document.getElementById('edit-cust-name').value.trim();
          const phone   = document.getElementById('edit-cust-phone').value.trim();
          const address = document.getElementById('edit-cust-address').value.trim();
          const errorEl = document.getElementById('edit-customer-error');
          if (!name || !phone || !address) {
            errorEl.textContent = 'Name, phone, and address are all required.';
            errorEl.classList.remove('hidden');
            return;
          }
          try {
            await apiFetch(`/api/customers/${customerId}`, {
              method: 'PATCH',
              body: JSON.stringify({ name, phone, address }),
            });
            closeModal();
            await loadCustomers();
          } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
          }
        },
      },
    ]);
  } catch (err) {
    alert(`Failed to load customer: ${err.message}`);
  }
}

async function toggleCustomerActive(customerId, currentlyActive) {
  const verb = currentlyActive ? 'deactivate' : 'activate';
  try {
    await apiFetch(`/api/customers/${customerId}/${verb}`, { method: 'POST' });
    await loadCustomers();
  } catch (err) {
    alert(`Failed to ${verb} customer: ${err.message}`);
  }
}

async function deleteCustomer(customerId) {
  const ok = await confirmDialog({
    title: 'Delete customer',
    message: 'Are you sure you want to delete this customer? This cannot be undone.',
    confirmText: 'Delete',
  });
  if (!ok) return;
  try {
    await apiFetch(`/api/customers/${customerId}`, { method: 'DELETE' });
    await loadCustomers();
  } catch (err) {
    alert(`Failed to delete customer: ${err.message}`);
  }
}

// ============================================================
// FISH TYPES
// ============================================================

async function loadFishTypes() {
  fishTypesLoading.classList.remove('hidden');
  fishTypesEmpty.classList.add('hidden');
  fishTypesList.innerHTML = '';

  try {
    const qs = buildListQuery({
      search:    fishTypeSearch.value,
      sortBy:    fishTypeSortBy.value,
      sortOrder: fishTypeSortOrder.value,
    });
    const fishTypes = await apiFetch(`/api/fish-types/${qs}`);
    state.fishTypesCache = fishTypes || [];
    fishTypesLoading.classList.add('hidden');

    if (!fishTypes || fishTypes.length === 0) {
      fishTypesEmpty.classList.remove('hidden');
      return;
    }

    fishTypesList.innerHTML = fishTypes.map(ft => `
      <li class="${isActive(ft) ? '' : 'list-item-inactive'}" data-fish-type-id="${ft.id}">
        <div class="fish-info">
          <h4>${escapeHtml(ft.name)}</h4>
          <p>ID: ${ft.id}</p>
        </div>
        <div class="row-actions">
          <span class="badge ${isActive(ft) ? 'badge-active' : 'badge-inactive'}">
            ${isActive(ft) ? 'Active' : 'Inactive'}
          </span>
          <button class="btn btn-sm btn-outline edit-fish-btn" data-id="${ft.id}">Edit</button>
          <button class="btn btn-sm btn-outline toggle-fish-btn" data-id="${ft.id}" data-active="${isActive(ft)}">
            ${isActive(ft) ? 'Deactivate' : 'Activate'}
          </button>
          <button class="btn btn-sm btn-danger delete-fish-btn" data-id="${ft.id}">Delete</button>
        </div>
      </li>
    `).join('');

    fishTypesList.querySelectorAll('.edit-fish-btn').forEach(btn => {
      btn.addEventListener('click', () => openEditFishType(parseInt(btn.dataset.id, 10)));
    });
    fishTypesList.querySelectorAll('.toggle-fish-btn').forEach(btn => {
      btn.addEventListener('click', () => toggleFishTypeActive(
        parseInt(btn.dataset.id, 10), btn.dataset.active === 'true'
      ));
    });
    fishTypesList.querySelectorAll('.delete-fish-btn').forEach(btn => {
      btn.addEventListener('click', () => deleteFishType(parseInt(btn.dataset.id, 10)));
    });
  } catch (err) {
    fishTypesLoading.classList.add('hidden');
    fishTypesList.innerHTML =
      `<div class="error">Failed to load fish types: ${escapeHtml(err.message)}</div>`;
  }
}

const debouncedFishTypeSearch = debounce(() => {
  saveFiltersFor('fish-types');
  loadFishTypes();
}, 300);
fishTypeSearch.addEventListener('input', debouncedFishTypeSearch);
fishTypeSortBy.addEventListener('change', () => { saveFiltersFor('fish-types'); loadFishTypes(); });
fishTypeSortOrder.addEventListener('change', () => { saveFiltersFor('fish-types'); loadFishTypes(); });
fishTypeRefreshBtn.addEventListener('click', () => loadFishTypes());

createFishTypeBtn.addEventListener('click', () => {
  const html = `
    <div class="form-group"><label>Name *</label><input type="text" id="ft-name" maxlength="100"></div>
    <div id="create-fish-type-error" class="error hidden"></div>
  `;

  openModal('New Fish Type', html, [
    { text: 'Cancel', class: 'btn-outline', action: closeModal },
    {
      text: 'Create',
      class: 'btn-primary',
      action: async () => {
        const name    = document.getElementById('ft-name').value.trim();
        const errorEl = document.getElementById('create-fish-type-error');
        if (!name) {
          errorEl.textContent = 'Name is required.';
          errorEl.classList.remove('hidden');
          return;
        }
        try {
          await apiFetch('/api/fish-types/', {
            method: 'POST',
            body: JSON.stringify({ name }),
          });
          closeModal();
          await loadFishTypes();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.classList.remove('hidden');
        }
      },
    },
  ]);
});

async function openEditFishType(id) {
  try {
    const ft = await apiFetch(`/api/fish-types/${id}`);
    const html = `
      <div class="form-group"><label>Name *</label><input type="text" id="edit-ft-name" value="${escapeHtml(ft.name)}" maxlength="100"></div>
      <div id="edit-fish-error" class="error hidden"></div>
    `;

    openModal('Edit Fish Type', html, [
      { text: 'Cancel', class: 'btn-outline', action: closeModal },
      {
        text: 'Save',
        class: 'btn-primary',
        action: async () => {
          const name    = document.getElementById('edit-ft-name').value.trim();
          const errorEl = document.getElementById('edit-fish-error');
          if (!name) {
            errorEl.textContent = 'Name is required.';
            errorEl.classList.remove('hidden');
            return;
          }
          try {
            await apiFetch(`/api/fish-types/${id}`, {
              method: 'PATCH',
              body: JSON.stringify({ name }),
            });
            closeModal();
            await loadFishTypes();
          } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
          }
        },
      },
    ]);
  } catch (err) {
    alert(`Failed to load fish type: ${err.message}`);
  }
}

async function toggleFishTypeActive(id, currentlyActive) {
  const verb = currentlyActive ? 'deactivate' : 'activate';
  try {
    await apiFetch(`/api/fish-types/${id}/${verb}`, { method: 'POST' });
    await loadFishTypes();
  } catch (err) {
    alert(`Failed to ${verb} fish type: ${err.message}`);
  }
}

async function deleteFishType(id) {
  const ok = await confirmDialog({
    title: 'Delete fish type',
    message: 'Are you sure you want to delete this fish type? This cannot be undone.',
    confirmText: 'Delete',
  });
  if (!ok) return;
  try {
    await apiFetch(`/api/fish-types/${id}`, { method: 'DELETE' });
    await loadFishTypes();
  } catch (err) {
    alert(`Failed to delete fish type: ${err.message}`);
  }
}

// ============================================================
// SUPPLIERS
// ============================================================

async function loadSuppliers() {
  suppliersLoading.classList.remove('hidden');
  suppliersEmpty.classList.add('hidden');
  suppliersList.innerHTML = '';

  try {
    const qs = buildListQuery({
      search:    supplierSearch.value,
      sortBy:    supplierSortBy.value,
      sortOrder: supplierSortOrder.value,
    });
    const suppliers = await apiFetch(`/api/suppliers/${qs}`);
    state.suppliersCache = suppliers || [];
    suppliersLoading.classList.add('hidden');

    if (!suppliers || suppliers.length === 0) {
      suppliersEmpty.classList.remove('hidden');
      return;
    }

    suppliersList.innerHTML = suppliers.map(s => `
      <li class="${isActive(s) ? '' : 'list-item-inactive'}" data-supplier-id="${s.id}">
        <div class="supplier-info">
          <h4>${escapeHtml(s.name)}</h4>
          <p>${escapeHtml(s.phone || '')}${s.address ? ' · ' + escapeHtml(s.address) : ''}</p>
        </div>
        <div class="row-actions">
          <span class="badge ${isActive(s) ? 'badge-active' : 'badge-inactive'}">
            ${isActive(s) ? 'Active' : 'Inactive'}
          </span>
          <button class="btn btn-sm btn-outline edit-supplier-btn" data-id="${s.id}">Edit</button>
          <button class="btn btn-sm btn-outline toggle-supplier-btn" data-id="${s.id}" data-active="${isActive(s)}">
            ${isActive(s) ? 'Deactivate' : 'Activate'}
          </button>
          <button class="btn btn-sm btn-danger delete-supplier-btn" data-id="${s.id}">Delete</button>
        </div>
      </li>
    `).join('');

    suppliersList.querySelectorAll('.edit-supplier-btn').forEach(btn => {
      btn.addEventListener('click', () => openEditSupplier(parseInt(btn.dataset.id, 10)));
    });
    suppliersList.querySelectorAll('.toggle-supplier-btn').forEach(btn => {
      btn.addEventListener('click', () => toggleSupplierActive(
        parseInt(btn.dataset.id, 10), btn.dataset.active === 'true'
      ));
    });
    suppliersList.querySelectorAll('.delete-supplier-btn').forEach(btn => {
      btn.addEventListener('click', () => deleteSupplier(parseInt(btn.dataset.id, 10)));
    });
  } catch (err) {
    suppliersLoading.classList.add('hidden');
    suppliersList.innerHTML =
      `<div class="error">Failed to load suppliers: ${escapeHtml(err.message)}</div>`;
  }
}

const debouncedSupplierSearch = debounce(() => {
  saveFiltersFor('suppliers');
  loadSuppliers();
}, 300);
supplierSearch.addEventListener('input', debouncedSupplierSearch);
supplierSortBy.addEventListener('change', () => { saveFiltersFor('suppliers'); loadSuppliers(); });
supplierSortOrder.addEventListener('change', () => { saveFiltersFor('suppliers'); loadSuppliers(); });
supplierRefreshBtn.addEventListener('click', () => loadSuppliers());

createSupplierBtn.addEventListener('click', () => {
  const html = `
    <div class="form-group"><label>Name *</label><input type="text" id="sup-name" maxlength="100"></div>
    <div class="form-group"><label>Phone *</label><input type="text" id="sup-phone" maxlength="20"></div>
    <div class="form-group"><label>Address *</label><textarea id="sup-address" rows="2" maxlength="255"></textarea></div>
    <div id="create-supplier-error" class="error hidden"></div>
  `;

  openModal('New Supplier', html, [
    { text: 'Cancel', class: 'btn-outline', action: closeModal },
    {
      text: 'Create',
      class: 'btn-primary',
      action: async () => {
        const name    = document.getElementById('sup-name').value.trim();
        const phone   = document.getElementById('sup-phone').value.trim();
        const address = document.getElementById('sup-address').value.trim();
        const errorEl = document.getElementById('create-supplier-error');
        if (!name || !phone || !address) {
          errorEl.textContent = 'Name, phone, and address are all required.';
          errorEl.classList.remove('hidden');
          return;
        }
        try {
          await apiFetch('/api/suppliers/', {
            method: 'POST',
            body: JSON.stringify({ name, phone, address }),
          });
          closeModal();
          await loadSuppliers();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.classList.remove('hidden');
        }
      },
    },
  ]);
});

async function openEditSupplier(id) {
  try {
    const s = await apiFetch(`/api/suppliers/${id}`);
    const html = `
      <div class="form-group"><label>Name *</label><input type="text" id="edit-sup-name" value="${escapeHtml(s.name)}" maxlength="100"></div>
      <div class="form-group"><label>Phone *</label><input type="text" id="edit-sup-phone" value="${escapeHtml(s.phone)}" maxlength="20"></div>
      <div class="form-group"><label>Address *</label><textarea id="edit-sup-address" rows="2" maxlength="255">${escapeHtml(s.address)}</textarea></div>
      <div id="edit-supplier-error" class="error hidden"></div>
    `;

    openModal('Edit Supplier', html, [
      { text: 'Cancel', class: 'btn-outline', action: closeModal },
      {
        text: 'Save',
        class: 'btn-primary',
        action: async () => {
          const name    = document.getElementById('edit-sup-name').value.trim();
          const phone   = document.getElementById('edit-sup-phone').value.trim();
          const address = document.getElementById('edit-sup-address').value.trim();
          const errorEl = document.getElementById('edit-supplier-error');
          if (!name || !phone || !address) {
            errorEl.textContent = 'Name, phone, and address are all required.';
            errorEl.classList.remove('hidden');
            return;
          }
          try {
            await apiFetch(`/api/suppliers/${id}`, {
              method: 'PATCH',
              body: JSON.stringify({ name, phone, address }),
            });
            closeModal();
            await loadSuppliers();
          } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
          }
        },
      },
    ]);
  } catch (err) {
    alert(`Failed to load supplier: ${err.message}`);
  }
}

async function toggleSupplierActive(id, currentlyActive) {
  const verb = currentlyActive ? 'deactivate' : 'activate';
  try {
    await apiFetch(`/api/suppliers/${id}/${verb}`, { method: 'POST' });
    await loadSuppliers();
  } catch (err) {
    alert(`Failed to ${verb} supplier: ${err.message}`);
  }
}

async function deleteSupplier(id) {
  const ok = await confirmDialog({
    title: 'Delete supplier',
    message: 'Are you sure you want to delete this supplier? This cannot be undone.',
    confirmText: 'Delete',
  });
  if (!ok) return;
  try {
    await apiFetch(`/api/suppliers/${id}`, { method: 'DELETE' });
    await loadSuppliers();
  } catch (err) {
    alert(`Failed to delete supplier: ${err.message}`);
  }
}

// ============================================================
// MODAL HELPERS
// ============================================================

function openModal(title, bodyHtml, buttons = []) {
  modalTitle.textContent = title;
  modalBody.innerHTML = bodyHtml;
  modalFooter.innerHTML = '';

  buttons.forEach(btn => {
    const button = document.createElement('button');
    button.textContent = btn.text;
    button.className = `btn ${btn.class}`;
    button.addEventListener('click', btn.action);
    modalFooter.appendChild(button);
  });

  modalOverlay.classList.remove('hidden');
}

function closeModal() {
  modalOverlay.classList.add('hidden');
  modalTitle.textContent = '';
  modalBody.innerHTML = '';
  modalFooter.innerHTML = '';
}

modalClose.addEventListener('click', closeModal);
modalOverlay.addEventListener('click', (e) => {
  if (e.target === modalOverlay) closeModal();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !modalOverlay.classList.contains('hidden')) closeModal();
});

// ============================================================
// BOOTSTRAP
// ============================================================

async function bootstrap() {
  const saved = persist.load();
  const view  = saved?.view || 'trips';

  restoreFiltersFor('customers');
  restoreFiltersFor('fish-types');
  restoreFiltersFor('suppliers');

  Object.entries(views).forEach(([key, el]) => {
    el.classList.toggle('active', key === view);
  });
  navLinks.forEach(link => {
    link.classList.toggle('active', link.dataset.view === view);
  });

  // Always probe the backend on load so the badge reflects reality.
  runHealthCheck();

  if (view === 'customers')  await loadCustomers();
  if (view === 'fish-types') await loadFishTypes();
  if (view === 'suppliers')  await loadSuppliers();
  if (view === 'trips') {
    if (saved?.tripId) {
      await openTrip(String(saved.tripId));
    } else {
      await loadTrips();
    }
  }
}

function currentViewName() {
  for (const [name, el] of Object.entries(views)) {
    if (el.classList.contains('active')) return name;
  }
  return 'trips';
}

document.addEventListener('DOMContentLoaded', () => {
  window.addEventListener('beforeunload', () => {
    persist.save({ view: currentViewName() });
  });
  bootstrap();
});