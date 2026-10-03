export type Severity = "Critical" | "High" | "Medium" | "Low"
export type Category = "Code" | "Secrets" | "Dependencies" | "Configuration"
export type FindingStatus = "Open" | "Reviewed" | "Resolved" | "False positive"
export type ScanStatus = "Completed" | "Partial" | "Failed" | "Running" | "Queued"
export type DemoOutcome = "Completed" | "Partial" | "Failed" | "No findings"
export type Repository = {
  id: string
  name: string
  description: string
  language: string
  branch: string
  commit: string
  visibility: string
  connected: string
  owner?: string
  url?: string
  access?: "granted" | "denied"
}
export type Scan = {
  id: string
  repoId: string
  status: ScanStatus
  date: string
  relative: string
  duration: string
  progress: number
  stage: number
  isNew?: boolean
  findingIds?: string[]
  commit?: string
  partialRetry?: boolean
  retryOf?: string
  outcome?: DemoOutcome
  findingsSnapshot?: Finding[]
  startedAt?: string
  completedAt?: string
}
export type Finding = {
  id: string
  repoId: string
  title: string
  severity: Severity
  category: Category
  confidence: "High" | "Medium" | "Low"
  file: string
  line: number
  scanner: string
  rule: string
  description: string
  evidence: string
  fixed: string
  remediation: string
  impact: string
  status: FindingStatus
  aiState?: "limited" | "unavailable"
  reviewNote?: string
  scanId?: string
  context?: RepositoryContext[]
}
export type RepositoryContext = {
  file: string
  summary: string
  relationship: string
  code: string
}

export const repositories: Repository[] = [
  {
    id: "web-app",
    name: "Amalitech/web-app",
    description: "Customer-facing web application",
    language: "TypeScript",
    branch: "main",
    commit: "a8f3c21",
    visibility: "Private",
    connected: "Sep 12, 2026",
  },
  {
    id: "api-service",
    name: "Amalitech/api-service",
    description: "Core API and user management service",
    language: "Python",
    branch: "main",
    commit: "7c1d9e4",
    visibility: "Private",
    connected: "Sep 14, 2026",
  },
  {
    id: "mobile-app",
    name: "Amalitech/mobile-app",
    description: "React Native mobile application",
    language: "TypeScript",
    branch: "develop",
    commit: "b4e6a92",
    visibility: "Private",
    connected: "Sep 18, 2026",
  },
  {
    id: "internal-dashboard",
    name: "Amalitech/internal-dashboard",
    description: "Internal operations and analytics",
    language: "TypeScript",
    branch: "main",
    commit: "f92c8d1",
    visibility: "Private",
    connected: "Sep 19, 2026",
  },
  {
    id: "infra",
    name: "Amalitech/infrastructure",
    description: "Infrastructure as code",
    language: "HCL",
    branch: "main",
    commit: "ca910f4",
    visibility: "Private",
    connected: "Sep 22, 2026",
  },
  {
    id: "docs",
    name: "Amalitech/docs",
    description: "Developer documentation",
    language: "JavaScript",
    branch: "main",
    commit: "ec830a1",
    visibility: "Public",
    connected: "Sep 25, 2026",
  },
  {
    id: "worker",
    name: "Amalitech/background-worker",
    description: "Asynchronous task processing",
    language: "Python",
    branch: "main",
    commit: "890dca2",
    visibility: "Private",
    connected: "Sep 27, 2026",
  },
  {
    id: "sdk",
    name: "Amalitech/client-sdk",
    description: "Public API client library",
    language: "TypeScript",
    branch: "main",
    commit: "21ea8f0",
    visibility: "Public",
    connected: "Sep 30, 2026",
  },
]

