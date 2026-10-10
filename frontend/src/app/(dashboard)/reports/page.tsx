"use client"

import { Suspense } from "react"
import { Reports } from "@/app/reports"

export default function ReportsPage() {
  return (
    <Suspense fallback={null}>
      <Reports />
    </Suspense>
  )
}
