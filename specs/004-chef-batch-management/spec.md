# Feature Specification: Chef Batch Management

**Feature Branch**: `004-chef-batch-management`
**Created**: 2026-05-07
**Status**: Draft
**Input**: User description: "Add a new page that only chefs can use in order to list and manage batch properties. This is intended as a way to simplify batch management and all existing batch properties."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View All Batches (Priority: P1)

The chef opens the batch management page and sees a clear, scannable list of all existing
batches. Each row shows the batch name, status (OPEN / CLOSED / COMPLETED), cutoff date,
and the number of available varieties. This gives the chef an at-a-glance overview without
needing to open each batch individually.

**Why this priority**: A chef cannot manage batches they cannot see. The list view is the
foundation for every other management action and delivers immediate value on its own.

**Independent Test**: A chef can navigate to the batch management page and see all existing
batches with their key properties, without any edit or create functionality being present.

**Acceptance Scenarios**:

1. **Given** a chef is authenticated and navigates to the batch management page, **When**
   the page loads, **Then** all existing batches are displayed in a list with name, status,
   cutoff date, and variety count visible for each.
2. **Given** there are no batches yet, **When** the chef opens the batch management page,
   **Then** a clear empty state is displayed indicating no batches exist, with a prompt
   to create the first one.
3. **Given** a non-chef user attempts to access the batch management page, **When** the
   page is requested, **Then** they are redirected away and shown a clear message that this
   area is restricted.

---

### User Story 2 - Create a New Batch (Priority: P2)

The chef creates a new batch by providing all required properties: a name, a cutoff date,
a maximum bottle volume, and the coquito varieties available for ordering. On saving,
the batch becomes visible in the list with OPEN status.

**Why this priority**: Creating batches is how the chef opens new ordering windows.
Without this, the list view has limited utility. It depends on P1 (list view) to confirm
the batch was saved successfully.

**Independent Test**: A chef can fill out the new-batch form with valid values, save it,
and immediately see the new batch appear in the batch list with the correct status and
properties.

**Acceptance Scenarios**:

1. **Given** a chef is on the batch management page, **When** they initiate a new batch
   and fill in all required fields with valid values, **Then** the batch is saved and
   appears in the list with OPEN status and the correct details.
2. **Given** a chef attempts to save a new batch with a cutoff date in the past, **When**
   they submit the form, **Then** the system rejects the submission and displays a specific,
   actionable error message.
3. **Given** a chef leaves a required field empty, **When** they attempt to save, **Then**
   the form highlights the missing field with a clear, friendly message and does not submit.
4. **Given** a chef selects varieties to include in the batch, **When** they save,
   **Then** only the selected varieties are listed as available for that batch.

---

### User Story 3 - Edit an Existing Batch (Priority: P3)

The chef opens an existing batch and edits its properties: name, cutoff date, maximum
bottle volume, available varieties, and status. Changes take effect immediately and are
reflected in the list view.

**Why this priority**: Batches need to evolve — dates shift, varieties are added or
removed, and batches must be closed or completed. Editing depends on the list (P1) and
benefits from the create flow (P2) establishing the data patterns.

**Independent Test**: A chef can open an existing batch, change its name and cutoff date,
save, and see the updated values reflected in both the detail view and the list.

**Acceptance Scenarios**:

1. **Given** a chef selects a batch from the list, **When** the detail view opens,
   **Then** all current batch properties are displayed and editable.
2. **Given** a chef edits a batch and saves valid changes, **When** the save completes,
   **Then** the updated values appear immediately in both the detail view and the list.
3. **Given** a batch has status COMPLETED, **When** the chef views its properties,
   **Then** the fields are presented as read-only with a clear label indicating the batch
   is finalized and cannot be edited.
4. **Given** a chef initiates an OPEN → CLOSED status change, **When** they trigger the
   action, **Then** a confirmation dialog is displayed showing the current number of active
   requests; only after the chef confirms does the status update and the batch appear as
   closed in the list.
5. **Given** a chef initiates a CLOSED → COMPLETED status change, **When** they trigger
   the action, **Then** the status updates immediately with no confirmation dialog, and the
   batch is marked as finalized and read-only in the list.
6. **Given** a chef attempts to save an edit with an invalid value (e.g., a negative
   bottle volume), **When** they submit, **Then** a specific, actionable error message
   is shown and the change is not persisted.

---

### Edge Cases

- What happens when a chef tries to remove a variety from a batch that already has
  confirmed requests for that variety?
- How does the system handle two chefs editing the same batch simultaneously?
- What happens if the chef sets a cutoff date that is earlier than today while there
  are still PENDING requests on that batch?
- How is an empty batch list displayed on first use before any batch is created?
- What happens when a chef sets the batch status to CLOSED while the cutoff date is
  still in the future?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The batch management page MUST be accessible only to users with the chef
  role; all other authenticated users MUST be redirected away with a clear access-denied
  message. A dedicated navigation menu item linking to the batch management page MUST be
  visible only to authenticated chefs and hidden from all other users.
