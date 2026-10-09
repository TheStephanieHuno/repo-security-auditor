"use client"

import { useEffect, useState } from "react"
import { useTheme } from "next-themes"
import { Popover } from "@base-ui/react/popover"
import {
  Link,
  Navigate,
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
} from "@/lib/router"
import {
  Activity,
  ArrowRight,
  Bell,
  BookOpen,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  FileText,
  FolderGit2,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Play,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Sun,
  TriangleAlert,
  XIcon,
} from "lucide-react"
import { Button, buttonVariants } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import { EmptyState, LinkButton, SearchInput, ScanDialog } from "./components"
import { getWorkspaceFindings } from "./data"
import { useStore } from "./store"

const navigation = [
  { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
  { name: "Repositories", path: "/repositories", icon: FolderGit2 },
  { name: "Scan history", path: "/scans", icon: Activity },
  { name: "Reports", path: "/reports", icon: FileText },
]
export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={cn("relative max-w-full", compact ? "w-72" : "w-full")}>
      <img
        src="/assets/80a52.svg"
        alt="Repo Security Auditor"
        className="block h-auto w-full dark:invisible"
      />
      <div className="absolute inset-0 hidden items-center gap-2 dark:flex">
        <img
          src="/assets/48bdb.svg"
          alt=""
          className="h-full w-auto shrink-0"
        />
        <span
          className={cn(
            "font-bold leading-none text-foreground",
            compact ? "text-2xl" : "text-lg",
          )}
        >
          Repo Security
          <br />
          Auditor
        </span>
      </div>
    </div>
  )
}

