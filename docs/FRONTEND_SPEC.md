Fish Seed Distribution — Frontend Specification
Prepared for the frontend developer. Backend: FastAPI REST API under /api. October 2026.
1. What this app is
An owner-only tool for a live fish-seed distribution business. The owner buys fish seed from one supplier for each trip, carries it to meeting spots, and hands bags to trusted customers. The app replaces paper lists. It answers: who wants how much, what arrived, what is left, who got what, what does each customer owe, and can I close the trip.
One user: the owner. Used on a phone, outdoors, one-handed, on a weak network.
2. Words used
• Trip: one purchase and distribution run on one date with one supplier. Status is PLANNING, IN_PROGRESS or CLOSED.
• Fish type: a variety, for example Rohu or Katla.
• Bag: the only unit. Whole numbers.
• Trip customer: a customer assigned to one trip. It has its own id (trip_customer_id), which is not the customer id. Handovers and rates use trip_customer_id.
• Demand (requirement): bags a customer asked for, per fish type.
• Supplier list: what the owner orders from the supplier. Draft first, then final.
• Packing list: what goes on the vehicle.
• Slip (supplier delivery): what actually arrived. Delivered, rejected and damaged bags per fish type.
• Handover: bags given to one customer at one moment, one line per fish type.
• Stock left: slip bags minus handed bags, per fish type.
• Self: a customer record named Self. Leftover bags are handed to Self so stock reaches zero.
• Rate: price per bag. Secret. Never shown anywhere.
• Bill: bags times the rate saved at handover, totalled per customer.
• Close: the owner finishes the trip. It becomes read-only.
3. Golden rules (not negotiable)
1. Never show a selling rate. Not in lists, bills, forms, tooltips, URLs, logs, error messages or analytics. The API never returns one. Do not calculate one either: for a customer with one fish type, total divided by bags equals the rate. Treat the bill screen as sensitive (section 7.14).
2. Rate inputs are write-only. Empty when opened, never prefilled, cleared after saving, autocomplete off. After saving show only a Rate set badge.
3. Never keep the session token in localStorage or sessionStorage. Use the cookie. Send every request with credentials: include.
4. Money is a string such as 850.00. Never convert it to a float for arithmetic. Format for display only, Indian style (en-IN, rupee sign).
5. Handover submit is idempotent. Create one submit_reference (a UUID) when the form opens. Reuse the same value for every retry of that form. A new form gets a new value.
6. Stock problems are warnings, not blocks. Handing over more than the stock left is allowed. The server flags it. Show a clear warning.
7. A closed trip is read-only. Hide write actions. The server also rejects them with 409.
8. The server owns the totals. Show server numbers. Client math is only a live preview.
9. Phone first. 360 px wide, tap targets of 44 px or more, numeric keypad for bag fields (inputmode numeric).
10. Time. The server sends ISO timestamps with a timezone. Show them in Asia/Kolkata.
4. Setup and environment
• API base URL from an env var, for example VITE_API_BASE_URL, default http://127.0.0.1:8000/api.
• The dev origin must be listed in the backend variable CORS_ORIGINS. http://localhost:5173 is listed. No wildcards exist.
• /docs and /openapi.json work in development and are hidden in production. Generate TypeScript types from openapi.json (openapi-typescript).
• Cookie login works when screens and API share a site. localhost on two ports counts as one site. For production use one domain with two subdomains. If that is impossible, token mode exists: login with token_in_body set to true, keep the token in memory only, send it as Authorization: Bearer. A page refresh then signs the owner out.
• Suggested stack: React, Vite, TypeScript, React Router, TanStack Query, Tailwind, Vitest, Testing Library.
5. One full trip, with numbers
Master data exists: fish types Rohu and Katla; customers Danish, Jiyan and Self; supplier Vinod.
1. The owner logs in.
2. Creates a trip: date 2026-10-23, supplier Vinod, fish types Rohu and Katla. Status PLANNING.
3. Assigns customers Danish, Jiyan and Self to the trip.
4. Enters demand: Danish 10 Rohu, Jiyan 10 Katla. Totals: Rohu 10, Katla 10. Planned quantity 10 each. No shortfall.
5. Generates the supplier list draft from demand and finalizes it.
6. Creates the packing list.
7. The supplier arrives. The owner records a slip: Rohu delivered 12, Katla delivered 10, nothing rejected or damaged. The trip becomes IN_PROGRESS. Stock left: Rohu 12, Katla 10.
8. The owner sets rates (hidden): Rohu default 50, Katla default 80, Danish Rohu override 45, Self Rohu override 0.
9. At the spot: handover to Danish, 10 Rohu. Handover to Jiyan, 10 Katla. Stock left: Rohu 2, Katla 0.
10. The owner tries to close. The server refuses: Stock left. Rohu: 2.
11. Handover to Self, 2 Rohu. Stock left is zero everywhere.
12. Bill: Danish 450.00, Jiyan 800.00, Self 0.00. Trip total 1250.00. Complete.
13. The owner closes the trip. Status CLOSED. closed_at is set. Every screen is now read-only.
If a rate is set after handovers were made, the unpriced lines are priced automatically. Lines that already have a rate never change. The bill shows incomplete until every line has a rate.
6. Navigation
• Bottom bar: Trips, Customers, More (fish types, suppliers, log out).
• Inside a trip, a horizontal step bar: Setup, Demand, Supply, Packing, Slips, Stock, Handovers, Review, Rates, Bill, Close. Show a status chip (PLANNING, IN_PROGRESS, CLOSED) at the top.
• Any 401 sends the owner to Login and returns to the same page after sign-in.
7. Screens
Field names below come from the live API. Where a payload is not spelled out, read /openapi.json.
7.1 Login
• Fields: username, password.
• POST /api/auth/login. Success sets a cookie. Wrong user and wrong password give the same 401 message. After 5 wrong tries from one device the server answers 429 with a Retry-After header: show the wait time.
• GET /api/auth/me on app start decides signed in or not. POST /api/auth/logout ends the session (204).
• No sign-up, no reset link. The owner resets the password on the server.
7.2 Trips list
• GET /api/trips/. Fields: id, trip_date, supplier_id, status, created_at, closed_at.
• Show newest first, status chip, date, supplier name (join with suppliers). Tap opens the trip. Button: New trip.
• Empty state: no trips yet.
7.3 Create trip
• Fields: trip date, supplier (active only), fish types (active only, at least one).
• POST /api/trips/ with trip_date, supplier_id, fish_type_ids. The new trip starts as PLANNING.
• Add a fish type later: POST /api/trips/{trip_id}/fish-types.
7.4 Master data: fish types, customers, suppliers
• Same screen pattern for all three. List with search, add, edit, deactivate and activate, delete.
• GET/POST /api/fish-types/, /api/customers/, /api/suppliers/. GET/PATCH/DELETE on /{id}. POST /{id}/activate and /{id}/deactivate.
• Fish type: name. Customer: name, phone, address. Supplier: name, phone, address. Phone numbers may repeat.
• DELETE returns 409 when the record is in use. Tell the owner to deactivate instead.
• Make sure a customer named Self exists.
7.5 Trip setup: customers
• GET /api/trips/{trip_id}/customers lists trip customers (id, trip_id, customer_id). It has no names: join with the customers list.
• Add: POST /api/trips/{trip_id}/customers with customer_id. Inactive customers cannot be added (400). Adding twice gives 409.
• Copy from an earlier trip: POST /api/trips/{destination_trip_id}/customers/copy-from/{source_trip_id}. Only the customer list is copied, never quantities.
7.6 Demand
• A grid: rows are customers, columns are fish types. Row total and column total at the bottom.
• Read everything with GET /api/trips/{trip_id}/requirements-table. It returns fish_types, customers (with trip_customer_id, name, phone, address, quantities, total_bags) and fish_totals (quantity_bags, planned_quantity_bags, effective_planned_quantity_bags, shortfall_bags, shortfall_exists) and grand_total_bags.
• Write a cell: POST /api/trips/{trip_id}/customers/{customer_id}/requirements, and PATCH on .../requirements/{requirement_id}. Here customer_id is the customer id, and the customer must already be on the trip.
• Planned quantity per fish type: PATCH /api/trips/{trip_id}/fish-types/{fish_type_id}/planned-quantity. Highlight a shortfall.
7.7 Supply list (order to the supplier)
• POST /api/trips/{trip_id}/supplier-lists/drafts builds a draft from demand.
• Edit one fish: PATCH /api/trips/{trip_id}/supplier-lists/{supplier_list_id}/items/{fish_type_id}.
• Finalize: POST .../{supplier_list_id}/finalize. Only one final list per trip. A final list cannot be edited.
• GET /api/trips/{trip_id}/supplier-lists and GET .../{supplier_list_id} to read.
7.8 Packing list
• POST /api/trips/{trip_id}/packing-list creates it. GET reads it.
• PATCH /api/trips/{trip_id}/packing-list/items/{fish_type_id} changes a quantity. DELETE removes an item. POST .../items adds one.
7.9 Slips (what arrived)
• Form: per fish type delivered bags, rejected bags, damaged bags (rejected plus damaged cannot exceed delivered). Optional: tub count, vehicle, driver, and the final supplier list it belongs to.
• POST /api/trips/{trip_id}/supplier-deliveries. List: GET same path. One: GET .../{delivery_id}.
• Several slips per trip are allowed and add up. The first slip moves the trip to IN_PROGRESS. A closed trip returns 409.
• Response includes accepted_bags, shortage_bags, excess_bags and total_bags per line. Show variance against the plan.
7.10 Stock
• GET /api/trips/{trip_id}/stock. Per fish type: slip_bags, rejected_bags, damaged_bags, handed_bags, left_bags, over_slip, on_slip.
• left_bags is slip minus handed. Rejected and damaged are information only and do not change left_bags.
• Highlight left_bags that are negative (over_slip is true) in red. Show on_slip false as Not on any slip.
• Show a small stock strip at the top of the handover screen, refreshed after every submit.
7.11 Handovers (the main field screen)
• Flow: choose a customer from the trip customers (names joined in), enter bags per fish type, optional note, Submit.
• POST /api/trips/{trip_id}/handovers with trip_customer_id, submit_reference, optional handed_over_at and note, and lines (fish_type_id, bags). Each fish type appears once. Bags of 0 are accepted. Negative values are rejected (422).
• Answers: 201 saved. 200 the same submit_reference was already saved: show success and do not save twice. 409 the reference was used with different data, or the trip is closed. 404 unknown trip customer or fish.
• Block double taps with a disabled button and a spinner. Keep the same reference if the network failed. Offer Retry.
• Warn before submit when bags exceed the stock left, but allow it.
• History: GET /api/trips/{trip_id}/handovers and GET .../{handover_id}. Responses have ids only. Join customer names with the requirements table or customers list.
• GET /api/trips/{trip_id}/handover-totals: bags per customer and fish type, for a customer summary.
• No edit and no delete exist yet. Warn the owner that a submit cannot be undone.
7.12 Review
• A read-only summary: demand against plan, delivered against handed, stock left, and totals per customer. Built from requirements-table, stock and handover-totals. No rates here.
7.13 Rates (write-only)
• GET /api/trips/{trip_id}/rate-status shows only flags: for each fish type default_set (true or false) and override_trip_customer_ids (customers with their own rate).
• Set trip defaults: PUT /api/trips/{trip_id}/rates with a rates list of fish_type_id and rate_per_bag.
• Set one customer: PUT /api/trips/{trip_id}/customers/{trip_customer_id}/rates with the same body. Here the id is trip_customer_id.
• Responses contain only fish_type_id and rate_set. The number is never returned.
• rate_per_bag: zero or more, at most two decimals. Sending again overwrites the old value. The owner cannot view the old value: say so in the UI.
• Setting a rate prices old unpriced lines but never changes priced lines. A fish must be on the trip, else 404.
7.14 Bill (sensitive)
• GET /api/trips/{trip_id}/bill. Per customer: trip_customer_id, customer_id, total_bags, unpriced_bags, total_amount (string), complete. Plus trip totals. No per-fish amounts and no rate.
• Not on lists or the home page. Open it only on an explicit tap. Hide it again after 30 seconds, or when the tab loses focus or the owner leaves the screen. No prefetch. No caching to disk.
• If complete is false show Incomplete and the number of unpriced bags, with a link to Rates.
• Works on closed trips.
7.15 Close
• Button shows only when the trip is IN_PROGRESS.
• POST /api/trips/{trip_id}/close. 200 returns trip, stock and totals. Show a summary and then the read-only trip.
• 409 Stock left. Rohu: 2: show which fish still has bags and a shortcut to Handover to Self.
• 409 Only an in-progress trip can be closed: the trip has no slip yet, or is already closed.
• Negative stock does not block closing. Unpriced lines do not block closing.
8. Errors
Status
Meaning
UI
401
Not signed in or session ended
Go to Login, come back after
403
Origin not allowed
Show a setup error; this is a configuration problem
404
Not found, or not on this trip
Message from detail
409
Conflict or closed trip or stock left
Show the detail text
422
Validation: detail is a list with loc and msg
Mark the field
429
Too many login tries
Show Retry-After seconds
5xx or network
Server problem
Retry button; keep the form data
Errors normally arrive as a JSON body with a detail field. Never log request bodies that contain a password or a rate.
9. Data notes
• IDs are integers.
• Quantities are integers (bags).
• Money and totals are strings with two decimals.
• Timestamps carry a timezone.
• Status values: PLANNING, IN_PROGRESS, CLOSED.
• Lists have no pagination yet.
10. Not built yet
Payments (advance, paid online, paid offline, remaining), supplier cost, expenses and profit and loss, handover reversal or edit, returns and defects as stock events, meeting points, change-password, two-factor login, trip lock and versions, reports and dashboard. Do not design screens that need these without asking the owner.
11. Open decisions for the owner
• Language: English only, or Marathi and Hindi too. Build text through a translation layer from the start.
• Offline or weak network: queue handovers and send later, or require a connection.
• Hosting: one domain with two subdomains (cookie login) or token mode.
• Whether the bill should be shareable as an image or WhatsApp message per customer.
• Whether a helper may enter handovers without seeing bills or rates.
12. Acceptance checklist
• No rate appears in any screen, response log or network trace shown to the user. The Rates screen shows flags only.
• Reload while signed in keeps the session. Logout then back button shows Login.
• A handover double tap saves once. Retry with the same reference returns 200 and the same record.
• Over-stock handover shows a warning and succeeds. Stock shows a negative number in red.
• Closing with stock left shows the fish and the shortcut. Closing after Self handover succeeds.
• A closed trip shows no write buttons. Forcing a write shows the server message.
• Works at 360 px width, thumb-reachable, numeric keypad for bags.
• Login lock shows the wait time. A 401 from any page returns to Login and back.
• The Section 5 example gives exactly Danish 450.00, Jiyan 800.00, Self 0.00, total 1250.00.
13. Suggested build order
1. Setup, login, guarded routes, trips list.
2. Trip shell with steps, master data screens.
3. Customers on trip, demand grid, supply list, packing list.
4. Slips, stock, handovers (the field screen).
5. Rates, bill, close.
6. Review screen, polish, accessibility, tests.
7. Payments after the backend adds them.