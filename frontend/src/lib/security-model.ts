// Static presentation metadata and pure selectors used by the screens.
// Repository, scan, finding, and report records themselves come from API hooks.
export { categories, getRepositoryFindings, getWorkspaceFindings, getScanFindings, getFindingContext, scannerInfo, severityOrder, scanBoundaries, scanActivity, scanStages } from "@/app/data"
export type { Category, DemoOutcome, Finding, FindingStatus, Repository, Scan, Severity, ScanStatus } from "@/app/data"
