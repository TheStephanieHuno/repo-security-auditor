"use client"
import { Suspense } from "react"
import { SignUp } from "@/app/auth"
export default function SignUpPage() { return <Suspense fallback={null}><SignUp /></Suspense> }
