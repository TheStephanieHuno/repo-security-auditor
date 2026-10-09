"use client"

import { Suspense } from "react"
import { Login } from "@/app/auth"

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <Login />
    </Suspense>
  )
}
