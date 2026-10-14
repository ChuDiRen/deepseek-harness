/**
 * Per-session advisor runtime (spec §2 S2, §4 mapping rows, §6, §8.2 KD-2,
 * §8.5 KD-5) — the "advisor model call + note extraction + drain/backlog"
 * core.
 *
 * One {@link AdvisorRuntime} exists per session (created on `agent/created` or
 * lazily on the first stepped `turn/end`, disposed on `agent/disposed` /
 * `session/disposed` — wired in `index.ts`). It owns:
 *
 * - a FIFO queue of pending transcript deltas (bounded — spec §6 "bounded
 *   backlog"; drop-newest when full);
 * - a serialized async drain loop: one `llm.stream` call per delta with
 *   `{ provider, model, system, messages: [user delta], maxTokens }` (the
 *   configured budget — {@link AdvisorRuntimeOptions.maxTokens}, default
 *   `ADVISOR_MAX_TOKENS`) and `purpose` left UNSET (KD-5 — an advisor call is
 *   an ordinary conversation request);
 * - a call-level deadline on every `llm.stream` call (dsh-timeout `deadline`,
 *   fused with the dispose signal and raced per chunk): a hung provider stream
 *   times out instead of wedging the drain, and a timeout is a transient
 *   failure (KD-5 retry → drop);
 * - KD-2 JSON-frame extraction: the first balanced `{…}` in the reply is
 *   parsed (tolerant of prose/fences), `note` must be non-empty (else
 *   drop+log), `severity` missing/invalid defaults to `nit`, no parse retry;
 *   the KD-I2 prose fallback (issue #102, opt-in — see
 *   {@link extractProseFallbackNote}) lets a reply that yields no valid
 *   frame note through as a nit note when the `proseFallback` option is on —
 *   no parseable frame at all, or frames whose note is empty/invalid; the
 *   JSON frame keeps priority (a usable frame note blocks the fallback), and
 *   the default (off) preserves the KD-2 drop semantics;
 * - KD-I3 drop visibility (issue #102): a completed call whose reply yields
 *   no note is classified — EMPTY (body empty after trim; the classic case is
 *   a thinking model exhausting the token budget) vs UNPARSED (text present,
 *   no parseable frame, fallback off/rescued nothing) — counted with
 *   timestamps and warn-once hints, readable via the `emptyReplies` /
 *   `unparsedReplies` / `lastEmptyReplyAt` / `lastUnparsedReplyAt` getters
 *   (the T7 `/advisor status` surface);
 * - the KD-5 failure policy: transient → 1 retry with a short backoff → drop;
 *   3 consecutive dropped deltas → flush the pending backlog (never stall);
 *   permanent errors (`invalid_request_error`, model-not-found, "is not
 *   supported when") → halt the session's advisor; quota/rate-limit → pause
 *   (`quota_exhausted`), batch retained, no auto-resume timer; the in-flight
 *   call is aborted on dispose via the `signal`. `halted` is terminal in
 *   place — the command layer rebuilds the runtime (dispose + recreate); a
 *   `quota_exhausted` runtime resumes via {@link AdvisorRuntime.resume}.
 *
 * The runtime never parks the primary loop: everything is fire-and-forget
 * async and a failing advisor can only drop its own backlog.
 *
 * @module dsh-advisor/advisor-runtime
 */
import type { GenerateOptions, LlmResolvedModelInfo, StreamChunk } from '@deepseek-ai/dsh-llm';
import type { EmissionGuard } from './emission-guard.js';
import type { Delta } from './transcript.js';
/** Severity vocabulary (spec §6) carried by every delivered advice note. */
export type AdviceSeverity = 'nit' | 'concern' | 'blocker';
/** One extracted advice note, fed to the T5 emission guard for delivery. */
export interface AdviceNote {
    readonly note: string;
    readonly severity: AdviceSeverity;
}
/**
 * Per-session runtime status surface for T7 `/advisor status`.
 *
 * T4 sets `running` | `quota_exhausted` | `halted`; `paused` is reserved for
 * explicit pause semantics and `disabled` for the config gate — the runtime is
 * never constructed in either state (`index.ts` returns early when the resolved
 * config is disabled).
 */
