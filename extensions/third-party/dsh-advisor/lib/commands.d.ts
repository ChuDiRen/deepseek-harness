/**
 * T7 — slash commands (spec §2 S5, §6 status surface, §8.5 KD-5 seed-on-enable,
 * §5.3 session model override).
 *
 * One `/advisor` command is registered (through {@link registerAdvisorCommands})
 * with these forms:
 *
 * - `/advisor`           — toggle the per-session override (on ↔ off);
 * - `/advisor on`        — enable the advisor for this session;
 * - `/advisor off`       — disable the advisor for this session;
 * - `/advisor status`    — report the per-session status surface;
 * - `/advisor config`    — show the composed advisor config (global defaults);
 * - `/advisor model`     — show the effective reviewer route + source;
 * - `/advisor model set <provider> <model>` — pin an atomic pair for the
 *   invoking session only (validated via `resolveModelInfo`, 60 s, no retry);
 * - `/advisor model reset` — re-inherit the current global defaults;
 * - anything else        — usage text.
 *
 * All forms are **session-scoped and ephemeral**: they drive per-session
 * overrides ({@link AdvisorSessionOverrides} — the enable flag and the
 * runtime-only atomic model pair, fenced by per-session generations) that the
 * runtime gate and the effective resolver consult, so no command ever touches
 * the persisted config (spec §4 mapping, §5.3 — matches omp `/advisor`
 * semantics). Enabling a session whose effective route has no complete pair
 * starts no model call: the S4 explicit gate (spec §5.2) applies AFTER session
 * resolution, and the status/on text explains the disabled-with-reason.
 *
 * The module is cordis-free (pure parse + render + registration contract), so
 * it is unit-testable with a fake command registry and a fake controller;
 * `index.ts` binds it into the plugin through the conditional
 * `ctx.inject(['commands'], ...)` child (commands must NOT join the top-level
 * inject list — T1 fix).
 *
 * @module dsh-advisor/commands
 */
import type { CommandDefinition } from '@deepseek-ai/dsh-commands';
import type { Agent } from '@deepseek-ai/dsh-agent';
import type { AdvisorRuntimeStatus } from './advisor-runtime.js';
/** The parsed form of the exact text following `/advisor`. */
export type AdvisorCommand = {
    readonly kind: 'toggle';
} | {
    readonly kind: 'on';
} | {
    readonly kind: 'off';
} | {
    readonly kind: 'status';
} | {
    readonly kind: 'config';
} | {
    readonly kind: 'model';
    readonly sub: AdvisorModelCommand;
} | {
    readonly kind: 'usage';
};
/**
 * The parsed form of the text following `/advisor model` (spec §5.3 B1
 * surface): bare → show, `set <provider> <model>` → set (parsed by
 * {@link parseModelSetArgs}), `reset` → reset, anything else → model usage.
 */
export type AdvisorModelCommand = {
    readonly kind: 'show';
} | {
    readonly kind: 'set';
    readonly args: string;
} | {
    readonly kind: 'reset';
} | {
    readonly kind: 'usage';
};
/**
 * Parse the text following `/advisor model`. `set` keeps its RAW remainder —
 * the atomic-pair validation ({@link parseModelSetArgs}) owns it, because the
 * set flow reports a precise rejection reason in the command reply.
 */
export declare function parseAdvisorModelCommand(rawInput: string): AdvisorModelCommand;
/**
 * The result of parsing `/advisor model set` arguments into the atomic pair
 * (spec §5.3 pair validation).
 */
export type ModelSetArgs = {
    readonly ok: true;
    readonly provider: string;
    readonly model: string;
} | {
    readonly ok: false;
    readonly reason: string;
};
/**
 * Validate one structured `{provider, model}` pair (spec §5.3 pair validation):
 * both values must be strings that are non-empty after outer trim, with no
 * whitespace INSIDE either identifier (the same rules `parseModelSetArgs`
 * enforces for the CLI form — one validation source shared by the command face
 * and the web gateway face, so the two surfaces can never diverge). Outer
 * whitespace is trimmed; case is retained; model ids containing `/` are fine
 * (`/` is not whitespace). Never throws — every rejection carries a
 * user-facing reason.
 */
export declare function parseModelPair(provider: unknown, model: unknown): ModelSetArgs;
/**
 * Validate `/advisor model set <provider> <model>` arguments (spec §5.3):
 * exactly two arguments; outer whitespace trimmed; case retained; blank or
 * partial pairs, extra fields (a third argument), and whitespace-containing
 * identifiers rejected. Separate args are what allow model ids containing
 * `/`. Never throws — every rejection carries a user-facing reason.
 */
