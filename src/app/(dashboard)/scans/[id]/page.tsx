"use client"

import { Suspense } from "react"
import { ScanPage } from "@/app/scans"

export default function ScanDetailPage() {
  return (
    <Suspense fallback={null}>
      <ScanPage />
    </Suspense>
  )
}