export type AdvisorRuntimeStatus = 'running' | 'paused' | 'quota_exhausted' | 'halted' | 'disabled';
/** Minimal `ctx.llm` surface the runtime drives (satisfied by `LlmRuntime`). */
export interface AdvisorLlm {
    stream(options: GenerateOptions): AsyncIterable<StreamChunk>;
    /**
     * Optional capability query (LlmRuntime exposes it; injected fakes may not).
     * Used to capability-gate `reasoningEffort` (qc2 W-1 / qc1 W-1 / qc3 F-3):
     * the dsh LlmRuntime rejects an explicit effort for any model whose adapter
     * does not declare it, so the runtime resolves the model's declared efforts
     * and passes `'off'` only when the model supports it. Absent → the option
     * is omitted and `resolveCallFor` materializes the adapter default.
     */
    resolveModelInfo?(provider: string, model: string, signal?: AbortSignal): Promise<LlmResolvedModelInfo>;
}
/** Logger seam (cordis `ctx.logger('advisor')` satisfies it; console works too). */
export interface AdvisorRuntimeLogger {
    debug(message: string, ...args: unknown[]): void;
    warn(message: string, ...args: unknown[]): void;
}
/** Options for one per-session {@link AdvisorRuntime}. */
export interface AdvisorRuntimeOptions {
    /** Resolved provider route (the explicit gate guarantees it when enabled). */
    readonly provider: string;
    /** Resolved model id (the explicit gate guarantees it when enabled). */
    readonly model: string;
    /** System prompt sent with every advisor call (config override or KD-2 default). */
    readonly systemPrompt: string;
    /** Backoff for the single transient retry (KD-5); default 1000ms. */
    readonly retryBackoffMs?: number;
    /**
     * Call-level deadline for one `llm.stream` call (qc2 W-4 / qc3 W-1): a hung
     * provider stream (no chunk, no end, no error) times out instead of wedging
     * this session's drain. A timeout is classified as a transient failure —
     * KD-5 retry(1) → drop. Default 60000ms.
     */
    readonly callTimeoutMs?: number;
    /** Bounded backlog (spec §6); default 32 — drop-newest with a log when full. */
    readonly maxQueued?: number;
    /**
     * Token budget for one advisor call (KD-I1, issue #102 — the config key
     * `maxTokens` threaded through): when omitted the code default
     * {@link ADVISOR_MAX_TOKENS} (768) applies, keeping every pre-existing
     * 768 pin valid. Bounds (128..16384) are enforced by the config schema;
     * the runtime threads the value as-is.
     */
    readonly maxTokens?: number;
    /**
     * Opt-in prose fallback (KD-I2, issue #102): when true, a completed call
     * whose reply has text but yields NO valid note from its JSON frames — no
     * parseable frame at all, or frames whose note is empty/invalid — delivers
     * the cleaned prose body ({@link extractProseFallbackNote}: trim → strip a
     * surrounding fence → cap) as a `nit` note through the normal
     * guard/delivery pipeline. Default false — the KD-2 drop semantics stay
     * byte-identical.
     */
    readonly proseFallback?: boolean;
    /** The llm service (`ctx.llm`); injectable for tests. */
    readonly llm: AdvisorLlm;
    /**
     * The T5 emission guard gating extracted notes before delivery. Defaults to
     * a fresh {@link createEmissionGuard} (per-runtime lifetime — a new guard
     * per session); injectable for tests.
     */
    readonly guard?: EmissionGuard;
    /**
     * Invoked once per extracted note that passes the T5 emission guard
     * (accepted = delivered to T6; suppressed notes are dropped silently).
     */
    readonly onNote: (note: AdviceNote) => void;
    readonly logger?: AdvisorRuntimeLogger;
}
/**
 * User-directed token budget for one advisor call (256 → 5120 → 768).
 * Exported so the test suites assert the pinned value instead of a magic
 * literal.
 *
 * Supersession chain: the frozen spec §8.2 (KD-2) pins `maxTokens: 256` ("so
 * a runaway reply cannot blow the budget"); the 5120 value (a 20x worst-case
 * per-call ceiling) was a USER-DIRECTED supersession adopted together with
 * `reasoningEffort: 'off'` when reasoning-heavy replies could starve the JSON
 * frame. With thinking-off now the capability-gated default (see
 * `resolveReasoningEffort`), the reasoning headroom is unnecessary: this 768
 * value is the latest USER-DIRECTED supersession — a modest budget that fits
 * one `ADVISOR_NOTE_MAX_CHARS` note plus the JSON frame. The runaway-reply
 * guard stays re-bounded downstream: `extractAdviceNote` caps the note at
 * `ADVISOR_NOTE_MAX_CHARS` and `buildAdvisorMessage` bounds the notice
 * summary via `boundContextSummary`.
 *
 * KD-I1 (issue #102, user direction 2026-09-29): KD-6's "code invariant, not
 * an operator switch" ruling was superseded again — the budget is now
 * operator-configurable (config key `maxTokens`, bounds 128..16384, Settings
 * UI in Task 3) because thinking models behind third-party gateways exhaust a
 * fixed budget on reasoning and return an EMPTY body (finish: max-tokens).
 * This constant remains the CODE DEFAULT for unconfigured/plain entries: the
 * runtime falls back to it, so default behavior (and every existing 768 pin)
 * is unchanged.
 */