export const scans: Scan[] = [
  {
    id: "12",
    repoId: "web-app",
    status: "Completed",
    date: "Oct 1, 2026 · 14:42",
    relative: "4 min ago",
    duration: "3m 42s",
    progress: 100,
    stage: 10,
  },
  {
    id: "10",
    repoId: "api-service",
    status: "Partial",
    date: "Oct 1, 2026 · 13:15",
    relative: "1 hour ago",
    duration: "2m 58s",
    progress: 100,
    stage: 10,
  },
  {
    id: "9",
    repoId: "mobile-app",
    status: "Completed",
    date: "Sep 30, 2026 · 16:24",
    relative: "Yesterday",
    duration: "2m 16s",
    progress: 100,
    stage: 10,
  },
  {
    id: "8",
    repoId: "internal-dashboard",
    status: "Failed",
    date: "Sep 30, 2026 · 11:08",
    relative: "Yesterday",
    duration: "18s",
    progress: 10,
    stage: 1,
  },
  {
    id: "7",
    repoId: "infra",
    status: "Queued",
    date: "Oct 1, 2026 · 14:45",
    relative: "Just now",
    duration: "—",
    progress: 0,
    stage: 0,
  },
  {
    id: "11",
    repoId: "web-app",
    status: "Completed",
    date: "Sep 29, 2026 · 09:30",
    relative: "2 days ago",
    duration: "3m 26s",
    progress: 100,
    stage: 10,
    commit: "3d7e091",
    findingIds: [
      "aws-key",
      "sql-injection",
      "lodash",
      "subprocess",
      "requests",
      "s3",
      "jwt",
      "minimist",
      "cookie",
      "urllib",
    ],
  },
  {
    id: "6",
    repoId: "internal-dashboard",
    status: "Completed",
    date: "Sep 28, 2026 · 15:12",
    relative: "3 days ago",
    duration: "2m 41s",
    progress: 100,
    stage: 10,
  },
]

