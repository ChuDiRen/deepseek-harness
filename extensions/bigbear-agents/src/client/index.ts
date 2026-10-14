/**
 * The bigbear extension's settings page, browser half: the toolkit directory
 * and the AI gateway values the toolkit CLIs read from the environment, over
 * the `bigbear-agents` namespace the extension's host row serves. The page
 * registers into the Plugins page's `plugins.item` slot while the Host serves
 * that namespace, so a deployment without the extension shows no trace of it.
 */

// Type-only: pulls the locale plugin's Context merge (ctx.locale).
import type {} from '@deepseek-ai/dsh-client-locale/client'
// Type-only: the ctx.configForms Context merge. Cross-plugin collaboration
// goes through the service, never a value import (client bundle purity gate).
import type {} from '@deepseek-ai/dsh-client-ui-settings/client'
// Type-only: the Plugins page's SlotMap merge (the 'plugins.item' entry).
import type {} from '@deepseek-ai/dsh-client-ui-plugin-manager/client'
import type {} from '@deepseek-ai/dsh-client-ui-renderer/client'
import type { Context as ClientContext } from '@deepseek-ai/cordis'
import { BigbearCard } from './BigbearCard.tsx'
import { BIGBEAR_NS, BigbearCardController } from './bigbear-card-controller.ts'
import { en, zh, type BigbearSettingsLocaleKey } from './locales.ts'

export type { BigbearCardProps } from './BigbearCard.tsx'
export type { BigbearCardFace, BigbearCardState, BigbearSettings } from './bigbear-card-controller.ts'
export type { BigbearSettingsLocaleKey } from './locales.ts'

declare module '@deepseek-ai/dsh-client-ui-slots' {
  interface LocaleNamespaceMap {
    /** Bigbear settings page copy. */
    'settings.bigbear': BigbearSettingsLocaleKey
  }
}

/** Dictionary namespace owned by this plugin. */
export const NS = 'settings.bigbear'

/** Required services (cordis fiber inject). */
export const inject = ['slots', 'locale', 'configForms']

/**
 * Mount the bigbear settings page while the Host serves its namespace.
 * @param ctx - the browser plugin context.
 */
export function apply(ctx: ClientContext): void {
  const t = ctx.locale.bind(NS)
  ctx.effect(() => ctx.locale.register(NS, { zh, en }), 'bigbear-agents: dictionaries')
  const card = new BigbearCardController(ctx.configForms.get(BIGBEAR_NS))
  ctx.effect(() => () => { card.dispose() }, 'bigbear-agents: form subscriptions')
  ctx.effect(() => ctx.configForms.whileServed([BIGBEAR_NS], () => ctx.slots.inject('plugins.item', () => ctx.slots.register({
    name: 'plugins.item', id: 'bigbear', order: 45, label: () => t('title'), locale: NS, inject: () => card.inject(),
  }, BigbearCard))), 'bigbear-agents: page')
}
