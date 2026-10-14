/**
 * The `at-file` settings face: the durable enable switch, pasted-mention
 * policy, and file-name filters. 0.2 settings pages generate from the
 * plugin's Config schema, so the fields ride the entry's `Config`; this
 * store serves the runtime live reads from an in-memory overlay and
 * persists every write into the entry's profile Config through the
 * settings forms service, keeping the page, restarts, and the running
 * plugin consistent.
 */
import type { Context } from '@deepseek-ai/cordis'
import type { AtFileSettings } from './contract.ts'

/** The profile entry id whose Config section carries the at-file settings. */
export const AT_FILE_ENTRY_ID = 'dsh-at-file'

/** The settings-forms service face the store persists through. */
interface SettingsFormsFace {
  update(ns: string, patch: object): Promise<void>
}

/**
 * Live settings store over the entry Config.
 * @param ctx - the plugin context reading the settings forms service.
 * @param initial - settings resolved from the entry Config at load.
 */
export class AtFileSettingsStore {
  private value: AtFileSettings
  constructor(private readonly ctx: Context, initial: AtFileSettings) {
    this.value = initial
  }

  /** Current live value. */
  get(): AtFileSettings {
    return this.value
  }

  /**
   * Apply one patch immediately and persist it into the entry's profile Config.
   * @param patch - settings fields to change.
   * @returns the merged live value.
   */
  async update(patch: Partial<AtFileSettings>): Promise<AtFileSettings> {
    this.value = { ...this.value, ...patch }
    const forms = this.ctx.get('settings') as SettingsFormsFace | undefined
    if (forms === undefined) {
      this.ctx.logger.warn('dsh-at-file: settings service unavailable; the change is session-only')
      return this.value
    }
    try {
      await forms.update(AT_FILE_ENTRY_ID, patch)
    } catch (error) {
      this.ctx.logger.warn('dsh-at-file: settings persistence failed: %s', String(error))
    }
    return this.value
  }
}
