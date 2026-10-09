import {
  categories,
  getFindingContext,
  getScanFindings,
  repositoryMetadata,
  scannerInfo,
  severityOrder,
  type Finding,
  type Repository,
  type Scan,
} from "./data"

export function buildReport(repo: Repository, scan: Scan, findings: Finding[]) {
  const captured = getScanFindings(scan, findings)
  return {
    disclaimer:
      "Fictional frontend demo. No repository was fetched, no scanner ran, and no AI service was called.",
    scope:
      "Configured static checks on a repository snapshot. Not a guarantee of security or exploitability. Incomplete scanner coverage remains explicitly reported.",
    repository: repositoryMetadata(repo),
    scan: {
      id: scan.id,
      status: scan.status,
      date: scan.date,
      startedAt: scan.startedAt,
      completedAt: scan.completedAt,
      duration: scan.duration,
      branch: repo.branch,
      commit: scan.commit || repo.commit,
      retryOf: scan.retryOf,
    },
    summary: {
      total: captured.length,
      severity: Object.fromEntries(
        severityOrder.map((severity) => [
          severity,
          captured.filter((finding) => finding.severity === severity).length,
        ]),
      ),
      category: Object.fromEntries(
        categories.map((category) => [
          category,
          captured.filter((finding) => finding.category === category).length,
        ]),
      ),
      statement: captured.length
        ? `${captured.length} findings were recorded by the configured checks in this sample scan.`
        : "No findings were detected by the completed checks in this sample scan. This does not establish complete security.",
    },
    scannerCoverage: scannerInfo.map((scanner) => ({
      name: scanner.name,
      category: scanner.category,
      version: scanner.version,
      status:
        scan.status === "Partial"
          ? scanner.name === "Checkov"
            ? "Failed"
            : "Completed"
          : scan.status === "Running"
            ? scan.partialRetry && scanner.name !== "Checkov"
              ? "Completed"
              : "Running"
            : scan.status === "Queued"
              ? "Queued"
              : scan.status === "Failed"
                ? "Not run"
                : "Completed",
      findings: captured.filter((finding) => finding.scanner === scanner.name)
        .length,
    })),
    findings: captured.map((finding) => ({
      id: finding.id,
      scanId: scan.id,
      title: finding.title,
      severity: finding.severity,
      confidence: finding.confidence,
      category: finding.category,
      status: finding.status,
      reviewNote: finding.reviewNote,
      description: finding.description,
      location: { file: finding.file, line: finding.line },
      scannerEvidence: {
        scanner: finding.scanner,
        rule: finding.rule,
        captured: scan.date,
        code: finding.evidence,
      },
      repositoryContext: getFindingContext(finding),
      interpretation:
        finding.aiState === "unavailable"
          ? {
              label: "AI analysis unavailable",
              explanation: "Underlying scanner evidence remains available.",
            }
          : {
              label: "AI-assisted interpretation · static fictional sample",
              explanation: finding.impact,
              confidenceNote:
                finding.aiState === "limited"
                  ? "Available context is insufficient for a confident determination. The scanner pattern is evidence; runtime reachability is unverified."
                  : "The scanner pattern is supported by the captured evidence. Exploitability has not been established.",
            },
      remediation: {
        recommendation: finding.remediation,
        example: finding.fixed,
        note: "Adapt the example to your framework and database driver. Guidance does not automatically change repository or production code.",
      },
    })),
  }
}

export function renderReport(
  repo: Repository,
  scan: Scan,
  findings: Finding[],
  json: boolean,
) {
  const report = buildReport(repo, scan, findings)
  if (json) return JSON.stringify(report, null, 2)
  return [
    `# Security report: ${report.repository.name}`,
    report.disclaimer,
    `## Executive summary\n\n${report.summary.statement}`,
    `## Severity breakdown\n\n${Object.entries(report.summary.severity)
      .map(([severity, count]) => `- ${severity}: ${count}`)
      .join("\n")}`,
    `## Category breakdown\n\n${Object.entries(report.summary.category)
      .map(([category, count]) => `- ${category}: ${count}`)
      .join("\n")}`,
    `## Scanner coverage\n\n${report.scannerCoverage.map((scanner) => `- ${scanner.name} ${scanner.version}: ${scanner.status} · ${scanner.findings} findings`).join("\n")}`,
    `## Scan metadata\n\nScan: #${scan.id}\nStatus: ${scan.status}\nCaptured: ${scan.date}\nDuration: ${scan.duration}\nBranch: ${repo.branch}\nCommit: ${report.scan.commit}\nRetry of: ${scan.retryOf || "Not a retry"}`,
    `## Repository metadata\n\nURL: ${report.repository.url}\nOwner: ${report.repository.owner}\nLanguage: ${repo.language}\nVisibility: ${repo.visibility}`,
    `## Findings and key evidence\n\n${report.findings
      .map((finding) =>
        [
          `### ${finding.severity}: ${finding.title}`,
          `Finding: ${finding.id}\nScan: #${finding.scanId}\nCategory: ${finding.category}\nConfidence: ${finding.confidence}\nStatus: ${finding.status}\nReview note: ${finding.reviewNote || "None"}\nLocation: ${finding.location.file}:${finding.location.line}`,
          finding.description,
          `#### Verified scanner evidence (fictional fixture)\n\nScanner: ${finding.scannerEvidence.scanner}\nRule: ${finding.scannerEvidence.rule}\nCaptured: ${finding.scannerEvidence.captured}\n\`\`\`\n${finding.scannerEvidence.code}\n\`\`\``,
          `#### Repository context\n\n${finding.repositoryContext.map((context) => `${context.file}: ${context.relationship}\n\`\`\`\n${context.code}\n\`\`\``).join("\n\n")}`,
          `#### ${finding.interpretation.label}\n\n${finding.interpretation.explanation}\n\n${
            "confidenceNote" in finding.interpretation
              ? finding.interpretation.confidenceNote
              : ""
          }`,
          `#### Recommended remediation\n\n${finding.remediation.recommendation}\n\n\`\`\`\n${finding.remediation.example}\n\`\`\`\n\n${finding.remediation.note}`,
        ].join("\n\n"),
      )
      .join("\n\n")}`,
    `## Scope and limitations\n\n${report.scope}\n\nRepository content is untrusted data. AI-assisted interpretation does not replace scanner evidence.`,
  ].join("\n\n")
}