export declare function parseModelSetArgs(rawArgs: string): ModelSetArgs;
/**
 * Parse the text following `/advisor` (the dsh `parseCommand` split already
 * yields `rawInput` including the separator whitespace, e.g. `' on'` for
 * `/advisor on`). Subcommands match exactly after trimming — same
 * case-sensitivity as dsh command names; anything else is a usage error.
 */
export declare function parseAdvisorCommand(rawInput: string): AdvisorCommand;
/**
 * The runtime-only reviewer model override for one session (spec §5.3) — an
 * **atomic** `{ provider, model }` pair. It never merges with the global
 * pair (no half-pairs) and is never persisted: it lives in memory for the
 * live-session lifetime and is cleared by reset, dispose, owner teardown,
 * cold resume, or restart.
 */
export interface AdvisorModelPair {
    readonly provider: string;
    readonly model: string;
}
/**
 * Where a session's effective reviewer route comes from (spec §5.3):
 * `session` = a pinned `AdvisorModelPair`, `global` = the composed global
 * advisor pair.
 */
export type AdvisorModelSource = 'session' | 'global';
/**
 * The per-session overrides consulted by the runtime gate and the effective
 * resolver (`src/index.ts`):
 *
 * - enable: `override ?? true` (`/advisor on|off|toggle`) — there is no
 *   config-level switch anymore (2026-09-26: the config `enabled` key was
 *   removed; a running plugin row IS enabled, and the row toggle turns every
 *   session off at once), so the default is ON and only an explicit
 *   `/advisor off` override suppresses a session;
 * - model: the complete session pair ?? the composed global pair — the pair
 *   is atomic, so the two levels are never merged (spec §5.3);
 * - generation: a per-session counter that fences async model work — a newer
 *   set/reset supersedes unresolved older work, and dispose/owner teardown
 *   (which wipe the counter) can never be undone by a delayed completion.
 *
 * Nothing here touches the persisted config. All maps are keyed by session id
 * and hold only LIVE sessions' state: `clear` runs on `agent/disposed` /
 * `session/disposed`, `clearModel` runs on reset (an emptied entry is
 * removed), and `disposeAll` runs on owner teardown — state stays
 * O(live overrides), with no historical SessionId accumulation and no
 * TTL/GC job.
 */
export declare class AdvisorSessionOverrides {
    private readonly enables;
    private readonly models;
    private readonly generations;
    /** Effective switch for one session: `override ?? true` (a running row is on). */
    effective(sessionId: string): boolean;
    /** Set the enable override for one session. */
    set(sessionId: string, enabled: boolean): void;
    /** The session's pinned model pair, or `undefined` when it inherits. */
    model(sessionId: string): AdvisorModelPair | undefined;
    /** Commit the (already validated) atomic pair for one session. */
    setModel(sessionId: string, pair: AdvisorModelPair): void;
    /**
     * Remove a session's model pin (reset-to-inherit). @returns `true` when a
     * pin was actually removed — `false` means the session was already
     * inheriting (a reset no-op).
     */
    clearModel(sessionId: string): boolean;
    /**
     * Bump and return the session's model-work generation — the fence token an
     * async validation captures; any later `beginModelGeneration` (a newer
     * set/reset) or any state wipe makes the captured value stale.
     */
    beginModelGeneration(sessionId: string): number;
    /** The session's current model-work generation (0 before the first). */
    modelGeneration(sessionId: string): number;
    /** Sessions holding ANY per-session override state (enable and/or pair). */
    overrideSessionIds(): IterableIterator<string>;
    /**
     * Drop ALL per-session state for one session (enable + pair + generation) —
     * the `agent/disposed` / `session/disposed` cleanup. Wiping the generation
     * invalidates any in-flight validation for the session (captured values are
     * ≥ 1 and can never again match the post-clear default 0).
     */
    clear(sessionId: string): void;
    /**
     * Owner teardown: wipe every session's state. Pending validations for any
     * session become stale exactly like a per-session `clear` — a delayed
     * completion can never commit after the owner is gone.
     */
    disposeAll(): void;
}
/**
 * Per-session status snapshot consumed by `/advisor status`. Built by the
 * wiring (`index.ts`) from the resolved config, the session's runtime, and
 * the override state.
 */
