# Feature Specification: Responsive Layout Across All Flows

**Feature Branch**: `007-responsive-layout`
**Created**: 2026-10-16
**Status**: Draft
**Input**: User description: "Responsive layout across all site flows: make every user flow use desktop space well (roughly 1024px and wider) while still working visually on mobile (375px). Today each page is a single narrow column capped at a fixed width, leaving large empty margins on desktop. Flows in scope: request a coquito, view/edit/cancel my request, cook view, chef batch management (incl. Manage Access), chef variety management, 404 page, and the global shell (chef nav, Log out button, top banner). Layout/presentation only; no behavior changes; existing test selectors preserved; WCAG 2.1 AA; touch targets ≥ 44px."

## Overview

Every page of Coquito Please is currently laid out as one narrow column (480–800px wide) regardless of screen size, and no page adapts to the width of the screen. On a laptop or desktop monitor most of the screen is empty margin; chefs editing batches or varieties must scroll past the entire list to reach the edit form that opens beneath it. On phones the pages mostly work, but a few rows are cramped (pickup date/time side by side, ingredient rows with four fields, button rows that don't wrap) and the floating chef navigation and Log out button overlap each other and can cover the last item on the page.

This feature makes every existing flow adapt its layout to three width ranges — **mobile**, **tablet**, and **desktop** — without changing what any flow does.

### Width ranges (used throughout this spec)

| Range | Viewport width | Reference device |
|-------|----------------|------------------|
| Mobile | below 640px | 375px phone |
| Tablet | 640px – 1023px | 768px tablet portrait |
| Desktop | 1024px and wider | 1280px and 1440px laptop/monitor |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chef manages batches and varieties side-by-side on desktop (Priority: P1)

A chef planning a holiday batch opens Manage Batches on a laptop. The batch list appears in a column on the left and the selected batch's details (edit form, status controls, Manage Access panel) appear in a panel on the right, so the chef can click from batch to batch and see details immediately without scrolling. Manage Varieties works the same way, and a variety's ingredient rows show name, quantity, unit and category on one line. On a phone, both pages remain a single stacked column, and ingredient fields stack so each is comfortably wide.

**Why this priority**: The chef pages are the narrowest on the site (480px) yet are the ones used most on a laptop, and the detail form rendering below the full list is the largest usability cost of the current layout.

**Independent Test**: Open `#/batches` and `#/varieties` at 1280px with several items; select an item and confirm the details appear beside the list without scrolling. Repeat at 375px and confirm a single column with no horizontal scrolling.

**Acceptance Scenarios**:

1. **Given** a chef on Manage Batches at desktop width with 5+ batches, **When** they select a batch, **Then** the batch's edit form appears in a detail panel beside the list and the list remains visible.
2. **Given** the same chef selects "New Batch" at desktop width, **When** the form opens, **Then** it appears in the same detail panel beside the list.
3. **Given** a chef at desktop width with the detail panel showing an OPEN batch, **When** they expand Manage Access, **Then** the user search input and its Search button sit on one row, and search results and the access list are fully readable without truncating email addresses shorter than 40 characters.
4. **Given** a chef at mobile width, **When** they select a batch or variety, **Then** the detail panel appears below the list in a single column and the page brings the detail panel into view.
5. **Given** a chef editing a variety at desktop width, **When** they view the ingredients editor, **Then** each ingredient's name, quantity, unit, category and Remove control appear on a single row.
6. **Given** a chef editing a variety at mobile width, **When** they view the ingredients editor, **Then** each ingredient's fields stack so no input is narrower than 120px and the Remove control remains at least 44×44px.
7. **Given** a chef at desktop width, **When** they view the batch create/edit form's variety checklist, **Then** varieties are shown in multiple columns.
8. **Given** a confirmation dialog (Close Batch, Remove access) at any width, **When** it opens, **Then** it is centred, fully visible, and its buttons are reachable without scrolling.

---

### User Story 2 - Customer places a request comfortably on any device (Priority: P1)

A customer opens the request link. On desktop, the form uses the wider space: short related fields (name and email; pickup date and time) sit side by side, the variety picture grid shows more varieties per row, and the bottle-preference and cost choices appear as side-by-side options. On a phone, every field is full width and date and time stack vertically.

**Why this priority**: This is the primary customer-facing flow and the entry point for all orders.

**Independent Test**: Load `#/?batchId=<id>` at 375px, 768px, and 1280px; complete and submit the form at each width.

**Acceptance Scenarios**:

1. **Given** a customer at desktop width, **When** the form loads, **Then** name and email appear side by side, pickup date and time appear side by side, and the variety grid shows at least 4 varieties per row (when 4 or more exist).
2. **Given** a customer at mobile width, **When** the form loads, **Then** every field is full width, pickup date and time are stacked, and no horizontal scrolling occurs.
3. **Given** a customer at desktop width, **When** they view bottle preference and cost contribution, **Then** each question's options appear side by side.
4. **Given** a validation error on any field at any width, **When** it appears, **Then** it is shown directly beneath its own field and does not shift the neighbouring side-by-side field out of alignment.
5. **Given** a successful submission at any width, **When** the confirmation appears, **Then** the confirmation card and its "View My Order" link are fully visible and readable.
6. **Given** any width, **When** the hero heading renders, **Then** it scales down on mobile so it fits on at most 2 lines at 375px.

---

### User Story 3 - Customer reviews, edits or cancels a request on any device (Priority: P2)

A customer opens their manage link. On desktop the order summary is presented in a wider card with the details arranged in two columns of label/value pairs, and the edit form uses the same side-by-side date/time arrangement as the request form. On a phone the summary is a single column, long values (such as a pickup location) wrap beneath their label rather than squeezing against it, and the Edit/Cancel and Save/Discard button rows wrap instead of compressing.

**Why this priority**: Secondary customer flow; less frequent than placing a request but used on phones from a shared link.

**Independent Test**: Open `#/manage/<id>` for an editable and a locked request at 375px and 1280px; open the edit form and the cancel dialog at each width.

**Acceptance Scenarios**:

1. **Given** a customer at desktop width, **When** the summary loads, **Then** the summary details are arranged in two columns.
2. **Given** a customer at mobile width with a pickup location longer than 30 characters, **When** the summary loads, **Then** the value is fully readable and does not overlap or squeeze its label.
3. **Given** a customer opens the page directly (not after submitting the request form), **When** they open the edit form, **Then** the inputs are styled identically to the request form's inputs.
4. **Given** a customer at mobile width, **When** they view action buttons (Edit/Cancel, Save/Discard, dialog Yes/Keep), **Then** each button's label is fully visible on one line, wrapping the row if necessary.
5. **Given** the cancel dialog at mobile width, **When** it opens, **Then** it fits within the screen with at least 16px margin on each side.
6. **Given** the locked, cancelled and not-found states, **When** shown at any width, **Then** they are centred and use the same width rules as the summary card.

---

### User Story 4 - Cook works through the shopping list on a large screen or phone (Priority: P2)

A cook opens the cook view on a laptop or kitchen tablet. On desktop, the per-variety ingredient checklists are arranged in columns and the total shopping list sits alongside or beneath them, so the whole list is visible with far less scrolling. The preview banner lines up with the content. On a phone, sections stack in a single column with large checkboxes, as today.

**Why this priority**: Used during shopping and cooking; the current 800px column is already usable, so the gain is less than for the chef pages.

**Independent Test**: Open `#/cook?batchId=<id>` for a batch with 3+ varieties at 1280px and 375px; tick items at each width.

**Acceptance Scenarios**:

1. **Given** a batch with 3+ varieties at desktop width, **When** the cook view loads, **Then** variety sections are shown in at least 2 columns.
2. **Given** the preview banner is shown at desktop width, **When** the page loads, **Then** the banner's left and right edges align with the content area beneath it.
3. **Given** mobile width, **When** the totals table renders, **Then** all three columns are readable without the page scrolling horizontally (the table itself may scroll horizontally if needed).
4. **Given** any width, **When** a cook ticks an ingredient, **Then** the checkbox and its row remain at least 44px tall.

---

### User Story 5 - Navigation and global controls never cover content (Priority: P1)

Any signed-in user sees the Log out control, and chefs additionally see links to Manage Batches and Manage Varieties. At every width these controls are fully visible, never overlap one another, and never hide page content such as the last list row or a submit button. The top status banner, when shown, does not cover the page heading.

**Why this priority**: The overlap at phone width affects every chef on every page, and controls covering submit buttons can block task completion.

**Independent Test**: Sign in as a chef and as a non-chef; at 375px and 1280px, visit every route and scroll to the bottom of each page; trigger the top banner.

**Acceptance Scenarios**:

1. **Given** a chef at 375px, **When** any page loads, **Then** the chef navigation links and the Log out control do not overlap.
2. **Given** any user at any width, **When** they scroll to the bottom of any page, **Then** the last content item (submit button, last list row, last table row) is fully visible and clickable.
3. **Given** the top banner is shown, **When** the page renders, **Then** the page heading is not hidden beneath it.
4. **Given** a chef at any width, **When** they view the navigation, **Then** the current page's link is visually distinguishable from the others.

The floating bottom-corner chef nav and Log out button are replaced by a persistent header bar at the top of every page, containing the app name, the chef links (chefs only) and Log out. On mobile the header wraps its links onto a second line rather than overlapping.

---

### User Story 6 - Not-found page is consistent at every width (Priority: P3)

A visitor following a bad link sees the 404 card centred and readable on any device, using the same card and width rules as other pages.

**Why this priority**: Rarely seen; low effort.

**Independent Test**: Visit `#/does-not-exist` at 375px and 1280px.

**Acceptance Scenarios**:

1. **Given** an unknown route at any width, **When** the page loads, **Then** the not-found card is centred, readable, and its link back to the home page is at least 44px tall.

---

### Edge Cases

- **Exactly at a boundary** (639/640px, 1023/1024px): layout switches cleanly with no intermediate broken state or horizontal scrollbar.
- **Very wide screens** (1920px+): content is capped at a maximum readable width and centred; text lines do not stretch across the full screen.
- **Browser zoom at 200%** on a 1280px screen (effective 640px): layout follows the tablet rules and remains fully usable (WCAG 1.4.10 Reflow).
- **Small phones** (320px): no horizontal page scrolling; all controls remain usable.
- **Rotating a device** between portrait and landscape: layout updates without losing form input or the selected batch/variety.
- **Long content** (long batch/variety names, long emails in Manage Access, long ingredient names, 15+ varieties): text wraps or truncates with the full value still available (e.g., on hover/focus or in the detail panel); nothing overflows its container.
- **Empty states** (no batches, no varieties, no ingredients): empty-state message is centred within the list area; desktop detail panel shows a neutral prompt or is empty without breaking layout.
- **Chef selects an item at desktop width, then narrows the window to mobile**: the selection and any unsaved form input are preserved.
- **Keyboard users**: focus order follows the visual order (list before detail panel; left field before right field).

## Requirements *(mandatory)*

### Functional Requirements

**Global**

- **FR-001**: Every page MUST render without horizontal page scrolling at all widths from 320px to 2560px.
- **FR-002**: The site MUST define three width ranges (mobile < 640px, tablet 640–1023px, desktop ≥ 1024px) as shared design values used consistently by every page.
- **FR-003**: Each page's main content MUST widen beyond its current cap at desktop width, up to a shared maximum content width, and remain centred beyond that width.
- **FR-004**: Headings MUST scale with viewport width so that page titles fit on at most 2 lines at 375px.
- **FR-005**: Shared form field and input styling MUST appear identically on every page that uses it, regardless of which page the user opened first.
- **FR-006**: All interactive controls MUST keep a minimum touch target of 44×44px at every width; existing references to an undefined touch-target value MUST be corrected so this minimum actually applies.
- **FR-007**: The chef navigation, Log out control, and top banner MUST NOT overlap each other or obscure page content at any width (see User Story 5 clarification).
- **FR-008**: Focus order MUST match visual order at every width.
- **FR-009**: All pages MUST meet WCAG 2.1 AA at every width range, including 1.4.10 Reflow and 1.4.4 Resize Text.

**Request a coquito**

- **FR-010**: At tablet and desktop widths, name/email and pickup date/time MUST each appear as side-by-side pairs; at mobile width all fields MUST stack.
- **FR-011**: The variety picture grid MUST show more varieties per row as width increases (at least 2 at 375px, at least 4 at 1024px+).
- **FR-012**: At tablet and desktop widths, bottle-preference and cost-contribution options MUST appear side by side; at mobile width they MUST stack.
- **FR-013**: There MUST be a single, consistent definition of the date/time pair layout shared by the request form and the manage-request edit form.

**View/edit/cancel request**

- **FR-014**: At desktop width the order summary MUST arrange its details in two columns; at mobile width, label and value MUST stack when the value does not fit beside the label.
- **FR-015**: Action button rows (summary, edit form, cancel dialog) MUST wrap rather than compress labels at narrow widths.
- **FR-016**: The cancel dialog MUST fit within the viewport with at least 16px margin at mobile width.

**Cook view**

- **FR-017**: At desktop width, variety ingredient sections MUST be arranged in at least 2 columns when there are 2 or more varieties.
- **FR-018**: The preview banner MUST align with the content width at every width.
- **FR-019**: The totals table MUST remain readable at mobile width without causing horizontal page scroll.

**Chef batch & variety management**

- **FR-020**: At desktop width, Manage Batches and Manage Varieties MUST present the item list and the detail/create panel side by side, with the list remaining visible while a detail is open.
- **FR-021**: At mobile and tablet widths, the list and detail panel MUST stack, and selecting an item or "New" MUST bring the detail panel into view.
- **FR-022**: At desktop width, the batch form's variety checklist MUST show multiple columns.
- **FR-023**: At desktop width, Manage Access search input and Search button MUST share a row.
- **FR-024**: Variety ingredient rows MUST show all fields on one row at desktop width and stack at mobile width.
- **FR-025**: The batch edit form MUST use the same card styling as the batch create form.

**Constraints**

- **FR-026**: No flow's behavior, data, text, or sequence of steps may change; only layout and presentation (and the minimal scroll-into-view in FR-021) may change.
- **FR-027**: All existing automated-test selectors and class names that tests depend on MUST be preserved.
- **FR-028**: The chef pages' primary and secondary buttons MUST be given the site's standard button styling (existing colours and shapes), replacing the current unstyled browser default.
- **FR-029**: A persistent header bar MUST appear at the top of every page with the app name, chef navigation links (chefs only), and Log out; it MUST replace the floating bottom-corner controls and MUST NOT cover page content at any width.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At 1280px, every page's main content occupies at least 70% of the viewport width (up to the shared maximum content width), compared with 37–62% today.
- **SC-002**: At 1280px, a chef can open the details of any batch or variety without scrolling the page, for lists of up to 10 items.
- **SC-003**: Zero pages show horizontal page scrolling at 320px, 375px, 768px, 1024px, 1280px and 1920px.
- **SC-004**: Zero instances of global controls overlapping each other or covering content, across all routes at 375px and 1280px, for both chef and non-chef users.
- **SC-005**: Automated accessibility checks report zero WCAG 2.1 AA violations on every route at 375px and 1280px.
- **SC-006**: All existing automated tests pass unchanged.
- **SC-007**: Page load time on a median mobile device stays within 3 seconds and does not regress by more than 10%.
- **SC-008**: A customer can complete the request form at 375px and at 1280px with every field, error message and button fully visible without zooming.

## Clarifications

### Session 2026-10-16

- Q: Where should global navigation and Log out live? → A: A persistent top header bar on every page, replacing the floating bottom-corner controls.
- Q: Should unstyled chef-page buttons be styled in this feature? → A: Yes, apply the site's standard button styling.

## Assumptions

- Width ranges are 640px and 1024px boundaries; the shared desktop maximum content width is around 1200px (to be finalized in planning against the design system). The cook view keeps its larger text and checkbox sizes at every width.
- The request form's hero remains a full-width band; only its contents' sizing adapts.
- On manage-request, the edit form continues to replace the summary when opened (current behavior); side-by-side summary + edit is not introduced, as it would change flow behavior.
- The cook view's access-check and `cookSecret` handling, the unused starter stylesheet, and other unused CSS noted during discovery are out of scope except where removing them is required by the code-quality principle for files this feature touches.
- Role gating, routing, and API behavior are unchanged.
- Existing colours, typography and spacing values are reused; no new visual identity is introduced. Any new shared values (breakpoints, maximum content width) are added to the existing design tokens.
- Tablet behaviour follows mobile rules for list/detail pages and desktop rules for side-by-side form field pairs unless stated otherwise.
