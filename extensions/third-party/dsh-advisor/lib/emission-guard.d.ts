/**
 * Emission guard (spec §4 mapping row — omp `advisor/emission-guard.ts`
 * ported 1:1: normalize / dedupe / content-free suppression / one-per-update
 * / escalation; §6 one-note-per-update; §8.2 KD-2 "guard also drops extras").
 *
 * The guard sits between the T4 runtime (note extraction) and delivery (T6):
 * {@link EmissionGuard.accept} returns `true` to pass a note through to the
 * delivery callback and `false` to suppress it **silently** — the caller can
 * never tell an accepted from a suppressed note, and no error is thrown.
 *
 * Rules (in order):
 * 1. **Normalization** — lowercase, NFKC, every run of non-alphanumeric
 *    characters collapsed to one space, trimmed. `"Stop."`, `*stop*` and
 *    `"  STOP  "` all key to `stop`.
 * 2. **Content-free phrase filter** — short phrases with no concrete reason
 *    (`stop`, `done`, `complete`, `no issue continue`, `lgtm`,
 *    `nothing to add`, plus documented equivalents — see
 *    {@link CONTENT_FREE_PHRASES}) are suppressed. Matching is exact on the
 *    normalized text, so a note that merely contains a phrase survives.
 * 3. **Per-update rate limit** — at most one note per advisor model cycle is
 *    accepted. The runtime signals each new cycle with {@link
 *    EmissionGuard.beginUpdate} (once per processed delta), resetting the
 *    latch. A guard whose `beginUpdate` is never called still accepts the
 *    first note of the session (fail-safe toward fewer notes).
 * 4. **Normalized dedupe with escalation** — a normalized note already
 *    accepted this session is dropped, with a FIFO-bounded history
 *    (default 4096, omp parity; {@link DEFAULT_MAX_HISTORY}); the oldest
 *    entry is evicted past the bound. A repeat at equal or lower severity is
 *    suppressed, but a real escalation (nit → concern → blocker) of the same
 *    note is accepted and updates the remembered severity.
 *
 * Guard state clears per session: a new runtime (and therefore a new guard)
 * is created per session and discarded on dispose; {@link
 * EmissionGuard.reset} is exposed for the KD-5 session-reset triggers
 * (`compact/*`, `user/message` replace) when the reset wiring lands.
 *
 * @module dsh-advisor/emission-guard
 */
import type { AdviceNote } from './advisor-runtime.js';
/**
 * FIFO dedupe history bound (omp parity: 4096). Deliberately capped — a
 * session that accepts more than this many distinct notes keeps only the most
 * recent window, so an old note may legitimately be advised again.
 */
export declare const DEFAULT_MAX_HISTORY = 4096;
/**
 * Content-free phrases suppressed at delivery. The omp base list is
 * `stop` / `done` / `complete` / `no issue continue` / `lgtm` /
 * `nothing to add` (this is also the frame the KD-2 prompt asks the model to
 * emit when there is nothing to advise). Additions beyond the omp base —
 * short acknowledgements with no concrete reason — are listed after them.
 */
export declare const CONTENT_FREE_PHRASES: ReadonlySet<string>;
/** Options for one {@link EmissionGuard}. */
export interface EmissionGuardOptions {
    /**
     * FIFO dedupe history bound (normalized notes remembered per session);
     * default {@link DEFAULT_MAX_HISTORY} (4096, omp parity).
     */
    readonly maxHistory?: number;
}
/**
 * Per-session emission guard. One instance per advisor runtime; created via
 * {@link createEmissionGuard} (or the constructor directly).
 */
export declare class EmissionGuard {
    private readonly maxHistory;
    /**
     * normalized note → last accepted severity. Map insertion order is the
     * FIFO order (updating an existing key does not move it), so the oldest
     * entry is simply the first key.
     */
    private readonly history;
    /** One-note-per-update latch; reset by {@link beginUpdate} and {@link reset}. */
    private acceptedThisUpdate;
    constructor(options?: EmissionGuardOptions);
    /**
     * Mark the start of one advisor model cycle (one processed transcript
     * delta). The per-update rate limit latch resets here, so each cycle may
     * deliver one note again. The runtime calls this once per delta it drains.
     */
    beginUpdate(): void;
    /**
     * Accept or suppress one extracted note.
     *
     * @returns `true` = pass through to delivery (T6); `false` = suppressed
     *   (normalized-empty, content-free, a repeat at equal/lower severity, or
     *   the second note of the same update). Never throws.
     */
    accept(note: AdviceNote): boolean;
    /**
     * Clear all session state (dedupe history + per-update latch). Exposed for
     * the KD-5 session-reset triggers; a new session gets a fresh guard anyway
     * (per-runtime lifetime).
     */
    reset(): void;
}
/** Factory (plan T5: "Export the guard class + a factory"). */
export declare function createEmissionGuard(options?: EmissionGuardOptions): EmissionGuard;