export interface AdvisorSessionStatus {
    /** Effective switch for this session (`override ?? true` — row on = on). */
    readonly enabled: boolean;
    /**
     * Present iff the session is effectively enabled but the S4 explicit gate
     * blocks model calls (provider/model missing or empty) — disabled-with-
     * reason (spec §5.2).
     */
    readonly disabledReason?: string;
    /** Configured provider route (shown even while disabled — spec §5.2). */
    readonly provider?: string;
    /** Configured model id (shown even while disabled — spec §5.2). */
    readonly model?: string;
    /**
     * Where the reported route comes from (spec §5.3) — present iff
     * `provider`/`model` are: `session` = the session's pinned pair,
     * `global` = the composed global advisor pair.
     */
    readonly modelSource?: AdvisorModelSource;
    /** The session's runtime status; `disabled` when no runtime exists. */
    readonly runtimeStatus: AdvisorRuntimeStatus;
    /** Deltas waiting to be drained (bounded backlog, spec §6). */
    readonly pendingCount: number;
    /** Epoch-ms of the last accepted note; undefined before the first (T4). */
    readonly lastActivityAt?: number;
    /**
     * Empty replies dropped since the runtime was created (KD-I3, issue #102) —
     * the classic case is a thinking model exhausting the token budget (empty
     * body, finish: max-tokens). 0 for a session without a live runtime.
     */
    readonly emptyReplies: number;
    /**
     * Replies dropped since the runtime was created because they carried a body
     * but no parseable JSON note and the opt-in prose fallback did not rescue
     * them (KD-I3, issue #102). 0 for a session without a live runtime.
     */
    readonly unparsedReplies: number;
    /** Epoch-ms of the last empty-reply drop; undefined before the first. */
    readonly lastEmptyReplyAt?: number;
    /** Epoch-ms of the last unparsed-reply drop; undefined before the first. */
    readonly lastUnparsedReplyAt?: number;
}
/**
 * Render the status surface. Kept minimal and truthful: state, the S4 reason
 * when the gate blocks, the resolved provider/model, the runtime status with
 * the pending count, the last accepted-note activity (ISO, or `never`), and —
 * ONLY when a drop counter is non-zero (KD-I3, issue #102) — one `Dropped:`
 * line with the per-class counts, the ISO timestamp of each class's last drop
 * when present, and the same repair hints the runtime's warn-once logs carry
 * (empty → raise maxTokens; unparsed → enable proseFallback). The zero-drop
 * output stays byte-identical to the pre-issue-#102 surface.
 */
export declare function advisorStatusText(status: AdvisorSessionStatus): string;
/** Validation deadline for one `/advisor model set` lookup (60 s — matches
 * the runtime's whole-call deadline default, `src/advisor-runtime.ts`). */
export declare const ADVISOR_MODEL_VALIDATION_TIMEOUT_MS = 60000;
/** The effective reviewer route for one session (spec §5.3). */
export interface AdvisorModelRoute {
    readonly provider?: string;
    readonly model?: string;
    /** `session` when the effective pair is the session's pin, else `global`. */
    readonly source: AdvisorModelSource;
}
/** Outcome of one `/advisor model set` attempt (spec §5.3 validation + fencing). */
export type AdvisorSetModelOutcome = {
    readonly kind: 'committed';
    readonly status: AdvisorSessionStatus;
} | {
    readonly kind: 'unchanged';
    readonly status: AdvisorSessionStatus;
} | {
    readonly kind: 'rejected';
    readonly reason: string;
} | {
    readonly kind: 'failed';
    readonly reason: string;
} | {
    readonly kind: 'cancelled';
} | {
    readonly kind: 'superseded';
} | {
    readonly kind: 'gone';
};
/** Outcome of one `/advisor model reset`. */
export type AdvisorResetModelOutcome = {
    readonly kind: 'reset';
    readonly status: AdvisorSessionStatus;
} | {
    readonly kind: 'noop';
};
/**
 * Render the `/advisor model` surface: the effective pair, its source, and
 * the live-session lifetime (spec §5.3 — the reply must name the lifetime).
 */
export declare function advisorModelText(route: AdvisorModelRoute): string;
/** Render one `/advisor model set` outcome. */
export declare function modelSetText(outcome: AdvisorSetModelOutcome): string;
/** Render one `/advisor model reset` outcome. */
export declare function modelResetText(outcome: AdvisorResetModelOutcome): string;
/**
 * Composed-config surface consumed by `/advisor config`. **Session-less by
 * design**: the wiring builds it from the same resolved config the web card
 * reads (`/api/advisor/get` — the live entry config, with the hard gate
 * applied), so a per-session `/advisor off` override can never misreport the
 * persisted config. Runtime state stays owned by the status surface
 * (`AdvisorSessionStatus`); config and status are separate.
 */
