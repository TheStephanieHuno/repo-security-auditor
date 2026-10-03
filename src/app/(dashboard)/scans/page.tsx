"use client"

import { Suspense } from "react"
import { ScanHistory } from "@/app/scans"

export default function ScansPage() {
  return (
    <Suspense fallback={null}>
      <ScanHistory />
    </Suspense>
  )
}
