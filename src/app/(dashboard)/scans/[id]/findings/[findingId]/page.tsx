"use client"

import { Suspense } from "react"
import { FindingDetail } from "@/app/findings"

export default function FindingDetailPage() {
  return (
    <Suspense fallback={null}>
      <FindingDetail />
    </Suspense>
  )
}
