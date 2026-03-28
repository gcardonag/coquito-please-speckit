# Feature Specification: Coquito Request App

**Feature Branch**: `001-coquito-request-app`
**Created**: 2026-03-28
**Status**: Draft
**Input**: User description: "Build an application that enables people to request a bottle of a particular type of coquito, the date and time they would like the coquito to be given to them, the location they would like to exchange the coquito, whether they would like to provide a bottle or not with a maximum volume limit, and whether they would like to contribute to the cost of the coquito. The request should remind people of when the coquito request is coming up, with the option to cancel or adjust the request up to a cut-off date. After the cut-off date, a list of ingredients to shop for is produced for the cook to procure. The request process should be a simple easy-to-navigate form with a friendly interface that references the art of making coquito as well as Puertorican culture. Reminders should be in a friendly tone. The cook would like a simple interface that is easy to read for use while shopping and cooking."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Submit a Coquito Request (Priority: P1)

A requester visits the app and fills out a friendly, culturally-themed form to order a
bottle of coquito. They select the coquito variety, the pickup date and time, the exchange
location, whether they will bring their own bottle (up to the volume limit), and whether
they want to contribute to the cost. On submission they receive a confirmation and are
enrolled in reminder notifications.

**Why this priority**: This is the core value of the application. Without it nothing else
functions. Every other user story builds on a successfully submitted request.

**Independent Test**: A requester can open the app, complete the form end-to-end, and
receive a confirmation — without any other feature being present.

**Acceptance Scenarios**:

1. **Given** a requester opens the app, **When** they complete all required fields and
   submit, **Then** their request is saved, a confirmation is displayed with a full order
   summary, and they are scheduled to receive reminders.
2. **Given** a requester tries to submit with a required field empty, **When** they tap
   submit, **Then** the form highlights the missing field with a friendly, specific message
   and does not submit.
3. **Given** a requester selects "bring my own bottle" and enters a volume above the
   maximum limit, **When** they attempt to submit, **Then** the form displays the maximum
   volume allowed and prompts them to adjust.
4. **Given** a requester selects a pickup date that is past the order cut-off, **When**
   they try to submit, **Then** they are informed ordering for that date has closed and
   are guided to choose an available date.

---

### User Story 2 - Manage an Existing Request (Priority: P2)

A requester who has already submitted an order wants to view, edit, or cancel it. They
open the app and see their request details. If the cut-off date has not passed they can
modify or cancel; if it has, the request is read-only with a warm explanation.

**Why this priority**: Requesters need the confidence that they can change their minds.
This reduces last-minute surprises for the cook and improves requester satisfaction.

**Independent Test**: Given an existing request, a user can view it, modify the coquito
type or pickup time, save changes, and see an updated confirmation — without the cook
view or ingredient list needing to exist.

**Acceptance Scenarios**:

1. **Given** a requester has an active order and the cut-off has not passed, **When**
   they open their request, **Then** they see all current details with options to edit
   or cancel.
2. **Given** a requester edits their order before the cut-off, **When** they save,
   **Then** the order is updated, a new confirmation is shown, and reminders are
   rescheduled to reflect any date change.
3. **Given** a requester tries to edit after the cut-off, **When** they open their
   request, **Then** they see their order as read-only with a friendly note explaining
   that changes are no longer possible and when to expect their coquito.
4. **Given** a requester cancels before the cut-off, **When** they confirm cancellation,
   **Then** the order is removed, they receive a friendly cancellation confirmation, and
   no further reminders are sent.

---

### User Story 3 - Receive Reminders (Priority: P3)

Requesters automatically receive friendly, culturally-warm reminder notifications ahead
of their pickup date. Reminders include their order summary and a direct link to manage
the request.

**Why this priority**: Reminders reduce no-shows and late cancellations, helping the
cook plan accurately. They depend on requests existing (P1) and being modifiable (P2).

**Independent Test**: A submitted request triggers at least one reminder at a defined
interval before the pickup date, containing the order summary and a management link.

**Acceptance Scenarios**:

1. **Given** a submitted request is at least one reminder interval from pickup, **When**
   the reminder time arrives, **Then** the requester receives a notification with their
   order summary and a link to manage the request.
2. **Given** a requester cancels their order, **When** the next scheduled reminder time
   arrives, **Then** no notification is sent.
3. **Given** a requester modifies their pickup date, **When** the next reminder is
   scheduled, **Then** it reflects the updated date.

---

### User Story 4 - Cook's Ingredient List (Priority: P4)

After the cut-off date the cook opens the app and sees a consolidated, easy-to-read
ingredient shopping list derived from all confirmed requests. The list is organized for
practical use while shopping and cooking.

**Why this priority**: This is the cook's primary tool. It depends on requests being
finalized after cut-off, so it naturally follows all requester-facing stories.

