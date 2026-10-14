/**
 * Advisor settings card (plan dsh-advisor-plugin-config-card-ux, task 1;
 * flat rebuild 2026-09-26 — plan dsh-advisor-web-config-flat-n10): the card
 * registered into the Plugins page's `plugins.bundle.config` keyed slot (key
 * `dsh-advisor` — the bundle's package name the page dispatches). It keeps
 * the n5 gateway channel — the store reads/writes the advisor config through
 * `/api/advisor/get` + `/api/advisor/set` (KD-G3) — while the layout is the
 * official settings-page language: NO collapsible box. The page already
 * renders the plugin title/description above the card (the `locale/*.json`
 * meta files the host resolves per UI language), so the fields tile directly
 * beneath it: provider select, model select (ALWAYS rendered — there is no
 * enable checkbox to gate them; the config-level `enabled` switch was removed
 * and the plugin-row toggle is the master switch), system-prompt textarea,
 * and the paired `immuneTurns`/`maxDeltaMessages` numbers (joined by
 * `maxTokens`, issue #102) plus the `proseFallback` checkbox; then the footer
 * with the failed message + Discard/Save carrying the upstream disabled
 * semantics — save = `!dirty || invalid || saving`, discard = `!dirty ||
 * saving` (KD-U1, Global Constraints). Save additionally carries `!writable`
 * and the store refuses writes outright in read-only environments (W-1, qc2
 * fix wave) — see the disabled-term comment in the ready branch. The former
 * collapsible chrome (header button, rotating chevron, dirty "unsaved" pill,
 * card-local disclosure state) is gone with the switch it mirrored: nothing
 * is hidden, so nothing needs disclosure state, and the readOnly / saved /
 * error / namespaceUnavailable notices are flat and always-on (the derived-
 * open semantics they used to ride — AC-1/AC-3 — have no surface left).
 *
 * The form behavior is unchanged from the card-form plan: provider/model
 * selects limited to the system-configured providers and their models
 * (KD-S2), the required-pair gate (KD-S4, also enforced in the store), and
 * Save writing the advisor config through the gateway channel (store →
 * `connection.rpc.call('/api', 'advisor/set', { patch })`). Discard rewinds
 * the draft to the last-known host config (client-side only — no gateway
 * write). The textarea's placeholder IS the built-in reviewer prompt
 * (`DEFAULT_ADVISOR_SYSTEM_PROMPT` — same-package import, a pure string
 * constant the bundler inlines; SSOT stays `src/prompts.ts`), so the field
 * shows exactly what an empty prompt inherits; the "leave empty" hint rides
 * below it.
 *
 * Presentation follows the official settings-form values via
 * `advisor-card.module.css` (12px field padding, 0.5px hairline separators,
 * 34px inputs, dark solid Save) — every color resolves through a
 * `--dsw-alias-*` token so the card adapts to the light/dark theme.
 *
 * A stored provider/model that is no longer among the current options
 * surfaces warning copy (`staleProvider`/`staleModel`) instead of blocking
 * Save: the user keeps the stored value (it still applies as stored) or
 * reselects — the host gate rejects truly invalid configurations on write.
 * Clearing a number input leaves the field empty; the store then omits that
 * key from the apply patch (the stored value stays unchanged).
 *
 * Degraded/error states keep the flat layout (KD-U3): the config-channel
 * notice or the load error + retry render as always-on blocks — a card that
 * cannot render its form shows that state on every render, including through
 * a background refresh of a degraded card (the store's latched `degraded`
 * keeps the notice up while `status === 'loading'`, qc1 S-2 fix wave).
 * A healthy card holds its form through the same refresh window (fields
 * disabled — the store keeps the last settled providers/draft/applyState
 * until the ready update), so a post-apply reload never unmounts the form or
 * blinks the saved notice away.
 * When the last load could not reach the `advisor.get` gateway endpoint (the
 * gateway channel is down or not ready on this host), the form is replaced
 * by the `namespaceUnavailable` notice and Save is never offered, so the
 * page never presents a writable-looking editor whose writes the host would
 * refuse (KD-G5). Note: without a settings service the gateway's `get` still
 * succeeds (entry fallback — the form renders), while `set` fails with a
 * clear "settings service is unavailable" error; the notice covers channel
 * unreachability, not the no-settings-service case.
 */
import type { ReactNode } from 'react';
import type { InjectFace, PropsLocale, PropsRuntime } from '@deepseek-ai/dsh-client-ui-slots';
import type { SnapshotStore } from '@deepseek-ai/dsh-client-store';
import type { AdvisorSettingsState, AdvisorSettingsStore } from './advisor-store.ts';
/** Injected dependencies of {@link AdvisorCard} (slot `inject`). The `hooks`
 * compartment carries the bare snapshot store; the slot renderer binds it to
 * the `useSnapshot` selector hook the component consumes (host renderer contract). */
export interface AdvisorCardInjected {
    /** The card store (loaded on mount, refreshed on pushed invalidations). */
    controller: AdvisorSettingsStore;
    /** Bare snapshot source the renderer binds as `useSnapshot`. */
    hooks: {
        snapshot: SnapshotStore<AdvisorSettingsState>;
    };
}
/**
 * Props the renderer binds for the card: the `plugins.bundle.config` runtime
 * share (the owner passes the `view` the page asks for — this seat is
 * `page`-only), the framework-synthesized `t` seat for the declared
 * `settings.advisor` namespace (KD-1 — `t` is NOT part of the inject face),
 * and the registrant's business face.
 */
export type AdvisorCardProps = PropsRuntime<'plugins.bundle.config'> & PropsLocale<'settings.advisor'> & InjectFace<AdvisorCardInjected>;
/**
 * Render the advisor card inside its bundle's configuration section on the
 * Plugins page — flat: the notices, the form, and the footer tile directly
 * under the page's plugin title/description, with no chrome of our own.
 * @param props - slot-delivered injected dependencies and the synthesized t seat.
 * @returns the card.
 */
export declare function AdvisorCard(props: AdvisorCardProps): ReactNode;
