/**
 * Advisor settings plugin, browser half. Registers the Advisor card into the
 * shell-declared `plugins.bundle.config` keyed slot (the Plugins page's
 * per-bundle configuration seat — key `dsh-advisor`, the bundle's package name
 * the page dispatches, rendered on the bundle's own page between its
 * description and its rows) and, since B2, an Advisor action into the
 * shell-declared `conversation.session.header.actions` list slot (the
 * per-session reviewer-model control, bound to the slot parent's SessionId —
 * the global card stays global-only). The card's store joins the settings
 * namespaces and the provider directory through the connection wire, and
 * keeps fresh on pushed invalidations. Export discipline: the client half
 * value-imports ONLY the frozen platform module table (CLIENT_EXTERNALS:
 * react / `@deepseek-ai/cordis` / ui-slots / ui-primitives / the documented
 * `@deepseek-ai/dsh-client-store` exemption); every other
 * `@deepseek-ai/*` import is type-only (erased at build) — values arrive via
 * cordis injection (`ctx.get('connection')`, slot inject faces, the
 * `settingsSchema` service). Mirrors the ui-models reference entry.
 */
import type { Context as ClientContext } from '@deepseek-ai/cordis';
import { type AdvisorKey } from './locales.ts';
export type { AdvisorCardInjected, AdvisorCardProps } from './advisor-card.tsx';
export type { AdvisorSessionActionInjected, AdvisorSessionActionProps } from './advisor-session.tsx';
export type { AdvisorKey } from './locales.ts';
export type { AdvisorDraft, AdvisorSessionMenuState, AdvisorSessionModelController, AdvisorSessionRpcPayload, AdvisorSessionSelection, AdvisorSessionSnapshotView, AdvisorSettingsState, AdvisorSettingsStore, ApplyFailure, ApplyState, ModelOption, ModelsEmptyReason, ProviderOption, } from './advisor-store.ts';
declare module '@deepseek-ai/dsh-client-ui-slots' {
    interface LocaleNamespaceMap {
        /** The Advisor settings card copy. */
        'settings.advisor': AdvisorKey;
    }
}
export { refreshIfLoaded } from './advisor-store.ts';
/**
 * Required services (cordis fiber inject). The target slot is declared by
 * ui-plugin-manager's apply (its `plugins` main-panel entry), whose activation
 * order relative to this one is NOT constrained; registration depends on the
 * slot through `slots.inject()`.
 *
 * rc.1 dotted-namespace contract: each client Remote namespace is a
 * child-fiber service named `remote.<ns>` (upstream `remoteServiceKey`), and
 * the traceable proxy forwards `ctx.remote.llm` / `.settings` / `.session`
 * to those context properties — consumers MUST declare the dotted names
 * here or the fiber walk throws `cannot get property "remote.llm" without
 * inject`. `remote` stays for the `$on` invalidation face; `connection` for
 * the `connection.rpc` gateway channel. Reference shape:
 * ../deepseek-harness/packages/client/ui-settings-models/src/client/index.ts.
 */
export declare const inject: string[];
/**
 * Register the Advisor card once the `plugins.bundle.config` declaration is on
 * the ledger, wire its store to the connection, and keep it fresh on every
 * pushed invalidation (settings or provider topology).
 * @param ctx - client root context.
 */
export declare function apply(ctx: ClientContext): void;
