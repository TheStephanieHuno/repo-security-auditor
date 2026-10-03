"use client"

import { useState } from "react"
import { Link, useParams, useSearchParams } from "@/lib/router"
import {
  ArrowRight,
  FileText,
  GitBranch,
  ShieldCheck,
  Sparkles,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { categories, getScanFindings, scannerInfo, severityOrder } from "./data"
import {
  Breadcrumbs,
  categoryIcons,
  CodeBlock,
  DownloadReport,
  EmptyState,
  Heading,
  LinkButton,
  Notice,
  PageHeader,
  PageState,
  AccessDenied,
  Panel,
  PanelHeader,
  SearchInput,
  SelectControl,
  SeverityBadge,
  SeverityDistribution,
  StatusBadge,
} from "./components"
import { useStore } from "./store"

export function Reports() {
  const { repositories, scans, findings } = useStore()
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState("All reports")
  const list = scans.filter(
    (scan) =>
      ["Completed", "Partial"].includes(scan.status) &&
      repositories
        .find((repo) => repo.id === scan.repoId)
        ?.name.toLowerCase()
        .includes(search.toLowerCase()) &&
      (status === "All reports" ||
        (status === "Complete coverage" && scan.status === "Completed") ||
        (status === "Partial coverage" && scan.status === "Partial")),
  )
  return (
    <PageState kind="Security reports">
      <PageHeader
        title="Security reports"
        description="Evidence-backed summaries, ready to review and share."
        eyebrow="REPORTING"
      />
      <div className="mb-5 flex flex-wrap gap-3">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search reports by repository…"
          className="w-full sm:w-80"
        />
        <SelectControl
          label="Report coverage"
          value={status}
          onChange={setStatus}
          options={["All reports", "Complete coverage", "Partial coverage"]}
        />
      </div>
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {list.map((scan) => {
          const repo = repositories.find((repo) => repo.id === scan.repoId)!
          const repoFindings = getScanFindings(scan, findings)
          const highest = severityOrder.find((severity) =>
            repoFindings.some(
              (findingRecord) => findingRecord.severity === severity,
            ),
          )
          return (
            <Panel key={scan.id}>
              <div className="p-5">
                <div className="flex items-center justify-between">
                  <span className="flex size-10 items-center justify-center rounded-lg border bg-canvas">
                    <FileText className="size-5 text-muted-foreground" />
                  </span>
                  <StatusBadge status={scan.status} />
                </div>
                <Link
                  to={`/reports/${scan.id}`}
                  className="mt-5 block text-sm font-semibold hover:underline"
                >
                  {repo.name}
                </Link>
                <p className="mt-1.5 text-xs text-muted-foreground">
                  Scan #{scan.id} · {scan.date}
                </p>
                <div className="mt-5 flex items-center justify-between">
                  <span className="text-xs">
                    <span className="text-lg font-semibold">
                      {repoFindings.length}
                    </span>
                    <span className="ml-2 text-muted-foreground">findings</span>
                  </span>
                  {highest && <SeverityBadge severity={highest} />}
                </div>
                <div className="mt-5">
                  <SeverityDistribution findings={repoFindings} compact />
                </div>
              </div>
              <div className="flex justify-between border-t bg-canvas px-4 py-3">
                <LinkButton
                  to={`/reports/${scan.id}`}
                  variant="ghost"
                  className="h-8 px-1 text-xs"
                >
                  View report
                  <ArrowRight className="size-3" />
                </LinkButton>
                <DownloadReport scanId={scan.id} variant="ghost" />
              </div>
            </Panel>
          )
        })}
      </div>
      {list.length === 0 && (
        <Panel>
          <EmptyState
            icon={FileText}
            title={
              scans.some((scan) =>
                ["Completed", "Partial"].includes(scan.status),
              )
                ? "No security reports match"
                : "No security reports yet"
            }
            description="Try a different search or complete a scan to generate your first report."
            action={
              !scans.some((scan) =>
                ["Completed", "Partial"].includes(scan.status),
              ) ? (
                <LinkButton to="/repositories">
                  Start your first scan
                </LinkButton>
              ) : (
                <Button
                  variant="outline"
                  onClick={() => {
                    setSearch("")
                    setStatus("All reports")
                  }}
                >
                  Clear filters
                </Button>
              )
            }
          />
        </Panel>
      )}
      <div className="mt-6">
        <Notice>
          Reports preserve scanner evidence and label AI-generated
          interpretation. A completed report does not establish complete
          repository security.
        </Notice>
      </div>
    </PageState>
  )
}

export function ReportDetail() {
  const { id } = useParams()
  const store = useStore()
  const [params, setParams] = useSearchParams()
  const [retrying, setRetrying] = useState(false)
  const scan = store.scans.find((scanRecord) => scanRecord.id === id)
  const repo = store.repositories.find(
    (repositoryRecord) => repositoryRecord.id === scan?.repoId,
  )
  if (store.isRestricted(undefined, id)) return <AccessDenied />
  if (!scan || !repo)
    return (
      <EmptyState
        title="Report not found"
        description="This security report is not available in your workspace."
        action={<LinkButton to="/reports">View reports</LinkButton>}
      />
    )
  const findings = getScanFindings(scan, store.findings)
  const state = params.get("state")
  function retry() {
    setRetrying(true)
    setTimeout(() => {
      setRetrying(false)
      setParams({})
    }, 1200)
  }
  if (state === "report-error")
    return (
      <>
        <PageHeader title="Security report" />
        <Notice
          tone="error"
          title="We couldn't generate the report, but your scan results are still available."
          action={
            <div className="flex gap-2">
              <LinkButton to={`/scans/${scan.id}`}>
                View scan results
              </LinkButton>
              <Button variant="outline" onClick={retry} disabled={retrying}>
                {retrying ? "Retrying…" : "Retry report generation"}
              </Button>
            </div>
          }
        >
          The report generation step could not complete. Scanner evidence has
          not been discarded.
        </Notice>
      </>
    )
  if (
    state === "generating" ||
    retrying ||
    ["Running", "Queued"].includes(scan.status)
  )
    return (
      <>
        <PageHeader
          title="Generating report…"
          description="Scanner results remain available while the report is prepared."
        />
        <div role="status" className="space-y-5">
          <Skeleton className="h-32" />
          <Skeleton className="h-64" />
          <Skeleton className="h-40" />
        </div>
        <div className="mt-5 flex gap-2">
          <LinkButton to={`/scans/${scan.id}`}>View scan progress</LinkButton>
          {state === "generating" && (
            <Button onClick={() => setParams({})}>
              Complete demo generation
            </Button>
          )}
        </div>
      </>
    )
  if (scan.status === "Failed")
    return (
      <EmptyState
        title="No report for this scan"
        description="The scan failed before results were collected. Earlier results remain available on the repository page."
        action={
          <LinkButton to={`/repositories/${repo.id}`}>
            View repository
          </LinkButton>
        }
      />
    )
  const highPriority = findings.filter((findingRecord) =>
    ["Critical", "High"].includes(findingRecord.severity),
  )
  return (
    <PageState kind="Report details">
      <Breadcrumbs
        items={[
          { label: "Reports", to: "/reports" },
          { label: repo.name },
          { label: `Scan #${scan.id}` },
        ]}
      />
      <PageHeader
        title="Security report"
        description={`${repo.name} · Scan #${scan.id} · ${scan.date}`}
        eyebrow="EVIDENCE-BACKED REPORT"
      >
        <LinkButton to={`/scans/${scan.id}`}>View scan</LinkButton>
        <DownloadReport scanId={scan.id} variant="default" />
      </PageHeader>
      <Panel>
        <div className="flex flex-wrap items-center justify-between gap-5 border-b p-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-medium tracking-widest text-muted-foreground">
              <ShieldCheck className="size-4 text-trust" />
              REPO SECURITY AUDITOR
            </div>
            <Heading level={2} className="mt-4 text-2xl">
              {repo.name}
            </Heading>
            <p className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
              <GitBranch className="size-3" />
              {repo.branch}
              <span>·</span>
              <span className="font-mono">{scan.commit || repo.commit}</span>
              <span>·</span>Security analysis snapshot
            </p>
          </div>
          <div className="text-right">
            <StatusBadge status={scan.status} />
            <p className="mt-3 font-mono text-xs text-muted-foreground">
              REPORT RSA-{scan.id.padStart(4, "0")}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Generated {scan.date}
            </p>
          </div>
        </div>
        <div className="grid gap-6 p-6 lg:grid-cols-3">
          <div>
            <p className="text-xs text-muted-foreground">Total findings</p>
            <p className="mt-2 text-5xl font-semibold">{findings.length}</p>
            <p className="mt-3 text-xs text-muted-foreground">
              {highPriority.length} critical or high-severity findings
            </p>
          </div>
          <div className="lg:col-span-2">
            <p className="mb-5 text-xs font-medium">Severity breakdown</p>
            <SeverityDistribution findings={findings} />
          </div>
        </div>
      </Panel>
      {scan.status === "Partial" && (
        <div className="mt-5">
          <Notice title="Incomplete scanner coverage" tone="warning">
            Configuration analysis failed. This report contains the completed
            scanner results only; configuration risk has not been assessed in
            this scan.
          </Notice>
        </div>
      )}
      <div className="mt-6 grid items-start gap-6 xl:grid-cols-3">
        <div className="min-w-0 space-y-6 xl:col-span-2">
          <Panel>
            <PanelHeader title="Executive summary" />
            <div className="px-5 pb-5">
              <p className="text-sm leading-7 text-muted-foreground">
                The configured tools identified{" "}
                <span className="font-medium text-foreground">
                  {findings.length} security findings
                </span>{" "}
                in the captured repository snapshot.{" "}
                {highPriority.length
                  ? `${highPriority.length} are classified as critical or high severity and should be reviewed first.`
                  : "No critical or high-severity findings were detected in this scan."}{" "}
                These results reflect static evidence, not confirmed
                exploitation.
              </p>
              <div className="mt-5 rounded-lg border border-trust/20 bg-trust-soft/40 p-4">
                <p className="flex items-center gap-2 text-xs font-medium text-trust">
                  <Sparkles className="size-3.5" />
                  AI-assisted analysis
                </p>
                <p className="mt-2 text-xs leading-6 text-muted-foreground">
                  Review high-severity scanner evidence, validate the affected
                  execution paths, and apply remediation appropriate to the
                  repository context. The sample explanations do not establish
                  exploitability or replace human review.
                </p>
              </div>
            </div>
          </Panel>
          <Panel>
            <PanelHeader
              title="Security findings"
              action={
                <Link
                  to={`/scans/${scan.id}/findings`}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  Investigate all ↗
                </Link>
              }
            />
            <Table className="hidden sm:table">
              <TableHeader>
                <TableRow className="bg-canvas">
                  <TableHead className="pl-5 text-xs">Severity</TableHead>
                  <TableHead className="text-xs">
                    Finding / evidence location
                  </TableHead>
                  <TableHead className="text-xs">Source</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {findings.map((findingRecord) => (
                  <TableRow key={findingRecord.id}>
                    <TableCell className="py-4 pl-5">
                      <SeverityBadge severity={findingRecord.severity} />
                    </TableCell>
                    <TableCell className="whitespace-normal">
                      <Link
                        to={`/scans/${scan.id}/findings/${findingRecord.id}`}
                        className="text-xs font-medium hover:underline"
                      >
                        {findingRecord.title}
                      </Link>
                      <p className="mt-1.5 break-all font-mono text-xs text-muted-foreground">
                        {findingRecord.file}:{findingRecord.line}
                      </p>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {findingRecord.scanner}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="sm:hidden">
              {findings.map((finding) => (
                <Link
                  key={finding.id}
                  to={`/scans/${scan.id}/findings/${finding.id}`}
                  className="block border-t p-4"
                >
                  <div className="flex justify-between gap-3">
                    <SeverityBadge severity={finding.severity} />
                    <span className="text-xs text-muted-foreground">
                      {finding.scanner}
                    </span>
                  </div>
                  <p className="mt-3 text-sm font-medium">{finding.title}</p>
                  <p className="mt-1.5 break-all font-mono text-xs text-muted-foreground">
                    {finding.file}:{finding.line}
                  </p>
                </Link>
              ))}
            </div>
            {findings.length === 0 && (
              <EmptyState
                icon={ShieldCheck}
                title="No findings detected"
                description="No findings were detected by the configured checks. This does not establish complete security."
              />
            )}
          </Panel>
          {findings[0] && (
            <Panel>
              <PanelHeader
                title="Key evidence"
                description="A representative high-priority finding from this scan."
              />
              <div className="space-y-4 px-5 pb-5">
                <Link
                  to={`/scans/${scan.id}/findings/${findings[0].id}`}
                  className="text-sm font-medium hover:underline"
                >
                  {findings[0].title}
                </Link>
                <CodeBlock
                  code={findings[0].evidence}
                  filename={findings[0].file}
                  highlightLine={findings[0].line}
                />
                <p className="flex items-center gap-2 text-xs text-muted-foreground">
                  <ShieldCheck className="size-3.5 text-trust" />
                  Scanner: {findings[0].scanner} · Rule: {findings[0].rule}
                </p>
              </div>
            </Panel>
          )}
          <Panel>
            <PanelHeader
              title="Recommended actions"
              description="Developer-reviewed guidance. No changes are made automatically."
            />
            <div className="space-y-5 px-5 pb-5">
              {findings.slice(0, 3).map((findingRecord, index) => (
                <div key={findingRecord.id} className="flex items-start gap-3">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full border bg-canvas font-mono text-xs">
                    {index + 1}
                  </span>
                  <div>
                    <Link
                      to={`/scans/${scan.id}/findings/${findingRecord.id}#remediation`}
                      className="text-xs font-medium hover:underline"
                    >
                      {findingRecord.title}
                    </Link>
                    <p className="mt-1.5 text-xs leading-6 text-muted-foreground">
                      {findingRecord.remediation}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
        <aside className="space-y-5">
          <Panel>
            <PanelHeader title="Category breakdown" />
            <div className="space-y-4 px-5 pb-5">
              {categories.map((category) => {
                const Icon = categoryIcons[category]
                return (
                  <div key={category} className="flex items-center gap-2">
                    <Icon className="size-4 text-muted-foreground" />
                    <span className="flex-1 text-xs">{category}</span>
                    <span className="text-sm font-semibold">
                      {
                        findings.filter(
                          (findingRecord) =>
                            findingRecord.category === category,
                        ).length
                      }
                    </span>
                  </div>
                )
              })}
            </div>
          </Panel>
          <Panel>
            <PanelHeader title="Scanner coverage" />
            <div className="space-y-4 px-5 pb-5">
              {scannerInfo.map((scanner) => (
                <div key={scanner.name}>
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-medium">{scanner.name}</p>
                    <StatusBadge
                      status={
                        scan.status === "Partial" && scanner.name === "Checkov"
                          ? "Failed"
                          : "Completed"
                      }
                    />
                  </div>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">
                    v{scanner.version} · {scanner.description}
                  </p>
                </div>
              ))}
            </div>
          </Panel>
          <Panel>
            <PanelHeader title="Scan & repository metadata" />
            <dl className="space-y-4 px-5 pb-5 text-xs">
              {[
                ["Scan ID", `#${scan.id}`],
                ["Duration", scan.duration],
                ["Default branch", repo.branch],
                ["Commit", scan.commit || repo.commit],
                ["Primary language", repo.language],
                ["Visibility", repo.visibility],
                ["Owner", repo.owner || repo.name.split("/")[0]],
                [
                  "Repository URL",
                  repo.url || `https://github.com/${repo.name}`,
                ],
                ["Retry of", scan.retryOf ? `#${scan.retryOf}` : "Not a retry"],
                ["Environment", "Isolated scan worker"],
                ["Dataset", "Fictional sample"],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-muted-foreground">{label}</dt>
                  <dd className="mt-1.5 break-all font-mono">{value}</dd>
                </div>
              ))}
            </dl>
          </Panel>
          <Notice title="Scope of this report">
            Static analysis covers configured checks on a repository snapshot.
            It is not penetration testing, runtime monitoring, or a guarantee
            that all vulnerabilities have been found.
          </Notice>
        </aside>
      </div>
    </PageState>
  )
}