const base = {
  status: "Open" as FindingStatus,
  confidence: "High" as const,
  repoId: "web-app",
}
export const findings: Finding[] = [
  {
    ...base,
    id: "aws-key",
    title: "Exposed AWS access key",
    severity: "Critical",
    category: "Secrets",
    file: "config/aws.ts",
    line: 18,
    scanner: "Gitleaks",
    rule: "aws-access-token",
    description:
      "A credential-shaped AWS access key is committed to the repository.",
    evidence:
      '17  const config = {\n18    accessKeyId: "AKIA…[REDACTED]",\n19    region: "us-east-1"\n20  };',
    fixed:
      "const config = {\n  accessKeyId: process.env.AWS_ACCESS_KEY_ID,\n  region: process.env.AWS_REGION\n};",
    remediation:
      "Revoke and rotate the exposed credential, then remove it from the working tree and repository history. Use environment variables or a secrets manager.",
    impact:
      "If this credential is active and has permissions, an unauthorized user could access AWS resources. Credential validity and permissions have not been tested.",
  },
  {
    ...base,
    id: "private-key",
    title: "Private key committed to repository",
    severity: "Critical",
    category: "Secrets",
    file: "config/service.pem",
    line: 1,
    scanner: "Gitleaks",
    rule: "private-key",
    description:
      "A private-key header and matching structure were detected in a tracked file.",
    evidence:
      "1  -----BEGIN PRIVATE KEY-----\n2  [REDACTED — fictional sample]\n3  -----END PRIVATE KEY-----",
    fixed: "SERVICE_PRIVATE_KEY_PATH=/run/secrets/service_key",
    remediation:
      "Rotate the key and remove the tracked file. Store the replacement in your deployment secrets manager.",
    impact:
      "An active key could allow impersonation of the associated service. The scanner does not establish whether this key is currently used.",
  },
  {
    ...base,
    id: "sql-injection",
    title: "Possible SQL injection",
    severity: "High",
    category: "Code",
    file: "api/users.py",
    line: 42,
    scanner: "Semgrep",
    rule: "python.lang.security.injection.sql.sql-injection",
    description:
      "User-controlled input appears to be incorporated directly into a SQL query.",
    evidence:
      '40  def get_user(user_id):\n41      cursor = db.cursor()\n42      cursor.execute("SELECT * FROM users WHERE id = " + user_id)\n43      return cursor.fetchone()',
    fixed:
      'def get_user(user_id):\n    cursor = db.cursor()\n    cursor.execute(\n        "SELECT * FROM users WHERE id = ?",\n        (user_id,)\n    )\n    return cursor.fetchone()',
    remediation:
      "Use parameterized queries rather than concatenating user input into SQL statements. This example uses SQLite-style placeholders; adapt it to your database driver.",
    impact:
      "An attacker may be able to influence the structure of a database query if the input is not properly parameterized. Exploitability depends on upstream validation and query reachability.",
  },
  {
    ...base,
    id: "lodash",
    title: "Vulnerable lodash dependency",
    severity: "High",
    category: "Dependencies",
    file: "package.json",
    line: 24,
    scanner: "Trivy",
    rule: "CVE-2021-23337",
    description:
      "lodash 4.17.20 is affected by a known command-injection vulnerability.",
    evidence:
      '23  "dependencies": {\n24    "lodash": "4.17.20"\n25  }\n\nAdvisory: CVE-2021-23337\nFixed version: 4.17.21',
    fixed: '"dependencies": {\n  "lodash": "^4.17.21"\n}',
    remediation:
      "Upgrade lodash to 4.17.21 or later and regenerate the lockfile. Review template usage and run the application test suite.",
    impact:
      "The affected template API may allow command injection with untrusted template configuration. Presence of the dependency does not prove the vulnerable API is reachable.",
  },
  {
    ...base,
    id: "subprocess",
    title: "Shell command uses untrusted input",
    severity: "High",
    category: "Code",
    file: "api/export.py",
    line: 67,
    scanner: "Semgrep",
    rule: "python.lang.security.audit.subprocess-shell-true",
    description:
      "A subprocess invocation enables shell parsing for a constructed command.",
    evidence: '67  subprocess.run("convert " + filename, shell=True)',
    fixed: 'subprocess.run(["convert", validated_filename], check=True)',
    remediation:
      "Pass arguments as an array and avoid shell=True. Validate filenames and restrict the process to expected inputs.",
    impact:
      "Shell metacharacters could change command behavior if the filename is controlled by an untrusted caller.",
  },
  {
    ...base,
    id: "requests",
    title: "Outdated requests dependency",
    severity: "High",
    category: "Dependencies",
    file: "requirements.txt",
    line: 8,
    scanner: "Trivy",
    rule: "CVE-2023-32681",
    description:
      "An installed requests version may forward proxy credentials on redirects.",
    evidence:
      "8  requests==2.28.2\nAdvisory: CVE-2023-32681\nFixed version: 2.31.0",
    fixed: "requests>=2.31.0",
    remediation:
      "Upgrade requests to a maintained version at or above 2.31.0 and verify proxy and redirect behavior.",
    impact:
      "Proxy authorization headers may be leaked under specific redirect conditions. Repository context does not establish proxy usage.",
  },
  {
    ...base,
    id: "debug",
    title: "Debug mode enabled",
    severity: "Medium",
    category: "Configuration",
    confidence: "Medium",
    file: "docker-compose.yml",
    line: 31,
    scanner: "Checkov",
    rule: "CUSTOM_DOCKER_DEBUG_01",
    description:
      "Debug mode is enabled in a container environment configuration.",
    evidence:
      '30  environment:\n31    DEBUG: "true"\n32    APP_ENV: "development"',
    fixed: 'environment:\n  DEBUG: "false"\n  APP_ENV: "production"',
    remediation:
      "Disable debug mode for production deployments. Keep development and production configuration separate.",
    impact:
      "Debug output may expose internal details if this configuration is used in a publicly accessible environment.",
    aiState: "limited",
  },
  {
    ...base,
    id: "s3",
    title: "S3 bucket encryption not configured",
    severity: "Medium",
    category: "Configuration",
    confidence: "Medium",
    file: "infra/storage.tf",
    line: 12,
    scanner: "Checkov",
    rule: "CKV_AWS_19",
    description:
      "An explicit encryption configuration is missing from the Terraform resource.",
    evidence:
      '12  resource "aws_s3_bucket" "uploads" {\n13    bucket = "amalitech-demo-uploads"\n14  }',
    fixed:
      'resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {\n  bucket = aws_s3_bucket.uploads.id\n  rule {\n    apply_server_side_encryption_by_default {\n      sse_algorithm = "aws:kms"\n    }\n  }\n}',
    remediation:
      "Declare the required server-side encryption policy explicitly and verify the deployed bucket settings.",
    impact:
      "The IaC does not declare an encryption policy. AWS defaults and organization policies may still provide encryption.",
    aiState: "limited",
  },
  {
    ...base,
    id: "jwt",
    title: "JWT signature verification disabled",
    severity: "Medium",
    category: "Code",
    file: "auth/token.py",
    line: 28,
    scanner: "Semgrep",
    rule: "python.jwt.security.unverified-jwt-decode",
    description: "A token decode call bypasses signature verification.",
    evidence: '28  jwt.decode(token, options={"verify_signature": False})',
    fixed: 'jwt.decode(token, public_key, algorithms=["RS256"])',
    remediation:
      "Verify signatures using a trusted key and an explicit algorithm allowlist. Validate issuer, audience, and expiration.",
    impact:
      "If this decoded token is used to authorize requests, modified claims may be trusted without cryptographic verification.",
  },
  {
    ...base,
    id: "minimist",
    title: "Prototype pollution in minimist",
    severity: "Medium",
    category: "Dependencies",
    file: "package-lock.json",
    line: 381,
    scanner: "Trivy",
    rule: "CVE-2021-44906",
    description:
      "A transitive minimist dependency is affected by prototype pollution.",
    evidence: '381  "minimist": { "version": "1.2.5" }\nFixed version: 1.2.6',
    fixed: "Update the parent package and regenerate package-lock.json.",
    remediation:
      "Update the package that introduces minimist to pull in a patched version and review untrusted CLI argument parsing.",
    impact:
      "Parsing attacker-controlled arguments with the affected version may modify object prototypes.",
    aiState: "unavailable",
  },
  {
    ...base,
    id: "cookie",
    title: "Session cookie missing Secure flag",
    severity: "Low",
    category: "Configuration",
    confidence: "Medium",
    file: "config/session.ts",
    line: 14,
    scanner: "Checkov",
    rule: "CUSTOM_COOKIE_SECURE_01",
    description:
      "The session cookie configuration does not require HTTPS transport.",
    evidence: "14  cookie: { httpOnly: true, secure: false }",
    fixed: 'cookie: { httpOnly: true, secure: true, sameSite: "lax" }',
    remediation:
      "Enable secure cookies in HTTPS environments and verify proxy trust settings.",
    impact:
      "Cookies may be sent over an unencrypted connection if HTTP is available.",
  },
  {
    ...base,
    id: "urllib",
    title: "Outdated urllib3 dependency",
    severity: "Low",
    category: "Dependencies",
    file: "requirements.txt",
    line: 12,
    scanner: "Trivy",
    rule: "CVE-2023-43804",
    description:
      "An older urllib3 version may retain sensitive headers on redirects.",
    evidence: "12  urllib3==1.26.16\nFixed version: 1.26.17",
    fixed: "urllib3>=1.26.17",
    remediation:
      "Upgrade to a supported patched release and retest outbound HTTP requests.",
    impact:
      "Cookie headers may be forwarded on cross-origin redirects under specific conditions.",
  },
]

