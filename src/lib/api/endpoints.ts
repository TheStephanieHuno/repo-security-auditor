export const endpoints = {
  auth: {
    login: "/auth/login",
    register: "/auth/register",
    logout: "/auth/logout",
    passwordResetRequest: "/auth/password-reset/request",
    passwordResetConfirm: "/auth/password-reset/confirm",
  },
  users: {
    me: "/users/me",
    password: "/users/me/password",
    settings: "/users/me/settings",
  },
  repositories: {
    list: "/repositories",
    validate: "/repositories/validate",
    detail: (id: string) => `/repositories/${id}`,
    branches: (id: string) => `/repositories/${id}/branches`,
  },
  scans: {
    list: "/scans",
    trigger: "/scans",
    detail: (id: string) => `/scans/${id}`,
    status: (id: string) => `/scans/${id}/status`,
    cancel: (id: string) => `/scans/${id}/cancel`,
    findings: (id: string) => `/scans/${id}/findings`,
  },
  findings: {
    list: "/findings",
    detail: (id: string) => `/findings/${id}`,
  },
  reports: {
    list: "/reports",
    generate: "/reports",
    detail: (id: string) => `/reports/${id}`,
    pdf: (id: string) => `/reports/${id}/pdf`,
  },
  dashboard: {
    metrics: "/dashboard/metrics",
  },
  integrations: {
    github: "/integrations/github",
  },
} as const;
