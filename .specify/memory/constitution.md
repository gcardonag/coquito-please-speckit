<!--
SYNC IMPACT REPORT
==================
Version change: [TEMPLATE] → 1.0.0 (initial ratification)
Modified principles: N/A — all principles are new (first fill of template)
Added sections:
  - Core Principles: I. Code Quality, II. Testing Standards,
    III. User Experience Consistency, IV. Performance Requirements
  - Quality Gates
  - Development Workflow
  - Governance
Removed sections: N/A
Templates checked:
  - .specify/templates/plan-template.md  ✅ Constitution Check section present; aligns with all four principles
  - .specify/templates/spec-template.md  ✅ User story + acceptance scenario format supports UX Consistency and Testing Standards
  - .specify/templates/tasks-template.md ✅ Phase structure (tests-first option, checkpoints) aligns with Testing Standards principle
  - .specify/templates/commands/*.md     ✅ No such directory exists — no action required
Deferred TODOs: None
-->

# Coquito Please Constitution

## Core Principles

### I. Code Quality

All code MUST be readable, maintainable, and consistent with the project's established
conventions. The following rules are non-negotiable:

- Every function, class, or module MUST have a single, clearly stated responsibility.
- Duplicated logic MUST be extracted before a pull request is merged; no copy-paste
  implementations are permitted.
- Code MUST pass all configured linters and static analysis tools with zero warnings
  before merging.
- Dead code, commented-out blocks, and unused imports MUST be removed; they are not
  permitted in any merged commit.
- All public APIs and non-obvious logic MUST include inline documentation sufficient
  for a new contributor to understand intent without reading the implementation.

**Rationale**: Inconsistent or low-quality code compounds over time. Enforcing quality at
every merge keeps the codebase navigable and reduces the cost of future changes.

### II. Testing Standards

Automated testing is mandatory and follows a test-first discipline for all new features:

- Tests MUST be written before implementation code; the Red-Green-Refactor cycle is
  enforced for every user story.
- Every user story MUST have at least one integration test that exercises the full
  path from input to output without mocking the core domain layer.
- Unit test coverage MUST remain at or above 80% for all source modules; any PR that
  reduces coverage below this threshold is automatically rejected.
- Tests MUST be deterministic and isolated; flaky tests MUST be fixed or removed
  within one sprint of discovery.
- Contract tests MUST be written for every external interface (API endpoint, message
  queue schema, third-party integration) before the interface ships.

**Rationale**: Test-first discipline catches design flaws early and provides a living
specification of expected behavior. Coverage floors prevent silent regressions.

### III. User Experience Consistency

The product MUST present a coherent, predictable interface to users across all surfaces:

- All user-facing text (labels, errors, notifications, empty states) MUST follow the
  established content style guide; deviations require explicit design approval.
- Interactive elements (buttons, inputs, navigation) MUST behave identically across
  equivalent contexts; no surface-specific behavioral overrides without documented
  justification.
- Error messages MUST be actionable: they MUST state what went wrong, why, and what
  the user can do next. Generic messages ("Something went wrong") are prohibited.
- Accessibility MUST meet WCAG 2.1 AA as a minimum; new UI components MUST pass an
  automated accessibility check before merge.
- Visual and interaction design changes MUST be reviewed against the design system
  before implementation begins.

**Rationale**: Users build mental models from consistent patterns. Inconsistency erodes
trust and increases support burden.

### IV. Performance Requirements

The system MUST meet defined performance budgets at all times; degradation is a bug:

- API endpoints MUST respond within 200 ms at the 95th percentile under normal load.
- Page or screen load time (Time to Interactive) MUST not exceed 3 seconds on a
  median mobile device and connection.
- Any change that regresses a tracked performance metric by more than 10% MUST
  include a documented justification and a mitigation plan before merging.
- Background jobs and batch operations MUST not impact user-facing response times;
  they MUST run in isolated workers with resource caps.
- Performance benchmarks MUST be run as part of CI on every pull request that touches
  critical paths (data fetching, rendering, or request handling).

**Rationale**: Performance is a feature. Establishing measurable budgets and enforcing
them in CI prevents gradual degradation that is difficult to reverse.

## Quality Gates

Before any feature branch may be merged to the main branch, all of the following gates
MUST pass:

- All automated tests pass (unit, integration, contract).
- Code coverage is at or above 80% for modified modules.
- Linter and static analysis report zero warnings.
- Automated accessibility check passes for any UI changes.
- Performance benchmarks show no regression beyond the 10% threshold.
- A peer code review with at least one approval from a team member not on the
  implementing pair has been completed.
- The Constitution Check in the feature plan confirms no principle is violated; any
  deviation is documented in the Complexity Tracking section.

## Development Workflow

Features MUST progress through the following stages in order. Skipping stages is not
permitted:

1. **Spec** (`/speckit.specify`): captures user stories with acceptance scenarios,
   functional requirements, and success criteria.
2. **Plan** (`/speckit.plan`): defines architecture, data model, contracts, and
   passes the Constitution Check.
3. **Tasks** (`/speckit.tasks`): translates the plan into ordered, independently
   executable tasks organized by user story.
4. **Implementation** (`/speckit.implement`): executes tasks one by one; each
   checkpoint validates the user story independently before moving on.

If a spec is missing, incomplete, or conflicts with this constitution, work MUST stop
and the issue MUST be resolved before proceeding. Do not infer. Do not proceed.

## Governance

This constitution supersedes all other project practices, guidelines, and preferences.
Amendments require:

1. A written proposal identifying the principle or section being changed and the
   motivation for the change.
2. A version bump following semantic versioning:
   - **MAJOR**: principle removed or incompatibly redefined.
   - **MINOR**: new principle added or existing guidance materially expanded.
   - **PATCH**: clarification, wording fix, or non-semantic refinement.
3. A Sync Impact Report (prepended as an HTML comment at the top of this file)
   listing every affected template and command with ✅ (updated) or ⚠ (pending) status.
4. All ⚠ items MUST be resolved before the amendment is considered ratified.

All pull requests MUST include a Constitution Check confirming no principle is violated.
Undocumented complexity or quality shortcuts are grounds for rejection without exception.

**Version**: 1.0.0 | **Ratified**: 2026-03-27 | **Last Amended**: 2026-03-27