const additional: Array<[string, Severity, Category, string, string, number, string]> =
  [
    [
      "api-service",
      "High",
      "Code",
      "Unsafe deserialization pattern",
      "api/serialization.py",
      38,
      "Semgrep",
    ],
    [
      "api-service",
      "Medium",
      "Dependencies",
      "Outdated PyYAML dependency",
      "requirements.txt",
      17,
      "Trivy",
    ],
    [
      "api-service",
      "Medium",
      "Code",
      "TLS verification disabled",
      "services/client.py",
      22,
      "Semgrep",
    ],
    [
      "api-service",
      "Low",
      "Dependencies",
      "Outdated certifi package",
      "requirements.txt",
      24,
      "Trivy",
    ],
    [
      "mobile-app",
      "High",
      "Dependencies",
      "Vulnerable axios dependency",
      "package.json",
      31,
      "Trivy",
    ],
    [
      "mobile-app",
      "Medium",
      "Configuration",
      "Cleartext traffic allowed",
      "android/AndroidManifest.xml",
      12,
      "Checkov",
    ],
    [
      "mobile-app",
      "Medium",
      "Code",
      "Insecure random number generation",
      "src/auth/token.ts",
      18,
      "Semgrep",
    ],
    [
      "mobile-app",
      "Low",
      "Configuration",
      "Backup enabled for application",
      "android/AndroidManifest.xml",
      9,
      "Checkov",
    ],
    [
      "internal-dashboard",
      "Medium",
      "Code",
      "Unescaped HTML rendering",
      "src/components/Preview.tsx",
      43,
      "Semgrep",
    ],
    [
      "internal-dashboard",
      "Medium",
      "Dependencies",
      "Outdated express dependency",
      "package.json",
      28,
      "Trivy",
    ],
    [
      "internal-dashboard",
      "Low",
      "Configuration",
      "Missing content security policy",
      "config/headers.ts",
      8,
      "Checkov",
    ],
    [
      "internal-dashboard",
      "Low",
      "Code",
      "Verbose error response",
      "api/errors.ts",
      21,
      "Semgrep",
    ],
  ]
