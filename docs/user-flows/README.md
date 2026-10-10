# Repo Security Auditor user-flow documentation

These documents describe the implemented Next.js routes, UI states, interactions, mock API calls, redirects, and recovery paths. The primary journeys are authenticate, connect a repository, choose a branch, run a scan, inspect evidence/findings, and generate/download a PDF report; Settings and Help provide account, integration, preference, and guidance surfaces.

## Documents

1. [Screen inventory](./01-screen-inventory.md)
2. [Transition inventory](./02-transition-inventory.md)
3. [End-to-end user flows](./03-user-flows.md)
4. [Coverage check](./04-coverage-check.md)
5. [Review findings and decisions](./05-review-findings.md)

## How to read these docs

Screen IDs (S-*) identify a rendered route or distinct state. Transition IDs (T-*) identify a clickable, keyboard, form, redirect, polling, or close action. Flow IDs (F-*) compose transitions into user journeys. Cosmetic marks a control that only closes UI, changes local presentation state, or shows a toast without a navigational or server-side result. Source citations use the current file and line numbers.

