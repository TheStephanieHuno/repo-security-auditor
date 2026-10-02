"use client"

import { useEffect, useState } from "react"
import { Link, useParams, useSearchParams } from "@/lib/router"
import {
  Check,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  FileCode2,
  GitBranch,
  Info,
  ListFilter,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  XIcon,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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
  getWorkspaceFindings,
  getFindingContext,
  severityOrder,
  type FindingStatus,
} from "./data"
import {
  Breadcrumbs,
  CodeBlock,
  Confidence,
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
  StatusBadge,
} from "./components"
import { useStore } from "./store"

export function WorkspaceFindings() {
  return (
    <>
      <PageHeader
        title="Workspace findings"
        description="Review security evidence across all connected repositories."
        eyebrow="FINDING REVIEW"
      />
      <FindingsList scanId="all" />
    </>
  )
}

export function FindingsList({ scanId }: { scanId: string }) {
  const store = useStore()
  const [params] = useSearchParams()
  const scan = store.scans.find((scanRecord) => scanRecord.id === scanId)
  const [search, setSearch] = useState("")
  const [severity, setSeverity] = useState("All severities")
  const [category, setCategory] = useState(
    params.get("category") || "All categories",
  )
  const [scanner, setScanner] = useState(
    params.get("scanner") || "All scanners",
  )
  const [status, setStatus] = useState("All statuses")
  const [confidence, setConfidence] = useState("All confidence")
  const [sort, setSort] = useState("Severity")
  const [page, setPage] = useState(1)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [multi, setMulti] = useState<string[]>([])
  const all =
    scanId === "all"
      ? getWorkspaceFindings(store.scans, store.findings)
      : getScanFindings(scan, store.findings)
  const filtered = all
    .filter(
      (findingRecord) =>
        `${findingRecord.title} ${findingRecord.file} ${findingRecord.description}`
          .toLowerCase()
          .includes(search.toLowerCase()) &&
        (severity === "All severities" ||
          findingRecord.severity === severity) &&
        (category === "All categories" ||
          findingRecord.category === category) &&
        (scanner === "All scanners" || findingRecord.scanner === scanner) &&
        (status === "All statuses" || findingRecord.status === status) &&
        (confidence === "All confidence" ||
          findingRecord.confidence === confidence) &&
        (multi.length === 0 || multi.includes(findingRecord.severity)),
    )
    .sort((first, second) =>
      sort === "Severity"
        ? severityOrder.indexOf(first.severity) -
          severityOrder.indexOf(second.severity)
        : sort === "Confidence"
          ? ["High", "Medium", "Low"].indexOf(first.confidence) -
            ["High", "Medium", "Low"].indexOf(second.confidence)
          : sort === "File"
            ? first.file.localeCompare(second.file)
            : sort === "Oldest"
              ? capturedAt(first.repoId) - capturedAt(second.repoId)
              : capturedAt(second.repoId) - capturedAt(first.repoId),
    )
  useEffect(() => {
    setPage(1)
  }, [search, severity, category, scanner, status, confidence, sort, multi])
  function findingPath(finding: typeof all[number]) {
    const latest = store.scans.find(
      (item) =>
        item.repoId === finding.repoId &&
        ["Completed", "Partial"].includes(item.status),
    )
    return `/scans/${
      scanId === "all" ? finding.scanId || latest?.id : scanId
    }/findings/${finding.id}`
  }
  function capturedAt(repoId: string) {
    const capture =
      scan ||
      store.scans.find(
        (item) =>
          item.repoId === repoId &&
          ["Completed", "Partial"].includes(item.status),
      )
    const timestamp = Date.parse(
      (capture?.date || "").replace(" · ", " ") + " UTC",
    )
    return Number.isFinite(timestamp) ? timestamp : Number.MAX_SAFE_INTEGER
  }
  const pageSize = 8
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const list = filtered.slice((page - 1) * pageSize, page * pageSize)
  const filterCount = [
    severity !== "All severities",
    category !== "All categories",
    scanner !== "All scanners",
    status !== "All statuses",
    confidence !== "All confidence",
    multi.length > 0,
  ].filter(Boolean).length
  function clear() {
    setSearch("")
    setSeverity("All severities")
    setCategory("All categories")
    setScanner("All scanners")
    setStatus("All statuses")
    setConfidence("All confidence")
    setMulti([])
  }
  return (
    <PageState kind="Findings">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <Heading level={2} className="text-lg">
            Findings
          </Heading>
          <p className="mt-1 text-xs text-muted-foreground">
            {all.length} issues detected · Severity and confidence are assessed
            separately.
          </p>
        </div>
        <SelectControl
          label="Sort findings"
          value={sort}
          onChange={setSort}
          options={["Severity", "Confidence", "Newest", "Oldest", "File"]}
        />
      </div>
      <div className="mb-4 flex flex-wrap gap-2.5">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search findings or file paths…"
          className="w-full sm:flex-1"
        />
        <div className="hidden gap-2.5 md:flex">
          <SelectControl
            label="Severity"
            value={severity}
            onChange={setSeverity}
            options={["All severities", ...severityOrder]}
          />
          <SelectControl
            label="Category"
            value={category}
            onChange={setCategory}
            options={["All categories", ...categories]}
          />
          <SelectControl
            label="Status"
            value={status}
            onChange={setStatus}
            options={[
              "All statuses",
              "Open",
              "Reviewed",
              "Resolved",
              "False positive",
            ]}
          />
        </div>
        <Button
          variant="outline"
          className="h-9"
          onClick={() => setFiltersOpen(true)}
        >
          <ListFilter className="size-3.5" />
          Filters
          {filterCount > 0 && (
            <Badge variant="secondary" className="rounded-md">
              {filterCount}
            </Badge>
          )}
        </Button>
        {filterCount > 0 && (
          <Button variant="ghost" className="h-9 text-xs" onClick={clear}>
            Clear
            <XIcon className="size-3" />
          </Button>
        )}
      </div>
      {multi.length > 0 && (
        <div className="mb-3 flex gap-2">
          {multi.map((value) => (
            <Button
              key={value}
              variant="outline"
              className="h-6 text-xs"
              onClick={() =>
                setMulti((current) => current.filter((item) => item !== value))
              }
            >
              {value}
              <XIcon className="size-3" />
            </Button>
          ))}
        </div>
      )}
      <Panel className="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow className="bg-canvas">
              <TableHead className="pl-5 text-xs">Severity</TableHead>
              <TableHead className="text-xs">Finding / location</TableHead>
              <TableHead className="text-xs">Category</TableHead>
              <TableHead className="text-xs">Confidence</TableHead>
              <TableHead className="text-xs">Source / status</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.map((findingRecord) => (
              <TableRow key={findingRecord.id}>
                <TableCell className="py-5 pl-5">
                  <SeverityBadge severity={findingRecord.severity} />
                </TableCell>
                <TableCell className="max-w-sm whitespace-normal">
                  <Link
                    to={findingPath(findingRecord)}
                    className="text-sm font-medium hover:underline"
                  >
                    {findingRecord.title}
                  </Link>
                  {scanId === "all" && (
                    <p className="mt-1 text-xs font-medium text-muted-foreground">
                      {
                        store.repositories.find(
                          (repo) => repo.id === findingRecord.repoId,
                        )?.name
                      }
                    </p>
                  )}
                  <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                    {findingRecord.description}
                  </p>
                  <p className="mt-1.5 font-mono text-xs text-muted-foreground">
                    {findingRecord.file}:{findingRecord.line}
                  </p>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {findingRecord.category}
                </TableCell>
                <TableCell>
                  <Confidence value={findingRecord.confidence} />
                </TableCell>
                <TableCell>
                  <p className="text-xs">{findingRecord.scanner}</p>
                  <div className="mt-1.5">
                    <StatusBadge status={findingRecord.status} />
                  </div>
                </TableCell>
                <TableCell className="pr-4">
                  <Link
                    to={findingPath(findingRecord)}
                    className="inline-flex rounded p-1 hover:bg-muted"
                    aria-label={`View ${findingRecord.title}`}
                  >
                    <ChevronRight className="size-4 text-muted-foreground" />
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {list.length === 0 && (
          <EmptyState
            title={
              all.length
                ? "No findings match your filters"
                : "No findings detected"
            }
            description={
              all.length
                ? "Try a broader search or clear a filter. The underlying scanner results are still available."
                : "No findings were detected by the completed checks. This does not establish complete security."
            }
            action={
              all.length ? (
                <Button variant="outline" onClick={clear}>
                  Clear filters
                </Button>
              ) : (
                <LinkButton
                  to={scanId === "all" ? "/repositories" : `/reports/${scanId}`}
                >
                  {scanId === "all" ? "View repositories" : "View report"}
                </LinkButton>
              )
            }
          />
        )}
      </Panel>
      <div className="space-y-3 md:hidden">
        {list.map((findingRecord) => (
          <Link key={findingRecord.id} to={findingPath(findingRecord)}>
            <Panel className="mb-3">
              <div className="p-4">
                <div className="mb-3 flex justify-between">
                  <SeverityBadge severity={findingRecord.severity} />
                  <StatusBadge status={findingRecord.status} />
                </div>
                <p className="text-sm font-medium">{findingRecord.title}</p>
                <p className="mt-2 font-mono text-xs text-muted-foreground">
                  {findingRecord.file}:{findingRecord.line}
                </p>
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                  {findingRecord.description}
                </p>
                <div className="mt-4 flex justify-between">
                  <Confidence value={findingRecord.confidence} />
                  <span className="text-xs text-muted-foreground">
                    {findingRecord.scanner}
                  </span>
                </div>
              </div>
            </Panel>
          </Link>
        ))}
        {list.length === 0 && (
          <EmptyState
            title={
              all.length
                ? "No findings match your filters"
                : "No findings detected"
            }
            description={
              all.length
                ? "Try a broader search."
                : "No findings were detected by the completed checks. This does not establish complete security."
            }
            action={
              all.length ? (
                <Button onClick={clear}>Clear filters</Button>
              ) : (
                <LinkButton to="/repositories">View repositories</LinkButton>
              )
            }
          />
        )}
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-4 text-xs text-muted-foreground">
        <span>
          Showing {filtered.length ? (page - 1) * pageSize + 1 : 0}–
          {Math.min(page * pageSize, filtered.length)} of {filtered.length}{" "}
          findings
        </span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon-sm"
            aria-label="Previous page"
            disabled={page <= 1}
            onClick={() => setPage((current) => current - 1)}
          >
            <ChevronLeft className="size-3" />
          </Button>
          <span>
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="icon-sm"
            aria-label="Next page"
            disabled={page >= totalPages}
            onClick={() => setPage((current) => current + 1)}
          >
            <ChevronRight className="size-3" />
          </Button>
        </div>
      </div>
      <Dialog open={filtersOpen} onOpenChange={setFiltersOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Filter findings</DialogTitle>
            <DialogDescription>
              Focus on the evidence most relevant to your review.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-5 py-3">
            <div>
              <p className="mb-3 text-xs font-medium">
                Severity · select multiple
              </p>
              <div className="flex flex-wrap gap-4">
                {severityOrder.map((value) => (
                  <label
                    key={value}
                    className="flex items-center gap-2 text-xs"
                  >
                    <Checkbox
                      checked={multi.includes(value)}
                      onCheckedChange={(checked) =>
                        setMulti((current) =>
                          checked
                            ? [...current, value]
                            : current.filter((item) => item !== value),
                        )
                      }
                    />
                    {value}
                  </label>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                {
                  label: "Category",
                  value: category,
                  set: setCategory,
                  options: ["All categories", ...categories],
                },
                {
                  label: "Scanner",
                  value: scanner,
                  set: setScanner,
                  options: [
                    "All scanners",
                    "Semgrep",
                    "Gitleaks",
                    "Trivy",
                    "Checkov",
                  ],
                },
                {
                  label: "Confidence",
                  value: confidence,
                  set: setConfidence,
                  options: ["All confidence", "High", "Medium", "Low"],
                },
                {
                  label: "Status",
                  value: status,
                  set: setStatus,
                  options: [
                    "All statuses",
                    "Open",
                    "Reviewed",
                    "Resolved",
                    "False positive",
                  ],
                },
              ].map((item) => (
                <div key={item.label}>
                  <p className="mb-2 text-xs font-medium">{item.label}</p>
                  <SelectControl
                    label={item.label}
                    value={item.value}
                    onChange={item.set}
                    options={item.options}
                  />
                </div>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={clear}>
              Reset filters
            </Button>
            <Button onClick={() => setFiltersOpen(false)}>
              Show {filtered.length} findings
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageState>
  )
}

export function FindingDetail() {
  const { id: scanId, findingId } = useParams()
  const store = useStore()
  const [params] = useSearchParams()
  const [statusOpen, setStatusOpen] = useState(false)
  const [selectedStatus, setSelectedStatus] =
    useState<FindingStatus>("Reviewed")
  const [reason, setReason] = useState("")
  const [aiRetried, setAiRetried] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)
  const [activeSection, setActiveSection] = useState("evidence")
  const [contextIndex, setContextIndex] = useState(0)
  const scan = store.scans.find((scanRecord) => scanRecord.id === scanId)
  const finding = getScanFindings(scan, store.findings).find(
    (findingRecord) =>
      findingRecord.id === findingId && findingRecord.repoId === scan?.repoId,
  )
  const repo = store.repositories.find(
    (repositoryRecord) => repositoryRecord.id === scan?.repoId,
  )
  if (store.isRestricted(undefined, scanId)) return <AccessDenied />
  if (
    !finding ||
    !repo ||
    !scan ||
    !getScanFindings(scan, store.findings).some(
      (item) => item.id === finding.id,
    )
  )
    return (
      <EmptyState
        title="Finding not found"
        description="The finding is not available for this scan."
        action={<LinkButton to="/scans">Back to scans</LinkButton>}
      />
    )
  const related = getScanFindings(scan, store.findings)
    .filter(
      (findingRecord) =>
        findingRecord.id !== finding.id &&
        findingRecord.repoId === finding.repoId &&
        (findingRecord.category === finding.category ||
          findingRecord.scanner === finding.scanner),
    )
    .slice(0, 3)
  const aiUnavailable =
    !aiRetried &&
    (finding.aiState === "unavailable" || params.get("state") === "ai-error")
  const limited =
    finding.aiState === "limited" || params.get("state") === "uncertainty"
  function jump(section: string) {
    setActiveSection(section)
    document
      .getElementById(section)
      ?.scrollIntoView({ behavior: "smooth", block: "start" })
  }
  const contexts = getFindingContext(finding)
  const selectedContext = contexts[contextIndex] || contexts[0]
  return (
    <PageState kind="Finding details">
      <Breadcrumbs
        items={[
          { label: "Repositories", to: "/repositories" },
          { label: repo.name, to: `/repositories/${repo.id}` },
          { label: `Scan #${scan.id}`, to: `/scans/${scan.id}` },
          { label: "Finding" },
        ]}
      />
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <SeverityBadge severity={finding.severity} />
        <Badge variant="outline" className="h-6 rounded-md">
          {finding.category}
        </Badge>
        <span className="text-xs text-muted-foreground">
          RSA-
          {finding.id === "sql-injection"
            ? "0042"
            : finding.id.toUpperCase().slice(0, 8)}
        </span>
        <StatusBadge status={finding.status} />
      </div>
      {finding.reviewNote && (
        <div className="mb-5">
          <Notice title="Review note">{finding.reviewNote}</Notice>
        </div>
      )}
      <PageHeader title={finding.title} description={finding.description}>
        <Button
          variant="outline"
          className="h-9"
          onClick={() => {
            setSelectedStatus(finding.status === "Open" ? "Reviewed" : "Open")
            setStatusOpen(true)
          }}
        >
          {finding.status === "Open" ? (
            <CheckCheck className="size-4" />
          ) : (
            <RotateCcw className="size-4" />
          )}
          {finding.status === "Open" ? "Mark as reviewed" : "Change status"}
        </Button>
        <LinkButton to={`/reports/${scan.id}`}>View report</LinkButton>
      </PageHeader>
      <div className="mb-6 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <FileCode2 className="size-3.5" />
          <span className="font-mono">
            {finding.file}:{finding.line}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <ShieldCheck className="size-3.5" />
          Detected by {finding.scanner}
        </span>
        <Confidence value={finding.confidence} />
      </div>
      <div className="mb-6 flex max-w-full gap-2 overflow-x-auto border-b pb-2">
        {[
          "evidence",
          "context",
          "ai-analysis",
          "remediation",
          "traceability",
        ].map((section) => (
          <Button
            key={section}
            variant="ghost"
            className={cn(
              "h-8 shrink-0 text-xs",
              activeSection === section && "bg-muted font-medium",
            )}
            onClick={() => jump(section)}
          >
            {
              ({
                evidence: "Scanner evidence",
                context: "Repository context",
                "ai-analysis": "AI explanation",
                remediation: "Remediation",
                traceability: "Traceability",
              } as Record<string, string>)[section]
            }
          </Button>
        ))}
      </div>
      <div className="grid items-start gap-6 xl:grid-cols-4">
        <div className="min-w-0 space-y-6 xl:col-span-3">
          <Panel>
            <div id="evidence" className="scroll-mt-24">
              <PanelHeader
                title="Verified scanner evidence"
                description="Captured by a deterministic scanner. Not generated by AI."
                action={
                  <Badge
                    variant="secondary"
                    className="h-6 gap-1 rounded-md bg-trust-soft text-trust"
                  >
                    <ShieldCheck className="size-3.5" />
                    Scanner source
                  </Badge>
                }
              />
              <div className="space-y-4 px-5 pb-5">
                <CodeBlock
                  code={finding.evidence}
                  filename={finding.file}
                  highlightLine={finding.line}
                />
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-md border bg-canvas p-3">
                    <p className="text-xs text-muted-foreground">Scanner</p>
                    <p className="mt-1 text-xs font-medium">
                      {finding.scanner}
                    </p>
                  </div>
                  <div className="rounded-md border bg-canvas p-3">
                    <p className="text-xs text-muted-foreground">Location</p>
                    <p className="mt-1 font-mono text-xs">
                      Line {finding.line}
                    </p>
                  </div>
                  <div className="rounded-md border bg-canvas p-3">
                    <p className="text-xs text-muted-foreground">Captured at</p>
                    <p className="mt-1 text-xs">{scan.date}</p>
                  </div>
                </div>
                <div className="rounded-md border bg-canvas p-3">
                  <p className="text-xs text-muted-foreground">
                    Rule / advisory
                  </p>
                  <p className="mt-1.5 break-all font-mono text-xs">
                    {finding.rule}
                  </p>
                </div>
                {finding.category === "Secrets" && (
                  <Notice>
                    Credential values are redacted. This fictional sample
                    contains no usable credentials. The scanner has not tested
                    credential validity.
                  </Notice>
                )}
              </div>
            </div>
          </Panel>
          <Panel>
            <PanelHeader title="Why this matters" />
            <div className="px-5 pb-5">
              <p className="text-sm leading-7 text-muted-foreground">
                {finding.impact}
              </p>
              <p className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                <Info className="size-3.5" />
                Potential impact is an interpretation, not proof of
                exploitation.
              </p>
            </div>
          </Panel>
          <Panel>
            <div id="context" className="scroll-mt-24">
              <PanelHeader
                title="Repository context"
                description="Relevant sample context gathered around this finding."
              />
              <div className="px-5 pb-5">
                <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-canvas p-4">
                  <FileCode2 className="size-5 text-muted-foreground" />
                  <div className="flex-1">
                    <p className="font-mono text-xs">{finding.file}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {finding.category === "Code"
                        ? "User management service"
                        : finding.category === "Dependencies"
                          ? "Application dependency manifest"
                          : "Application configuration"}
                    </p>
                  </div>
                  <span className="flex items-center gap-1 font-mono text-xs text-muted-foreground">
                    <GitBranch className="size-3" />
                    {repo.branch}
                    <span className="mx-2">·</span>
                    {scan.commit || repo.commit}
                  </span>
                </div>
                <p className="mb-3 mt-5 text-xs font-medium">
                  Captured context files · fictional fixtures
                </p>
                <div className="flex flex-wrap gap-2">
                  {contexts.map((context, index) => (
                    <Button
                      key={context.file}
                      variant={contextIndex === index ? "secondary" : "outline"}
                      size="sm"
                      className="max-w-full text-xs"
                      onClick={() => setContextIndex(index)}
                      aria-pressed={contextIndex === index}
                    >
                      <FileCode2 className="size-3" />
                      <span className="truncate font-mono">{context.file}</span>
                    </Button>
                  ))}
                </div>
                <div className="mt-4 space-y-3">
                  <p className="text-xs font-medium">
                    {selectedContext.summary}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {selectedContext.relationship}
                  </p>
                  <CodeBlock
                    code={selectedContext.code}
                    filename={selectedContext.file}
                    highlight={false}
                  />
                </div>
                <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
                  Context is from the captured repository snapshot. Upstream
                  validation, deployed configuration, and runtime reachability
                  have not been independently verified.
                </p>
              </div>
            </div>
          </Panel>
          <Panel className="border-trust/25">
            <div id="ai-analysis" className="scroll-mt-24">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-trust/15 bg-trust-soft/50 px-5 py-4">
                <Heading level={2} className="flex items-center gap-2 text-sm">
                  <Sparkles className="size-4 text-trust" />
                  AI-assisted analysis
                </Heading>
                <Badge
                  variant="outline"
                  className="rounded-md border-trust/20 text-trust"
                >
                  Interpretation
                </Badge>
              </div>
              <div className="p-5">
                <p className="mb-5 text-xs leading-relaxed text-muted-foreground">
                  Generated from the scanner evidence and repository context
                  above. AI explanations do not replace the underlying evidence.
                </p>
                {aiUnavailable ? (
                  <Notice
                    title="AI analysis unavailable"
                    tone="warning"
                    action={
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="outline"
                          onClick={() => jump("evidence")}
                        >
                          View scanner evidence
                        </Button>
                        <Button
                          variant="outline"
                          disabled={aiLoading}
                          onClick={() => {
                            setAiLoading(true)
                            setTimeout(() => {
                              setAiRetried(true)
                              setAiLoading(false)
                            }, 900)
                          }}
                        >
                          {aiLoading ? (
                            <>
                              <RotateCcw className="size-3 animate-spin" />
                              Retrying…
                            </>
                          ) : (
                            <>
                              Retry AI analysis
                              <RotateCcw className="size-3" />
                            </>
                          )}
                        </Button>
                      </div>
                    }
                  >
                    The explanation service could not be reached. The underlying
                    scanner evidence and remediation guidance are still
                    available.
                  </Notice>
                ) : (
                  <div className="space-y-5">
                    <div>
                      <p className="mb-2 flex items-center gap-2 text-xs font-semibold">
                        <ShieldCheck className="size-3.5 text-trust" />
                        What is verified
                      </p>
                      <p className="text-sm leading-7 text-muted-foreground">
                        {finding.scanner} detected the pattern described by{" "}
                        <span className="break-all font-mono text-xs text-foreground">
                          {finding.rule}
                        </span>{" "}
                        in{" "}
                        <span className="font-mono text-xs text-foreground">
                          {finding.file}:{finding.line}
                        </span>
                        . {finding.description}
                      </p>
                    </div>
                    <div>
                      <p className="mb-2 flex items-center gap-2 text-xs font-semibold">
                        <Sparkles className="size-3.5 text-muted-foreground" />
                        What is inferred
                      </p>
                      <p className="text-sm leading-7 text-muted-foreground">
                        {finding.impact} The surrounding sample context suggests
                        this location belongs to the application, but does not
                        establish that the vulnerable path is reached in
                        production.
                      </p>
                    </div>
                    <Notice
                      title={limited ? "Limited confidence" : "Confidence note"}
                      tone={limited ? "warning" : "neutral"}
                    >
                      {limited
                        ? "The available evidence is not sufficient to make a confident determination about impact. Verify deployment settings, input validation, and whether the affected code is reachable."
                        : "The scanner supports the presence of the detected pattern, but exploitability has not been established. Validate input handling and runtime context before drawing conclusions."}
                    </Notice>
                    <p className="text-xs text-muted-foreground">
                      Sample explanation · Context: scanner output, relevant
                      code, repository metadata
                    </p>
                  </div>
                )}
              </div>
            </div>
          </Panel>
          <Panel>
            <div id="remediation" className="scroll-mt-24">
              <PanelHeader
                title="Recommended remediation"
                description="Guidance for a developer to review and apply. No code is modified automatically."
              />
              <div className="space-y-5 px-5 pb-5">
                <p className="text-sm leading-7 text-muted-foreground">
                  {finding.remediation}
                </p>
                <div className="grid gap-4 lg:grid-cols-2">
                  <div>
                    <p className="mb-2 text-xs font-medium text-muted-foreground">
                      BEFORE · DETECTED PATTERN
                    </p>
                    <CodeBlock
                      code={finding.evidence}
                      filename={finding.file}
                      highlightLine={finding.line}
                    />
                  </div>
                  <div>
                    <p className="mb-2 text-xs font-medium text-trust">
                      AFTER · ILLUSTRATIVE EXAMPLE
                    </p>
                    <CodeBlock
                      code={finding.fixed}
                      filename="Suggested change"
                      highlight={false}
                    />
                  </div>
                </div>
                <div className="rounded-lg border bg-canvas p-4">
                  <Heading level={3} className="text-xs">
                    Why this helps
                  </Heading>
                  <p className="mt-2 text-xs leading-6 text-muted-foreground">
                    {finding.id.endsWith("sql-injection")
                      ? "Parameterization separates SQL structure from supplied data so input is treated as a value, rather than part of the query. Validate input independently and use the placeholder syntax supported by your database driver."
                      : finding.category === "Secrets"
                        ? "Rotation invalidates a leaked credential. Moving the replacement outside version control reduces accidental disclosure, but does not remove the original exposure from repository history."
                        : finding.category === "Dependencies"
                          ? "A supported patched release removes the known vulnerable behavior. Run tests and check whether any vulnerable APIs were used; upgrading alone does not validate all application behavior."
                          : "A secure configuration or API removes the detected pattern. Review it in your actual deployment context and validate the change with tests."}
                  </p>
                </div>
                <Notice>
                  These examples are illustrative, not a universal fix. Review
                  the framework, version, and deployment context before applying
                  a change.
                </Notice>
              </div>
            </div>
          </Panel>
          <Panel>
            <div id="traceability" className="scroll-mt-24">
              <PanelHeader
                title="Source traceability"
                description="A transparent chain from detection to interpretation."
              />
              <dl className="grid gap-x-6 gap-y-5 px-5 pb-5 sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-muted-foreground">
                    Scan / finding identifier
                  </dt>
                  <dd className="mt-1.5 break-all font-mono text-xs">
                    #{scan.id} / {finding.id}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">
                    Originating scanner
                  </dt>
                  <dd className="mt-1.5 text-sm">{finding.scanner}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">
                    Evidence captured
                  </dt>
                  <dd className="mt-1.5 text-sm">{scan.date}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">
                    Rule / advisory
                  </dt>
                  <dd className="mt-1.5 break-all font-mono text-xs">
                    {finding.rule}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">
                    Repository snapshot
                  </dt>
                  <dd className="mt-1.5 font-mono text-xs">
                    {scan.commit || repo.commit} · {repo.branch}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs text-muted-foreground">
                    Sample interpretation context
                  </dt>
                  <dd className="mt-2 flex flex-wrap gap-2">
                    {[
                      "Scanner result",
                      "Relevant code",
                      "Repository metadata",
                    ].map((text) => (
                      <Badge
                        key={text}
                        variant="secondary"
                        className="rounded-md font-normal"
                      >
                        {text}
                      </Badge>
                    ))}
                  </dd>
                </div>
              </dl>
              <p className="px-5 pb-5 text-xs leading-relaxed text-muted-foreground">
                Repository content is untrusted data, not instructions for
                analysis. Sample explanations are static; no AI service executes
                in this prototype.
              </p>
            </div>
          </Panel>
        </div>
        <aside className="space-y-5 xl:sticky xl:top-24">
          <Panel>
            <PanelHeader title="Finding at a glance" />
            <dl className="space-y-5 px-5 pb-5 text-xs">
              {[
                [
                  "Severity",
                  <SeverityBadge key="severity" severity={finding.severity} />,
                ],
                [
                  "Confidence",
                  <Confidence key="confidence" value={finding.confidence} />,
                ],
                [
                  "Status",
                  <StatusBadge key="status" status={finding.status} />,
                ],
                ["Category", finding.category],
                ["Detected by", finding.scanner],
              ].map(([label, value]) => (
                <div key={String(label)}>
                  <dt className="mb-1.5 text-muted-foreground">{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
            <div className="border-t bg-canvas p-4">
              <Button
                variant="outline"
                className="w-full text-xs"
                onClick={() => {
                  setSelectedStatus(finding.status)
                  setStatusOpen(true)
                }}
              >
                Update finding status
              </Button>
            </div>
          </Panel>
          <Panel>
            <PanelHeader
              title="Related findings"
              description="Shared category or scanner source in this scan. Grouping does not establish an attack path."
            />
            <div className="px-4 pb-4">
              {related.length ? (
                related.map((findingRecord) => (
                  <Link
                    key={findingRecord.id}
                    to={`/scans/${scan.id}/findings/${findingRecord.id}`}
                    className="block border-b py-3 first:pt-0 last:border-0"
                  >
                    <SeverityBadge severity={findingRecord.severity} />
                    <p className="mt-2 text-xs font-medium leading-relaxed hover:underline">
                      {findingRecord.title}
                    </p>
                    <p className="mt-1 break-all font-mono text-xs text-muted-foreground">
                      {findingRecord.file}:{findingRecord.line}
                    </p>
                  </Link>
                ))
              ) : (
                <p className="text-xs leading-relaxed text-muted-foreground">
                  No related findings were identified.
                </p>
              )}
            </div>
          </Panel>
          <Notice title="Review, then verify">
            A reviewed status records a human assessment. It does not change
            scanner evidence or prove remediation.
          </Notice>
        </aside>
      </div>
      <Dialog open={statusOpen} onOpenChange={setStatusOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Update finding status</DialogTitle>
            <DialogDescription>
              Record your assessment. The original evidence is always preserved.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm font-medium">{finding.title}</p>
            <SelectControl
              label="Finding status"
              value={selectedStatus}
              onChange={(value) => setSelectedStatus(value as FindingStatus)}
              options={["Open", "Reviewed", "Resolved", "False positive"]}
            />
            {["Resolved", "False positive"].includes(selectedStatus) && (
              <>
                <label
                  htmlFor="status-reason"
                  className="block text-xs font-medium"
                >
                  Review note (required)
                </label>
                <Input
                  id="status-reason"
                  placeholder="What did you verify?"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                />
                <Notice>
                  {selectedStatus === "Resolved"
                    ? "This records a local review decision, not a verified fix. Run a new scan to validate remediation."
                    : "This records a local assessment. It does not override the original scanner evidence."}
                </Notice>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStatusOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={
                ["Resolved", "False positive"].includes(selectedStatus) &&
                !reason.trim()
              }
              onClick={() => {
                store.setFindingStatus(finding.id, selectedStatus, reason)
                setStatusOpen(false)
                setReason("")
              }}
            >
              <Check className="size-3.5" />
              Save status
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageState>
  )
}
