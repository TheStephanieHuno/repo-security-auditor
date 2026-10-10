import type { Metadata } from "next"
import { ThemeProvider } from "next-themes"
import { Toaster } from "@/components/ui/sonner"
import { Providers } from "@/lib/api/QueryProvider"
import "@/index.css"

export const metadata: Metadata = {
  title: "Repo Security Auditor",
  description: "Evidence-backed security review and vulnerability management",
  icons: {
    icon: "/assets/48bdb.svg",
    shortcut: "/assets/48bdb.svg",
    apple: "/assets/48bdb.svg",
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased font-sans" suppressHydrationWarning>
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          <Providers>
            {children}
            <Toaster
              position="bottom-right"
              closeButton
              toastOptions={{ className: "font-sans text-sm" }}
            />
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  )
}
