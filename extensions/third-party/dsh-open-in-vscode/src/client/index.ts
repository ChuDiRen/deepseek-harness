/**
 * dsh-open-in-vscode client plugin: the browser half of the session "..."
 * menu "Open in VSCode" row. Mounts the openInVscode Remote namespace and
 * registers the row into the harness's `sidebar.workspaces.session.menu.item`
 * slot, with zh/en dictionaries. The row's click closes the menu and asks the
 * host to launch the editor on the session's workspace directory.
 */
import type { Context as ClientContext } from '@deepseek-ai/cordis'
import type { ISessions } from '@deepseek-ai/dsh-api-session-controller/client'
// Type-only: pulls the ui-workspace SlotMap merge (the session menu owner share).
import type {} from '@deepseek-ai/dsh-client-ui-renderer/client'
// Type-only: pulls the ui-workspace SlotMap merge (the session menu owner share).
import type {} from '@deepseek-ai/dsh-client-ui-workspace/client'
// Type-only: brings the ctx.locale Context merge.
import type {} from '@deepseek-ai/dsh-client-locale/client'
import { OPEN_IN_VSCODE_REMOTE } from './remote.ts'
import { NS, en, zh } from './locales.ts'
import { OpenInVscodeRow, type OpenInVscodeInjected } from './row.tsx'
import { adoptStyles } from './styles.ts'

/** Required services: slots, the gateway Remote face, locale, and the two snapshot catalogs. */
export const inject = ['slots', 'remote', 'locale', 'sessions']

/** The mounted openInVscode namespace service's callable face. */
interface OpenInVscodeNamespaceFace {
  open(path: string, signal?: AbortSignal): Promise<
    { ok: true; value: { opened: true } } | { ok: false; error: { code: string; message: string; details: object } }
  >
}

/**
 * Compose the session menu row.
 * @param ctx - client root context.
 */
export function apply(ctx: ClientContext): void {
  adoptStyles()
  ctx.effect(() => ctx.locale.register(NS, { zh, en }), 'dsh-open-in-vscode: dictionaries')

  // The mounted namespace handle resolves through the service store
  // (`ctx.reflect.get`), not through `ctx.remote.openInVscode`: the
  // generated-style dotted read walks the cordis fiber chain, which stops at
  // the Loader's runtime-less internal forks between a plugin entry and the
  // root fiber — the namespace service mounted under the gateway entry is
  // unreachable that way (the store path resolves it by isolation label).
  let openInVscode: OpenInVscodeNamespaceFace | undefined
  ctx.effect(async () => {
    const dispose = await ctx.remote.$mount(OPEN_IN_VSCODE_REMOTE)
    openInVscode = (ctx.reflect as unknown as { get(name: string): unknown })
      .get('remote.openInVscode') as OpenInVscodeNamespaceFace | undefined
    if (openInVscode === undefined) {
      throw new Error('dsh-open-in-vscode: the openInVscode Remote namespace did not mount')
    }
    return () => {
      openInVscode = undefined
      void dispose()
    }
  }, 'dsh-open-in-vscode: remote')

  const open = async (path: string): Promise<void> => {
    if (openInVscode === undefined) {
      throw new Error('dsh-open-in-vscode: the openInVscode Remote is not mounted')
    }
    const result = await openInVscode.open(path)
    if (!result.ok) {
      throw new Error(`open-in-vscode: ${result.error.code}: ${result.error.message}`)
    }
  }

  const sessions = ctx.get('sessions') as ISessions
  ctx.slots.inject('sidebar.workspaces.session.menu.item', () => ctx.slots.register({
    name: 'sidebar.workspaces.session.menu.item',
    id: 'open-in-vscode',
    order: 450,
    locale: NS,
    inject: (): OpenInVscodeInjected => ({ open, sessions }),
  }, OpenInVscodeRow))
}