export declare const ADVISOR_MAX_TOKENS = 768;
/**
 * One extracted note's length cap (qc3 F-2 / qc2 S-1): a verbose/rogue advisor
 * reply must not inject an unbounded user-role message into the primary
 * session (the token budget is now matched to this cap — 768). Truncated with
 * a '…' marker. The KD-I2 prose fallback note is capped by the same bound —
 * a raised generation budget must not enlarge the injection surface.
 */
export declare const ADVISOR_NOTE_MAX_CHARS = 768;
/**
 * Extract one {@link AdviceNote} from the advisor's reply (KD-2).
 *
 * Locates the first balanced `{…}` object (tolerant of surrounding prose and
 * markdown fences), parses it, and validates: `note` must be a non-empty
 * string after trim (else drop), `severity` missing/invalid defaults to
 * `nit`. A reply with no parseable frame returns `undefined` — the caller
 * drops + logs, and there is NO retry for parse failures (the retry budget is
 * reserved for transport errors, KD-2). The note is capped at
 * {@link ADVISOR_NOTE_MAX_CHARS} with a '…' marker (qc3 F-2 — the 20x token
 * budget must not translate into an unbounded injection into the primary
 * session). Never throws.
 */
export declare function extractAdviceNote(reply: string): AdviceNote | undefined;
/**
 * The KD-I2 prose fallback cleanup (issue #102; opt-in — see
 * {@link AdvisorRuntimeOptions.proseFallback}). Frozen-spec supersession
 * note: the strict KD-2 JSON-frame requirement stays the DEFAULT — this
 * function is applied at the extraction call site ONLY when
 * {@link extractAdviceNote} extracted no valid note (no parseable frame, or
 * every frame's note empty/invalid) AND the flag is on, so a reply whose
 * frame yields a usable note still delivers that note.
 *
 * Cleanup: trim → strip ONE surrounding markdown fence (an unterminated or
 * non-surrounding fence is kept as-is) → cap at {@link ADVISOR_NOTE_MAX_CHARS}
 * with a '…' marker (the same injection bound as {@link extractAdviceNote} —
 * a raised generation budget must not enlarge the primary session's injection
 * surface). An empty result (whitespace-only reply, fence-only reply) is NOT
 * prose: the caller classifies it as an EMPTY drop (KD-I3), never as an
 * unparsed/prose case. Severity is always `nit` — prose carries no structured
 * severity. Never throws.
 */
export declare function extractProseFallbackNote(reply: string): AdviceNote | undefined;
/**
 * Per-session advisor runtime: queue deltas, async drain, `llm.stream` call,
 * JSON-frame note extraction, and the KD-5 failure policy. All async work is
 * fire-and-forget — the primary loop is never parked.
 */
