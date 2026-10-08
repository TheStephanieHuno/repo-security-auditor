"use client"

import { toast } from "sonner"
import { useState } from "react"
import { Link, useNavigate, useParams, useSearchParams } from "@/lib/router"
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  Circle,
  Loader2,
  Play,
  RotateCcw,
  ShieldCheck,
  XIcon,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"
import {
  categories,
  getScanFindings,
  scanBoundaries,
  scanActivity,
  scannerInfo,
  scanStages,
  type ScanStatus,
} from "@/lib/security-model"
import { isLive, toTitleCase } from "@/lib/api/index"
import {
  Breadcrumbs,
  CancelScanDialog,
  categoryIcons,
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
  ScanDialog,
  SearchInput,
  SelectControl,
  SeverityBadge,
  SeverityDistribution,
  StatusBadge,
} from "./components"
import { useRepositories, useScans, useFindings, useScanStatus } from "@/lib/api/hooks"
import { FindingsList } from "./findings"

export function ScanHistory() {
  const { data: reposData, isLoading: rLoading } = useRepositories(1, 100)
  const { data: scansData, isLoading: sLoading } = useScans(1, 100)
  const { data: findingsData, isLoading: fLoading } = useFindings({ page_size: 1000 })
  const repositories = reposData?.items || []
  const scans = scansData?.items || []
  const allFindings = findingsData?.items || []
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState("All statuses")
  const [date, setDate] = useState("All dates")
  const [repoFilter, setRepoFilter] = useState("All repositories")
  const [scanOpen, setScanOpen] = useState(false)
  if (rLoading || sLoading || fLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="animate-spin text-muted-foreground">
          <svg className="size-6" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
      </div>
    )
  }

  const list = scans.filter((scan) => {
    const repo = repositories.find(
      (repositoryRecord) => repositoryRecord.id === scan.repoId,
    )
    return (
      repo?.name.toLowerCase().includes(search.toLowerCase()) &&
      (repoFilter === "All repositories" || repo.name === repoFilter) &&
      (status === "All statuses" || scan.status === status) &&
      (date === "All dates" ||
        (date === "Today" && scan.date.startsWith("Oct 1")) ||
        date === "Last 7 days")
    )
  })
  return (
    <PageState kind="Scans">
      <PageHeader
        title="Scan history"
        description="A traceable record of every analysis, including incomplete checks."
        eyebrow="SECURITY ACTIVITY"
      >
        <Button className="h-9" onClick={() => setScanOpen(true)}>
          <Play className="size-3.5" />
          Start new scan
        </Button>
      </PageHeader>
      <div className="mb-5 flex flex-wrap gap-3">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search scans…"
          className="w-full sm:w-64"
        />
        <SelectControl
          label="Filter repository"
          value={repoFilter}
          onChange={setRepoFilter}
          options={[
            "All repositories",
            ...repositories.map(
              (repositoryRecord) => repositoryRecord.name,
            ),
          ]}
        />
        <SelectControl
          label="Filter scan status"
          value={status}
          onChange={setStatus}
          options={[
            "All statuses",
            "Completed",
            "Partial",
            "Failed",
            "Running",
            "Queued",
          ]}
        />
        <SelectControl
          label="Filter scan date"
          value={date}
          onChange={setDate}
          options={["All dates", "Today", "Last 7 days"]}
        />
      </div>
      <Panel className="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow className="bg-canvas">
              <TableHead className="pl-5 text-xs">Repository / scan</TableHead>
              <TableHead className="text-xs">Date</TableHead>
              <TableHead className="text-xs">Status</TableHead>
              <TableHead className="text-xs">Findings</TableHead>
              <TableHead className="text-xs">Duration</TableHead>
              <TableHead className="pr-5 text-right text-xs">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.map((scan) => {
              const repo = repositories.find(
                (repositoryRecord) => repositoryRecord.id === scan.repoId,
              )!
              const findings = ["Completed", "Partial"].includes(scan.status)
                ? getScanFindings(scan, allFindings)
                : []
              return (
                <TableRow key={scan.id}>
                  <TableCell className="py-4 pl-5">
                    <Link
                      to={`/scans/${scan.id}`}
                      className="text-xs font-medium hover:underline"
                    >
                      {repo.name}
                    </Link>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      #{scan.id} · {scan.branch || repo.branch}
                    </p>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {scan.date}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={scan.status} />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-medium">
                        {["Completed", "Partial"].includes(scan.status)
                          ? findings.length
                          : "—"}
                      </span>
                      {findings.some(
                        (findingRecord) =>
                          findingRecord.severity === "Critical",
                      ) && <SeverityBadge severity="Critical" />}
                      {findings.some(
                        (findingRecord) => findingRecord.severity === "High",
                      ) && (
                        <span className="text-high">
                          {
                            findings.filter(
                              (findingRecord) =>
                                findingRecord.severity === "High",
                            ).length
                          }{" "}
                          high
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {scan.duration}
                  </TableCell>
                  <TableCell className="pr-5">
                    <div className="flex justify-end gap-1">
                      <LinkButton
                        to={`/scans/${scan.id}`}
                        variant="ghost"
                        className="h-7 text-xs"
                      >
                        View
                        <ChevronRight className="size-3" />
                      </LinkButton>
                      {["Completed", "Partial"].includes(scan.status) && (
                        <LinkButton
                          to={`/reports/${scan.id}`}
                          variant="ghost"
                          className="h-7 text-xs"
                        >
                          Report
                        </LinkButton>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
        {list.length === 0 && (
          <EmptyState
            title={
              scans.length
                ? "No scans match your filters"
                : "No scans yet"
            }
            description="Clear the filters or start a new security scan."
            action={
              <Button
                variant="outline"
                onClick={() => {
                  setSearch("")
                  setStatus("All statuses")
                  setRepoFilter("All repositories")
                  setDate("All dates")
                }}
              >
                Clear filters
              </Button>
            }
          />
        )}
      </Panel>
      <div className="space-y-3 md:hidden">
        {list.length === 0 && (
          <Panel>
            <EmptyState
              title={
                scans.length
                  ? "No scans match your filters"
                  : "No scans yet"
              }
              description="Try a broader search or clear the filters."
              action={
                <Button
                  variant="outline"
                  onClick={() => {
                    setSearch("")
                    setStatus("All statuses")
                    setRepoFilter("All repositories")
                    setDate("All dates")
                  }}
                >
                  Clear filters
                </Button>
              }
            />
          </Panel>
        )}
        {list.map((scan) => (
          <Panel key={scan.id}>
            <div className="space-y-3 p-4">
              <Link to={`/scans/${scan.id}`} className="text-sm font-medium">
                {
                  repositories.find(
                    (repositoryRecord) => repositoryRecord.id === scan.repoId,
                  )?.name
                }
              </Link>
              <div className="flex justify-between">
                <span className="font-mono text-xs text-muted-foreground">
                  Scan #{scan.id}
                </span>
                <StatusBadge status={scan.status} />
              </div>
              <p className="text-xs text-muted-foreground">{scan.date}</p>
              <LinkButton to={`/scans/${scan.id}`} className="w-full">
                View scan
                <ArrowRight className="size-3" />
              </LinkButton>
            </div>
          </Panel>
        ))}
      </div>
      <p className="mt-4 text-xs text-muted-foreground">
        Showing {list.length} scans · All times in UTC
      </p>
      <ScanDialog open={scanOpen} onOpenChange={setScanOpen} />
    </PageState>
  )
}

export function ScanPage({ findingsTab = false }: { findingsTab?: boolean }) {
  const { id } = useParams()
  const { data: reposData, isLoading: rLoading } = useRepositories(1, 100)
  const { data: scansData, isLoading: sLoading } = useScans(1, 100)
  const { data: findingsData, isLoading: fLoading } = useFindings({ page_size: 1000 })
  const repositories = reposData?.items || []
  const scans = scansData?.items || []
  const allFindings = findingsData?.items || []
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [scanOpen, setScanOpen] = useState(false)
  const [cancelOpen, setCancelOpen] = useState(false)
  function retry() { setScanOpen(true) }

  const original = scans.find((scan) => scan.id === id)
  const override = params.get("state")
  const scan =
    original &&
    (["queued", "running", "failed", "partial"].includes(override || "")
      ? {
          ...original,
          status: toTitleCase(override!) as ScanStatus,
          stage: override === "running" ? 4 : original.stage,
          progress: override === "running" ? 43 : original.progress,
        }
      : original)

  // Poll status only while the scan is in a non-terminal state.
  const isActive = scan?.status === "Queued" || scan?.status === "Running"
  const { data: liveStatus } = useScanStatus(isActive ? (scan?.id ?? "") : "")

  if (rLoading || sLoading || fLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="animate-spin text-muted-foreground">
          <svg className="size-6" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
      </div>
    )
  }

  // Merge the most-recent polled status/progress into the scan object.
  // toTitleCase converts the lowercase backend value to the UI type using the single mapping.
  const displayScan =
    scan && liveStatus
      ? {
          ...scan,
          status: (toTitleCase(liveStatus.status) || scan.status) as ScanStatus,
          progress: liveStatus.progress,
          stage: liveStatus.stage,
        }
      : scan

  const repo = repositories.find((item) => item.id === displayScan?.repoId)
  if (!displayScan || !repo)
    return (
      <EmptyState
        title="Scan not found"
        description="This scan is not available in your workspace."
        action={<LinkButton to="/scans">View scan history</LinkButton>}
      />
    )
  const findings = getScanFindings(displayScan, allFindings)
  const previous = scans.find(
    (item) =>
      item.repoId === repo.id &&
      Number(item.id) < Number(displayScan.id) &&
      ["Completed", "Partial"].includes(item.status),
  )
  const priorFindings = getScanFindings(previous, allFindings)
  const tab = findingsTab ? "findings" : params.get("tab") || "overview"
  const progressView =
    ["Queued", "Running", "Failed"].includes(displayScan.status) &&
    !(findingsTab && displayScan.partialRetry)
  const changeTab = (value: unknown) => {
    const next = String(value)
    if (next === "findings")
      navigate(
        `/scans/${displayScan.id}/findings${
          displayScan.status === "Partial" ? "?state=partial" : ""
        }`,
      )
    else
      navigate(
        `/scans/${displayScan.id}?tab=${next}${
          override === "partial" ? "&state=partial" : ""
        }`,
      )
  }
  return (
    <PageState kind="Scan results">
      {displayScan.retryOf && (
        <Notice title="Rescan with preserved evidence">
          This is a new scan attempt.{" "}
          <Link to={`/scans/${displayScan.retryOf}`} className="underline">
            Original scan #{displayScan.retryOf}
          </Link>{" "}
          remains in history.
        </Notice>
      )}
      <details className="mb-5 rounded-lg border bg-background p-4 text-xs">
        <summary className="cursor-pointer font-medium">
          Scan execution boundaries · frontend preview
        </summary>
        <p className="mt-3 text-muted-foreground">
          Example worker policy, not enforced by this frontend. Independent
          scanner checks would run in parallel; normalization and interpretation
          follow evidence collection.
        </p>
        <dl className="mt-3 grid gap-3 sm:grid-cols-2">
          {scanBoundaries.map((boundary) => (
            <div key={boundary.label}>
              <dt className="text-muted-foreground">{boundary.label}</dt>
              <dd className="mt-1">{boundary.value}</dd>
            </div>
          ))}
        </dl>
      </details>
      <Breadcrumbs
        items={[
          { label: "Repositories", to: "/repositories" },
          { label: repo.name, to: `/repositories/${repo.id}` },
          { label: `Scan #${displayScan.id}` },
        ]}
      />
      <PageHeader
        title={
          progressView
            ? displayScan.status === "Failed"
              ? "Scan failed"
              : `Scanning ${repo.name}`
            : "Security results"
        }
        description={
          progressView
            ? displayScan.status === "Queued"
              ? "Your scan is queued and waiting for an isolated worker."
              : displayScan.status === "Failed"
                ? "Repository ingestion could not be completed."
                : "Independent checks are gathering evidence from your repository."
            : `${repo.name} · Scan #${displayScan.id} · ${displayScan.date}`
        }
        eyebrow={
          progressView
            ? "SECURITY ANALYSIS"
            : displayScan.status === "Completed"
              ? "SCAN COMPLETE"
              : "AVAILABLE RESULTS"
        }
      >
        {!progressView && (
          <>
            <DownloadReport scanId={displayScan.id} />
            <Button className="h-9" onClick={() => setScanOpen(true)}>
              <RotateCcw className="size-3.5" />
              Rescan
            </Button>
          </>
        )}
      </PageHeader>
      {displayScan.partialRetry && displayScan.status === "Running" && (
        <div className="mb-5">
          <Notice
            title="Retrying configuration analysis"
            tone="warning"
            action={
              <LinkButton to={`/scans/${displayScan.id}/findings`}>
                View preserved findings
                <ArrowRight className="size-3" />
              </LinkButton>
            }
          >
            The completed code, secrets, and dependency results remain available
            while the failed check is retried.
          </Notice>
        </div>
      )}
      {progressView ? (
        <>
          <Panel>
            <div className="border-b px-6 py-5">
              <div className="flex items-center justify-between">
                <StatusBadge status={displayScan.status} />
                <span className="font-mono text-sm font-medium">
                  {displayScan.status === "Queued"
                    ? "Awaiting worker"
                    : `${displayScan.progress}%`}
                </span>
              </div>
              <Progress
                value={displayScan.status === "Queued" ? 0 : displayScan.progress}
                aria-label="Overall scan progress"
                className="mt-5 [&_[data-slot=progress-track]]:h-2 [&_[data-slot=progress-indicator]]:bg-trust"
              />
              <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted-foreground">
                <span>
                  Branch:{" "}
                  <span className="font-mono text-foreground">
                    {displayScan.branch || repo.branch}
                  </span>
                </span>
                <span>
                  Commit:{" "}
                  <span className="font-mono text-foreground">
                    {displayScan.commit || repo.commit}
                  </span>
                </span>
                <span>
                  Estimated remaining:{" "}
                  <span className="text-foreground">
                    {displayScan.isNew ? "less than a minute" : "a few minutes"}
                  </span>
                </span>
              </div>
            </div>
            <div className="grid lg:grid-cols-5">
              <div className="p-6 lg:col-span-3">
                <Heading level={2} className="mb-5 text-sm">
                  Analysis pipeline
                </Heading>
                <div className="space-y-4">
                  {scanStages.map((stage, index) => {
                    const isScanner = index >= 2 && index <= 5
                    const completed =
                      displayScan.status !== "Queued" && index < displayScan.stage
                    const running =
                      displayScan.status === "Running" &&
                      (index === displayScan.stage ||
                        (isScanner &&
                          displayScan.stage >= 2 &&
                          displayScan.stage <= 5 &&
                          index >= displayScan.stage))
                    const failed = displayScan.status === "Failed" && index === 1
                    return (
                      <div
                        key={stage}
                        className="flex items-center gap-3 text-xs"
                      >
                        {completed ? (
                          <CheckCircle2 className="size-4 text-trust" />
                        ) : failed ? (
                          <XIcon className="size-4 text-critical" />
                        ) : running ? (
                          <Loader2 className="size-4 animate-spin text-trust motion-reduce:animate-none" />
                        ) : (
                          <Circle className="size-4 text-muted-foreground/40" />
                        )}
                        <span
                          className={cn(
                            completed
                              ? "text-foreground"
                              : running
                                ? "font-medium"
                                : "text-muted-foreground",
                          )}
                        >
                          {stage}
                        </span>
                        {index === 8 && (
                          <Badge
                            variant="outline"
                            className="rounded-md text-xs"
                          >
                            Interpretation, not detection
                          </Badge>
                        )}
                        <span
                          className={cn(
                            "ml-auto",
                            completed
                              ? "text-trust"
                              : failed
                                ? "text-critical"
                                : "text-muted-foreground",
                          )}
                        >
                          {completed
                            ? "Complete"
                            : failed
                              ? "Failed"
                              : running
                                ? "Running"
                                : "Pending"}
                        </span>
                      </div>
                    )
                  })}
                </div>
                <p className="mt-6 text-xs leading-relaxed text-muted-foreground">
                  The four scanners run independently in parallel.
                  Normalization, correlation, and AI interpretation follow the
                  available results.
                </p>
              </div>
              <div className="border-t bg-canvas p-6 lg:col-span-2 lg:border-t-0 lg:border-l">
                <Heading
                  level={2}
                  className="mb-5 flex items-center gap-2 text-sm"
                >
                  <Activity className="size-4" />
                  Activity log
                </Heading>
                <div
                  aria-live="polite"
                  className="space-y-5 font-mono text-xs leading-relaxed"
                >
                  {displayScan.status === "Queued" ? (
                    <p className="text-muted-foreground">
                      Job queued. Waiting for an available scan worker.
                    </p>
                  ) : (
                    scanActivity
                      .slice(0, Math.min(displayScan.stage + 1, 10))
                      .map((activity, index) => (
                        <div key={activity} className="flex gap-3">
                          <span className="shrink-0 text-muted-foreground">
                            +{String(index * 2).padStart(2, "0")}s
                          </span>
                          <span
                            className={
                              index === displayScan.stage
                                ? "text-trust"
                                : "text-muted-foreground"
                            }
                          >
                            {activity}
                          </span>
                        </div>
                      ))
                  )}
                </div>
                <div className="mt-8">
                  {!isLive && (
                    <Notice>
                      Frontend demo: the pipeline is simulated. No repository
                      content is executed or analyzed.
                    </Notice>
                  )}
                </div>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-4 border-t px-6 py-4">
              <span className="flex items-center gap-2 text-xs text-muted-foreground">
                <ShieldCheck className="size-4 text-trust" />
                Isolated scan environment
              </span>
              {displayScan.status === "Queued" && !displayScan.isNew ? (
                <Button onClick={retry}>
                  <Play className="size-3" />
                  Start security scan
                </Button>
              ) : (
                displayScan.status !== "Failed" && (
                  <div className="flex items-center gap-2">
                    <Button variant="outline" onClick={() => setCancelOpen(true)}>
                      Cancel scan
                    </Button>
                  </div>
                )
              )}
            </div>
          </Panel>
          {displayScan.status === "Failed" && (
            <div className="mt-5">
              <Notice
                tone="error"
                title="Repository ingestion failed"
                action={
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" onClick={retry}>
                      <RotateCcw className="size-3" />
                      Rescan
                    </Button>
                    <LinkButton to={`/repositories/${repo.id}?tab=findings`}>
                      View previous findings
                    </LinkButton>
                  </div>
                }
              >
                The GitHub connection timed out before files could be retrieved.
                No checks ran in this scan. Findings from previous completed
                scans are still available.
              </Notice>
            </div>
          )}
        </>
      ) : (
        <>
          {displayScan.status === "Partial" && (
            <div className="mb-5">
              <Notice
                tone="warning"
                title="3 of 4 security checks completed"
                action={
                  <div className="flex flex-wrap gap-2">
                    <LinkButton to={`/scans/${displayScan.id}/findings`}>
                      View available findings
                    </LinkButton>
                    <Button variant="outline" onClick={retry}>
                      <RotateCcw className="size-3" />
                      Rescan
                    </Button>
                  </div>
                }
              >
                Secret, code, and dependency checks completed. Configuration
                analysis exceeded its time limit; completed results have been
                preserved. Coverage is incomplete.
              </Notice>
            </div>
          )}
          <Tabs value={tab} onValueChange={changeTab}>
            <TabsList
              variant="line"
              className="mb-5 h-10 w-full justify-start gap-6 border-b px-0"
            >
              {["overview", "findings", "scanners", "history"].map((item) => (
                <TabsTrigger
                  key={item}
                  value={item}
                  className="h-9 flex-none px-0 text-xs capitalize"
                >
                  {item}
                  {item === "findings" && (
                    <Badge variant="secondary" className="rounded-md">
                      {findings.length}
                    </Badge>
                  )}
                </TabsTrigger>
              ))}
            </TabsList>
            <TabsContent value="overview">
              <div className="grid gap-5 xl:grid-cols-3">
                <Panel className="xl:col-span-2">
                  <PanelHeader
                    title="Finding severity"
                    action={
                      <span className="text-xs text-muted-foreground">
                        {findings.length} total findings
                      </span>
                    }
                  />
                  <div className="px-5 pb-6">
                    <div className="mb-6 flex items-end gap-3">
                      <p className="text-5xl font-semibold tabular-nums">
                        {findings.length}
                      </p>
                      <p className="pb-1 text-sm text-muted-foreground">
                        findings detected
                      </p>
                    </div>
                    <SeverityDistribution findings={findings} />
                  </div>
          </Panel>
                <Panel>
                  <PanelHeader title="Scan context" />
                  <dl className="space-y-4 px-5 pb-5 text-xs">
                    {[
                      [
                        "Status",
                        <StatusBadge key="status" status={displayScan.status} />,
                      ],
                        ["Branch", displayScan.branch || repo.branch],
                      ["Commit", displayScan.commit || repo.commit],
                      ["Duration", displayScan.duration],
                      [
                        "Files analyzed",
                        repo.id === "web-app" ? "284 (sample)" : "126 (sample)",
                      ],
                      ["Environment", "Isolated worker"],
                    ].map(([label, value]) => (
                      <div
                        key={String(label)}
                        className="flex justify-between gap-3"
                      >
                        <dt className="text-muted-foreground">{label}</dt>
                        <dd className="font-mono">{value}</dd>
                      </div>
                    ))}
                  </dl>
                </Panel>
              </div>
              <Panel className="mt-5">
                <PanelHeader
                  title="Findings by category"
                  description="Evidence normalized across the configured analysis tools."
                />
                <div className="grid grid-cols-2 border-t xl:grid-cols-4">
                  {categories.map((category) => {
                    const Icon = categoryIcons[category]
                    const list = findings.filter(
                      (findingRecord) => findingRecord.category === category,
                    )
                    return (
                      <Link
                        key={category}
                        to={`/scans/${displayScan.id}/findings?category=${category}`}
                        className="border-r p-5 last:border-r-0 hover:bg-muted/40"
                      >
                        <Icon className="mb-4 size-5 text-muted-foreground" />
                        <p className="text-xs font-medium">{category}</p>
                        <p className="mt-2 text-2xl font-semibold">
                          {list.length}
                          <span className="ml-2 text-xs font-normal text-muted-foreground">
                            findings
                          </span>
                        </p>
                        <p className="mt-3 text-xs text-muted-foreground">
                          {
                            scannerInfo.find(
                              (scanRecord) => scanRecord.category === category,
                            )?.name
                          }
                          <ChevronRight className="ml-1 inline size-3" />
                        </p>
                      </Link>
                    )
                  })}
                </div>
              </Panel>
              <div className="mt-5">
                <Notice title="What the evidence shows">
                  {findings.length
                    ? "The current findings include security-relevant code patterns, dependency advisories, and configuration or credential checks. Review reachability and deployment context before assessing exploitability."
                    : "No findings were detected by the configured checks. This scan does not establish complete security."}
                </Notice>
              </div>
              <>
                {previous && (
                  <Panel className="mt-5">
                    <PanelHeader
                      title={`What changed since scan #${previous.id}?`}
                      description="Compared by normalized finding ID within the sample repository snapshots."
                    />
                    <div className="grid grid-cols-3 gap-4 px-5 pb-5">
                      <div>
                        <p className="text-xl font-semibold text-high">
                          +
                          {
                            findings.filter(
                              (finding) =>
                                !priorFindings.some(
                                  (prior) => prior.id === finding.id,
                                ),
                            ).length
                          }
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          New findings
                        </p>
                      </div>
                      <div>
                        <p className="text-xl font-semibold text-trust">
                          {
                            priorFindings.filter(
                              (prior) =>
                                !findings.some(
                                  (finding) => finding.id === prior.id,
                                ),
                            ).length
                          }
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          No longer detected
                        </p>
                      </div>
                      <div>
                        <p className="text-xl font-semibold">
                          {
                            findings.filter((finding) =>
                              priorFindings.some(
                                (prior) => prior.id === finding.id,
                              ),
                            ).length
                          }
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Unchanged
                        </p>
                      </div>
                    </div>
                  </Panel>
                )}
              </>
              <Panel className="mt-5">
                <PanelHeader title="Recommended next steps" />
                <div className="grid gap-5 px-5 pb-5 md:grid-cols-3">
                  {[
                    {
                      step: "01",
                      title: "Review highest-severity evidence",
                      copy: "Verify the location, rule, and captured scanner output.",
                      to: `/scans/${displayScan.id}/findings`,
                    },
                    {
                      step: "02",
                      title: "Understand the context",
                      copy: "Separate verified patterns from inferred impact.",
                      to: findings[0]
                        ? `/scans/${displayScan.id}/findings/${findings[0].id}`
                        : `/scans/${displayScan.id}/findings`,
                    },
                    {
                      step: "03",
                      title: "Share the security report",
                      copy: "Bring evidence and remediation guidance to your team.",
                      to: `/reports/${displayScan.id}`,
                    },
                  ].map((item) => (
                    <Link
                      key={item.step}
                      to={item.to}
                      className="group rounded-lg border p-4 hover:bg-canvas"
                    >
                      <p className="font-mono text-xs text-muted-foreground">
                        {item.step}
                      </p>
                      <p className="mt-3 text-xs font-medium group-hover:underline">
                        {item.title}
                      </p>
                      <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                        {item.copy}
                      </p>
                    </Link>
                  ))}
                </div>
              </Panel>
            </TabsContent>
            <TabsContent value="findings">
              <FindingsList scanId={displayScan.id} />
            </TabsContent>
            <TabsContent value="scanners">
              <div className="grid gap-4 md:grid-cols-2">
                {scannerInfo.map((scanner) => {
                  const failed =
                    displayScan.status === "Partial" && scanner.name === "Checkov"
                  const running =
                    displayScan.partialRetry &&
                    displayScan.status === "Running" &&
                    scanner.name === "Checkov"
                  return (
                    <Panel key={scanner.name}>
                      <div className="p-5">
                        <div className="flex items-center justify-between">
                          <Heading level={2}>{scanner.description}</Heading>
                          <StatusBadge
                            status={
                              failed
                                ? "Failed"
                                : running
                                  ? "Running"
                                  : "Completed"
                            }
                          />
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {scanner.category} scanner
                        </p>
                        <div className="mt-6 flex gap-8">
                          <div>
                            <p className="text-2xl font-semibold">
                              {failed
                                ? "—"
                                : findings.filter(
                                    (findingRecord) =>
                                      findingRecord.scanner === scanner.name,
                                  ).length}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              Findings
                            </p>
                          </div>
                          <div>
                            <p className="text-lg font-medium">
                              {failed ? "Timed out" : scanner.duration}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              Duration
                            </p>
                          </div>
                        </div>
                        <div className="mt-5 border-t pt-4 font-mono text-xs text-muted-foreground">
                          Version {scanner.version} ·{" "}
                          {failed
                            ? "Results unavailable"
                            : "Evidence preserved"}
                        </div>
                        {failed && (
                          <p className="mt-3 text-xs text-medium">
                            Configuration checks exceeded the worker time limit.
                            Other results remain available.
                          </p>
                        )}
                      </div>
                      <div className="border-t bg-canvas p-3">
                        {failed ? (
                          <Button
                            variant="outline"
                            className="w-full"
                            onClick={retry}
                          >
                            Rescan
                          </Button>
                        ) : (
                          <LinkButton
                            to={`/scans/${displayScan.id}/findings?scanner=${scanner.name}`}
                            variant="ghost"
                            className="w-full"
                          >
                            View findings
                            <ArrowRight className="size-3" />
                          </LinkButton>
                        )}
                      </div>
                    </Panel>
                  )
                })}
              </div>
            </TabsContent>
            <TabsContent value="history">
              <Panel>
                <PanelHeader title="Repository scan history" />
                {scans
                  .filter((scanRecord) => scanRecord.repoId === displayScan.repoId)
                  .map((item) => (
                    <Link
                      key={item.id}
                      to={`/scans/${item.id}`}
                      className="flex items-center justify-between gap-4 border-t p-5 hover:bg-muted/40"
                    >
                      <span className="font-mono text-xs">Scan #{item.id}</span>
                      <span className="text-xs text-muted-foreground">
                        {item.date}
                      </span>
                      <StatusBadge status={item.status} />
                      <ChevronRight className="size-4" />
                    </Link>
                  ))}
              </Panel>
            </TabsContent>
          </Tabs>
        </>
      )}
      {isActive && <CancelScanDialog scanId={displayScan.id} open={cancelOpen} onOpenChange={setCancelOpen} />}
      <ScanDialog repo={repo} initialBranch={displayScan.branch || repo.branch} open={scanOpen} onOpenChange={setScanOpen} />
    </PageState>
  )
}