const additionalEvidence = [
  {
    rule: "python.lang.security.deserialization.pickle",
    code: "payload = pickle.loads(request.body)",
    fix: "payload = json.loads(request.body)",
  },
  {
    rule: "CVE-2020-14343",
    code: "PyYAML==5.3.1",
    fix: "PyYAML>=5.4\nUse yaml.safe_load() for untrusted data.",
  },
  {
    rule: "python.requests.security.no-verify",
    code: "response = requests.get(service_url, verify=False)",
    fix: "response = requests.get(service_url, verify=True)",
  },
  {
    rule: "CVE-2023-37920",
    code: "certifi==2023.5.7",
    fix: "certifi>=2023.7.22",
  },
  {
    rule: "CVE-2023-45857",
    code: '"axios": "1.5.1"',
    fix: '"axios": "^1.6.0"',
  },
  {
    rule: "CUSTOM_ANDROID_CLEARTEXT_01",
    code: 'android:usesCleartextTraffic="true"',
    fix: 'android:usesCleartextTraffic="false"',
  },
  {
    rule: "javascript.security.insecure-random",
    code: "const token = Math.random().toString(36);",
    fix: "const token = crypto.randomUUID();",
  },
  {
    rule: "CUSTOM_ANDROID_BACKUP_01",
    code: 'android:allowBackup="true"',
    fix: 'android:allowBackup="false"',
  },
  {
    rule: "typescript.react.security.raw-html",
    code: "<div dangerouslySetInnerHTML={{ __html: preview }} />",
    fix: "<div>{preview}</div>",
  },
  {
    rule: "CVE-2024-29041",
    code: '"express": "4.18.2"',
    fix: '"express": "^4.19.2"',
  },
  {
    rule: "CUSTOM_HEADERS_CSP_01",
    code: 'headers: { "X-Content-Type-Options": "nosniff" }',
    fix: 'headers: { "Content-Security-Policy": "default-src \'self\'" }',
  },
  {
    rule: "typescript.security.verbose-error",
    code: "res.status(500).json({ error: err.stack });",
    fix: 'res.status(500).json({ error: "Internal server error" });',
  },
]
additional.forEach(
  ([repoId, severity, category, title, file, line, scanner], index) =>
    findings.push({
      ...base,
      id: `finding-${index + 13}`,
      repoId,
      severity,
      category,
      title,
      file,
      line,
      scanner,
      confidence: "Medium",
      rule: additionalEvidence[index].rule,
      description:
        "A security-relevant pattern was detected in the latest available scan. Review the captured evidence and deployment context.",
      evidence: `${line}  ${additionalEvidence[index].code}`,
      fixed: additionalEvidence[index].fix,
      remediation:
        "Review the affected API and update its configuration or dependency to a supported secure alternative. Validate against the actual runtime before applying changes.",
      impact:
        "The detected pattern may expose unintended behavior depending on deployment and input validation.",
      aiState: "limited",
    }),
)

