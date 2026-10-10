// Central registry of all API endpoint paths.
// When going live, update NEXT_PUBLIC_API_BASE_URL and switch NEXT_PUBLIC_API_MODE=live.

export const endpoints = {
  auth: {
    login: "/api/auth/login",
    logout: "/api/auth/logout",
    passwordResetRequest: "/api/auth/password-reset/request",
    passwordResetConfirm: "/api/auth/password-reset/confirm",
    register: "/api/auth/register",
  },
  users: {
    me: "/api/users/me",
    password: "/api/users/me/password",
    settings: "/api/users/me/settings",
  },
  repositories: {
    list: "/api/repositories",
    detail: (id: string) => `/api/repositories/${id}`,
    validate: "/api/repositories/validate",
    branches: (id: string) => `/api/repositories/${id}/branches`,
  },
  scans: {
    list: "/api/scans",
    detail: (id: string) => `/api/scans/${id}`,
    status: (id: string) => `/api/scans/${id}/status`,
    cancel: (id: string) => `/api/scans/${id}/cancel`,
    findings: (id: string) => `/api/scans/${id}/findings`,
    trigger: "/api/scans",
  },
  findings: {
    list: "/api/findings",
    detail: (id: string) => `/api/findings/${id}`,
  },
  reports: {
    list: "/api/reports",
    detail: (id: string) => `/api/reports/${id}`,
    pdf: (id: string) => `/api/reports/${id}/pdf`,
    generate: "/api/reports",
  },
  dashboard: {
    metrics: "/api/dashboard/metrics",
  },
  integrations: {
    github: "/api/integrations/github",
  },
} as const
