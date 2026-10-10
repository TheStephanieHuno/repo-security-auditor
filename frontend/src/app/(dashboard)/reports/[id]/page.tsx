"use client"

import { Suspense } from "react"
import { ReportDetail } from "@/app/reports"

export default function ReportDetailPage() {
  return (
    <Suspense fallback={null}>
      <ReportDetail />
    </Suspense>
  )
}
