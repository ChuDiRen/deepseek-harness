/**
 * dsh-at-file client plugin: the browser half of the Codex-style @file
 * mention. Mounts the atFile Remote namespace, registers the '@' trigger
 * source (floating picker landing a plain-text @path token), the
 * referenced-path dock above the composer (open/remove, gated by settings),
 * the settings section, and locale dictionaries. The Host only validates and
 * marks the chosen path; neither half reads mentioned file content.
 */
// Type-only: the ctx.remote merge and the forwarded Host-event face.
import type {} from '@deepseek-ai/dsh-api-remotes/client'
import type { SessionId } from '@deepseek-ai/dsh-api-remotes/client'
import type { Context as ClientContext } from '@deepseek-ai/cordis'
import { createSnapshotStore, type SnapshotStore } from './store.ts'
import type { InputTriggerServiceContract } from '@deepseek-ai/dsh-client-ui-input-trigger/client'
// Type-only: the conversation SlotMap / standard-kit merges for the dock seat.
import type {} from '@deepseek-ai/dsh-client-ui-conversation/client'
// Type-only: the ctx.locale Context merge.
import type {} from '@deepseek-ai/dsh-client-locale/client'
// Type-only: brings the settings.section SlotMap declaration into this program.
import type {} from '@deepseek-ai/dsh-client-ui-settings/client'
import type { AtFileSettings, AtFileSettingsUpdate, FileEntry, FileIgnoreRuleInput } from '../contract.ts'
import { AT_FILE_REMOTE } from './remote.ts'
import { createAtFileSource } from './source.ts'
import { FilesDock, type AtFileDockInjected } from './FilesDock.tsx'
import {
  AtFileSection,
  type AtFileSectionInjected,
  type AtFileSectionViewState,
} from './SettingsSection.tsx'
import { NS, en, zh } from './locales.ts'
import { adoptStyles } from './styles.ts'
import { FolderNavigator, type FolderNavigatorInjected } from './FolderNavigator.tsx'
import {
  defaultAtFileSettings,
  ignoreFilesSettingsKey,
  normalizeIgnoreFiles,
  normalizeWorkspaceIgnoreFiles,
  workspacePathKey,
} from '../defaults.ts'

/** Required services: picker pipeline, session projection, carrier, Remote face, slots, and locale. */
export const inject = ['inputTriggers', 'sessions', 'connection', 'remote', 'slots', 'locale']

/** The mounted atFile namespace service's callable face. */
interface AtFileNamespaceFace {
  search(sessionId: SessionId, signal?: AbortSignal): Promise<{ ok: true; value: readonly FileEntry[] } | { ok: false; error: { code: string; message: string; details: object } }>
  getSettings(): Promise<{ ok: true; value: AtFileSettings } | { ok: false; error: { code: string; message: string; details: object } }>
  updateSettings(update: AtFileSettingsUpdate): Promise<{ ok: true; value: AtFileSettings } | { ok: false; error: { code: string; message: string; details: object } }>
}

/** Session lookup face shared by the 0.1.1 Runtime and 0.1.2 Session Controller. */
interface SessionsFace {
  scope(sessionId: SessionId): unknown | undefined
}

/** Slot registry surface common to the pre- and post-0.1.2 client assemblies. */
interface SlotsFace {
  inject(name: string, factory: () => unknown): unknown
  register(entry: object, component: unknown): unknown
}

/** 0.1.1's direct Host API, retained as the open-path fallback. */
interface LegacyConnectionFace {
  readonly api?: {
    readonly host?: {
      openPath(request: { path: string }): Promise<{
        result: { ok: true } | { ok: false; error: { message: string } }
      }>
    }
  }
}

/** 0.1.2's generated Session Remote open-path surface. */
interface SessionOpenPathFace {
  openWorkspacePath?(request: { path: string }): Promise<{
    ok: true
    value: { opened: true }
  } | {
    ok: false
    error: { message: string }
  }>
}

/**
 * Compose the @file surface.
 * @param ctx - client root context.
 */
