import { getScanOutcome, type ScanOutcome } from "@/types"
export const scanOutcomeLabels: Record<ScanOutcome, string> = { queued: "Queued", running: "Running", completed_with_findings: "Completed with findings", completed_clean: "Completed clean", failed: "Failed", cancelled: "Cancelled" }
export { getScanOutcome }
