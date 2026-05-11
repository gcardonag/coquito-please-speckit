# Feature Specification: Chef Variety Management

**Feature Branch**: `005-variety-management`  
**Created**: 2026-05-09  
**Status**: Draft  
**Input**: User description: "Add a new page that only chefs can use in order to list, manage, and create coquito varieties and their properties. This is intended as a way to simplify variety management and all existing variety properties."

## Clarifications

### Session 2026-05-09

- Q: Should chefs be able to permanently delete a variety, or is deactivation the only removal mechanism? → A: No permanent delete — deactivate only.
- Q: How are ingredients identified for update/delete — system-assigned stable ID or chef-entered key? → A: System-assigned stable ID, hidden from the chef; renaming an ingredient's display name is a safe edit.
- Q: What does the chef see when a valid save fails due to a server or network error? → A: Inline error message; form stays open with edits intact so the chef can retry without re-entering data.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse All Varieties (Priority: P1)

A chef navigates to the Variety Management page and sees every variety in the system — both active and inactive — presented in a scannable list. Each entry shows the variety name, its active/inactive status, a short description, and its bottle yield. This gives the chef a complete picture of the variety catalog at a glance.

**Why this priority**: Viewing the full variety list is the entry point to all other management actions. Without it, no other story is reachable. It is also the quickest win that unblocks the chef from depending on direct database access.

**Independent Test**: Navigating to the Variety Management page and verifying that all seeded varieties appear with correct name, status, description, and bottle yield — delivers read-only catalog visibility independently of any write capability.

**Acceptance Scenarios**:

1. **Given** a chef is logged in, **When** they navigate to the Variety Management page, **Then** the page displays all varieties (active and inactive) with name, status badge, description, and bottle yield per bottle.
2. **Given** there are both active and inactive varieties, **When** the chef views the page, **Then** inactive varieties are visually distinguished from active ones (e.g., dimmed or labelled "Inactive").
3. **Given** a non-chef user is logged in, **When** they attempt to access the Variety Management page, **Then** access is denied and they are redirected or shown an appropriate error.

---

### User Story 2 - Edit Variety Properties (Priority: P2)

A chef selects an existing variety and edits its top-level properties: name, description, bottle yield in millilitres, and active/inactive status. Changes are saved immediately. This replaces the need to manipulate the database directly for minor updates.

**Why this priority**: Editing existing varieties is the most frequent maintenance action. Activating or deactivating a variety directly affects what customers can order, making this high-impact. Creating new varieties is less frequent than adjusting existing ones.

**Independent Test**: Selecting any seeded variety, changing its description and toggling its active status, saving, and confirming the changes persist on reload — delivers editing value independently of create or ingredient management.

**Acceptance Scenarios**:

1. **Given** a chef views the variety list, **When** they select a variety and change its name, description, bottle yield, or active status, **Then** saving the form updates the variety and the change is immediately reflected on the variety list.
2. **Given** a chef submits an edit with a blank name, **When** the form is submitted, **Then** submission is blocked and a clear error message indicates which field is required.
3. **Given** a chef deactivates a variety, **When** a customer views the public variety selection, **Then** that variety no longer appears in the customer-facing list.
4. **Given** a chef reactivates a previously inactive variety, **When** a customer views the public variety selection, **Then** that variety is available again.

---

### User Story 3 - Manage Variety Ingredients (Priority: P3)

A chef views the full ingredient list for a variety and can add new ingredients, edit existing ones (name, quantity per bottle, unit, category), or remove ingredients. Each ingredient change is reflected immediately in how the system calculates ingredient requirements for batches.

**Why this priority**: Ingredient management is more complex than top-level edits and is needed less frequently, but it is critical for recipe accuracy. Batch ingredient list generation depends entirely on this data being correct.

**Independent Test**: Opening any variety's ingredient section, adding a new ingredient with all required fields, saving, and verifying it appears in the ingredient list — delivers ingredient-add value independently of the create-variety story.

**Acceptance Scenarios**:

1. **Given** a chef opens a variety, **When** they view the ingredients section, **Then** all current ingredients are listed with name, quantity per bottle, unit, and category.
2. **Given** a chef adds a new ingredient with a name, quantity, unit, and category, **When** they save, **Then** the ingredient appears in the variety's ingredient list.
3. **Given** a chef edits an ingredient's quantity per bottle, **When** they save, **Then** the updated quantity is reflected in the ingredient list and in any subsequent batch ingredient calculations.
4. **Given** a chef removes an ingredient, **When** they confirm deletion, **Then** the ingredient no longer appears in the variety's ingredient list.
5. **Given** a chef submits an ingredient with a missing required field (name, quantity, unit, or category), **When** the form is submitted, **Then** submission is blocked and an actionable error message identifies the missing field.

---

### User Story 4 - Create a New Variety (Priority: P4)

A chef creates a brand-new coquito variety by providing a name, description, bottle yield, active status, and an initial set of ingredients. The new variety appears in the variety list immediately after creation and can be assigned to batches.

**Why this priority**: New varieties are created infrequently compared to edits. However, as the product expands its flavor offerings, having a self-service creation path removes the bottleneck of requiring engineering access to the database.

**Independent Test**: Creating a variety with a unique name, at least one ingredient, and saving — then verifying the variety appears in the chef's variety list with the correct details — delivers self-service creation value independently of other stories.

