/** The bigbear page's staged form over the extension's served config. */

import type { SnapshotStore } from '@deepseek-ai/dsh-client-store'
import {
  SettingsFormModel, settingsTextField,
  type SettingsFieldState, type SettingsFormActions, type SettingsFormScope, type SettingsFormShell,
} from '@deepseek-ai/dsh-client-ui-primitives'

/** Profile entry id of the bigbear extension row. */
export const BIGBEAR_NS = 'bigbear-agents'

/** The bigbear fields this page edits — the whole served schema by design. */
export interface BigbearSettings {
  toolkitDir?: string
  gatewayApiKey?: string
  gatewayBaseUrl?: string
  runnerModel?: string
  webModel?: string
  androidModel?: string
  visionModel?: string
}

/** What the bigbear page renders. */
export interface BigbearCardState extends SettingsFormShell {
  toolkitDir: SettingsFieldState
  gatewayApiKey: SettingsFieldState
  gatewayBaseUrl: SettingsFieldState
  runnerModel: SettingsFieldState
  webModel: SettingsFieldState
  androidModel: SettingsFieldState
  visionModel: SettingsFieldState
}

/** The registration-side face the bigbear page's slot entry injects. */
export interface BigbearCardFace extends SettingsFormActions {
  hooks: {
    /** Page snapshot bound by the renderer as useBigbearCard. */
    bigbearCard: SnapshotStore<BigbearCardState>
  }
}

const FIELDS = [
  'toolkitDir', 'gatewayApiKey', 'gatewayBaseUrl',
  'runnerModel', 'webModel', 'androidModel', 'visionModel',
] as const

/**
 * Bridges the extension entry's form onto the page's staged form. The served
 * schema nests gateway values under `gateway`; the page flattens them to one
 * card, so field names map onto config paths here.
 */
export class BigbearCardController {
  private readonly form: SettingsFormModel<Record<string, string | undefined>>
  private readonly store: SnapshotStore<BigbearCardState>

  /** @param scope - the shared configuration form of the bigbear extension entry. */
  constructor(scope: SettingsFormScope<Record<string, string | undefined>>) {
    this.form = new SettingsFormModel(scope, FIELDS.map(field => settingsTextField(field)))
    this.store = this.form.bind(() => this.projection())
  }

  private projection(): BigbearCardState {
    const shell = this.form.shell()
    const fields = Object.fromEntries(FIELDS.map(field => [field, this.form.field(field)]))
    return { ...shell, ...fields } as BigbearCardState
  }

  /**
   * Build the face the page's slot registration injects.
   * @returns the page's snapshot and its form actions.
   */
  inject(): BigbearCardFace {
    return { hooks: { bigbearCard: this.store }, ...this.form.actions() }
  }

  /** Release the form subscription. */
  dispose(): void { this.form.dispose() }
}