export interface AdvisorComposedConfig {
    /** Post-gate pair flag — not the per-session override. */
    readonly enabled: boolean;
    /** Present iff the composed config is disabled by the explicit gate. */
    readonly disabledReason?: string;
    /** Composed provider route (shown even while disabled — spec §5.2). */
    readonly provider?: string;
    /** Composed model id (shown even while disabled — spec §5.2). */
    readonly model?: string;
    /** Cooldown after a delivered interrupt (spec §6). */
    readonly immuneTurns: number;
    /** Delta window; 0 = unbounded (KD-3). */
    readonly maxDeltaMessages: number;
    /**
     * Token budget for one advisor call (KD-I1, issue #102). Present when the
     * composed read carries the key (the schema default fills 768 on the
     * resolved path); absent on a fallback-shaped read — the renderer shows the
     * line only when present, never a defaulted value for an absent key.
     */
    readonly maxTokens?: number;
    /**
     * Opt-in prose fallback switch (KD-I2, issue #102); same presence rule as
     * {@link AdvisorComposedConfig.maxTokens}.
     */
    readonly proseFallback?: boolean;
    /** True when the composed config carries a custom system prompt ("" = unset). */
    readonly systemPromptSet: boolean;
    /**
     * First line of the system prompt, truncated to ≤ 80 chars (empty when
     * unset — the `<default>` marker is the renderer's job).
     */
    readonly systemPromptSummary: string;
    /**
     * Whether the dsh-tui `tuiSettingsSections` seam is mounted (dsh-tui ≥
     * v0.8.0) — a RENDERER INPUT for the edit hint, computed LIVE at render
     * time by the wiring (`ctx.get('tuiSettingsSections') !== undefined`, plan
     * dsh-advisor-tui-settings-n9 T2). An environment signal, never derived
     * from the per-session override; it does not change the resolved-config
     * read. When true the hint lists the TUI `/settings` screen as a write
     * path; when false the profile patch layer hint is shown unchanged.
     */
    readonly tuiSettingsAvailable: boolean;
}
/**
 * First line of a system prompt, truncated to ≤ 80 chars with a trailing
 * ellipsis when the first line is longer — the TUI one-liner readback, never
 * a full dump (AC-2). Empty when the prompt is unset ('' → the renderer shows
 * `<default>`).
 */
export declare function summarizeSystemPrompt(prompt: string): string;
/**
 * Render the composed config surface. Mirrors the status renderer's minimal
 * line style; the edit hint points at the operator edit paths — when the TUI
 * `tuiSettingsSections` seam is mounted (dsh-tui ≥ v0.8.0) the TUI `/settings`
 * Advisor section is listed FIRST, followed by the profile patch layer
 * (`cordis.patch.yml`, whose `advisor` plugin row carries the volatile live
 * fields); otherwise only the file path.
 */
export declare function advisorConfigText(config: AdvisorComposedConfig): string;
/**
 * The session-scoped operations the `/advisor` handler drives. Implemented by
 * the wiring (`index.ts`) against the observer, the per-session runtimes, and
 * the resolved config; faked in unit tests.
 */
export interface AdvisorCommandController {
    /**
     * Apply the session override and start/stop the session's runtime:
     * enabling seeds the observer cursor to the current transcript length
     * (KD-5 — no full-history replay) and resumes/creates the runtime; disabling
     * disposes the runtime (aborts the in-flight call, drops the backlog).
     * @param sessionLength - current transcript length, used for the KD-5 seed.
     */
    setEnabled(sessionId: string, enabled: boolean, sessionLength?: number): void;
    /** Snapshot the per-session status surface. */
    getStatus(sessionId: string): AdvisorSessionStatus;
    /** Snapshot the composed config surface (session-less settings readback). */
    getConfig(): AdvisorComposedConfig;
    /** The session's effective reviewer route (pair + source — spec §5.3). */
    getModelRoute(sessionId: string): AdvisorModelRoute;
    /**
     * Validate and commit an atomic pair for the INVOKING session (spec §5.3):
     * resolve through the LLM service before commit (60 s deadline, fused with
     * `signal`, cancellable, NO automatic retry — failure leaves the previous
     * selection untouched), fenced by the per-session generation. Never toggles
     * the enable override; never starts a generation call.
     */
    setModel(sessionId: string, provider: string, model: string, agent: Agent, signal?: AbortSignal): Promise<AdvisorSetModelOutcome>;
    /**
     * Drop the session's pin and re-inherit the CURRENT global defaults (never
     * touches the enable override). Synchronous — no validation needed.
     * @param sessionLength - current transcript length, used for the re-seed
     *   when the effective route actually changes.
     */
    resetModel(sessionId: string, sessionLength?: number): AdvisorResetModelOutcome;
}
/** Minimal command registry surface (satisfied by the dsh `CommandService`). */
export interface AdvisorCommandRegistry {
    register(definition: CommandDefinition): () => void;
}
/** Usage text for an unknown `/advisor` subcommand. */
export declare const USAGE: string;
/** Usage text for an unknown `/advisor model` subcommand. */
export declare const MODEL_USAGE: string;
/**
 * Register the `/advisor` command with a command registry (the dsh
 * `CommandService`, or a fake in tests). Called from the plugin's conditional
 * `ctx.inject(['commands'], ...)` child — the command exists only when a
 * registry is composed.
 * @returns the registry disposer (the inject child owns its lifetime).
 */
export declare function registerAdvisorCommands(registry: AdvisorCommandRegistry, controller: AdvisorCommandController): () => void;
