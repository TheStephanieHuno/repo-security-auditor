# Repo Security Auditor

Next.js 15 + React 19 + Tailwind CSS v4 application.

## Development & Build

- Development Server: `npm run dev` (starts Next.js dev server on `http://localhost:3000`)
- Production Build: `npm run build` (builds optimized production bundles)
- Start Production: `npm run start` (serves production build)

## Project Structure

- `src/app/layout.tsx` - Root layout with ThemeProvider, StoreProvider, and Toaster
- `src/app/page.tsx` - Root redirect to `/dashboard`
- `src/app/login/page.tsx` - Authentication page
- `src/app/(dashboard)/layout.tsx` - App Shell navigation layout
- `src/app/(dashboard)/dashboard/page.tsx` - Security Overview dashboard
- `src/app/(dashboard)/repositories/page.tsx` - Repositories list and management
- `src/app/(dashboard)/repositories/new/page.tsx` - Add repository flow
- `src/app/(dashboard)/repositories/[id]/page.tsx` - Repository details and scan status
- `src/app/(dashboard)/repositories/[id]/scan/page.tsx` - Repository scanner trigger
- `src/app/(dashboard)/scans/page.tsx` - Scan run history and activity
- `src/app/(dashboard)/scans/[id]/page.tsx` - Individual scan results
- `src/app/(dashboard)/scans/[id]/findings/page.tsx` - Scan findings tab view
- `src/app/(dashboard)/scans/[id]/findings/[findingId]/page.tsx` - Finding inspection and remediation details
- `src/app/(dashboard)/findings/page.tsx` - Workspace findings view
- `src/app/(dashboard)/reports/page.tsx` - Security reports catalog
- `src/app/(dashboard)/reports/[id]/page.tsx` - Security report review and export
- `src/app/(dashboard)/settings/page.tsx` - Workspace settings and GitHub integration
- `src/app/(dashboard)/help/page.tsx` - Documentation and guidance
- `src/components/ui/` - Accessible UI primitives built on Base UI and Tailwind CSS
- `src/lib/router.tsx` - Seamless Next.js App Router navigation adapter
- `src/lib/utils.ts` - Standard `cn` utility powered by clsx and tailwind-merge
- `src/index.css` - Global theme variables, animations, and Tailwind CSS v4 imports
