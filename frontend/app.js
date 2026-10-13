/* ============================================================
   Fish Distribution Manager — Frontend
   Uses ONLY the existing FastAPI endpoints.
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

// ===== DOM helpers =====
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

// ===== DOM refs =====
const healthButton = $('health-button');
const healthResult = $('health-result');

const views = {
  trips:        $('view-trips'),
  customers:    $('view-customers'),
  'fish-types': $('view-fish-types'),
  suppliers:    $('view-suppliers'),
};
const navLinks = document.querySelectorAll('.sidebar nav a');

// Trips
const tripsListContainer  = $('trips-list-container');
const tripsList           = $('trips-list');
const tripsLoading        = $('trips-loading');
const tripsEmpty          = $('trips-empty');
const createTripBtn       = $('create-trip-btn');
const tripWorkspace       = $('trip-workspace');
const tripTitle           = $('trip-title');
const tripMeta            = $('trip-meta');
const backToTripsBtn      = $('back-to-trips-btn');
const addCustomerToTripBtn= $('add-customer-to-trip-btn');
const addFishToTripBtn    = $('add-fish-to-trip-btn');

// Requirements table
const reqLoading  = $('requirements-loading');
const reqError    = $('requirements-error');
const reqThead    = $('requirements-thead');
const reqTbody    = $('requirements-tbody');
const reqTfoot    = $('requirements-tfoot');
const reqEmpty    = $('requirements-empty');       // no customers
const reqNoFish   = $('requirements-no-fish');     // no fish types
const emptyAddCustomerBtn = $('empty-add-customer-btn');
const emptyAddFishBtn     = $('empty-add-fish-btn');

// Customers
const customersList     = $('customers-list');
const customersLoading  = $('customers-loading');
const customersEmpty    = $('customers-empty');
const createCustomerBtn = $('create-customer-btn');
const customerSearch    = $('customer-search');

// Fish types
const fishTypesList     = $('fish-types-list');
const fishTypesLoading  = $('fish-types-loading');
const fishTypesEmpty    = $('fish-types-empty');
const createFishTypeBtn = $('create-fish-type-btn');

// Suppliers
const suppliersList     = $('suppliers-list');
const suppliersLoading  = $('suppliers-loading');
const suppliersEmpty    = $('suppliers-empty');
const createSupplierBtn = $('create-supplier-btn');

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

// ===== Navigation =====
function switchView(name) {
  Object.entries(views).forEach(([key, el]) => {
    el.classList.toggle('active', key === name);
  });
  navLinks.forEach(link => {
    link.classList.toggle('active', link.dataset.view === name);
  });

  if (name === 'customers')  loadCustomers();
  if (name === 'fish-types') loadFishTypes();
  if (name === 'suppliers')  loadSuppliers();
  if (name === 'trips')      loadTrips();
}

navLinks.forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    switchView(link.dataset.view);
  });
});

// ===== Health check =====
healthButton.addEventListener('click', async () => {
  healthResult.textContent = 'Checking…';
  try {
    const data = await apiFetch('/api/health');
    healthResult.textContent = `OK · ${JSON.stringify(data)}`;
  } catch (err) {
    healthResult.textContent = `Error: ${err.message}`;
  }
});

// ============================================================
// TRIPS
// ============================================================

async function loadTrips() {
  tripsLoading.classList.remove('hidden');
  tripsEmpty.classList.add('hidden');
  tripsList.innerHTML = '';
  tripWorkspace.classList.add('hidden');
  tripsListContainer.classList.remove('hidden');

  try {
    const trips = await apiFetch('/api/trips/');
    tripsLoading.classList.add('hidden');

    if (!Array.isArray(trips) || trips.length === 0) {
      tripsEmpty.classList.remove('hidden');
      return;
    }

    tripsList.innerHTML = trips.map(trip => {
      const supplierName =
        trip.supplier?.name ||
        trip.supplier_name ||
        (trip.supplier_id ? `Supplier #${trip.supplier_id}` : 'No supplier');
      const date   = trip.trip_date || trip.date || 'No date';
      const status = trip.status || (trip.is_active === false ? 'Inactive' : 'Active');

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
  tripsListContainer.classList.add('hidden');
  tripWorkspace.classList.remove('hidden');
  tripTitle.textContent = `Trip #${tripId}`;
  tripMeta.textContent = 'Loading…';

  try {
    const trip = await apiFetch(`/api/trips/${tripId}`);
    const supplierName =
      trip.supplier?.name ||
      trip.supplier_name ||
      (trip.supplier_id ? `Supplier #${trip.supplier_id}` : 'No supplier');

    tripTitle.textContent = `Trip #${trip.id}`;
    tripMeta.textContent =
      `Date: ${trip.trip_date || 'N/A'} · Supplier: ${supplierName} · Status: ${trip.status || 'Active'}`;

    await loadRequirementsTable(tripId);
  } catch (err) {
    tripMeta.textContent = `Error: ${err.message}`;
    reqError.textContent = `Failed to load trip: ${err.message}`;
    reqError.classList.remove('hidden');
  }
}

backToTripsBtn.addEventListener('click', () => {
  state.currentTripId = null;
  tripWorkspace.classList.add('hidden');
  tripsListContainer.classList.remove('hidden');
  loadTrips();
});

// ============================================================
// REQUIREMENTS TABLE
// Response schema (per spec):
//   { trip_id,
//     fish_types: [{ id, name, ... }],
//     customers:  [{ customer_id, trip_customer_id, name, phone, address,
//                    total_bags,
//                    quantities: [{ fish_type_id, quantity_bags }] }],
//     fish_totals: [{ fish_type_id, total_quantity }],
//     grand_total_bags }
// ============================================================

async function loadRequirementsTable(tripId) {
  reqLoading.classList.remove('hidden');
  reqError.classList.add('hidden');
  reqEmpty.classList.add('hidden');
  reqNoFish.classList.add('hidden');
  reqThead.innerHTML = '';
  reqTbody.innerHTML = '';
  reqTfoot.innerHTML = '';

  try {
    const data = await apiFetch(`/api/trips/${tripId}/requirements-table`);
    reqLoading.classList.add('hidden');

    const fishTypes = Array.isArray(data.fish_types) ? data.fish_types : [];
    const customers = Array.isArray(data.customers)  ? data.customers  : [];
    const fishTotals= Array.isArray(data.fish_totals) ? data.fish_totals : [];

    // --- Empty-state branches ---
    if (customers.length === 0) {
      reqEmpty.classList.remove('hidden');
      return;
    }
    if (fishTypes.length === 0) {
      reqNoFish.classList.remove('hidden');
      return;
    }

    // --- HEADER ---
    // Fixed columns: Customer Name, Mobile, Address
    // Dynamic columns: one per fish type
    // Then: Customer Total, Actions
    let headHtml = `
      <tr>
        <th>Customer</th>
        <th>Mobile</th>
        <th>Address</th>
    `;
    fishTypes.forEach(ft => {
      headHtml += `<th title="${escapeHtml(String(ft.name))}">${escapeHtml(ft.name)}</th>`;
    });
    headHtml += `<th>Customer Total</th><th>Actions</th></tr>`;
    reqThead.innerHTML = headHtml;

    // --- BODY ---
    let bodyHtml = '';
    customers.forEach(cust => {
      // Spec field names: name, phone, address, total_bags
      const name    = cust.name    || cust.customer_name || 'N/A';
      const phone   = cust.phone   || cust.mobile        || '—';
      const address = cust.address || '—';
      const total   = cust.total_bags ?? 0;

      bodyHtml += '<tr>';

      // Clickable customer name → opens requirements modal
      bodyHtml += `
        <td>
          <span class="customer-link"
                data-customer-id="${cust.customer_id}"
                data-trip-customer-id="${cust.trip_customer_id ?? ''}">
            ${escapeHtml(String(name))}
          </span>
        </td>
      `;
      bodyHtml += `<td>${escapeHtml(String(phone))}</td>`;
      bodyHtml += `<td>${escapeHtml(String(address))}</td>`;

      // Dynamic fish quantities — match on fish_type_id
      fishTypes.forEach(ft => {
        const qtyEntry = (cust.quantities || [])
          .find(q => q.fish_type_id === ft.id);
        const qty = qtyEntry ? (qtyEntry.quantity_bags ?? 0) : 0;
        bodyHtml += `<td>${qty}</td>`;
      });

      bodyHtml += `<td><strong>${total}</strong></td>`;

      // Actions: only the requirements editor is supported by the API.
      // (No remove-from-trip endpoint exists — no such button.)
      bodyHtml += `
        <td>
          <button class="btn btn-sm btn-outline edit-req-btn"
                  data-customer-id="${cust.customer_id}"
                  data-trip-customer-id="${cust.trip_customer_id ?? ''}">
            Edit
          </button>
        </td>
      `;

      bodyHtml += '</tr>';
    });
    reqTbody.innerHTML = bodyHtml;

    // --- FOOTER (Fish Totals) ---
    // Fixed cells for Customer/Mobile/Address
    let footHtml = `
      <tr>
        <td colspan="3" class="totals-label">Fish Totals</td>
    `;
    fishTypes.forEach(ft => {
      const t = fishTotals.find(x => x.fish_type_id === ft.id);
      footHtml += `<td>${t ? (t.total_quantity ?? 0) : 0}</td>`;
    });
    footHtml += `<td>${data.grand_total_bags ?? 0}</td><td></td></tr>`;
    reqTfoot.innerHTML = footHtml;

    // --- Attach handlers ---
    document.querySelectorAll('.customer-link').forEach(el => {
      el.addEventListener('click', () => {
        openRequirementsModal(
          tripId,
          el.dataset.customerId,
          el.dataset.tripCustomerId
        );
      });
    });
    document.querySelectorAll('.edit-req-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        openRequirementsModal(
          tripId,
          btn.dataset.customerId,
          btn.dataset.tripCustomerId
        );
      });
    });

  } catch (err) {
    reqLoading.classList.add('hidden');
    reqError.textContent = `Failed to load requirements: ${err.message}`;
    reqError.classList.remove('hidden');
  }
}

// ============================================================
// REQUIREMENTS MODAL — view / create / update
// ============================================================

async function openRequirementsModal(tripId, customerId, tripCustomerId) {
  try {
    const [requirements, trip] = await Promise.all([
      apiFetch(`/api/trips/${tripId}/customers/${customerId}/requirements`),
      apiFetch(`/api/trips/${tripId}`),
    ]);

    // The trip payload carries its configured fish types.
    const tripFishTypes = trip.fish_types || trip.trip_fish_types || [];

    let html = '<form id="requirements-form">';
    if (tripFishTypes.length === 0) {
      html += '<p class="muted">No fish types are configured on this trip.</p>';
    } else {
      tripFishTypes.forEach(ft => {
        const existing = (requirements || []).find(r => r.fish_type_id === ft.id);
        const qty      = existing ? (existing.quantity_bags ?? existing.quantity ?? 0) : 0;
        const reqId    = existing ? existing.id : '';
        html += `
          <div class="form-group">
            <label>${escapeHtml(ft.name)}</label>
            <input type="number" min="0" step="1"
                   name="fish_${ft.id}"
                   value="${qty}"
                   data-fish-type-id="${ft.id}"
                   data-requirement-id="${reqId}">
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
            const quantity      = isNaN(raw) || raw < 0 ? 0 : raw;

            if (requirementId) {
              // Update existing record
              tasks.push(
                apiFetch(
                  `/api/trips/${tripId}/customers/${customerId}/requirements/${requirementId}`,
                  {
                    method: 'PATCH',
                    body: JSON.stringify({ quantity_bags: quantity }),
                  }
                )
              );
            } else if (quantity > 0) {
              // Create only when a real value was entered (avoids empty rows)
              tasks.push(
                apiFetch(
                  `/api/trips/${tripId}/customers/${customerId}/requirements`,
                  {
                    method: 'POST',
                    body: JSON.stringify({
                      fish_type_id: fishTypeId,
                      quantity_bags: quantity,
                    }),
                  }
                )
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
              ${escapeHtml(c.name)}${c.phone || c.mobile ? ' · ' + escapeHtml(c.phone || c.mobile) : ''}
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

    // Live filter
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
// ADD FISH TYPE TO TRIP
// ============================================================

addFishToTripBtn.addEventListener('click', addFishTypeFlow);
emptyAddFishBtn.addEventListener('click', addFishTypeFlow);

async function addFishTypeFlow() {
  if (!state.currentTripId) return;

  try {
    const fishTypes = await apiFetch('/api/fish-types/');
    state.fishTypesCache = fishTypes || [];

    const activeFishTypes = (fishTypes || []).filter(ft => ft.is_active !== false);
    if (activeFishTypes.length === 0) {
      alert('No active fish types available. Create one first.');
      return;
    }

    const html = `
      <div class="form-group">
        <label>Select Fish Type</label>
        <select id="fish-type-select">
          ${activeFishTypes.map(ft => `
            <option value="${ft.id}">${escapeHtml(ft.name)}</option>
          `).join('')}
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
    state.suppliersCache = suppliers;
    state.fishTypesCache = fishTypes;

    const activeSuppliers = (suppliers || []).filter(s => s.is_active !== false);
    const activeFishTypes = (fishTypes || []).filter(ft => ft.is_active !== false);

    const html = `
      <div class="form-group">
        <label>Trip Date</label>
        <input type="date" id="trip-date" required>
      </div>
      <div class="form-group">
        <label>Supplier</label>
        <select id="trip-supplier">
          <option value="">— No supplier —</option>
          ${activeSuppliers.map(s => `
            <option value="${s.id}">${escapeHtml(s.name)}</option>
          `).join('')}
        </select>
      </div>
      <div class="form-group">
        <label>Fish Types</label>
        <div class="checkbox-group">
          ${activeFishTypes.length === 0
            ? '<span class="muted">No active fish types.</span>'
            : activeFishTypes.map(ft => `
                <label>
                  <input type="checkbox" value="${ft.id}" class="trip-fish-checkbox">
                  ${escapeHtml(ft.name)}
                </label>
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
          const selectedFish = Array.from(
            document.querySelectorAll('.trip-fish-checkbox:checked')
          ).map(cb => parseInt(cb.value, 10));
          const errorEl      = document.getElementById('create-trip-error');

          if (!date) {
            errorEl.textContent = 'Trip date is required.';
            errorEl.classList.remove('hidden');
            return;
          }

          const payload = {
            trip_date: date,
            supplier_id: supplierVal ? parseInt(supplierVal, 10) : null,
            fish_type_ids: selectedFish,
          };

          try {
            await apiFetch('/api/trips/', {
              method: 'POST',
              body: JSON.stringify(payload),
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
    const customers = await apiFetch('/api/customers/');
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
  const term = (customerSearch.value || '').toLowerCase();
  const filtered = customers.filter(c => {
    const name  = (c.name || '').toLowerCase();
    const phone = String(c.phone || c.mobile || '').toLowerCase();
    return name.includes(term) || phone.includes(term);
  });

  if (filtered.length === 0) {
    customersEmpty.classList.remove('hidden');
    customersList.innerHTML = '';
    return;
  }
  customersEmpty.classList.add('hidden');

  customersList.innerHTML = filtered.map(c => `
    <li>
      <div class="customer-info">
        <h4>${escapeHtml(c.name || 'Unnamed')}</h4>
        <p>${escapeHtml(c.phone || c.mobile || 'No phone')} · ${escapeHtml(c.address || 'No address')}</p>
      </div>
      <span class="badge ${c.is_active !== false ? 'badge-active' : 'badge-inactive'}">
        ${c.is_active !== false ? 'Active' : 'Inactive'}
      </span>
    </li>
  `).join('');
}

customerSearch.addEventListener('input', () => {
  if (state.customersCache.length) renderCustomers(state.customersCache);
});

createCustomerBtn.addEventListener('click', () => {
  const html = `
    <div class="form-group">
      <label>Name *</label>
      <input type="text" id="cust-name">
    </div>
    <div class="form-group">
      <label>Phone</label>
      <input type="text" id="cust-phone">
    </div>
    <div class="form-group">
      <label>Address</label>
      <textarea id="cust-address" rows="2"></textarea>
    </div>
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

        if (!name) {
          errorEl.textContent = 'Name is required.';
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

// ============================================================
// FISH TYPES
// ============================================================

async function loadFishTypes() {
  fishTypesLoading.classList.remove('hidden');
  fishTypesEmpty.classList.add('hidden');
  fishTypesList.innerHTML = '';

  try {
    const fishTypes = await apiFetch('/api/fish-types/');
    state.fishTypesCache = fishTypes || [];
    fishTypesLoading.classList.add('hidden');

    if (!fishTypes || fishTypes.length === 0) {
      fishTypesEmpty.classList.remove('hidden');
      return;
    }

    fishTypesList.innerHTML = fishTypes.map(ft => `
      <li>
        <div class="fish-info">
          <h4>${escapeHtml(ft.name)}</h4>
          <p>ID: ${ft.id}</p>
        </div>
        <span class="badge ${ft.is_active !== false ? 'badge-active' : 'badge-inactive'}">
          ${ft.is_active !== false ? 'Active' : 'Inactive'}
        </span>
      </li>
    `).join('');
  } catch (err) {
    fishTypesLoading.classList.add('hidden');
    fishTypesList.innerHTML =
      `<div class="error">Failed to load fish types: ${escapeHtml(err.message)}</div>`;
  }
}

createFishTypeBtn.addEventListener('click', () => {
  const html = `
    <div class="form-group">
      <label>Name *</label>
      <input type="text" id="ft-name">
    </div>
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

// ============================================================
// SUPPLIERS
// ============================================================

async function loadSuppliers() {
  suppliersLoading.classList.remove('hidden');
  suppliersEmpty.classList.add('hidden');
  suppliersList.innerHTML = '';

  try {
    const suppliers = await apiFetch('/api/suppliers/');
    state.suppliersCache = suppliers || [];
    suppliersLoading.classList.add('hidden');

    if (!suppliers || suppliers.length === 0) {
      suppliersEmpty.classList.remove('hidden');
      return;
    }

    suppliersList.innerHTML = suppliers.map(s => `
      <li>
        <div class="supplier-info">
          <h4>${escapeHtml(s.name)}</h4>
          <p>
            ${escapeHtml(s.contact || s.phone || '')}
            ${s.address ? '· ' + escapeHtml(s.address) : ''}
          </p>
        </div>
        <span class="badge ${s.is_active !== false ? 'badge-active' : 'badge-inactive'}">
          ${s.is_active !== false ? 'Active' : 'Inactive'}
        </span>
      </li>
    `).join('');
  } catch (err) {
    suppliersLoading.classList.add('hidden');
    suppliersList.innerHTML =
      `<div class="error">Failed to load suppliers: ${escapeHtml(err.message)}</div>`;
  }
}

createSupplierBtn.addEventListener('click', () => {
  const html = `
    <div class="form-group">
      <label>Name *</label>
      <input type="text" id="sup-name">
    </div>
    <div class="form-group">
      <label>Contact</label>
      <input type="text" id="sup-contact">
    </div>
    <div class="form-group">
      <label>Address</label>
      <textarea id="sup-address" rows="2"></textarea>
    </div>
    <div id="create-supplier-error" class="error hidden"></div>
  `;

  openModal('New Supplier', html, [
    { text: 'Cancel', class: 'btn-outline', action: closeModal },
    {
      text: 'Create',
      class: 'btn-primary',
      action: async () => {
        const name    = document.getElementById('sup-name').value.trim();
        const contact = document.getElementById('sup-contact').value.trim();
        const address = document.getElementById('sup-address').value.trim();
        const errorEl = document.getElementById('create-supplier-error');

        if (!name) {
          errorEl.textContent = 'Name is required.';
          errorEl.classList.remove('hidden');
          return;
        }

        try {
          await apiFetch('/api/suppliers/', {
            method: 'POST',
            body: JSON.stringify({ name, contact, address }),
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
// INIT
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  switchView('trips');
});