- **FR-002**: The system MUST display all existing batches on the batch management page,
  showing at minimum: batch name, status, cutoff date, and number of available varieties.
- **FR-003**: The system MUST allow a chef to create a new batch by providing: a unique
  batch name, a cutoff date (must be a future date), a maximum bottle volume, and one or
  more coquito varieties; only varieties marked as active MUST be presented for selection.
- **FR-004**: The system MUST allow a chef to edit all properties of an existing batch
  that has OPEN or CLOSED status; COMPLETED batches MUST be read-only.
- **FR-005**: The system MUST allow a chef to manually transition a batch status from
  OPEN to CLOSED, and from CLOSED to COMPLETED, via explicit controls on the batch detail
  view; reverse transitions MUST be prevented. Additionally, the system MUST automatically
  transition any OPEN batch to CLOSED when its cutoff date is reached, without requiring
  chef action.
- **FR-011**: Before a chef can manually transition a batch from OPEN to CLOSED, the
  system MUST display a confirmation dialog showing the current count of active requests
  on that batch; the transition MUST only proceed after explicit chef confirmation.
- **FR-006**: The system MUST validate all inputs on batch create and edit: cutoff date
  must be a valid future date, maximum bottle volume must be a positive number, at least
  one variety must be selected, and the batch name must be unique across all existing
  batches; a duplicate name MUST be rejected at save with a specific error message.
- **FR-007**: The system MUST display actionable error messages when validation fails,
  stating specifically what is wrong and how to correct it; generic error messages are
  prohibited.
- **FR-008**: The system MUST reflect saved changes in the batch list immediately after
  a successful create or edit operation, without requiring a manual page refresh.
- **FR-009**: The batch management page MUST display a clear empty state when no batches
  exist, guiding the chef to create the first batch.
- **FR-010**: The batch list MUST visually distinguish batches by status (OPEN, CLOSED,
  COMPLETED) to allow the chef to scan and prioritize at a glance.
- **FR-012**: The system MUST prevent a chef from removing a variety from a batch's
  available list if one or more non-cancelled requests for that batch reference the
  variety; a specific, actionable error message MUST be displayed naming the variety
  that cannot be removed and stating that confirmed requests exist for it.

### Key Entities

- **Batch**: A production window that constrains what can be ordered. Key properties:
  unique identifier, human-readable name, cutoff date, maximum bottle volume in ml,
  list of available coquito variety identifiers, status (OPEN / CLOSED / COMPLETED),
  creation timestamp.
- **Coquito Variety**: A named flavor definition that a batch can make available for
  ordering. Referenced by identifier; its full details (ingredients, image) are managed
  separately.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A chef can view all batches and identify the status and cutoff date of any
  batch within 5 seconds of opening the batch management page.
- **SC-002**: A chef can create a new batch with all required properties in under
  2 minutes from opening the new-batch form.
- **SC-003**: A chef can locate and edit a specific batch property in under 1 minute
  of opening the batch management page.
- **SC-004**: 100% of invalid batch inputs (past cutoff date, missing fields, invalid
  volume) are caught before saving and surfaced with specific, actionable error messages.
- **SC-005**: Status and property changes made by the chef are visible in the batch list
  within 3 seconds of a successful save, with no manual refresh required.

## Clarifications

### Session 2026-05-07

- Q: Are status transitions (OPEN → CLOSED → COMPLETED) triggered manually by the chef, automatically by the system, or both? → A: Manual controls on the batch detail view, with the system also auto-closing an OPEN batch when its cutoff date is reached.
- Q: Which varieties should appear in the selection list when creating or editing a batch? → A: Only active varieties.
- Q: Does closing a batch (OPEN → CLOSED) require a confirmation dialog? → A: Yes, confirmation required for OPEN → CLOSED (showing active request count); CLOSED → COMPLETED proceeds without a dialog.
- Q: How does a chef navigate to the batch management page? → A: Dedicated navigation menu item visible only to authenticated chefs.
- Q: Is batch name uniqueness hard-enforced by the system or a soft guideline? → A: Hard-enforced — duplicate names are rejected at save with a specific error message.

## Assumptions

- The chef role is already defined and enforced by the existing authentication system
  (Cognito); this feature uses that role without modifying the auth layer.
- Coquito varieties are already stored and retrievable; the batch management page displays
  them for selection but does not create or edit variety definitions.
- Only one chef account exists at this time; concurrent editing conflict resolution is
  out of scope for this version.
- Batch deletion is out of scope; batches progress through statuses (OPEN → CLOSED →
  COMPLETED) rather than being removed.
- The page is expected to work on both desktop and mobile; the chef may use it from a
  laptop when planning and from a phone while coordinating.
- The maximum bottle volume applies globally to all orders within the batch; per-variety
  volume limits are out of scope.
- Status transitions only flow forward (OPEN → CLOSED → COMPLETED); reactivating a
  CLOSED or COMPLETED batch is out of scope for this version.
