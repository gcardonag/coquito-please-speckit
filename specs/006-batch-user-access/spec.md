# Feature Specification: Batch User Access Management

**Feature Branch**: `006-batch-user-access`  
**Created**: 2026-05-23  
**Status**: Draft  
**Input**: User description: "Add a new feature to the batch management page (#/batches) that only chefs can use in order to grant access to users to the batch. This process should allow adding either existing users with the option to search users or allow creating a user. Users should consist of emails that map to a first name and optional last name."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Grant Existing User Batch Access (Priority: P1)

A chef managing a batch navigates to the batch management page (#/batches) and needs to grant an existing user access to that batch. The chef can search for the user by name or email, select them from the results, and confirm granting access. This is the primary path because most users being added will already exist in the system.

**Why this priority**: Chefs will most frequently be re-adding known users to new batches. Fast search-and-grant is the core workflow and provides immediate value on its own.

**Independent Test**: Can be fully tested by a chef searching for a known user and granting them batch access, then verifying the user appears in the batch's access list.

**Acceptance Scenarios**:

1. **Given** a chef is on the batch management page (#/batches) for an active batch, **When** the chef opens the "Manage Access" panel and types a name or email into the search field, **Then** the system displays matching users from the user directory with their full name and email.
2. **Given** search results are displayed, **When** the chef selects a user and confirms, **Then** the user is granted access to the batch and the access list reflects the new entry immediately.
3. **Given** a user already has access to the batch, **When** the chef attempts to grant that user access again, **Then** the system prevents the duplicate and displays a clear message indicating the user already has access.
4. **Given** a chef searches for a user, **When** no matching users are found, **Then** the system displays an empty state with a prompt to create a new user instead.

---

### User Story 2 - Create a New User and Grant Batch Access (Priority: P2)

A chef needs to add someone to a batch who does not yet exist in the system. The chef can create a new user by providing their email address, first name, and optionally their last name. Upon successful creation, the new user is automatically granted access to the current batch.

**Why this priority**: Onboarding new users is a necessary complement to searching existing ones. Without it, chefs cannot add first-time users, but it is secondary because it applies to a smaller subset of interactions.

**Independent Test**: Can be fully tested by a chef creating a brand-new user (email + first name) and verifying the user appears in both the user directory and the batch's access list.

**Acceptance Scenarios**:

1. **Given** a chef is on the batch management page (#/batches), **When** the chef opens the "Manage Access" panel and chooses to create a new user, **Then** a form is presented with fields for email (required), first name (required), and last name (optional).
2. **Given** the chef submits the form with a valid email and first name, **When** the form is confirmed, **Then** the new user is created and immediately granted access to the current batch.
3. **Given** the chef enters an email that is already associated with an existing user, **When** the form is submitted, **Then** the system displays a clear error indicating the email is taken and suggests searching for that user instead.
4. **Given** the chef submits the form with a missing required field (email or first name), **When** the form is confirmed, **Then** the system highlights the missing field and prevents submission.
5. **Given** the chef enters an email in an invalid format, **When** the form is confirmed, **Then** the system rejects the entry with a message explaining the required format.

---

### User Story 3 - View Users with Batch Access (Priority: P3)

A chef managing a batch can view a list of all users currently granted access to that batch. This provides visibility into who can interact with the batch and confirms that recent access grants were applied correctly.

**Why this priority**: Visibility into current access is necessary for chefs to manage their batch responsibly, but it delivers supporting value rather than primary value — access must first be granted before viewing is useful.

**Independent Test**: Can be fully tested by opening the "Manage Access" panel on a batch that already has users and verifying the correct list of names and emails is displayed.

**Acceptance Scenarios**:

1. **Given** a chef is on the batch management page (#/batches) for a batch with existing access grants, **When** the chef opens the "Manage Access" panel, **Then** the system displays a list of all users with access, showing each user's full name and email.
2. **Given** no users have been granted access to the batch yet, **When** the chef opens the "Manage Access" panel, **Then** the system displays an empty state with a prompt to add the first user.

---

### User Story 4 - Revoke a User's Batch Access (Priority: P3)

A chef viewing the Manage Access panel for an open batch can remove a user who was previously granted access. The chef selects the user from the access list and confirms the revocation. The user is immediately removed from the batch's access list.

**Why this priority**: Revocation is necessary for complete access management but is less urgent than granting access; it is secondary to the grant workflows.

**Independent Test**: Can be fully tested by revoking access for a user on the batch's access list and verifying they no longer appear in the list.

**Acceptance Scenarios**:

1. **Given** a chef is on the batch management page (#/batches) for an open batch with users in the access list, **When** the chef selects a user and chooses to remove their access, **Then** the system displays a confirmation prompt before proceeding.
2. **Given** the confirmation prompt is displayed, **When** the chef confirms the revocation, **Then** the user is removed from the batch access list immediately.
3. **Given** the confirmation prompt is displayed, **When** the chef cancels, **Then** no change is made and the user remains in the access list.
4. **Given** a batch is closed, **When** a chef views the batch management page (#/batches), **Then** the revoke action is unavailable and the access list is read-only.

---

### Edge Cases

- What happens when a batch is closed — can a chef still grant access, or is the "Manage Access" feature locked?
- What happens if a user search returns a very large number of results — is there a result cap or pagination?
- What happens if the user creation fails due to a system error — is the access grant also rolled back?
- What happens if user creation succeeds but the subsequent access grant call fails? The user exists in Cognito but has no batch access. The frontend MUST display an actionable error message naming the created user and offer a "Grant access" shortcut that retries only the grant step without re-creating the user.
- How does the system behave when two chefs attempt to grant the same user access to the same batch simultaneously?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST restrict the Manage Access feature to users with the chef role; non-chef users MUST NOT see or access the feature.
- **FR-002**: System MUST provide a search interface on the batch management page (#/batches) that allows a chef to find existing users by partial name or email match.
- **FR-003**: System MUST display search results showing each matching user's full name and email address.
- **FR-004**: System MUST allow a chef to select a user from search results and grant that user access to the current batch in a single confirmation action.
- **FR-005**: System MUST prevent granting access when the selected user already has access to the batch, and MUST display an actionable error message.
- **FR-006**: System MUST provide a form to create a new user with the following fields: email address (required), first name (required), last name (optional).
- **FR-007**: System MUST validate that the email address provided during user creation is correctly formatted and not already associated with an existing user.
- **FR-008**: System MUST automatically grant the newly created user access to the current batch upon successful creation.
- **FR-009**: System MUST display the list of all users currently granted access to the batch within the Manage Access panel.
- **FR-010**: System MUST restrict access grant and revoke actions to open batches only; the Manage Access panel MUST be hidden or disabled when the batch is closed.
- **FR-011**: System MUST allow a chef to remove (revoke) a user's access from the batch within the Manage Access panel, with an explicit confirmation step before the revocation is applied.

### Key Entities

- **User**: A person who can be granted batch access; identified by a unique email address; has a required first name and an optional last name; exists globally and can be granted access to any batch.
- **Batch Access Grant**: A record associating a specific user with a specific batch; represents permission to interact with that batch; created by a chef action.
- **Batch**: An existing entity representing a production run; the subject of the access grant; accessed via the batch management page (#/batches).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A chef can find an existing user and grant them batch access in under 60 seconds from opening the Manage Access panel.
- **SC-002**: A chef can create a new user and grant them batch access in under 2 minutes from opening the create user form.
- **SC-003**: 100% of access grants are immediately reflected in the batch's user access list without requiring a page reload.
- **SC-004**: Search results appear within 1 second of the chef entering a search query.
- **SC-005**: Duplicate access grants are prevented in 100% of attempts, with a clear message guiding the chef to the correct action.
- **SC-006**: The Manage Access feature is invisible and inaccessible to non-chef users in 100% of cases.

## Assumptions

- Only chefs (as defined by the existing role system) can use the Manage Access feature; no new roles or permissions beyond what already exists are introduced.
- The "current batch" is the batch whose batch management page (#/batches) the chef is viewing; access grants are batch-specific, not global.
- Users exist at a global scope (not per-batch); a user created for one batch is discoverable when granting access to other batches.
- "Batch access" grants users the ability to view and submit requests against the batch; the exact interaction model follows the existing request workflow.
- The feature is accessed via a panel or section within the existing batch management page (#/batches), not a separate page.
- Email is the unique identifier for a user; no two users may share the same email address.
- Access grants and revocations are only permitted on open batches; the Manage Access panel is hidden or read-only on closed batches.