export function Shell({ children }: { children?: React.ReactNode } = {}) {
  const { resolvedTheme, setTheme } = useTheme()
  const isDark = resolvedTheme === "dark"
  const store = useStore()
  const location = useLocation()
  const navigate = useNavigate()
  const [mobile, setMobile] = useState(false)
  const [command, setCommand] = useState(false)
  const [search, setSearch] = useState("")
  const [notifications, setNotifications] = useState(false)
  const [unread, setUnread] = useState(true)
  const [profile, setProfile] = useState(false)
  const [workspace, setWorkspace] = useState(false)
  const [quickScan, setQuickScan] = useState(false)
  useEffect(() => {
    setMobile(false)
    window.scrollTo(0, 0)
  }, [location.pathname])
  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault()
        setCommand((current) => !current)
      }
    }
    document.addEventListener("keydown", shortcut)
    return () => document.removeEventListener("keydown", shortcut)
  }, [])
  if (!store.authenticated)
    return (
      <Navigate
        to={`/login?redirect=${encodeURIComponent(location.pathname)}`}
        replace
      />
    )
  const section = location.pathname.startsWith("/repositories")
    ? "Repositories"
    : location.pathname.startsWith("/scans")
      ? "Scan history"
      : location.pathname.startsWith("/reports")
        ? "Reports"
        : location.pathname.startsWith("/settings")
          ? "Settings"
          : location.pathname.startsWith("/help")
            ? "Documentation"
            : "Dashboard"
  const resultRepos = store.repositories
    .filter((repo) => repo.name.toLowerCase().includes(search.toLowerCase()))
    .slice(0, 4)
  const resultFindings = getWorkspaceFindings(store.scans, store.findings)
    .filter((finding) =>
      finding.title.toLowerCase().includes(search.toLowerCase()),
    )
    .slice(0, 4)
  const securityAlert = getWorkspaceFindings(store.scans, store.findings).find(
    (finding) =>
      finding.severity === "Critical" &&
      finding.status === "Open" &&
      finding.scanId,
  )
  const sidebar = (
    <>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <Link
          to="/dashboard"
          aria-label="Repo Security Auditor home"
          className="block px-5 py-6"
        >
          <Brand />
        </Link>
        <div className="px-4">
          <Button
            variant="outline"
            className="h-11 w-full justify-start gap-2 bg-background px-3 text-xs"
            onClick={() => setWorkspace(true)}
          >
            <span className="flex size-6 items-center justify-center rounded-md bg-muted font-semibold">
              A
            </span>
            Amalitech workspace
            <ChevronDown className="ml-auto size-3.5 text-muted-foreground" />
          </Button>
        </div>
        <div className="mt-7 px-5 text-xs font-medium tracking-wider text-muted-foreground">
          WORKSPACE
        </div>
        <nav aria-label="Main navigation" className="mt-3 space-y-1 px-3">
          {navigation.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  "flex h-10 items-center gap-3 rounded-md px-3 text-sm transition-colors",
                  isActive
                    ? "bg-trust-soft font-medium text-trust"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )
              }
            >
              <item.icon className="size-4" strokeWidth={1.7} />
              {item.name}
              {item.name === "Repositories" && (
                <span className="ml-auto rounded border border-current/10 px-1.5 text-xs opacity-70">
                  {store.repositories.length}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="mt-6 px-3">
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              cn(
                "flex h-10 items-center gap-3 rounded-md px-3 text-sm",
                isActive
                  ? "bg-trust-soft font-medium text-trust"
                  : "text-muted-foreground hover:bg-muted",
              )
            }
          >
            <Settings2 className="size-4" strokeWidth={1.7} />
            Settings
          </NavLink>
        </div>
        <section
          aria-label="Quick actions"
          className="mx-4 mb-6 mt-5 border-t pt-5"
        >
          <p className="mb-2 px-1 text-xs font-medium tracking-wider text-muted-foreground">
            QUICK ACTIONS
          </p>
          <div className="space-y-1">
            <Link
              to="/repositories/new"
              onClick={() => setMobile(false)}
              className={cn(
                buttonVariants({ variant: "ghost" }),
                "h-9 w-full justify-start gap-2.5 px-2 text-xs font-normal text-muted-foreground",
              )}
            >
              <Plus className="size-4" strokeWidth={1.7} />
              Connect repository
            </Link>
            <Button
              variant="ghost"
              className="h-9 w-full justify-start gap-2.5 px-2 text-xs font-normal text-trust hover:bg-trust-soft hover:text-trust"
              onClick={() => {
                setMobile(false)
                if (!store.repositories.length) navigate("/repositories/new")
                else setQuickScan(true)
              }}
            >
              <Play className="size-4" strokeWidth={1.7} />
              Start security scan
            </Button>
          </div>
        </section>
        <div className="mt-auto px-4 pb-5 pt-2">
          <NavLink
            to="/help"
            className="flex items-center gap-3 px-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <BookOpen className="size-4" />
            Help & documentation<span className="ml-auto">↗</span>
          </NavLink>
        </div>
      </div>
      <div className="shrink-0 border-t p-4">
        <Button
          variant="ghost"
          className="h-auto w-full justify-start gap-3 p-0 hover:bg-transparent"
          onClick={() => setProfile(true)}
        >
          <span className="flex size-8 items-center justify-center rounded-full border bg-background text-xs font-medium">
            {store.profile.name
              .split(" ")
              .map((part) => part[0])
              .slice(0, 2)
              .join("")}
          </span>
          <span className="text-left">
            <span className="block text-xs font-medium">
              {store.profile.name}
            </span>
            <span className="block text-xs font-normal text-muted-foreground">
              {store.role}
            </span>
          </span>
          <ChevronDown className="ml-auto size-3.5 text-muted-foreground" />
        </Button>
      </div>
    </>
  )
  return (
    <div className="min-h-screen bg-canvas text-foreground">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r bg-sidebar lg:flex">
        {sidebar}
      </aside>
      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b bg-background/95 px-5 backdrop-blur-sm lg:px-8">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              aria-label="Open navigation"
              className="lg:hidden"
              onClick={() => setMobile(true)}
            >
              <Menu className="size-5" />
            </Button>
            <span className="hidden text-xs text-muted-foreground sm:block">
              Workspace
            </span>
            <ChevronRight className="hidden size-3 text-muted-foreground sm:block" />
            <span className="text-xs font-medium">{section}</span>
          </div>
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              className="hidden h-8 w-56 justify-start gap-2 text-xs font-normal text-muted-foreground md:flex"
              onClick={() => setCommand(true)}
            >
              <Search className="size-3.5" />
              Search anything…
              <kbd className="ml-auto rounded border px-1.5 py-0.5 text-xs">
                ⌘ K
              </kbd>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Search workspace"
              className="md:hidden"
              onClick={() => setCommand(true)}
            >
              <Search className="size-4" />
            </Button>
            <Link to="/settings?tab=demo">
              <Badge
                variant="outline"
                className="hidden rounded-md text-muted-foreground sm:inline-flex"
              >
                Demo workspace
              </Badge>
            </Link>
            <div className="hidden h-5 border-l sm:block" />
            <Button
              variant="ghost"
              size="icon"
              aria-label={
                isDark ? "Switch to light mode" : "Switch to dark mode"
              }
              title={isDark ? "Switch to light mode" : "Switch to dark mode"}
              onClick={() => setTheme(isDark ? "light" : "dark")}
              className="text-muted-foreground hover:text-foreground"
            >
              {isDark ? (
                <Sun className="size-4" />
              ) : (
                <Moon className="size-4" />
              )}
            </Button>
            <Popover.Root open={notifications} onOpenChange={setNotifications}>
              <Popover.Trigger
                render={
                  <Button variant="ghost" size="icon" className="relative" />
                }
                aria-label={
                  unread ? "Notifications, unread activity" : "Notifications"
                }
              >
                <Bell className="size-4" />
                {unread && (
                  <span className="absolute top-1.5 right-2 size-1.5 rounded-full bg-trust ring-2 ring-background" />
                )}
              </Popover.Trigger>
              <Popover.Portal>
                <Popover.Positioner
                  side="bottom"
                  align="end"
                  sideOffset={12}
                  className="z-50"
                >
                  <Popover.Popup className="w-80 max-w-[calc(100vw-2rem)] origin-(--transform-origin) overflow-hidden rounded-lg border border-border bg-card text-card-foreground shadow-none outline-none transition-[opacity,transform] duration-150 data-[starting-style]:translate-y-1 data-[starting-style]:opacity-0 data-[ending-style]:opacity-0 motion-reduce:transition-none">
                    <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
                      <Popover.Title className="text-xs font-semibold">
                        Recent security alerts
                      </Popover.Title>
                      <Popover.Close
                        render={<Button variant="ghost" size="icon-xs" />}
                        aria-label="Close notifications"
                      >
                        <XIcon className="size-3.5 text-muted-foreground" />
                      </Popover.Close>
                    </div>
                    <Popover.Description className="sr-only">
                      Recent findings and scan activity in your workspace.
                    </Popover.Description>
                    <div className="max-h-80 overflow-y-auto overscroll-contain [scrollbar-width:thin]">
                      {securityAlert && (
                        <Link
                          to={`/scans/${securityAlert.scanId}/findings/${securityAlert.id}`}
                          onClick={() => setNotifications(false)}
                          className="block border-b border-border px-4 py-3 transition-colors last:border-b-0 hover:bg-muted/40 focus-visible:bg-muted"
                        >
                          <div className="flex items-start gap-2 text-critical">
                            <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
                            <span className="text-xs font-medium">
                              {securityAlert.title}
                            </span>
                          </div>
                          <p className="mt-1 text-xs leading-5 text-muted-foreground">
                            Critical finding in{" "}
                            <span className="break-all">
                              {securityAlert.file}
                            </span>{" "}
                            (Scan #{securityAlert.scanId}).
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {
                              store.scans.find(
                                (scan) => scan.id === securityAlert.scanId,
                              )?.relative
                            }
                          </p>
                        </Link>
                      )}
                      {store.scans.slice(0, 3).map((scan) => {
                        const completed = scan.status === "Completed"
                        const failed =
                          scan.status === "Failed" || scan.status === "Partial"
                        const Icon = completed
                          ? CircleCheck
                          : failed
                            ? TriangleAlert
                            : Activity
                        const repository = store.repositories.find(
                          (repo) => repo.id === scan.repoId,
                        )
                        return (
                          <Link
                            key={scan.id}
                            to={`/scans/${scan.id}`}
                            onClick={() => setNotifications(false)}
                            className="block border-b border-border px-4 py-3 transition-colors last:border-b-0 hover:bg-muted/40 focus-visible:bg-muted"
                          >
                            <div
                              className={cn(
                                "flex items-center gap-2",
                                completed
                                  ? "text-trust"
                                  : failed
                                    ? "text-high"
                                    : "text-foreground",
                              )}
                            >
                              <Icon className="size-3.5 shrink-0" />
                              <span className="text-xs font-medium">
                                Scan #{scan.id} {scan.status.toLowerCase()}
                              </span>
                            </div>
                            <p className="mt-1 text-xs leading-5 text-muted-foreground">
                              {completed
                                ? "Security analysis finished for "
                                : failed
                                  ? "Security analysis needs attention for "
                                  : "Security analysis is in progress for "}
                              {repository?.name || "your repository"}.
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {scan.relative}
                            </p>
                          </Link>
                        )
                      })}
                      {!store.scans.length && (
                        <p className="py-6 text-center text-xs text-muted-foreground">
                          No alerts yet. Start a scan to see activity here.
                        </p>
                      )}
                    </div>
                    <div className="border-t bg-canvas px-4 py-2">
                      <Button
                        variant="ghost"
                        className="h-7 w-full text-xs text-muted-foreground"
                        disabled={!unread}
                        onClick={() => setUnread(false)}
                      >
                        {unread ? "Mark all as read" : "All caught up"}
                      </Button>
                    </div>
                  </Popover.Popup>
                </Popover.Positioner>
              </Popover.Portal>
            </Popover.Root>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full border bg-muted text-xs font-medium"
              aria-label="Open user menu"
              onClick={() => setProfile(true)}
            >
              {store.profile.name
                .split(" ")
                .map((part) => part[0])
                .slice(0, 2)
                .join("")}
            </Button>
          </div>
        </header>
        <main className="mx-auto max-w-screen-2xl px-5 py-7 md:px-8 md:py-8 xl:px-10">
          {children ?? <Outlet />}
        </main>
      </div>
      <ScanDialog
        key={store.repositories.map((repository) => repository.id).join("|")}
        open={quickScan}
        onOpenChange={setQuickScan}
      />
      <Dialog open={mobile} onOpenChange={setMobile}>
        <DialogContent className="inset-y-0 left-0 top-0 flex h-screen w-64 max-w-full translate-x-0 translate-y-0 flex-col gap-0 rounded-none bg-sidebar p-0 sm:max-w-64">
          <DialogTitle className="sr-only">Navigation</DialogTitle>
          <DialogDescription className="sr-only">
            Workspace navigation
          </DialogDescription>
          {sidebar}
        </DialogContent>
      </Dialog>
      <Dialog open={command} onOpenChange={setCommand}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Search workspace</DialogTitle>
            <DialogDescription>
              Jump to a repository, finding, or page.
            </DialogDescription>
          </DialogHeader>
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search repositories and findings…"
          />
          <div className="max-h-96 overflow-y-auto">
            <p className="mb-2 text-xs text-muted-foreground">Repositories</p>
            {resultRepos.map((repo) => (
              <Button
                key={repo.id}
                variant="ghost"
                className="h-10 w-full justify-start"
                onClick={() => {
                  navigate(`/repositories/${repo.id}`)
                  setCommand(false)
                }}
              >
                <FolderGit2 className="size-4 text-muted-foreground" />
                {repo.name}
                <ChevronRight className="ml-auto size-3" />
              </Button>
            ))}
            <p className="mb-2 mt-4 text-xs text-muted-foreground">Findings</p>
            {resultFindings.map((finding) => (
              <Button
                key={finding.id}
                variant="ghost"
                className="h-10 w-full justify-start"
                onClick={() => {
                  const scan = store.scans.find(
                    (scanRecord) => scanRecord.id === finding.scanId,
                  )
                  navigate(`/scans/${scan?.id || "8"}/findings/${finding.id}`)
                  setCommand(false)
                }}
              >
                <ShieldCheck className="size-4 text-muted-foreground" />
                <span className="truncate">{finding.title}</span>
                <ChevronRight className="ml-auto size-3" />
              </Button>
            ))}
            {resultRepos.length + resultFindings.length === 0 && (
              <EmptyState
                title="No search results"
                description="Try a repository name, vulnerability, or dependency."
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
      <Dialog open={profile} onOpenChange={setProfile}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{store.profile.name}</DialogTitle>
            <DialogDescription>
              {store.profile.email} · {store.role}
            </DialogDescription>
          </DialogHeader>
          <Link
            to="/settings"
            onClick={() => setProfile(false)}
            className={cn(
              buttonVariants({ variant: "outline" }),
              "h-9 gap-2 px-3.5",
            )}
          >
            <Settings2 className="size-4" />
            Account settings
          </Link>
          <Button
            variant="outline"
            onClick={() => {
              store.logout()
              setProfile(false)
              navigate("/login")
            }}
          >
            <LogOut className="size-4" />
            Sign out
          </Button>
        </DialogContent>
      </Dialog>
      <Dialog open={workspace} onOpenChange={setWorkspace}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Amalitech workspace</DialogTitle>
            <DialogDescription>
              A local prototype with fictional security evidence. No GitHub,
              scanner, or AI services are connected.
            </DialogDescription>
          </DialogHeader>
          <LinkButton to="/settings?tab=demo">
            Explore prototype states
            <ArrowRight className="size-4" />
          </LinkButton>
        </DialogContent>
      </Dialog>
    </div>
  )
}
