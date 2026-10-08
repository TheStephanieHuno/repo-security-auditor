"use client"

import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { toast } from "sonner"
import { useNavigate, useSearchParams } from "@/lib/router"
import { ArrowRight, Eye, EyeOff, Github, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Heading, Notice } from "./components"
import { useLogin, useRegister, useSession, useRequestPasswordReset, useConfirmPasswordReset } from "@/lib/api/hooks"
import { validatePasswordStrength } from "@/lib/password"

export function Login() {
  const devToolsEnabled = process.env.NEXT_PUBLIC_ENABLE_DEV_TOOLS === "true"
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [show, setShow] = useState(false)
  const [remember, setRemember] = useState(true)
  const { mutateAsync: login, isPending } = useLogin()
  const { data: session, isPending: sessionLoading } = useSession()
  const [error, setError] = useState(
    params.get("state") === "invalid"
      ? "Invalid email or password."
      : "",
  )
  const [forgot, setForgot] = useState(params.get("state") === "forgot")
  const [resetEmail, setResetEmail] = useState("")
  const [resetSent, setResetSent] = useState(false)
  const { mutateAsync: requestPasswordReset, isPending: resetPending } = useRequestPasswordReset()
  useEffect(() => {
    if (!sessionLoading && session) navigate("/dashboard")
  }, [navigate, session, sessionLoading])
  if (sessionLoading || session) return null
  async function signIn(demo = false) {
    setError("")
    if (params.get("state") === "network") {
      setError(
        "We couldn't connect. Your credentials were not submitted. Try again.",
      )
      return
    }

    try {
      if (demo) {
        await login({ email: "team.b@amalitechtraining.org", password: "demo-security" })
      } else {
        await login({ email, password })
      }
      navigate(
        params.get("redirect")?.startsWith("/") &&
          !params.get("redirect")?.startsWith("//")
          ? params.get("redirect")!
          : "/dashboard",
      )
    } catch (err) {
      if (err instanceof Error) setError(err.message)
      else setError("An unknown error occurred during sign in.")
    }
  }
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full px-6 py-12 sm:px-16">
        <div className="mx-auto w-full max-w-sm text-center">
          <div className="mb-12 flex justify-center">
            <img
              src="/assets/48bdb.svg"
              alt="Repo Security Auditor"
              className="h-auto w-20"
            />
          </div>
          <p className="mb-3 text-xs font-medium tracking-widest text-muted-foreground">
            WELCOME BACK
          </p>
          <Heading>Sign in to your workspace</Heading>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            A clearer picture of your code’s security awaits.
          </p>
          {devToolsEnabled && <Button
            variant="outline"
            disabled={isPending}
            className="mt-8 h-11 w-full"
            onClick={() => signIn(true)}
          >
            <Github className="size-4" />
            Continue with GitHub{" "}
            <span className="text-xs text-muted-foreground">(demo)</span>
          </Button>}
          <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex-1 border-t" />
            or sign in with email
            <span className="flex-1 border-t" />
          </div>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              signIn()
            }}
            className="space-y-5 text-left"
          >
            <div>
              <label htmlFor="email" className="mb-2 block text-xs font-medium">
                Email address
              </label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@company.com"
                className="h-11"
                required
              />
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between">
                <label htmlFor="password" className="text-xs font-medium">
                  Password
                </label>
                <Button
                  type="button"
                  variant="link"
                  className="h-auto p-0 text-xs"
                  onClick={() => setForgot(true)}
                >
                  Forgot password?
                </Button>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={show ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  className="h-11 pr-10"
                  required
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute top-1.5 right-1"
                  aria-label={show ? "Hide password" : "Show password"}
                  onClick={() => setShow((current) => !current)}
                >
                  {show ? (
                    <EyeOff className="size-4" />
                  ) : (
                    <Eye className="size-4" />
                  )}
                </Button>
              </div>
            </div>
            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              <Checkbox checked={remember} onCheckedChange={setRemember} />
              Remember me on this device
            </label>
            {error && (
              <Notice
                tone="error"
                action={
                  params.get("state") === "network" ? (
                    <Button
                      variant="outline"
                      onClick={() => {
                        setParams({})
                        setError("")
                      }}
                    >
                      Restore demo connection
                    </Button>
                  ) : undefined
                }
              >
                {error}
              </Notice>
            )}
            <Button type="submit" disabled={isPending} className="h-11 w-full">
              {isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Signing in…
                </>
              ) : (
                <>
                  Sign in
                  <ArrowRight className="size-4" />
                </>
              )}
            </Button>
          </form>
          {devToolsEnabled && <Button
            variant="outline"
            className="mt-7 h-11 w-full"
            disabled={isPending}
            onClick={() => signIn(true)}
          >
            Open demo workspace
            <ArrowRight className="size-4" />
          </Button>}
        </div>
      </div>
      <Dialog open={forgot} onOpenChange={setForgot}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {resetSent ? "Check your email" : "Reset your password"}
            </DialogTitle>
            <DialogDescription>
              {resetSent
                ? "If an account exists for that email, we sent reset instructions"
                : "Enter your email to request password reset instructions."}
            </DialogDescription>
          </DialogHeader>
          {resetSent ? (
            <>
              <Notice tone="success">
                If an account exists for that email, we sent reset instructions
              </Notice>
              <Button
                onClick={() => {
                  setForgot(false)
                  setResetSent(false)
                }}
              >
                Back to sign in
              </Button>
            </>
          ) : (
            <form
              onSubmit={async (event) => {
                event.preventDefault()
                try {
                  await requestPasswordReset({ email: resetEmail })
                  setResetSent(true)
                } catch (error) {
                  toast.error(error instanceof Error ? error.message : "Could not request a password reset.")
                }
              }}
              className="space-y-4"
            >
              <label htmlFor="reset-email" className="text-xs font-medium">
                Email address
              </label>
              <Input
                id="reset-email"
                type="email"
                required
                value={resetEmail}
                onChange={(event) => setResetEmail(event.target.value)}
                placeholder="you@company.com"
              />
              <Button type="submit" className="w-full">
                {resetPending ? "Sending…" : "Send reset instructions"}
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

const signUpSchema = z.object({
  name: z.string().trim().min(2, "Enter your full name."),
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().superRefine((v, ctx) => {
    const result = validatePasswordStrength(v)
    if (result !== true) ctx.addIssue({ code: "custom", message: result })
  }),
  confirmPassword: z.string(),
}).refine((values) => values.password === values.confirmPassword, { path: ["confirmPassword"], message: "Passwords must match." })
type SignUpValues = z.infer<typeof signUpSchema>

export function SignUp() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { mutateAsync: register, isPending } = useRegister()
  const { data: session, isPending: sessionLoading } = useSession()
  const { register: field, handleSubmit, setError, formState: { errors } } = useForm<SignUpValues>({ resolver: zodResolver(signUpSchema), defaultValues: { name: "", email: "", password: "", confirmPassword: "" } })
  const redirect = params.get("redirect")
  const safeRedirect = redirect?.startsWith("/") && !redirect.startsWith("//") ? redirect : "/dashboard"
  useEffect(() => {
    if (!sessionLoading && session) navigate("/dashboard")
  }, [navigate, session, sessionLoading])
  if (sessionLoading || session) return null
  async function submit(values: SignUpValues) {
    try { await register({ name: values.name, email: values.email, password: values.password }); navigate(safeRedirect) }
    catch (error) { 
      if (error && typeof error === 'object' && 'details' in error && Array.isArray((error as any).details)) {
        let hasFieldErrors = false;
        (error as any).details.forEach((detail: any) => {
          if (detail.field && detail.message) {
            // Check if it's a valid field for this form before setting
            if (['name', 'email', 'password'].includes(detail.field)) {
              hasFieldErrors = true;
              // @ts-ignore - hook form set error
              setError(detail.field as any, { type: "manual", message: detail.message });
            }
          }
        });
        if (!hasFieldErrors) {
          toast.error(error instanceof Error ? error.message : "Could not create your account.");
        }
      } else {
        toast.error(error instanceof Error ? error.message : "Could not create your account.");
      }
    }
  }
  return <div className="flex min-h-screen items-center justify-center bg-background"><div className="w-full max-w-sm px-6 py-12"><div className="mb-10 text-center"><img src="/assets/48bdb.svg" alt="Repo Security Auditor" className="mx-auto mb-8 w-20" /><p className="mb-3 text-xs font-medium tracking-widest text-muted-foreground">GET STARTED</p><Heading>Create your workspace account</Heading><p className="mt-3 text-sm text-muted-foreground">Start reviewing your repositories with evidence-backed security scans.</p></div><form onSubmit={handleSubmit(submit)} className="space-y-4">
    {([['name', 'Full name', 'text'], ['email', 'Email address', 'email'], ['password', 'Password', 'password'], ['confirmPassword', 'Confirm password', 'password']] as const).map(([name, label, type]) => <div key={name}><label className="mb-2 block text-xs font-medium">{label}</label><Input type={type} {...field(name)} className="h-11" />{errors[name] && <p className="mt-1 text-xs text-critical">{errors[name]?.message}</p>}</div>)}
    <Button type="submit" disabled={isPending} className="h-11 w-full">{isPending ? <Loader2 className="size-4 animate-spin" /> : "Create account"}</Button>
  </form><p className="mt-6 text-center text-xs text-muted-foreground">Already have an account? <button type="button" className="underline" onClick={() => navigate(`/login${redirect ? `?redirect=${encodeURIComponent(redirect)}` : ""}`)}>Sign in</button></p></div></div>
}

const resetSchema = z.object({
  password: z.string().superRefine((v, ctx) => {
    const result = validatePasswordStrength(v)
    if (result !== true) ctx.addIssue({ code: "custom", message: result })
  }),
  confirmPassword: z.string(),
}).refine((values) => values.password === values.confirmPassword, { path: ["confirmPassword"], message: "Passwords must match." })
type ResetValues = z.infer<typeof resetSchema>

export function ResetPassword() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const token = params.get("token") || ""
  const { mutateAsync: confirm, isPending, isSuccess, error } = useConfirmPasswordReset()
  const { register: field, handleSubmit, formState: { errors } } = useForm<ResetValues>({ resolver: zodResolver(resetSchema), defaultValues: { password: "", confirmPassword: "" } })
  async function submit(values: ResetValues) {
    await confirm({ token, password: values.password })
  }
  return <div className="flex min-h-screen items-center justify-center bg-background"><div className="w-full max-w-sm px-6 py-12"><div className="mb-10 text-center"><img src="/assets/48bdb.svg" alt="Repo Security Auditor" className="mx-auto mb-8 w-20" /><Heading>Set a new password</Heading><p className="mt-3 text-sm text-muted-foreground">Choose a new password for your account.</p></div>{!token ? <Notice tone="error">This reset link is missing its token or is invalid.</Notice> : isSuccess ? <><Notice tone="success">Your password was reset successfully.</Notice><Button className="mt-5 w-full" onClick={() => navigate("/login")}>Return to sign in</Button></> : <form onSubmit={handleSubmit(submit)} className="space-y-4">{([['password', 'New password'], ['confirmPassword', 'Confirm password']] as const).map(([name, label]) => <div key={name}><label className="mb-2 block text-xs font-medium">{label}</label><Input type="password" {...field(name)} className="h-11" />{errors[name] && <p className="mt-1 text-xs text-critical">{errors[name]?.message}</p>}</div>)}{error && <Notice tone="error">{error instanceof Error ? error.message : "This reset link is invalid or expired."}</Notice>}<Button type="submit" disabled={isPending} className="h-11 w-full">{isPending ? "Saving…" : "Set password"}</Button></form>}<p className="mt-6 text-center text-xs text-muted-foreground"><button type="button" className="underline" onClick={() => navigate("/login")}>Back to sign in</button></p></div></div>
}
