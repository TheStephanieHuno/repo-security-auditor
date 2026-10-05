"use client"

import { useState } from "react"
import { Link } from "@/lib/router"
import {
  Activity,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Clock3,
  FolderGit2,
  Play,
  Plus,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useRepositories, useScans, useFindings } from "@/lib/api/hooks"
import { categories, getWorkspaceFindings, getScanFindings } from "@/lib/security-model"
import {
  categoryIcons,
  EmptyState,
  Confidence,
  Heading,
  LinkButton,
  PageHeader,
  PageState,
  Panel,
  PanelHeader,
  RepositoryCard,
  ScanDialog,
  SeverityBadge,
  SeverityDistribution,
  StatusBadge,
} from "./components"

export function Dashboard() {
  const { data: reposData, isLoading: rLoading } = useRepositories(1, 100)
  const { data: scansData, isLoading: sLoading } = useScans(1, 100)
  const { data: findingsData, isLoading: fLoading } = useFindings({ page_size: 1000 })
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

  const repositories = reposData?.items || []
  const scans = scansData?.items || []
  const findings = findingsData?.items || []
  if (!repositories.length)
    return (
      <PageState kind="Repositories">
        <PageHeader
          title="Security Overview"
          description="Connect a repository to begin an evidence-backed security review."
        />
        <Panel>
          <EmptyState
            title="No repositories yet"
            description="Connect a GitHub repository to begin your first security scan."
            action={
              <LinkButton to="/repositories/new" variant="default">
                Connect repository
              </LinkButton>
            }
          />
        </Panel>
      </PageState>
    )
  const openFindings = getWorkspaceFindings(scans, findings).filter(
    (finding) => finding.status === "Open",
  )
  const priority = openFindings.filter(
    (findingRecord) =>
      findingRecord.severity === "Critical" ||
      findingRecord.severity === "High",
  )
  const latestCompleted = scans.find((scan) => scan.status === "Completed")
  const latestRepository = repositories.find(
    (repo) => repo.id === latestCompleted?.repoId,
  )
  const metrics = [
    {
      label: "Connected repositories",
      value: repositories.length,
      icon: FolderGit2,
      detail: "Across your workspace",
      extra: (
        <span className="flex items-center gap-1 text-trust">
          <CheckCircle2 className="size-3" />
          GitHub connected
        </span>
      ),
    },
    {
      label: "Open findings",
      value: openFindings.length,
      icon: ShieldCheck,
      detail: "Awaiting review or remediation",
      extra: (
        <span className="flex items-center gap-1 text-trust">
          <ShieldCheck className="size-3" />4 security categories
        </span>
      ),
    },
    {
      label: "Critical & high",
      value: priority.length,
      icon: TriangleAlert,
      detail: "Prioritize these findings",
      extra: (
        <span className="text-high">
          {
            priority.filter(
              (findingRecord) => findingRecord.severity === "Critical",
            ).length
          }{" "}
          critical ·{" "}
          {
            priority.filter(
              (findingRecord) => findingRecord.severity === "High",
            ).length
          }{" "}
          high
        </span>
      ),
    },
    {
      label: "Last completed scan",
      value:
        scans.find((scanRecord) => scanRecord.status === "Completed")
          ?.relative || "No scans",
      icon: Clock3,
      detail: latestRepository
        ? `${latestRepository.name} · ${latestRepository.branch}`
        : "Run your first scan",
      extra: (
        <span className="flex items-center gap-1 text-trust">
          <span className="size-1.5 rounded-full bg-trust" />
          All checks completed
        </span>
      ),
    },
  ]
  return (
    <PageState kind="Repositories">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs font-medium tracking-widest text-muted-foreground">
          WORKSPACE OVERVIEW
        </p>
        <span className="hidden items-center gap-2 text-xs text-muted-foreground sm:flex">
          <CalendarDays className="size-3.5" />
          Thursday, October 1, 2026
        </span>
      </div>
      <PageHeader
        title="Security Overview"
        description="A clear view of your repositories. A confident next step."
      >
        <Button
          variant="outline"
          className="h-9 gap-2 px-3.5"
          onClick={() => setScanOpen(true)}
        >
          <Play className="size-3.5" />
          Start new scan
        </Button>
        <LinkButton to="/repositories/new" variant="default">
          <Plus className="size-4" />
          Add repository
        </LinkButton>
      </PageHeader>
      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        {metrics.map((metric) => (
          <Panel key={metric.label}>
            <div className="p-5">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="font-medium">{metric.label}</span>
                <metric.icon className="size-4" strokeWidth={1.7} />
              </div>
              <p className="mt-4 text-2xl font-semibold tabular-nums md:text-3xl">
                {metric.value}
              </p>
              <p className="mt-1.5 text-xs text-muted-foreground">
                {metric.detail}
              </p>
            </div>
            <div className="border-t bg-canvas/50 px-5 py-2.5 text-xs">
              {metric.extra}
            </div>
          </Panel>
        ))}
      </div>
      <div className="mt-6 grid gap-5 xl:grid-cols-5">
        <Panel className="xl:col-span-3">
          <PanelHeader
            title="Security posture"
            action={
              <Badge
                variant="secondary"
                className="h-6 gap-1.5 rounded-md bg-medium-soft text-medium"
              >
                <CircleAlert className="size-3" />
                Needs attention
              </Badge>
            }
          />
          <div className="px-5 pb-5">
            <p className="text-xs leading-relaxed text-muted-foreground">
              {priority.length} high-priority findings need your review. Start
              with exposed credentials.
            </p>
            <div className="mt-5">
              <SeverityDistribution findings={openFindings} />
            </div>
            <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-3 border-t pt-4 sm:grid-cols-4">
              {categories.map((category) => {
                const Icon = categoryIcons[category]
                return (
                  <div key={category}>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Icon className="size-3.5" />
                      {category}
                    </div>
                    <p className="mt-1.5 text-sm font-medium">
                      {
                        openFindings.filter(
                          (findingRecord) =>
                            findingRecord.category === category,
                        ).length
                      }
                      <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                        findings
                      </span>
                    </p>
                  </div>
                )
              })}
            </div>
          </div>
          <div className="flex items-center justify-between border-t bg-canvas/50 px-5 py-3">
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <ShieldCheck className="size-3.5 text-trust" />
              Based on verified scanner evidence
            </span>
            <Link
              to="/findings"
              className="flex items-center gap-1.5 text-xs font-medium"
            >
              Review findings
              <ArrowRight className="size-3.5" />
            </Link>
          </div>
        </Panel>
        <Panel className="xl:col-span-2">
          <PanelHeader
            title="Recent scan activity"
            action={
              <Link
                to="/scans"
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                View all <span className="ml-1">↗</span>
              </Link>
            }
          />
          <div className="px-5 pb-3">
            {scans.slice(0, 3).map((scan, index) => (
              <Link
                key={scan.id}
                to={`/scans/${scan.id}`}
                className="group flex gap-3 border-b py-3.5 last:border-0"
              >
                <div className="flex flex-col items-center">
                  <span className="flex size-7 items-center justify-center rounded-full border bg-canvas">
                    <Activity className="size-3.5 text-muted-foreground" />
                  </span>
                  {index < 2 && <span className="mt-2 h-7 border-l" />}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium group-hover:underline">
                    {repositories.find((repo) => repo.id === scan.repoId)?.name}
                  </p>
                  <div className="mt-2 flex items-center justify-between">
                    <StatusBadge status={scan.status} />
                    <span className="text-xs text-muted-foreground">
                      {scan.relative}
                    </span>
                  </div>
                  <p className="mt-1.5 text-xs text-muted-foreground">
                    Scan #{scan.id} <span className="mx-1">·</span>{" "}
                    {scan.status === "Partial"
                      ? "3 of 4 checks completed"
                      : ["Completed", "Partial"].includes(scan.status)
                        ? `${getScanFindings(scan, findings).length} findings detected`
                        : scan.status === "Failed"
                          ? "No checks completed"
                          : "Results pending"}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </Panel>
      </div>
      <Panel className="mt-6">
        <PanelHeader
          title="Priority findings"
          description="The issues worth your attention first."
          action={
            <LinkButton to="/findings" variant="ghost" className="h-7 text-xs">
              View all findings
              <ArrowRight className="size-3" />
            </LinkButton>
          }
        />
        <Table className="hidden md:table">
          <TableHeader>
            <TableRow className="bg-canvas/70 hover:bg-canvas/70">
              <TableHead className="pl-5 text-xs">Severity</TableHead>
              <TableHead className="text-xs">Finding</TableHead>
              <TableHead className="hidden text-xs md:table-cell">
                Repository / location
              </TableHead>
              <TableHead className="hidden text-xs xl:table-cell">
                Confidence
              </TableHead>
              <TableHead className="text-xs">Source</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {priority.slice(0, 4).map((finding) => {
              const scan = scans.find(
                (scanRecord) => scanRecord.id === finding.scanId,
              )
              return (
                <TableRow key={finding.id}>
                  <TableCell className="py-4 pl-5">
                    <SeverityBadge severity={finding.severity} />
                  </TableCell>
                  <TableCell>
                    <Link
                      to={`/scans/${scan?.id || "12"}/findings/${finding.id}`}
                      className="text-xs font-medium hover:underline"
                    >
                      {finding.title}
                    </Link>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {finding.category}
                    </p>
                  </TableCell>
                  <TableCell className="hidden md:table-cell">
                    <p className="text-xs">
                      {
                        repositories.find(
                          (repositoryRecord) =>
                            repositoryRecord.id === finding.repoId,
                        )?.name
                      }
                    </p>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      {finding.file}:{finding.line}
                    </p>
                  </TableCell>
                  <TableCell className="hidden xl:table-cell">
                    <Confidence value={finding.confidence} />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {finding.scanner}
                  </TableCell>
                  <TableCell className="pr-5">
                    <Link
                      to={`/scans/${scan?.id || "12"}/findings/${finding.id}`}
                      aria-label={`View ${finding.title}`}
                      className="inline-flex rounded p-1 hover:bg-muted"
                    >
                      <ChevronRight className="size-4 text-muted-foreground" />
                    </Link>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
        <div className="md:hidden">
          {priority.slice(0, 4).map((finding) => {
            const scan = scans.find(
              (item) =>
                item.repoId === finding.repoId &&
                ["Completed", "Partial"].includes(item.status),
            )
            return (
              <Link
                key={finding.id}
                to={`/scans/${scan?.id}/findings/${finding.id}`}
                className="block border-t p-4 hover:bg-muted/40"
              >
                <div className="flex items-center justify-between">
                  <SeverityBadge severity={finding.severity} />
                  <span className="text-xs text-muted-foreground">
                    {finding.scanner}
                  </span>
                </div>
                <p className="mt-3 text-sm font-medium">{finding.title}</p>
                <p className="mt-1.5 break-all font-mono text-xs text-muted-foreground">
                  {finding.file}:{finding.line}
                </p>
                <div className="mt-3">
                  <Confidence value={finding.confidence} />
                </div>
              </Link>
            )
          })}
        </div>
      </Panel>
      <div className="mb-3 mt-7 flex items-center justify-between">
        <Heading level={2} className="text-sm">
          Your repositories{" "}
          <span className="ml-2 text-xs font-normal text-muted-foreground">
            {repositories.length} connected
          </span>
        </Heading>
        <Link
          to="/repositories"
          className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          View all repositories
          <ArrowRight className="size-3.5" />
        </Link>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {repositories.slice(0, 3).map((repo) => (
          <RepositoryCard key={repo.id} repo={repo} />
        ))}
      </div>
      <ScanDialog open={scanOpen} onOpenChange={setScanOpen} />
    </PageState>
  )
}
