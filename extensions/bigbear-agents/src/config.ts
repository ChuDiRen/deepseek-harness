/**
 * Bigbear extension deployment config: the values the Plugins settings page
 * edits, and the derived environment injection. Fields are `volatile()` so the
 * settings pipeline projects them into the live form and a saved override
 * reloads this row without a restart; the loader then hands {@link apply} live
 * references, which {@link plainConfig} unwraps once per generation.
 *
 * Field names are the settings page's flat form fields and must stay top-level:
 * the shared configuration form binds one field per top-level config key.
 *
 * Derived values are written into the host process environment for the
 * extension's own fiber lifetime, so every model shell call inherits them and
 * the toolkit CLIs read them ahead of their optional project `.env` files
 * (python-dotenv loads with override=False).
 */

import { isVolatile } from '@deepseek-ai/cosmokit'
import type { Volatile } from '@deepseek-ai/cordis'
import z from '@deepseek-ai/schemastery'

/** Deployment config of the bigbear extension as plain trimmed values. */
export interface BigbearConfig {
  /** Toolkit root override; defaults to the repository sibling resolution. */
  readonly toolkitDir?: string | undefined
  /** Shared gateway key for every toolkit CLI (`*_API_KEY`). */
  readonly gatewayApiKey?: string | undefined
  /** OpenAI-compatible gateway URL for every toolkit CLI (`*_BASE_URL`). */
  readonly gatewayBaseUrl?: string | undefined
  /** `AGENT_AI_MODEL` for bigbear-test-runner. */
  readonly runnerModel?: string | undefined
  /** `WEB_AUTOMATION_AI_MODEL` for bigbear-web-cli. */
  readonly webModel?: string | undefined
  /** `ANDROID_AI_MODEL` for bigbear-android-cli. */
  readonly androidModel?: string | undefined
  /** `VISION_MODEL` for the record CLIs' vision analysis. */
  readonly visionModel?: string | undefined
}

/** Row config as the loader passes it: every volatile field is a live reference. */
export interface RawBigbearConfig {
  readonly toolkitDir?: Volatile<string | undefined> | undefined
  readonly gatewayApiKey?: Volatile<string | undefined> | undefined
  readonly gatewayBaseUrl?: Volatile<string | undefined> | undefined
  readonly runnerModel?: Volatile<string | undefined> | undefined
  readonly webModel?: Volatile<string | undefined> | undefined
  readonly androidModel?: Volatile<string | undefined> | undefined
  readonly visionModel?: Volatile<string | undefined> | undefined
}

/** Runtime config schema served to the config editor and the settings page. */
// Inferred, not annotated: schemastery's volatile object shape and the
// hand-written {@link RawBigbearConfig} agree structurally but disagree under
// exactOptionalPropertyTypes (the same split bash-local accepts).
export const Config = z.object({
  toolkitDir: z.string().volatile(),
  gatewayApiKey: z.string().volatile(),
  gatewayBaseUrl: z.string().volatile(),
  runnerModel: z.string().volatile(),
  webModel: z.string().volatile(),
  androidModel: z.string().volatile(),
  visionModel: z.string().volatile(),
})

/** Unwrap one field's live reference into its current trimmed value. */
function text(value: Volatile<string | undefined> | string | undefined): string | undefined {
  const raw = isVolatile(value) ? value.get() : value
  if (typeof raw !== 'string') return undefined
  const trimmed = raw.trim()
  return trimmed === '' ? undefined : trimmed
}

/** Read the row config into plain trimmed values for one apply generation. */
export function plainConfig(config: RawBigbearConfig): BigbearConfig {
  return {
    toolkitDir: text(config.toolkitDir),
    gatewayApiKey: text(config.gatewayApiKey),
    gatewayBaseUrl: text(config.gatewayBaseUrl),
    runnerModel: text(config.runnerModel),
    webModel: text(config.webModel),
    androidModel: text(config.androidModel),
    visionModel: text(config.visionModel),
  }
}

/** One derived environment assignment. */
export type EnvAssignment = readonly [name: string, value: string]

/**
 * Derive the environment injection from the config. Every group receives the
 * shared gateway key/URL, so one gateway fills every CLI; values stay absent
 * when the config leaves them unset.
 * @param config - plain extension config.
 * @returns assignments sorted by variable name.
 */
export function deriveEnv(config: BigbearConfig): EnvAssignment[] {
  const groups: readonly (readonly [prefix: string, model: string | undefined])[] = [
    ['AGENT_AI', config.runnerModel],
    ['WEB_AUTOMATION_AI', config.webModel],
    ['ANDROID_AI', config.androidModel],
    ['VISION', config.visionModel],
  ]
  const assignments: EnvAssignment[] = []
  if (config.toolkitDir !== undefined) {
    assignments.push(['BIGBEAR_TOOLKIT_DIR', config.toolkitDir])
  }
  for (const [prefix, model] of groups) {
    if (config.gatewayApiKey !== undefined) assignments.push([`${prefix}_API_KEY`, config.gatewayApiKey])
    if (config.gatewayBaseUrl !== undefined) assignments.push([`${prefix}_BASE_URL`, config.gatewayBaseUrl])
    if (model !== undefined) assignments.push([`${prefix}_MODEL`, model])
  }
  return assignments.sort(([left], [right]) => left.localeCompare(right))
}