**Acceptance Scenarios**:

1. **Given** a chef opens the "Create Variety" form, **When** they submit a valid variety with name, description, bottle yield, and at least one ingredient, **Then** the new variety is saved and appears in the variety list.
2. **Given** a chef submits the create form with a blank name, **When** the form is submitted, **Then** submission is blocked with an error identifying the missing field.
3. **Given** a chef creates a variety without adding any ingredients, **When** they attempt to submit, **Then** they are warned that no ingredients have been added but may still choose to save the variety.
4. **Given** a variety with the same name already exists, **When** a chef creates another with the identical name, **Then** the system allows it and both varieties coexist (names are not enforced as unique).

---

### Edge Cases

- What happens when a chef saves an edit while another chef has concurrently modified the same variety? Last-write-wins is acceptable; no concurrent-edit detection is required for v1.
- What happens when a variety is referenced by one or more open batches and the chef deactivates it? The variety is deactivated in the catalog but remains in any existing batch's available variety list — no retroactive batch update occurs.
- What if the image key field is left blank during creation or edit? The variety is saved without an image; the UI shows a placeholder graphic.
- What if a chef enters a non-numeric value for bottle yield or ingredient quantity? The form must validate that these fields are positive numbers before allowing submission.
- What happens if the variety list is empty? The page displays an empty-state message encouraging the chef to create the first variety.
- Can a chef permanently delete a variety? No — permanent deletion is out of scope. Deactivation is the only removal path; this avoids cascade complexity with batches that already reference the variety.
- What happens if a save fails mid-submission (network timeout, server error)? The form displays an inline error message, remains open, and preserves all of the chef's edits so they can retry without data loss.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST restrict the Variety Management page and all its write operations to authenticated users with the chef role; any other user attempting access MUST receive a permission-denied response.
- **FR-002**: System MUST display all varieties (both active and inactive) on the Variety Management page, unlike the customer-facing listing which shows only active varieties.
- **FR-003**: System MUST allow a chef to edit any of the following top-level variety fields: name, description, bottle yield (ml), and active status.
- **FR-004**: System MUST allow a chef to add, edit, and remove individual ingredients on any variety; each ingredient requires a name, quantity per bottle (positive number), unit of measurement, and category.
- **FR-005**: System MUST allow a chef to create a new variety with at minimum a name and bottle yield; description, image key, active status, and ingredients are also configurable at creation time.
- **FR-006**: System MUST validate that required fields (variety name, bottle yield, and each ingredient's name/quantity/unit/category) are non-empty and that numeric fields contain positive numbers before accepting a save or create action.
- **FR-007**: System MUST provide actionable error messages when validation fails, stating which field is invalid and what the chef should do to correct it.
- **FR-008**: System MUST reflect all saved changes immediately in the variety list without requiring a full page reload.
- **FR-009**: System MUST allow a chef to toggle a variety's active status; deactivating a variety removes it from the customer-facing public variety listing on the next customer page load.
- **FR-010**: System MUST NOT provide a permanent delete action for varieties; deactivation is the only removal mechanism available to chefs in this feature.
- **FR-011**: When a save or create action fails due to a server or network error, the system MUST display an inline error message on the form, keep the form open, and preserve all of the chef's unsaved edits so they can correct the issue and retry without re-entering data.

### Key Entities

- **Variety**: A named coquito recipe managed by chefs. Attributes: system-assigned unique identifier, name, description, image reference key, bottle yield in millilitres, active/inactive status, and an ordered list of ingredients.
- **Ingredient**: A component of a variety's recipe. Attributes: system-assigned stable unique identifier (not visible or editable by the chef), name, quantity per bottle (positive decimal), unit of measurement (e.g., ml, g, oz), and category (e.g., dairy, spirit, flavoring). Renaming an ingredient's display name does not change its identity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A chef can view the complete variety catalog, including inactive varieties, within 3 seconds of navigating to the Variety Management page.
- **SC-002**: A chef can create a new variety end-to-end (fill form, add at least one ingredient, save) in under 3 minutes.
- **SC-003**: A chef can update a variety's active status and see the change reflected on the Variety Management page in under 5 seconds after saving.
- **SC-004**: 100% of invalid form submissions (missing required fields, non-numeric quantities) are rejected with specific, actionable error messages before any data is written.
- **SC-005**: Deactivating a variety removes it from the customer-facing variety selection on the next customer page load; no stale data is shown to customers after a chef deactivates a variety.
- **SC-006**: The Variety Management page is inaccessible to non-chef users; 100% of unauthorized access attempts receive a permission-denied response without exposing any variety data.

## Assumptions

- Chefs are already authenticated via the existing Cognito-based auth system; the chef role is determined by the existing role claim set at login, consistent with how the batch management page enforces chef-only access.
- Image management (uploading new images to storage) is out of scope for this feature; chefs can enter or update an image reference key manually, but no image-upload UI is required.
- There is no requirement to version or audit-log variety changes in v1; last-write-wins is acceptable.
- Variety identifiers are system-assigned at creation time and are not editable by the chef.
- The feature follows the existing hash-based single-page routing pattern (e.g., `#/varieties`) and the visual and interaction conventions established by the batch management page.
- Concurrent editing by multiple chefs simultaneously is possible but rare; no locking or conflict-resolution mechanism is required for v1.
- Mobile support follows the existing responsive design baseline already established for chef-facing pages.