export const severityOrder: Severity[] = ["Critical", "High", "Medium", "Low"]
export const categories: Category[] = [
  "Code",
  "Secrets",
  "Dependencies",
  "Configuration",
]
export const scannerInfo = [
  {
    name: "Semgrep",
    category: "Code",
    description: "Source-code analysis",
    duration: "1m 24s",
    version: "1.137.0",
  },
  {
    name: "Gitleaks",
    category: "Secrets",
    description: "Secret detection",
    duration: "32s",
    version: "8.28.0",
  },
  {
    name: "Trivy",
    category: "Dependencies",
    description: "Dependency analysis",
    duration: "1m 48s",
    version: "0.66.0",
  },
  {
    name: "Checkov",
    category: "Configuration",
    description: "Configuration / IaC",
    duration: "46s",
    version: "3.2.471",
  },
]
export const scanStages = [
  "Repository validation",
  "Repository ingestion",
  "Secret detection",
  "Source-code analysis",
  "Dependency analysis",
  "Configuration analysis",
  "Finding normalization",
  "Finding correlation",
  "AI-assisted analysis",
  "Report generation",
]
export const scanActivity = [
  "Repository access confirmed.",
  "Preparing isolated repository workspace…",
  "Gitleaks: searching for credential patterns…",
  "Semgrep: analyzing supported source files…",
  "Trivy: matching dependency versions against advisories…",
  "Checkov: checking configuration and IaC…",
  "Consolidating scanner evidence into normalized findings…",
  "Correlating locations and collecting repository context…",
  "Generating explanations from collected evidence…",
  "Preparing the security report…",
]
export function getScanFindings(scan: Scan | undefined, list: Finding[]) {
  if (
    !scan ||
    (!["Completed", "Partial"].includes(scan.status) && !scan.partialRetry)
  )
    return []
  const captured =
    scan.findingsSnapshot ??
    list.filter(
      (finding) =>
        finding.repoId === scan.repoId &&
        (!scan.findingIds || scan.findingIds.includes(finding.id)),
    )
  return captured
    .filter(
      (finding) =>
        (scan.status !== "Partial" &&
          !(scan.partialRetry && scan.status === "Running")) ||
        finding.category !== "Configuration",
    )
    .map((finding) => {
      const review = list.find((item) => item.id === finding.id)
      return {
        ...finding,
        scanId: scan.id,
        status: review?.status ?? finding.status,
        reviewNote: review?.reviewNote ?? finding.reviewNote,
      }
    })
}

export function repositoryMetadata(repo: Repository): Repository {
  return {
    ...repo,
    owner: repo.owner || repo.name.split("/")[0],
    url: repo.url || `https://github.com/${repo.name}`,
  }
}

