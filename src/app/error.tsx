"use client"

import { EmptyState, LinkButton } from "@/app/components"

export default function ErrorPage() {
  return (
    <div className="p-8">
      <EmptyState
        title="This page couldn't be opened"
        description="The application encountered an unexpected error. Saved sample data remains in your browser."
        action={<LinkButton to="/dashboard">Return to dashboard</LinkButton>}
      />
    </div>
  )
}
