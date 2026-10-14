/**
 * dsh-bigbear-agents — registers the three bigbear-toolkit automation agent
 * presets (Web UI / API / Android) with the host dsh-agent-preset-registry and
 * injects the deployment's toolkit gateway values into the host process
 * environment so model shell calls carry them to the toolkit CLIs.
 *
 * This package is the single source of truth: the profile mounts it through a
 * vendor junction, and nothing is copied to `$DSH_HOME/.agent-presets/`, so
 * edits in this repository take effect on the next dsh restart. Persona prose
 * lives in `personas/<presetId>.md`; the capability rows shared by every
 * preset are declared once in {@link commonPlugins}; the Plugins settings page
 * (browser half) edits {@link Config} through the host config editor, whose
 * override lands in the profile patch and reloads this row.
 *
 * The bigbear toolkit ships as the sibling directory
 * `extensions/bigbear-toolkit` and is located relative to this module, so the
 * repository is relocatable; the config's `toolkitDir` and the
 * `BIGBEAR_TOOLKIT_DIR` environment variable override the sibling lookup.
 * @module dsh-bigbear-agents
 */

import { access, constants, readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { join, resolve } from 'node:path'
import { Config, deriveEnv, plainConfig, type BigbearConfig, type RawBigbearConfig } from './config.ts'

/** Loader namespace name for this plugin row. */
export const name = 'bigbear-agents'

/** Required host services. */
export const inject = ['agentPresets', 'shellEnv']

export { Config }

/** Minimal structural view of the host services this plugin touches. */
interface HostContext {
  /** Register an effect-scoped disposal on the plugin's fiber. */
  effect(dispose: () => unknown, name: string): void
  agentPresets: {
    register(definition: PresetDefinition): Promise<() => Promise<void>>
  }
  shellEnv: {
    register(contributor: {
      name: string
      variables: Readonly<Record<string, { description: string }>>
      resolve(execution: unknown): Readonly<Record<string, string>>
    }): () => void
  }
  logger: {
    info(formatter: string, ...args: readonly unknown[]): void
    warn(formatter: string, ...args: readonly unknown[]): void
  }
}

/** One preset child row as the registry accepts it. */
interface PresetRow {
  readonly id?: string
  readonly name: string
  readonly config?: unknown
  readonly disabled?: boolean
  readonly group?: boolean
  readonly isolate?: Record<string, unknown>
}

/** The registry's preset definition surface this plugin submits. */
interface PresetDefinition {
  readonly id: string
  readonly name?: string
  readonly description?: string
  readonly order?: number
  readonly plugins: readonly PresetRow[]
}

/** Directory holding one `*.md` persona per preset id. */
const PERSONAS_DIR = fileURLToPath(new URL('../personas/', import.meta.url))

/**
 * Persona placeholder replaced with the resolved skill directory at
 * registration time. Deliberately not `{{…}}`-shaped: the persona prefix is
 * itself a strict prompt template, and only registered variables may keep
 * that syntax.
 */
const SKILL_DIR_PLACEHOLDER = '{{BIGBEAR_SKILL_DIR}}'

/** Historical toolkit location used before the toolkit moved into this repository. */
const LEGACY_TOOLKIT_DIR = 'E:/Full-link-load-testing/bigbear-toolkit'

/**
 * Locate the bigbear toolkit's SKILL.md library. Resolution order: the row
 * config's `toolkitDir`, then the `BIGBEAR_TOOLKIT_DIR` environment variable,
 * then the sibling `extensions/bigbear-toolkit` of this package, then the
 * legacy standalone location. A missing toolkit fails activation loudly.
 * @param configToolkitDir - toolkit root from the row config.
 * @param env - process environment override for tests.
 * @returns absolute path of the toolkit skill directory (forward slashes).
 */
export async function resolveSkillDir(
  configToolkitDir: string | undefined = undefined,
  env: NodeJS.ProcessEnv = process.env,
): Promise<string> {
  const candidates: string[] = []
  if (configToolkitDir !== undefined && configToolkitDir.trim() !== '') {
    candidates.push(resolve(configToolkitDir.trim()))
  }
  const fromEnv = env.BIGBEAR_TOOLKIT_DIR
  if (fromEnv !== undefined && fromEnv.trim() !== '') {
    candidates.push(resolve(fromEnv.trim()))
  }
  candidates.push(
    fileURLToPath(new URL('../../bigbear-toolkit/.claude/skills/', import.meta.url)),
    join(LEGACY_TOOLKIT_DIR, '.claude', 'skills'),
  )
  for (const candidate of candidates) {
    try {
      await access(candidate, constants.R_OK)
      return candidate.replaceAll('\\', '/')
    } catch {
      // Absent — try the next candidate.
    }
  }
  throw new Error(
    'bigbear-agents: bigbear toolkit skill directory not found. '
    + 'Set toolkitDir in the Plugins settings page or BIGBEAR_TOOLKIT_DIR in the environment, '
    + `or keep extensions/bigbear-toolkit beside this package. Tried:\n  ${candidates.join('\n  ')}`,
  )
}

/**
 * Capability rows shared by every bigbear preset, mirroring the shipped
 * `standard` preset's useful subset (platform-switched shells, file tools,
 * skill discovery, background jobs, the all-in-one editor, todo, ask-user,
 * and the compaction group).
 * @param skillDir - toolkit skill directory mounted for discovery.
 * @returns fresh Cordis entry rows, one set per registration.
 */
function commonPlugins(skillDir: string): PresetRow[] {
  return [
    {
      id: 'agent-instructions',
      name: '@deepseek-ai/dsh-agent-instructions',
      config: { maxBytes: 65536 },
    },
    {
      id: 'tool-bash',
      name: '@deepseek-ai/dsh-tool-bash',
      disabled: process.platform === 'win32',
    },
    {
      id: 'tool-pwsh',
      name: '@deepseek-ai/dsh-tool-pwsh',
      disabled: process.platform !== 'win32',
    },
    { id: 'tool-fs', name: '@deepseek-ai/dsh-tool-fs' },
    {
      id: 'tool-fs-search',
      name: '@deepseek-ai/dsh-tool-fs-search',
      config: { sampleOverCapGlobResults: false },
    },
    {
      id: 'skill-filesystem',
      name: '@deepseek-ai/dsh-skill-filesystem',
      config: { customSkillDirs: [skillDir] },
    },
    { id: 'tool-skill', name: '@deepseek-ai/dsh-tool-skill' },
    { id: 'tool-jobs', name: '@deepseek-ai/dsh-tool-jobs' },
    {
      id: 'tool-todo',
      name: '@deepseek-ai/dsh-tool-todo',
      config: { allowParallelInProgress: true },
    },
    { id: 'tool-ask-user', name: '@deepseek-ai/dsh-tool-ask-user' },
    {
      id: 'compaction',
      name: 'cordis:group',
      group: true,
      isolate: { compaction: true, toolResultPruner: true },
      config: [
        { id: 'compaction-basic', name: '@deepseek-ai/dsh-compaction-basic' },
        { id: 'command-compact', name: '@deepseek-ai/dsh-command-compact' },
        {
          id: 'tool-result-pruner',
          name: '@deepseek-ai/dsh-compaction-tool-result-pruner',
          config: { thresholdChars: 8192, headChars: 4096, tailChars: 1024 },
        },
      ],
    },
  ]
}

/** Preset roster in registration order; `persona` names `personas/<id>.md`. */
const PRESETS: readonly { id: string, name: string, description: string, order: number, persona: string }[] = [
  {
    id: 'bigbear-web',
    name: 'Web 自动化',
    description: '大熊工具箱 Web UI 全链路：页面采集→测试点→用例→编排→计划→执行→报告。',
    order: 5,
    persona: 'bigbear-web.md',
  },
  {
    id: 'bigbear-api',
    name: 'API 自动化',
    description: '大熊工具箱接口全链路：mitmproxy 录制→接口文档→用例→编排→计划→执行→报告。',
    order: 6,
    persona: 'bigbear-api.md',
  },
  {
    id: 'bigbear-android',
    name: 'APP 自动化',
    description: '大熊工具箱安卓全链路：设备采集→测试点→用例→编排→计划；真机执行走 adb+AI 视觉驱动。',
    order: 7,
    persona: 'bigbear-android.md',
  },
]

/**
 * Validate a parsed Cordis entry list the same way the registry does, so a
 * malformed declaration fails loud at activation instead of at session join.
 * @param rows - parsed entry list.
 * @param at - diagnostic prefix.
 * @returns the first invalid row, or undefined.
 */
export function entryListProblem(rows: unknown, at = ''): string | undefined {
  if (!Array.isArray(rows)) {
    return at === ''
      ? 'the composition must be a top-level list of plugin rows'
      : `group ${at} must hold a list of plugin rows`
  }
  for (const [index, row] of rows.entries()) {
    const label = at === '' ? `row ${String(index + 1)}` : `${at} row ${String(index + 1)}`
    if (typeof row !== 'object' || row === null || Array.isArray(row)) {
      return `${label} is not a plugin row (expected a map with a "name")`
    }
    const record = row as Record<string, unknown>
    if (typeof record.name !== 'string' || record.name === '') {
      return `${label} names no plugin (a "name" string is required)`
    }
    if (record.group === true) {
      const problem = entryListProblem(record.config, label)
      if (problem !== undefined) return problem
    }
  }
  return undefined
}

/**
 * The gateway values reach toolkit CLIs through the `ctx.shellEnv` registry:
 * a per-execution `DSH_BIGBEAR_*` overlay merged after the subprocess scrub,
 * so credential-shaped names survive (an ambient `*_API_KEY` would be stripped
 * as a suspected leaked credential) and no global process state can be rolled
 * back by a later fiber disposal. The toolkit CLIs read the plain names and
 * fall back to these aliases.
 * @param ctx - host Cordis context.
 * @param config - plain extension config.
 */
function applyEnv(ctx: HostContext, config: BigbearConfig): void {
  const variables: Record<string, { description: string }> = {}
  const resolved: Record<string, string> = {}
  for (const [name, value] of deriveEnv(config)) {
    if (name === 'BIGBEAR_TOOLKIT_DIR') continue
    const key = `DSH_BIGBEAR_${name}`
    variables[key] = { description: `Bigbear toolkit gateway value for ${name}` }
    resolved[key] = value
  }
  ctx.shellEnv.register({
    name: 'bigbear-agents',
    variables,
    resolve: () => resolved,
  })
}

/**
 * Install the environment injection and register every bigbear preset. A
 * broken persona or row fails the plugin row's activation loudly; saving new
 * settings reloads this row, which restores the previous environment first.
 * @param ctx - host Cordis context.
 * @param config - raw row configuration with live volatile references.
 */
export async function apply(ctx: HostContext, config: RawBigbearConfig = {}): Promise<void> {
  const values = plainConfig(config)
  applyEnv(ctx, values)
  const skillDir = await resolveSkillDir(values.toolkitDir)
  for (const preset of PRESETS) {
    const personaTemplate = await readFile(join(PERSONAS_DIR, preset.persona), 'utf8')
    if (!personaTemplate.includes(SKILL_DIR_PLACEHOLDER)) {
      throw new Error(
        `bigbear-agents: persona "${preset.persona}" lost its ${SKILL_DIR_PLACEHOLDER} placeholder; `
        + 'the runner needs the concrete skill directory at runtime',
      )
    }
    const prefix = personaTemplate.replaceAll(SKILL_DIR_PLACEHOLDER, skillDir)
    const plugins: PresetRow[] = [
      {
        id: 'persona',
        name: '@deepseek-ai/dsh-persona',
        config: { prefix, text: prefix },
      },
      ...commonPlugins(skillDir),
    ]
    const rowProblem = entryListProblem(plugins, `bigbear preset ${preset.id}`)
    if (rowProblem !== undefined) throw new Error(rowProblem)
    const dispose = await ctx.agentPresets.register({
      id: preset.id,
      name: preset.name,
      description: preset.description,
      order: preset.order,
      plugins,
    })
    ctx.effect(() => dispose, `bigbear-agents: unregister preset ${preset.id}`)
  }
}