export function createDemoFindings(
  repo: Repository,
  current: Finding[],
  scanId: string,
): Finding[] {
  const existing = current.filter((finding) => finding.repoId === repo.id)
  if (
    existing.length &&
    repositories.some((repository) => repository.id === repo.id)
  )
    return existing.map((finding) => ({ ...finding, scanId }))
  const templateIds =
    repo.language === "HCL"
      ? ["private-key", "s3"]
      : [
          "aws-key",
          "sql-injection",
          repo.language === "Python" ? "requests" : "lodash",
          "debug",
        ]
  return templateIds.map((templateId) => {
    const template = findings.find((finding) => finding.id === templateId)!
    const fixture: Finding = {
      ...template,
      id: `${repo.id}-${templateId}`,
      repoId: repo.id,
      scanId,
      status: "Open",
      reviewNote: undefined,
    }
    if (
      ["TypeScript", "JavaScript"].includes(repo.language) &&
      templateId === "sql-injection"
    ) {
      fixture.file = "api/users.ts"
      fixture.rule = "sample.javascript.sql-query-concatenation"
      fixture.evidence =
        '40  async function getUser(userId: string) {\n41    const connection = await pool.connect();\n42    return connection.query("SELECT * FROM users WHERE id = " + userId);\n43  }'
      fixture.fixed =
        'async function getUser(userId: string) {\n  return pool.query(\n    "SELECT * FROM users WHERE id = $1",\n    [userId]\n  );\n}'
      fixture.remediation =
        "Use parameterized queries rather than concatenating user input into SQL statements. This example uses node-postgres placeholders; adapt it to your database driver and validate input independently."
    }
    if (repo.language === "Python" && templateId === "aws-key") {
      fixture.file = "config/aws.py"
      fixture.evidence =
        '17  aws_config = {\n18      "access_key_id": "AKIA…[REDACTED]",\n19      "region": "us-east-1"\n20  }'
      fixture.fixed =
        'import os\n\naws_config = {\n    "access_key_id": os.environ["AWS_ACCESS_KEY_ID"],\n    "region": os.environ["AWS_REGION"]\n}'
    }
    const previous = existing.find((finding) => finding.id === fixture.id)
    return previous ? { ...previous, scanId } : fixture
  })
}

export function getRepositoryFindings(
  repoId: string,
  scanList: Scan[],
  findingList: Finding[],
) {
  const latest = scanList.find(
    (scan) =>
      scan.repoId === repoId &&
      (["Completed", "Partial"].includes(scan.status) || scan.partialRetry),
  )
  return getScanFindings(latest, findingList)
}

export function getWorkspaceFindings(scanList: Scan[], findingList: Finding[]) {
  const repoIds = [...new Set(scanList.map((scan) => scan.repoId))]
  return repoIds.flatMap((repoId) =>
    getRepositoryFindings(repoId, scanList, findingList),
  )
}

export function getFindingContext(finding: Finding): RepositoryContext[] {
  if (finding.context?.length) return finding.context
  const context = [
    {
      file: finding.file,
      summary: "Affected source captured by the scanner fixture",
      relationship: "Direct evidence source",
      code: finding.evidence,
    },
  ]
  if (finding.id === "sql-injection") {
    context.push({
      file: "routes/users.py",
      summary: "Sample caller of the user lookup function",
      relationship:
        "Calls api.users.get_user; upstream validation is not established",
      code: 'from api.users import get_user\n\n@router.get("/users/{user_id}")\ndef read_user(user_id: str):\n    return get_user(user_id)',
    })
    context.push({
      file: "database.py",
      summary: "Sample database driver context",
      relationship: "The captured example uses SQLite-style placeholders",
      code: 'import sqlite3\n\ndb = sqlite3.connect("sample-users.db")',
    })
  }
  return context
}

export const scanBoundaries = [
  { label: "Execution time", value: "10-minute limit (example policy)" },
  {
    label: "Worker resources",
    value: "Bounded CPU and memory (example policy)",
  },
  { label: "Workspace storage", value: "1 GB limit (example policy)" },
  { label: "Filesystem", value: "Temporary isolated workspace" },
  { label: "Network", value: "Restricted outbound access" },
  { label: "Cleanup", value: "Workspace removed after analysis" },
]
