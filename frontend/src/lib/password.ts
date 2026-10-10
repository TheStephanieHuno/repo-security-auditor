/**
 * Shared password complexity rules.
 *
 * Policy: min 8 chars, >=1 uppercase, >=1 lowercase, >=1 digit, >=1 special char.
 * Must match the server-side regex in Backend/app/schemas/generated.py.
 */

const PASSWORD_RULES: { re: RegExp; msg: string }[] = [
  { re: /.{8,}/, msg: "At least 8 characters" },
  { re: /[A-Z]/, msg: "At least 1 uppercase letter" },
  { re: /[a-z]/, msg: "At least 1 lowercase letter" },
  { re: /\d/, msg: "At least 1 number" },
  {
    re: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?`~]/,
    msg: "At least 1 special character",
  },
]

/**
 * Returns `true` when the password satisfies all complexity rules,
 * or the message of the first failing rule.
 */
export function validatePasswordStrength(value: string): true | string {
  const failed = PASSWORD_RULES.find((r) => !r.re.test(value))
  return failed ? failed.msg : true
}