export declare class AdvisorRuntime {
    private readonly provider;
    private readonly model;
    private readonly systemPrompt;
    private readonly maxTokens;
    private readonly proseFallback;
    private readonly retryBackoffMs;
    private readonly callTimeoutMs;
    private readonly maxQueued;
    private readonly llm;
    private readonly guard;
    private readonly onNote;
    private readonly logger;
    private readonly controller;
    /**
     * Per-(provider, model) reasoning-effort capability cache (qc2 W-1 / qc1
     * W-1 / qc3 F-3): resolving the model's declared efforts on EVERY advisor
     * call would add an adapter round-trip per delta; one resolution per
     * (provider, model) per runtime suffices — the route is pinned for the
     * runtime's lifetime. ONLY definitive verdicts are cached ('off' or a
     * successful no-'off' resolution); a resolution failure (throw or deadline
     * abort) is never cached, so the next call resolves afresh.
     */
    private readonly reasoningEffortCache;
    /** One-shot latch for the definitive no-'off' log line (log-once per runtime). */
    private thinkingOffLogged;
    private readonly queue;
    private state;
    private draining;
    private disposed;
    private consecutiveDrops;
    private drainPromise;
    /** Epoch-ms of the last note accepted by the emission guard (T7 status). */
    private lastActivityAt;
    /**
     * KD-I3 drop counters (issue #102): EMPTY vs UNPARSED no-note drops with
     * their last-occurrence timestamps — the "advisor is running but never
     * speaks" visibility surface (T2 renders them on `/advisor status`). Only
     * COMPLETED model calls are classified here; transport drops stay in the
     * KD-5 consecutive-drop path.
     */
    private emptyReplyCount;
    private unparsedReplyCount;
    private lastEmptyReplyTimestamp;
    private lastUnparsedReplyTimestamp;
    /** Warn-once latches, one per drop class per runtime (KD-I3). */
    private emptyReplyWarned;
    private unparsedReplyWarned;
    constructor(options: AdvisorRuntimeOptions);
    /** Current per-session status (T7 `/advisor status` surface). */
    status(): AdvisorRuntimeStatus;
    /** Number of deltas waiting to be drained (bounded by `maxQueued`). */
    get pendingCount(): number;
    /**
     * T7 `/advisor status` surface — epoch-ms of the last note accepted by the
     * emission guard, or `undefined` before the first accepted note.
     */
    get lastActivity(): number | undefined;
    /**
     * KD-I3 (issue #102) — replies dropped because the body was empty after
     * trim (mostly a reasoning model exhausting the token budget). Read-only
     * status outlet, same style as `pendingCount`/`lastActivity`.
     */
    get emptyReplies(): number;
    /**
     * KD-I3 (issue #102) — replies dropped because no valid note was extracted
     * (no parseable JSON frame, or frames whose note is empty/invalid) and the
     * prose fallback delivered nothing (`proseFallback` off, or on with an
     * empty cleanup result). Read-only status outlet.
     */
    get unparsedReplies(): number;
    /** KD-I3 — epoch-ms of the last EMPTY-reply drop, `undefined` before the first. */
    get lastEmptyReplyAt(): number | undefined;
    /** KD-I3 — epoch-ms of the last UNPARSED-reply drop, `undefined` before the first. */
    get lastUnparsedReplyAt(): number | undefined;
    /**
     * Queue one rendered transcript delta (from the T3 observer's `onDelta`).
     * While `quota_exhausted`, deltas queue up (bounded) but the drain is never
     * auto-restarted (KD-5 — no auto-resume timer); while `halted`/disposed they
     * are dropped with a log. Never throws, never parks the caller.
     */
    enqueue(delta: Delta): void;
    /** Abort the in-flight call and stop the drain (wiring: session/agent disposed). */
    dispose(): void;
    /**
     * Manual resume after a quota pause (T7 `/advisor on`); no-op when halted/
     * disposed — a halted runtime is terminal in place and is recovered by the
     * command layer via dispose-and-recreate (qc1/qc2/qc3 W-1/I-4), never
     * resumed here.
     */
    resume(): void;
    /**
     * KD-5 reset trigger: a compaction / surface rewrite clears the emission
     * guard's dedupe history and per-update latch — the session state is being
     * rewritten, so the old note history no longer applies (a note already
     * advised before the rewrite may legitimately be advised again). The wiring
     * (`index.ts` onRewrite) calls this alongside the delivery cooldown reset.
     */
    resetGuard(): void;
    /** Resolve once the current drain run settles (test/integration hook). */
    waitForDrain(): Promise<void>;
    private kickDrain;
    /** Serialized drain loop: process the queue one delta at a time. */
    private drain;
    /** KD-5: clear the pending backlog after consecutive failures (never stall). */
    private flushBacklog;
    /** Process one delta: attempt + single retry (transient), classify terminal failures. */
    private processDelta;
    /** One model call: build options, stream text, extract the note (KD-2). */
    private callModel;
    /**
     * KD-I3: count + timestamp an EMPTY-reply drop and warn ONCE per runtime
     * with the fix hint (raise the budget); repeats fall back to a debug line.
     * The finish reason rides along — `max-tokens` vs `stop` is the
     * budget-exhausted vs genuinely-empty tell (issue #102 evidence).
     */
    private recordEmptyReply;
    /**
     * KD-I3: count + timestamp an UNPARSED-reply drop and warn ONCE per runtime
     * with the fix hint (enable the prose fallback); repeats fall back to the
     * original KD-2 debug line.
     */
    private recordUnparsedReply;
    private buildOptions;
    /**
     * Capability-gate the `reasoningEffort: 'off'` option (qc2 W-1 / qc1 W-1 /
     * qc3 F-3): pass the branded 'off' effort only when the resolved model's
     * `reasoning.efforts` includes it, else omit the option (`resolveCallFor`
     * materializes the adapter default). Cached per (provider, model) — one
     * resolution per runtime, never per call — but ONLY definitive verdicts are
     * cached: a resolution failure (unknown route, adapter throw, or a deadline
     * abort — n4 QC N-5) is advisory and returns `undefined` WITHOUT caching, so
     * a transient failure retries the resolution on the next call instead of
     * latching thinking-off unavailable for the runtime's lifetime. A definitive
     * no-'off' verdict logs the unavailable line once per runtime
     * (`thinkingOffLogged`); resolution failures get no log-once latch of their
     * own. The optional `signal` (the call's deadline signal) is threaded into
     * `resolveModelInfo`, whose contract allows adapter-owned asynchronous
     * lookup with cancellation — a hung lookup that honors the signal aborts
     * with the call deadline instead of wedging the drain.
     */
    private resolveReasoningEffort;
    /** Emit the definitive no-'off' line exactly once per runtime. */
    private logThinkingOffUnavailable;
}
