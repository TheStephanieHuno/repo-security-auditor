"use client"

import { Suspense } from "react"
import { Dashboard } from "@/app/dashboard"

export default function DashboardPage() {
  return (
    <Suspense fallback={null}>
      <Dashboard />
    </Suspense>
  )
}