**Independent Test**: Given a set of finalized requests, the cook can open the ingredient
list and see a clear consolidated list grouped to aid shopping and cooking — without any
requester-facing features needing to be visible simultaneously.

**Acceptance Scenarios**:

1. **Given** the cut-off has passed and there are confirmed requests, **When** the cook
   opens the ingredient list, **Then** they see a consolidated list of all required
   ingredients scaled to the total order volume.
2. **Given** the ingredient list is open, **When** the cook is shopping, **Then** they
   can mark individual ingredients as acquired to track progress.
3. **Given** multiple coquito varieties are ordered, **When** the ingredient list is
   displayed, **Then** ingredients are organized to show per-variety quantities and a
   combined total.
4. **Given** the cook opens the app before the cut-off, **When** they navigate to the
   ingredient list, **Then** they see a preview clearly labeled as subject to change.

---

### Edge Cases

- What happens when a requester submits a request for a date so far in the future that
  the cut-off is still many months away?
- How does the system handle a requester submitting multiple requests for different dates?
- What if all requests for a given date are cancelled after the cut-off?
- How are reminders delivered if the requester has not granted notification permissions?
- What happens if the cook changes available coquito varieties after requests have been
  placed for an existing variety?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow requesters to submit an order specifying: coquito
  variety, pickup date and time, exchange location, bottle preference (own or provided),
  and cost contribution preference.
- **FR-002**: The system MUST enforce a maximum volume limit on requester-provided bottles
  and display this limit clearly in the form before and during submission.
- **FR-003**: The system MUST send at least two reminder notifications per confirmed
  request before the pickup date, in a friendly and culturally warm tone.
- **FR-004**: Requesters MUST be able to cancel or modify their order at any time before
  the cut-off date.
- **FR-005**: The system MUST prevent modifications to any request after the cut-off date
  and display a clear, friendly explanation when this occurs.
- **FR-006**: After the cut-off date the system MUST generate a consolidated ingredient
  shopping list for the cook scaled to all confirmed orders for that batch.
- **FR-007**: The requester form MUST include culturally resonant references to Puerto
  Rican coquito-making tradition in its copy and visual design.
- **FR-008**: The cook's ingredient list MUST be clearly readable in low-light or
  high-glare conditions typical of shopping and cooking (large text, high contrast).
- **FR-009**: The system MUST display a confirmation summary to the requester immediately
  after a successful submission or modification.
- **FR-010**: Reminders MUST include the requester's full order summary and a direct link
  to view or manage the request.
- **FR-011**: The cook MUST be able to mark individual ingredients as acquired on the
  shopping list.

### Key Entities

- **Request**: A single coquito order. Key attributes: requester identity, coquito
  variety, pickup date/time, exchange location, bottle preference, volume (if own bottle),
  cost contribution flag, status (pending/confirmed/cancelled), cut-off date.
- **Coquito Variety**: A named type of coquito available for ordering (e.g., classic,
  chocolate, piña). Defined by the cook; includes a recipe/ingredient list.
- **Reminder**: A scheduled notification tied to a request. Contains order summary and
  management link. Status: scheduled/sent/cancelled.
- **Ingredient List**: A cook-facing aggregation of ingredient quantities across all
  confirmed requests for a given batch, supporting per-variety and total breakdowns.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Requesters can complete the full order form in under 3 minutes from first
  opening the app.
- **SC-002**: At least 90% of submitted requests receive all scheduled reminder
  notifications without manual intervention.
- **SC-003**: The cook can locate any ingredient on the shopping list within 5 seconds
  of opening it.
- **SC-004**: Requesters who attempt to modify a locked order see a clear explanation
  100% of the time, with no error screen or blank state.
- **SC-005**: The ingredient list accurately reflects all confirmed orders with zero
  discrepancies between requests and listed quantities.
- **SC-006**: At least 85% of first-time requesters complete the form without needing
  outside help, as measured by form completion rate.

## Assumptions

- The cook is the sole operator of the system; multi-cook or admin hierarchy is out of
  scope for this version.
- Requesters are known individuals (friends and family) who access the app via a shared
  link; public open registration is out of scope for this version.
- The app is primarily mobile-facing for requesters; the cook's ingredient view is also
  expected to be used on a mobile device while shopping and cooking.
- Coquito varieties and their ingredient recipes are pre-configured by the cook before
  requests open; variety management is out of scope for this version.
- The cut-off date is a single fixed date per batch set by the cook, not per-requester.
- Cost contribution is a boolean preference (yes/no); payment processing and tracking of
  monetary transactions are out of scope for this version.
- The maximum bottle volume limit is a single global value set by the cook; per-variety
  limits are out of scope for this version.
- Reminder delivery channel (push notification or SMS) is determined during planning
  based on the target platform.
