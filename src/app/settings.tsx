"use client"

import { useState } from "react"
import { Link, useNavigate, useSearchParams } from "@/lib/router"
import {
  ArrowRight,
  Check,
  Github,
  KeyRound,
  LogOut,
  RotateCcw,
  ShieldCheck,
} from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
import {
  EmptyState,
  Heading,
  LinkButton,
  Notice,
  PageHeader,
  Panel,
  PanelHeader,
  SelectControl,
  StatusBadge,
} from "./components"
import { DEMO_LOGIN_EMAIL, useStore } from "./store"

const examples = [
  {
    title: "Dashboard",
    path: "/dashboard",
    states: ["loading", "empty", "error"],
  },
  {
    title: "Repository inventory",
    path: "/repositories",
    states: ["loading", "empty", "error"],
  },
  {
    title: "Repository detail",
    path: "/repositories/web-app",
    states: ["loading", "unauthorized", "scan-error"],
  },
  {
    title: "Repository validation",
    path: "/repositories/new",
    states: ["missing", "denied", "unsupported", "offline"],
  },
  {
    title: "Scan progress & results",
    path: "/scans/12",
    states: ["queued", "running", "failed", "partial", "loading", "error"],
  },
  {
    title: "Finding list",
    path: "/scans/12/findings",
    states: ["loading", "empty", "error"],
  },
  {
    title: "Finding detail",
    path: "/scans/12/findings/sql-injection",
    states: ["loading", "ai-error", "uncertainty"],
  },
  {
    title: "Scan history",
    path: "/scans",
    states: ["loading", "empty", "error"],
  },
  { title: "Reports", path: "/reports", states: ["loading", "empty", "error"] },
  {
    title: "Report generation",
    path: "/reports/12",
    states: ["generating", "report-error"],
  },
  {
    title: "Authentication",
    path: "/login",
    states: ["invalid", "network", "forgot"],
  },
]
export function Settings() {
  const store = useStore()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const tab = params.get("tab") || "profile"
  const [name, setName] = useState(store.profile.name)
  const [email, setEmail] = useState(store.profile.email)
  const [saved, setSaved] = useState(false)
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [connected, setConnected] = useState(() => {
    if (typeof window === "undefined") return true
    return localStorage.getItem("rsa-github") !== "false"
  })
  const [permissions, setPermissions] = useState(false)
  const [signout, setSignout] = useState(false)
  const [reset, setReset] = useState(false)
  const [notifications, setNotifications] = useState(() => {
    if (typeof window === "undefined") return { completion: true, failure: true }
    try {
      return (
        JSON.parse(localStorage.getItem("rsa-notifications") || "null") || {
          completion: true,
          failure: true,
        }
      )
    } catch {
      return { completion: true, failure: true }
    }
  })
  const [users, setUsers] = useState([
    { name: "Team B", email: DEMO_LOGIN_EMAIL, role: "Administrator" },
    {
      name: "Sam Rivera",
      email: "sam@amalitech.dev",
      role: "Security Analyst",
    },
    { name: "Jamie Chen", email: "jamie@amalitech.dev", role: "Developer" },
  ])
  return (
    <>
      <PageHeader
        title="Settings"
        description="Your profile, account security, and workspace preferences."
        eyebrow="ACCOUNT"
      />
      <Tabs
        value={tab}
        onValueChange={(value) => setParams({ tab: String(value) })}
      >
        <TabsList
          variant="line"
          className="mb-6 h-12 shrink-0 max-w-full justify-start gap-5 overflow-x-auto overflow-y-hidden border-b px-0 group-data-horizontal/tabs:h-12"
        >
          {[
            "profile",
            "security",
            "github",
            "notifications",
            ...(store.role === "Administrator" ? ["users"] : []),
            "demo",
          ].map((item) => (
            <TabsTrigger
              key={item}
              value={item}
              className="h-9 flex-none px-0 text-xs capitalize"
            >
              {item === "demo" ? "Prototype controls" : item}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value="profile">
          <div className="grid gap-6 xl:grid-cols-3">
            <Panel className="xl:col-span-2">
              <PanelHeader
                title="Personal information"
                description="Manage the profile shown in your workspace."
              />
              <form
                onSubmit={(event) => {
                  event.preventDefault()
                  store.setProfile({ name, email })
                  setSaved(true)
                  toast.success("Profile saved in this browser")
                }}
              >
                <div className="space-y-5 px-5 pb-6">
                  <div className="flex items-center gap-4">
                    <div className="flex size-14 items-center justify-center rounded-full border bg-muted text-lg font-medium">
                      {name
                        .split(" ")
                        .map((part) => part[0])
                        .slice(0, 2)
                        .join("")}
                    </div>
                    <div>
                      <p className="text-sm font-medium">Profile avatar</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Generated from your initials.
                      </p>
                    </div>
                  </div>
                  <div className="grid gap-5 sm:grid-cols-2">
                    <div>
                      <label
                        htmlFor="profile-name"
                        className="mb-2 block text-xs font-medium"
                      >
                        Full name
                      </label>
                      <Input
                        id="profile-name"
                        required
                        value={name}
                        onChange={(event) => {
                          setName(event.target.value)
                          setSaved(false)
                        }}
                        className="h-10"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="profile-email"
                        className="mb-2 block text-xs font-medium"
                      >
                        Email address
                      </label>
                      <Input
                        id="profile-email"
                        type="email"
                        required
                        value={email}
                        onChange={(event) => {
                          setEmail(event.target.value)
                          setSaved(false)
                        }}
                        className="h-10"
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <ShieldCheck className="size-4" />
                    Current role:{" "}
                    <span className="font-medium text-foreground">
                      {store.role}
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between border-t bg-canvas px-5 py-4">
                  <span className="text-xs text-muted-foreground">
                    {saved
                      ? "Changes saved locally"
                      : "Changes apply to this demo workspace."}
                  </span>
                  <Button type="submit">
                    <Check className="size-3" />
                    Save changes
                  </Button>
                </div>
              </form>
            </Panel>
            <Panel>
              <PanelHeader title="Account" />
              <div className="px-5 pb-5">
                <p className="text-xs leading-6 text-muted-foreground">
                  Signed in to Amalitech workspace. This prototype uses local
                  browser state, not production authentication.
                </p>
                <Button
                  variant="outline"
                  className="mt-5 w-full"
                  onClick={() => setSignout(true)}
                >
                  <LogOut className="size-4" />
                  Sign out
                </Button>
              </div>
            </Panel>
          </div>
        </TabsContent>
        <TabsContent value="security">
          <div className="max-w-3xl space-y-5">
            <Panel>
              <PanelHeader
                title="Password"
                description="Preview a lightweight password update workflow."
              />
              <div className="flex flex-wrap items-center justify-between gap-4 px-5 pb-5">
                <p className="text-xs text-muted-foreground">
                  No real credentials are stored in this prototype.
                </p>
                <Button variant="outline" onClick={() => setPasswordOpen(true)}>
                  <KeyRound className="size-4" />
                  Change password
                </Button>
              </div>
            </Panel>
            <Panel>
              <PanelHeader title="Authentication" />
              <div className="space-y-4 px-5 pb-5">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Email and password</span>
                  <Badge variant="outline" className="rounded-md">
                    Demo only
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">GitHub authentication</span>
                  <Badge variant="outline" className="rounded-md">
                    Simulated
                  </Badge>
                </div>
              </div>
            </Panel>
            <Notice>
              Production authentication and authorization must be enforced by
              the backend. This frontend demonstrates the intended
              access-control experience only.
            </Notice>
          </div>
        </TabsContent>
        <TabsContent value="github">
          <div className="max-w-3xl space-y-5">
            <Panel>
              <PanelHeader
                title="GitHub connection"
                description="Read-only repository access for security analysis."
              />
              <div className="px-5 pb-5">
                <div className="flex items-center gap-3">
                  <span className="flex size-10 items-center justify-center rounded-lg border bg-canvas">
                    <Github className="size-5" />
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-medium">Amalitech-demo</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Sample connection · {store.repositories.length} registered
                      repositories
                    </p>
                  </div>
                  <StatusBadge
                    status={connected ? "Connected" : "Not connected"}
                  />
                </div>
                <div className="mt-5 flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setPermissions(true)}
                  >
                    Review permissions
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setConnected((current) => !current)
                      localStorage.setItem("rsa-github", String(!connected))
                      toast.success(
                        connected
                          ? "Demo connection disconnected"
                          : "Demo connection restored",
                      )
                    }}
                  >
                    {connected ? "Disconnect (demo)" : "Connect (demo)"}
                  </Button>
                </div>
              </div>
            </Panel>
            {!connected && (
              <Notice
                tone="warning"
                title="GitHub connection is disconnected in the demo"
              >
                Saved scanner results remain available. Restore the connection
                before running a new analysis.
              </Notice>
            )}
            <Notice>
              GitHub tokens are not requested or stored here. Connecting and
              disconnecting only changes the local UI state.
            </Notice>
          </div>
        </TabsContent>
        <TabsContent value="notifications">
          <Panel className="max-w-3xl">
            <PanelHeader
              title="Scan notifications"
              description="Manage your local notification preferences."
            />
            {[
              {
                key: "completion",
                label: "Scan completion",
                copy: "Let me know when scanner results are ready.",
              },
              {
                key: "failure",
                label: "Scan or scanner failure",
                copy: "Notify me when coverage is incomplete or analysis fails.",
              },
            ].map((item) => (
              <div
                key={item.key}
                className="flex items-center justify-between gap-5 border-t px-5 py-5"
              >
                <div>
                  <p className="text-sm font-medium">{item.label}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {item.copy}
                  </p>
                </div>
                <Switch
                  aria-label={item.label}
                  checked={notifications[item.key]}
                  onCheckedChange={(checked) => {
                    const next = { ...notifications, [item.key]: checked }
                    setNotifications(next)
                    localStorage.setItem(
                      "rsa-notifications",
                      JSON.stringify(next),
                    )
                    toast.success("Notification preference saved")
                  }}
                />
              </div>
            ))}
            <div className="border-t bg-canvas px-5 py-4 text-xs text-muted-foreground">
              Preferences are saved in your browser. No emails are sent.
            </div>
          </Panel>
        </TabsContent>
        {store.role === "Administrator" && (
          <TabsContent value="users">
            <Panel>
              <PanelHeader
                title="Workspace users"
                description="Administrator-only role configuration preview."
              />
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-5">User</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user, index) => (
                    <TableRow key={user.email}>
                      <TableCell className="py-4 pl-5">
                        <p className="text-sm">{user.name}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {user.email}
                        </p>
                      </TableCell>
                      <TableCell>
                        <SelectControl
                          label={`Role for ${user.name}`}
                          value={user.role}
                          onChange={(value) => {
                            setUsers((current) =>
                              current.map((item, position) =>
                                position === index
                                  ? { ...item, role: value }
                                  : item,
                              ),
                            )
                            toast.success("Sample user role updated")
                          }}
                          options={[
                            "Developer",
                            "Security Analyst",
                            "Administrator",
                          ]}
                        />
                      </TableCell>
                      <TableCell>
                        <StatusBadge status="Connected" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="border-t bg-canvas p-4 text-xs text-muted-foreground">
                Sample account data. Backend permission checks are not
                implemented.
              </div>
            </Panel>
          </TabsContent>
        )}
        <TabsContent value="demo">
          <div className="space-y-5">
            <Notice title="Frontend prototype">
              All repositories, scanner results, AI explanations, and scan
              progress are fictional. Actions update local state only; no
              backend, GitHub, or AI service is called.
            </Notice>
            <Panel>
              <PanelHeader
                title="Role preview"
                description="Explore lightweight role-aware screens without changing production permissions."
              />
              <div className="flex flex-wrap items-center gap-4 px-5 pb-5">
                <SelectControl
                  label="Demo role"
                  value={store.role}
                  onChange={(value) => {
                    store.setRole(value)
                    toast.success(`Previewing ${value.toLowerCase()} role`)
                  }}
                  options={["Developer", "Security Analyst", "Administrator"]}
                />
                <p className="text-xs text-muted-foreground">
                  Administrators can see the Users tab. All roles can review
                  findings.
                </p>
              </div>
            </Panel>
            <Panel>
              <PanelHeader
                title="Repository access preview"
                description="Local UI-only permissions. This does not implement server-side authorization."
              />
              <div className="space-y-4 px-5 pb-5">
                <label className="flex items-center justify-between gap-4 text-xs">
                  Allow access to the sample repository
                  <Switch
                    checked={!store.isRestricted("web-app")}
                    onCheckedChange={(granted) =>
                      store.setRepositoryAccess("web-app", granted)
                    }
                    aria-label="Sample repository access"
                  />
                </label>
                <p className="text-xs text-muted-foreground">
                  When access is denied, the repository, findings, scans, and
                  reports disappear from workspace lists and search. Direct
                  links show a non-disclosing permission state.
                </p>
                <div className="flex flex-wrap gap-2">
                  <LinkButton to="/repositories/web-app">
                    Test repository access
                  </LinkButton>
                  <LinkButton to="/scans/12">Test scan access</LinkButton>
                  <LinkButton to="/reports/12">Test report access</LinkButton>
                </div>
              </div>
            </Panel>
            <Panel>
              <PanelHeader
                title="Explore application states"
                description="Preview recoverable failures, empty states, and skeleton loading across the complete workflow."
              />
              <div className="grid gap-5 px-5 pb-5 md:grid-cols-2 xl:grid-cols-3">
                {examples.map((example) => (
                  <div key={example.title} className="rounded-lg border p-4">
                    <p className="mb-3 text-xs font-medium">{example.title}</p>
                    <div className="flex flex-wrap gap-2">
                      {example.states.map((state) => (
                        <Link
                          key={state}
                          to={`${example.path}?state=${state}`}
                          className="rounded-md border bg-canvas px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                        >
                          {state.replace(/-/g, " ")}
                        </Link>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
            <Panel>
              <PanelHeader
                title="Reset demo workspace"
                description="Restore the initial sample repositories, findings, scans, and profile."
              />
              <div className="px-5 pb-5">
                <Button variant="outline" onClick={() => setReset(true)}>
                  <RotateCcw className="size-3" />
                  Reset sample data
                </Button>
              </div>
            </Panel>
          </div>
        </TabsContent>
        {![
          "profile",
          "security",
          "github",
          "notifications",
          "demo",
          ...(store.role === "Administrator" ? ["users"] : []),
        ].includes(tab) && (
          <EmptyState
            title="This settings area isn't available for your role"
            description="Only workspace administrators can manage users."
            action={<LinkButton to="/settings">Back to profile</LinkButton>}
          />
        )}
      </Tabs>
      <Dialog open={passwordOpen} onOpenChange={setPasswordOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change password (demo)</DialogTitle>
            <DialogDescription>
              Use fictional values only. This validates the form without
              changing authentication.
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              if (password !== confirm) {
                toast.error("Passwords do not match")
                return
              }
              toast.success("Password form validated", {
                description: "No real password was changed or stored.",
              })
              setPasswordOpen(false)
              setPassword("")
              setConfirm("")
            }}
            className="space-y-4"
          >
            <div>
              <label
                htmlFor="new-password"
                className="mb-2 block text-xs font-medium"
              >
                New demo password
              </label>
              <Input
                id="new-password"
                type="password"
                minLength={8}
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 8 characters"
              />
            </div>
            <div>
              <label
                htmlFor="confirm-password"
                className="mb-2 block text-xs font-medium"
              >
                Confirm demo password
              </label>
              <Input
                id="confirm-password"
                type="password"
                required
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
              />
            </div>
            <Button type="submit" className="w-full">
              Validate password update
            </Button>
          </form>
        </DialogContent>
      </Dialog>
      <Dialog open={permissions} onOpenChange={setPermissions}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Repository permissions</DialogTitle>
            <DialogDescription>
              Intended read-only permissions for the GitHub integration.
            </DialogDescription>
          </DialogHeader>
          {[
            "Read repository metadata",
            "Read repository contents",
            "No write access",
            "No automatic pull requests",
          ].map((item) => (
            <p key={item} className="flex items-center gap-2 text-xs">
              <Check className="size-3.5 text-trust" />
              {item}
            </p>
          ))}
          <Notice>
            These permissions describe the intended integration. No OAuth token
            exists in this demo.
          </Notice>
        </DialogContent>
      </Dialog>
      <Dialog open={signout} onOpenChange={setSignout}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Sign out of your workspace?</DialogTitle>
            <DialogDescription>
              Your local sample repositories and evidence will remain saved in
              this browser.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSignout(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                store.logout()
                navigate("/login")
              }}
            >
              Sign out
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Dialog open={reset} onOpenChange={setReset}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset the demo workspace?</DialogTitle>
            <DialogDescription>
              Local repository additions and finding review statuses will be
              restored to the original samples.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReset(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                store.reset()
                setReset(false)
                navigate("/dashboard")
              }}
            >
              Reset demo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export function Documentation() {
  return (
    <>
      <PageHeader
        title="Built on evidence"
        description="How Repo Security Auditor turns scanner output into a clear developer workflow."
        eyebrow="HELP & DOCUMENTATION"
      />
      <div className="grid gap-5 lg:grid-cols-3">
        {[
          {
            number: "01",
            title: "Connect & scan",
            copy: "Register a GitHub repository and confirm read-only access. Semgrep, Gitleaks, Trivy, and Checkov run independently inside an isolated worker.",
          },
          {
            number: "02",
            title: "Understand & verify",
            copy: "Review normalized findings with severity, confidence, source rules, and captured evidence. AI interpretation is labeled and never replaces scanner evidence.",
          },
          {
            number: "03",
            title: "Fix & report",
            copy: "Review remediation guidance, apply changes yourself, and run another scan. Export the evidence-backed report for your team.",
          },
        ].map((item) => (
          <Panel key={item.number}>
            <div className="p-6">
              <p className="font-mono text-xs text-muted-foreground">
                {item.number}
              </p>
              <Heading level={2} className="mt-4">
                {item.title}
              </Heading>
              <p className="mt-3 text-sm leading-7 text-muted-foreground">
                {item.copy}
              </p>
            </div>
          </Panel>
        ))}
      </div>
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Notice title="Severity is not confidence">
          Severity describes potential impact. Confidence describes how strongly
          the evidence supports a finding. Neither establishes guaranteed
          exploitability.
        </Notice>
        <Notice title="Partial results stay available">
          If a scanner or AI interpretation fails, completed scanner evidence is
          preserved. The interface clearly marks missing coverage.
        </Notice>
        <Notice title="Repository content is untrusted">
          The intended backend uses isolated temporary workspaces, bounded
          resources, and controlled file and network access. This UI does not
          execute repository content.
        </Notice>
        <Notice title="What is not included">
          No DAST, penetration testing, autonomous fixes, automatic pull
          requests, enterprise SSO, or continuous runtime monitoring.
        </Notice>
      </div>
      <div className="mt-6">
        <LinkButton to="/repositories/new" variant="default">
          Connect a repository
          <ArrowRight className="size-3" />
        </LinkButton>
      </div>
    </>
  )
}