export function apply(ctx: ClientContext): void {
  adoptStyles()
  ctx.effect(() => ctx.locale.register(NS, { zh, en }), 'dsh-at-file: dictionaries')

  const scope = createSnapshotStore({ value: defaultAtFileSettings() })
  const settingsViewState: AtFileSectionViewState = { filterScope: 'global', selectedWorkspace: '' }
  let settingsGeneration = 0
  let settingsTail: Promise<void> = Promise.resolve()

  const reportSettingsError = (
    operation: 'read' | 'update',
    error: { code: string; message: string } | unknown,
  ): void => {
    if (typeof error === 'object' && error !== null && 'code' in error && 'message' in error) {
      const remoteError = error as { code: string; message: string }
      console.error(`[dsh-at-file] settings ${operation} failed: ${remoteError.code}: ${remoteError.message}`)
      return
    }
    console.error(`[dsh-at-file] settings ${operation} failed:`, error)
  }

  // The mounted namespace handle resolves through the service store
  // (`ctx.reflect.get`), not through `ctx.remote.atFile`: the generated-style
  // dotted read walks the cordis fiber chain, which stops at the Loader's
  // runtime-less internal forks between a plugin entry and the root fiber —
  // the namespace service mounted under the gateway entry is unreachable
  // that way (the store path resolves it by isolation label instead).
  let atFile: AtFileNamespaceFace | undefined
  const loadSettings = async (): Promise<void> => {
    const remote = atFile
    if (remote === undefined) return
    const generation = ++settingsGeneration
    try {
      const result = await remote.getSettings()
      if (atFile !== remote || generation !== settingsGeneration) return
      if (!result.ok) {
        reportSettingsError('read', result.error)
        return
      }
      scope.set({ value: result.value })
    } catch (error) {
      if (atFile === remote && generation === settingsGeneration) reportSettingsError('read', error)
    }
  }

  const updateSettings = (update: AtFileSettingsUpdate): Promise<void> => {
    const operation = settingsTail.then(async () => {
      const remote = atFile
      if (remote === undefined) {
        reportSettingsError('update', new Error('the atFile Remote is not mounted'))
        return
      }
      const generation = ++settingsGeneration
      try {
        const result = await remote.updateSettings(update)
        if (atFile !== remote || generation !== settingsGeneration) return
        if (!result.ok) {
          reportSettingsError('update', result.error)
          return
        }
        scope.set({ value: result.value })
      } catch (error) {
        if (atFile === remote && generation === settingsGeneration) reportSettingsError('update', error)
      }
    })
    settingsTail = operation.catch(
      /* v8 ignore next -- every Remote and publication failure is contained inside operation. */
      () => {},
    )
    return operation
  }

  ctx.effect(async () => {
    const dispose = await ctx.remote.$mount(AT_FILE_REMOTE)
    atFile = (ctx.reflect as unknown as { get(name: string): unknown }).get('remote.atFile') as AtFileNamespaceFace | undefined
    if (atFile === undefined) {
      throw new Error('dsh-at-file: the atFile Remote namespace did not mount')
    }
    await loadSettings()
    return () => {
      settingsGeneration += 1
      atFile = undefined
      void dispose()
    }
  }, 'dsh-at-file: remote')

  const connection = ctx.get('connection') as LegacyConnectionFace
  const inputTriggers = ctx.get('inputTriggers') as InputTriggerServiceContract
  const sessions = ctx.get('sessions') as unknown as SessionsFace
  const slots = (ctx as unknown as { slots: SlotsFace }).slots
  const t = ctx.locale.bind(NS)

  const EMPTY_INDEX: readonly string[] = Object.freeze([])
  const indexScopes = new Map<SessionId, SnapshotStore<readonly string[]>>()
  const indexScopeOf = (sessionId: SessionId): SnapshotStore<readonly string[]> => {
    const existing = indexScopes.get(sessionId)
    if (existing !== undefined) return existing
    const created = createSnapshotStore<readonly string[]>(EMPTY_INDEX)
    indexScopes.set(sessionId, created)
    return created
  }
  // Per-session relative → entry maps back the dock's validation and open action.
  const entriesBySession = new Map<SessionId, ReadonlyMap<string, FileEntry>>()
  const search = async (sessionId: SessionId, signal: AbortSignal): Promise<readonly FileEntry[]> => {
    if (atFile === undefined) throw new Error('dsh-at-file: the atFile Remote is not mounted')
    const result = await atFile.search(sessionId, signal)
    if (!result.ok) {
      entriesBySession.delete(sessionId)
      indexScopeOf(sessionId).set(EMPTY_INDEX)
      throw new Error(`search failed: ${result.error.code}: ${result.error.message}`)
    }
    entriesBySession.set(sessionId, new Map(result.value.map(entry => [entry.relative, entry])))
    indexScopeOf(sessionId).set(result.value.map(entry => entry.relative))
    return result.value
  }

  const { source, invalidateAll } = createAtFileSource({ search })
  const clearIndexes = (): void => {
    entriesBySession.clear()
    for (const index of indexScopes.values()) index.set(EMPTY_INDEX)
  }
  // Reconnect may have rebuilt the host: cached indexes and path maps die with it.
  ctx.on('connection/reset', () => {
    invalidateAll()
    clearIndexes()
    void loadSettings()
  })
  // The settings switch gates the picker live. The schema default applies
  // until the first Host read, then every returned update replaces the snapshot.
  let sourceRegistered = false
  /* v8 ignore next -- replaced before use whenever a source is registered. */
  let sourceDispose = (): void => {}
  let ignoreFilesKey: string | undefined
  const syncSource = (): void => {
    const value = scope.getSnapshot().value
    const enabled = value.enabled
    const nextIgnoreFilesKey = ignoreFilesSettingsKey(value)
    if (ignoreFilesKey !== undefined && ignoreFilesKey !== nextIgnoreFilesKey) {
      invalidateAll()
      clearIndexes()
    }
    ignoreFilesKey = nextIgnoreFilesKey
    if (enabled && !sourceRegistered) {
      sourceDispose = inputTriggers.registerSource(source)
      sourceRegistered = true
    } else if (!enabled && sourceRegistered) {
      sourceDispose()
      /* v8 ignore next -- keeps teardown callable after the live registration is removed. */
      sourceDispose = () => {}
      sourceRegistered = false
    }
  }
  ctx.effect(() => {
    syncSource()
    const off = scope.subscribe(syncSource)
    return () => {
      off()
      sourceDispose()
    }
  }, 'dsh-at-file: source (settings-gated)')

  const openPath = (path: string): void => {
    const sessionRemote = (ctx.remote as unknown as { session?: SessionOpenPathFace }).session
    if (sessionRemote?.openWorkspacePath !== undefined) {
      void sessionRemote.openWorkspacePath({ path }).then((result) => {
        if (!result.ok) console.error('[dsh-at-file] open failed:', result.error.message)
      }, (error: unknown) => { console.error('[dsh-at-file] open failed:', error) })
      return
    }
    const legacyOpen = connection.api?.host?.openPath
    if (legacyOpen === undefined) {
      console.error('[dsh-at-file] open failed: no compatible Host open-path service')
      return
    }
    void legacyOpen({ path }).then((response) => {
      if (!response.result.ok) console.error('[dsh-at-file] open failed:', response.result.error.message)
    }, (error: unknown) => { console.error('[dsh-at-file] open failed:', error) })
  }

  const openRelative = (sessionId: SessionId, relative: string): void => {
    const entry = entriesBySession.get(sessionId)?.get(relative)
    if (entry === undefined) {
      console.error('[dsh-at-file] open failed: no index entry for', relative)
      return
    }
    openPath(entry.path)
  }

  slots.inject('conversation.input.dock', () => slots.register({
    name: 'conversation.input.dock',
    id: 'at-file',
    order: 20,
    locale: NS,
    inject: (sessionId: SessionId): AtFileDockInjected => ({
      onOpen: relative => { openRelative(sessionId, relative) },
      hooks: { scope, index: indexScopeOf(sessionId) },
    }),
  }, FilesDock))

  slots.inject('conversation.input.overlay', () => slots.register({
    name: 'conversation.input.overlay',
    id: 'at-file-folder-navigation',
    order: 1,
    inject: (sessionId: SessionId): FolderNavigatorInjected => {
      const actx = sessions.scope(sessionId)
      if (actx === undefined) throw new Error(`dsh-at-file: session "${String(sessionId)}" has no client scope`)
      return { controller: inputTriggers.sessionOf(actx as ClientContext), hooks: { scope } }
    },
  }, FolderNavigator))

  slots.inject('settings.section', () => slots.register({
    name: 'settings.section',
    id: 'at-file',
    order: 55,
    label: () => t('nav'),
    locale: NS,
    inject: (): AtFileSectionInjected => ({
      hooks: { scope },
      viewState: settingsViewState,
      setEnabled: async (enabled: boolean) => { await updateSettings({ field: 'enabled', value: enabled }) },
      setIgnorePastedMentions: async (ignorePastedMentions: boolean) => {
        await updateSettings({ field: 'ignorePastedMentions', value: ignorePastedMentions })
      },
      setIgnoreFiles: async (ignoreFiles: readonly FileIgnoreRuleInput[]) => {
        await updateSettings({ field: 'ignoreFiles', value: [...ignoreFiles] })
      },
      setWorkspaceIgnoreFiles: async (workspace: string, ignoreFiles: readonly FileIgnoreRuleInput[]) => {
        const current = normalizeWorkspaceIgnoreFiles(scope.getSnapshot().value.workspaceIgnoreFiles)
        const target = workspacePathKey(workspace)
        const next = current.filter(entry => workspacePathKey(entry.workspace) !== target)
        const normalized = normalizeIgnoreFiles(ignoreFiles)
        if (normalized.length > 0) next.push({ workspace, ignoreFiles: normalized })
        await updateSettings({ field: 'workspaceIgnoreFiles', value: next })
      },
    }),
  }, AtFileSection))
}
