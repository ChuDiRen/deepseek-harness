/**
 * dsh advisor plugin — a per-session reviewer model (port of the omp
 * "advisor" subsystem). Observes the primary transcript, reviews each stepped
 * turn with an explicitly configured model, and injects severity-ranked
 * advice (nit/concern/blocker) without polluting or recursively reviewing
 * itself.
 *
 * T1 scaffold: declares the Cordis plugin entry (`name`/`inject`/`apply`).
 * T2: config contract — the Loader schema (`Config`) plus the explicit
 * provider/model gate via `resolveAdvisorConfig` (spec §5 / S4).
 * T3: session observation — subscribe `session/event`, detect stepped
 * `turn/end` (reason.kind ∈ {completed, 'max-tokens', error}, spec §4), drive
 * a per-session bounded delta renderer, and dispose per-session state on
 * `session/disposed` / `agent/disposed` (KD-5).
 * T4: the per-session advisor runtime — queue each rendered delta, drain
 * asynchronously via `ctx.llm.stream` (system prompt + delta, `purpose` left
 * unset, KD-5), extract `{note, severity}` (KD-2), and apply the failure
 * policy (retry-light → drop, 3-drop backlog flush, quota pause, permanent
 * halt — never park the primary). The emission guard (T5) gates extracted
 * notes before delivery; the delivery router (T6) routes accepted notes into
 * the primary agent (nit → inject, concern/blocker → steer, immuneTurns
 * cooldown, KD-4 agent map). T7: `/advisor` toggle/on/off/status commands
 * (registered through the conditional `ctx.inject(['commands'], ...)` child)
 * drive a per-session override consulted by the runtime gate — the commands
 * start/stop per-session runtimes without touching the persisted config.
 * T2-tui (plan dsh-advisor-tui-client-n8): `/advisor config` — a session-less
 * readback of the composed `advisor` namespace (same resolved config the web
 * card reads), never the per-session override.
 * T2 (plan dsh-advisor-tui-settings-n9): the readback's edit hint is truthful
 * — `getConfig()` reports `tuiSettingsAvailable` LIVE at render time
 * (`ctx.get('tuiSettingsSections') !== undefined`), so the hint names the TUI
 * `/settings` Advisor section as a write path exactly while the seam is
 * mounted; the readback itself stays session-less and read-only.
 * Settings (plan dsh-advisor-settings-n2): the plugin-row entry config's five
 * live fields are schema-volatile (`src/config.ts`), read live through the
 * bridge source (`src/settings.ts`); committed volatile edits (Loader
 * `loader/volatile-update`) re-apply derived state (immuneTurns /
 * maxDeltaMessages / per-session runtimes) without a restart. There is no
 * config-level `enabled` key (2026-09-26): the plugin-row enable/disable
 * toggle IS the master switch, and the per-session `/advisor` override
 * defaults to ON (`override ?? true`).
 * Config gateway (plan dsh-advisor-settings-gateway-n5): `apply` also
 * registers the host-side `AdvisorConfigGateway` (`src/gateway.ts`) — the
 * `/api/advisor/get` + `/api/advisor/set` endpoints (explicit
 * `ctx.typert.register` contribution — the host typertGateway claims
 * `ctx.typert.local` first, so link-plugin module identity never matters)
 * that make the Settings card truly readable/writable from the web client.
 *
 * @module dsh-advisor
 */
import type { Context } from '@deepseek-ai/cordis';
import type { AdvisorConfig } from './config.js';
export declare const name = "dsh-advisor";
/** Services the advisor consumes; the row loads once all are available. */
export declare const inject: string[];
/** Loader schema (schemastery, strict) — validated by the cordis Loader. */
export { Config } from './config.js';
export type { AdvisorConfig, ResolvedAdvisorConfig } from './config.js';
export declare function apply(ctx: Context, config: AdvisorConfig): void;
