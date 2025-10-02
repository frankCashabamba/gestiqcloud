export type SafeParseSuccess<T> = { success: true; data: T }
export type SafeParseFailure = { success: false; error: ZodError }

type IssuePath = Array<string | number>

type Issue = {
  path: IssuePath
  message: string
}

class ZodString {
  private _checks: Array<(value: string) => string | null> = []
  private _defaultValue: string | undefined

  url() {
    this._checks.push((value) => {
      try {
        new URL(value)
        return null
      } catch {
        return 'Invalid url'
      }
    })
    return this
  }

  min(length: number) {
    this._checks.push((value) => {
      if (value.length < length) {
        return `Must be at least ${length} characters`
      }
      return null
    })
    return this
  }

  default(value: string) {
    this._defaultValue = value
    return this
  }

  _parse(value: unknown, path: IssuePath) {
    const val = value ?? this._defaultValue
    if (val === undefined) {
      return { success: false as const, issues: [{ path, message: 'Required' }] }
    }
    if (typeof val !== 'string') {
      return { success: false as const, issues: [{ path, message: 'Expected string' }] }
    }

    const errors: Issue[] = []
    for (const check of this._checks) {
      const res = check(val)
      if (res) errors.push({ path, message: res })
    }
    if (errors.length > 0) {
      return { success: false as const, issues: errors }
    }
    return { success: true as const, data: val }
  }
}

class ZodObject<TShape extends Record<string, any>> {
  constructor(private shape: { [K in keyof TShape]: any }) {}

  safeParse(data: any): SafeParseSuccess<{ [K in keyof TShape]: any }> | SafeParseFailure {
    const result: Record<string, any> = {}
    const issues: Issue[] = []
    const input = data ?? {}

    for (const key of Object.keys(this.shape)) {
      const schema = this.shape[key]
      const parsed = schema._parse(input[key], [key])
      if (parsed.success) {
        result[key] = parsed.data
      } else {
        issues.push(...parsed.issues)
      }
    }

    if (issues.length > 0) {
      return { success: false, error: new ZodError(issues) }
    }

    return { success: true, data: result as any }
  }
}

export class ZodError extends Error {
  issues: Issue[]

  constructor(issues: Issue[]) {
    super('Invalid input')
    this.issues = issues
  }

  flatten() {
    const fieldErrors: Record<string, string[]> = {}
    for (const issue of this.issues) {
      const key = issue.path.join('.') || ''
      if (!fieldErrors[key]) fieldErrors[key] = []
      fieldErrors[key].push(issue.message)
    }
    return { fieldErrors }
  }
}

export const z = {
  string: () => new ZodString(),
  object: <TShape extends Record<string, any>>(shape: { [K in keyof TShape]: any }) =>
    new ZodObject<TShape>(shape),
}

export type infer<T> = T extends { _parse: (...args: any) => { data: infer U } } ? U : never
