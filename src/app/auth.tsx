"use client"

import { useState } from "react"
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
import { DEMO_LOGIN_EMAIL, useStore } from "./store"

export function Login() {
  const store = useStore()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [show, setShow] = useState(false)
  const [remember, setRemember] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(
    params.get("state") === "invalid"
      ? `Invalid demo credentials. Try ${DEMO_LOGIN_EMAIL} and demo-security.`
      : "",
  )
  const [forgot, setForgot] = useState(params.get("state") === "forgot")
  const [resetEmail, setResetEmail] = useState("")
  const [resetSent, setResetSent] = useState(false)
  function signIn(demo = false) {
    setLoading(true)
    setError("")
    setTimeout(() => {
      if (params.get("state") === "network") {
        setError(
          "We couldn't connect. Your credentials were not submitted. Try again.",
        )
        setLoading(false)
        return
      }
      if (
        !demo &&
        (email !== DEMO_LOGIN_EMAIL || password !== "demo-security")
      ) {
        setError(
          `Invalid demo credentials. Try ${DEMO_LOGIN_EMAIL} and demo-security.`,
        )
        setLoading(false)
        return
      }
      store.login(remember)
      navigate(
        params.get("redirect")?.startsWith("/") &&
          !params.get("redirect")?.startsWith("//")
          ? params.get("redirect")!
          : "/dashboard",
      )
    }, 750)
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
          <Button
            variant="outline"
            disabled={loading}
            className="mt-8 h-11 w-full"
            onClick={() => signIn(true)}
          >
            <Github className="size-4" />
            Continue with GitHub{" "}
            <span className="text-xs text-muted-foreground">(demo)</span>
          </Button>
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
            <Button type="submit" disabled={loading} className="h-11 w-full">
              {loading ? (
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
          <Button
            variant="outline"
            className="mt-7 h-11 w-full"
            disabled={loading}
            onClick={() => signIn(true)}
          >
            Open demo workspace
            <ArrowRight className="size-4" />
          </Button>
        </div>
      </div>
      <Dialog open={forgot} onOpenChange={setForgot}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {resetSent ? "Reset request preview" : "Reset your password"}
            </DialogTitle>
            <DialogDescription>
              {resetSent
                ? "In a connected application, reset instructions would be sent to this email. No email was sent by this prototype."
                : "Enter your email to preview the password reset flow."}
            </DialogDescription>
          </DialogHeader>
          {resetSent ? (
            <>
              <Notice tone="success">
                Demo reset form accepted for {resetEmail}.
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
              onSubmit={(event) => {
                event.preventDefault()
                setResetSent(true)
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
                Preview reset request
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
