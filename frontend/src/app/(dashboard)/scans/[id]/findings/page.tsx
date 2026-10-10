"use client"

import { Suspense } from "react"
import { ScanPage } from "@/app/scans"

export default function ScanFindingsPage() {
  return (
    <Suspense fallback={null}>
      <ScanPage findingsTab />
    </Suspense>
  )
}
