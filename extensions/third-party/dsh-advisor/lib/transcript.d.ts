/**
 * Session observer + bounded delta renderer (spec §2 S2, §4 mapping table,
 * §6 self-review exclusion, §8.3 KD-3, §8.5 KD-5).
 *
 * `DeltaRenderer` is the pure transcript core: a cursor over the session event
 * log plus a fingerprint of the delivered prefix. `update(events)` extracts
 * the newly appended messages, excludes advisor-source messages (self-review
 * guard), and renders a role-annotated markdown delta bounded by the
 * `maxDeltaMessages` window. A prefix rewrite — a `compact/*` event, a
 * `user/message` with `surfaceOp.op === 'replace'`, or a fingerprint mismatch
 * (defensive fallback) — resets the cursor and replays the full post-rewrite
 * surface on the next update.
 *
 * `SessionTranscriptObserver` is the per-session wiring unit: it owns one
 * `DeltaRenderer` per session id and dispatches `session/event` tuples to
 * them. It has TWO trigger modes (KD-N4-5):
 *
 * 1. **turn/end** (standard turn-driven sessions): renders only on a stepped
 *    `turn/end` whose `reason.kind` is reviewable (`completed` | `max-tokens`
 *    | `error`; spec §4 — skip `aborted`/`blocked`/`interrupted`, i.e. do not
 *    critique user-cut-short turns). Byte-identical behavior — the original
 *    single-trigger path.
 * 2. **agent reply complete** (harness/agentic sessions, which never emit
 *    `turn/end`): fires on human-input arrival (`user/message` with
 *    `source.kind === 'user'`, or `agent/inbox/spliced` whose `inserted`
 *    carries a message with `source.kind === 'user'` — inbox-spliced input
 *    may commit as that event first and never re-emit as `user/message`).
 *    Non-user inbox splices (the advisor's own inject/steer deliveries,
 *    workspace/tool/empty splices) never trigger (C-1 self-trigger fix).
 *    Before rendering,
 *    a read-only predicate checks for an unreviewed non-advisor
 *    `assistant/message` since the renderer cursor; on a miss the cursor is
 *    untouched (the first user input of a session neither triggers nor
 *    advances). Append-type triggers pass `events` minus the trigger itself
 *    (the arriving input opens the next round); rewrite-type triggers
 *    (compact summary replace) pass the full log to trigger the KD-5 replay.
 *    Both modes share the same renderer/cursor, so the cursor advance dedupes
 *    (one delta per completed round), and both call `onSteppedTurnEnd` (the
 *    immuneTurns countdown — T6) before rendering.
 *
 * **Mode latch**: once a session has produced ANY `turn/end` event
 * (reviewable or not), the new gate sleeps for it — the session is a
 * standard turn-driven one and keeps verbatim behavior, including spec §4
 * skip-aborted (a cut-short first turn's unreviewed increment must not be
 * supplementarily reviewed by the new gate). Harness/agentic sessions never
 * emit `turn/end`, so their latch never arms.
 *
 * It also exposes the T6 delivery hooks: `onSteppedTurnEnd` (one completed
 * stepped primary turn — the immuneTurns countdown) and `onRewrite` (a
 * compact/replace event — the KD-5 latch reset). `index.ts` binds the cordis
 * `session/event` / `session/disposed` / `agent/disposed` listeners into an
 * instance of this class.
 *
 * @module dsh-advisor/transcript
 */
import type { SessionEvent } from '@deepseek-ai/dsh-session';
/** One incremental transcript delta handed to the advisor runtime (T4). */
export interface Delta {
    /** Role-annotated markdown of the new (or replayed) transcript messages. */
    readonly markdown: string;
    /**
     * Whether more transcript content is expected to follow the same logical
     * update. dsh closes a turn with `turn/end` (all its steps are done), so a
     * delta rendered at a stepped `turn/end` is always complete — `false` for
     * the MVP (see the task-3 report for the rationale).
     */
    readonly willContinue: boolean;
}
/** Options for one {@link DeltaRenderer}. */
export interface DeltaRendererOptions {
    /**
     * Bounded message window (spec §8.3 KD-3): keep the most recent N messages
     * and prepend the truncation marker when a rendered delta would exceed N;
     * `0` = unbounded. Default 60.
     */
    readonly maxDeltaMessages: number;
}
/** Default delta window (KD-3). */
export declare const DEFAULT_MAX_DELTA_MESSAGES = 60;
/** Marker line prepended when a rendered delta omits earlier messages (KD-3). */
export declare const TRUNCATION_MARKER = "\u2026 <earlier messages omitted>";
/**
 * Cursor + fingerprint bookkeeping over one session's event log.
 *
 * The renderer consumes the session event log (the full `session.events`
 * snapshot on each call — the cordis wiring passes the live log). It keeps:
 * - `cursor` — how many log events are consumed (seqs are contiguous from 0,
 *   so this equals the next unprocessed seq);
 * - `surface` / `messages` — the current ordered surface of derived
 *   non-advisor messages (seqs + messages), maintained incrementally for
 *   appends and rebuilt from a full fold after a reset;
 * - `deliveredFingerprint` — fingerprint of the delivered prefix, detecting a
 *   hidden rewrite;
 * - `droppedPrefix` — whether messages before the bounded window were dropped
 *   (drives the truncation marker on replay renders).
 */
export declare class DeltaRenderer {
    private maxDeltaMessages;
    private cursor;
    private readonly surface;
    private readonly messages;
    private deliveredFingerprint;
    private droppedPrefix;
    constructor(options?: Partial<DeltaRendererOptions>);
    /**
     * Update the bounded message window (live config — settings onChange, plan
     * dsh-advisor-settings-n2 T1). Existing fold state is kept; the new bound
     * applies from the next render on.
     */
    setMaxDeltaMessages(value: number): void;
    /**
     * Process a session event log snapshot and return the next delta, or
     * `undefined` when no new (renderable) content was appended.
     *
     * `skipLast` treats the final log event as excluded — the arriving trigger
     * of an append-type review (qc3 F1): equivalent to the caller slicing
     * `events.slice(0, events.length - 1)` WITHOUT the O(full-log) shallow copy
     * the reply-complete gate used to pay on every review. The excluded event
     * must be the last log entry (the wiring guarantees it).
     *
     * - Detects a reset: a rewrite event (`compact/*`, replace surface op) in
     *   the unconsumed portion, a shorter log than the cursor, or a delivered
     *   prefix whose fingerprint changed. On reset the cursor rewinds to 0 and
     *   the full post-rewrite surface is replayed (bounded by KD-3).
     * - Otherwise appends the new events, extracts their messages (advisor
     *   excluded), and renders only those (incremental delta).
     */
    update(events: readonly SessionEvent[], skipLast?: boolean): Delta | undefined;
    /**
     * Full reset: rewind the cursor to 0 and drop all fold state. The next
     * `update` replays the whole current surface (bounded). Also the KD-5
     * reset surface for emission-guard / immuneTurns latches (T5/T6 hook into
     * the same session lifecycle).
     */
    reset(): void;
    /**
     * Seed the cursor to `length` (KD-5 seed-on-enable): skip existing history
     * — the next update renders only events at/after `length` (no full-history
     * replay, matching omp).
     */
    seedTo(length: number): void;
    /**
     * Read-only predicate for the agentic reply-complete gate (KD-N4-5): does an
     * unreviewed non-advisor `assistant/message` increment exist since the
     * cursor? Scans the unconsumed log tail with the same derivation the
     * renderer uses (an empty-content `assistant/message` derives no message, so
     * it does not count) and excludes advisor-source messages (self-review
     * guard, spec §6). NEVER mutates state — a blind `update()` here would
     * pre-advance the cursor and lose the user prompt from the first
     * standard-session turn/end delta, so the caller only calls `update()` when
     * this returns true.
     */
    hasUnreviewedAssistant(events: readonly SessionEvent[]): boolean;
    /** Rebuild the fold from a full log (post-reset replay, bounded to `length`). */
    private rebuild;
    /** Incrementally fold new events in `[start, end)` (guaranteed append-only) and return added messages. */
    private append;
    /** Render the newly appended messages (incremental delta). */
    private renderTail;
    /** Render the current surface in full (post-reset replay, bounded). */
    private renderSurface;
    private render;
}
/** Callback contract for {@link SessionTranscriptObserver}. */
export interface SessionObserverOptions {
    /** Bounded delta window (KD-3); forwarded to every per-session renderer. */
    readonly maxDeltaMessages: number;
    /** Invoked once per stepped reviewable turn/end with the rendered delta. */
    readonly onDelta: (sessionId: string, delta: Delta) => void;
    /**
     * Invoked once per stepped reviewable turn/end (the same gate as `onDelta`),
     * before the delta is rendered — the delivery module (T6) counts completed
     * primary turns here to decrement its immuneTurns cooldown (spec §6).
     */
    readonly onSteppedTurnEnd?: (sessionId: string) => void;
    /**
     * Invoked when a rewrite event is observed (`compact/*` or a non-append
     * surface op) — the delivery module (T6) clears its immuneTurns latch here
     * (KD-5 reset triggers). Fires before the turn gate: a rewrite can arrive
     * outside a turn/end.
     */
    readonly onRewrite?: (sessionId: string) => void;
}
/** True when a `turn/end` event carries a reviewable end reason. */
export declare function isReviewableTurnEnd(event: SessionEvent): boolean;
/**
 * True when an event is a human-input arrival — the trigger of the agentic
 * reply-complete gate (KD-N4-5).
 *
 * - `user/message` with `source.kind === 'user'` — the primary signal: a
 *   direct human prompt (the queued message claimed for a step).
 * - `agent/inbox/spliced` — the fallback: inbox-spliced input commits as
 *   this log-only event first and may never re-emit as `user/message`
 *   (the merged `SessionEventMap` entry comes from the dsh-agent peer, per
 *   the `compact/*` precedent). Payload-discriminated (C-1 fix): the event
 *   only triggers when `inserted` is non-empty and carries at least one
 *   message whose `source.kind === 'user'`.
 *
 * `source.kind` is the ONLY discriminator, and every synthetic producer commits
 * a non-`user` kind, so nothing injected can self-trigger the review gate:
 *
 * - the advisor's OWN inject/steer deliveries — the producer-owned `advisor`
 *   kind (`form: 'notice'`);
 * - the other named producer kinds: model-selection notices, the
 *   time-context / tmux-context snapshots, tools-ptc (`ptc-mode`),
 *   user-approval, tool-registry availability rows — each a `kind` of its own
 *   in `MessageSourceMap`, which is what separates them now that no shared
 *   `plugin` arm exists;
 * - workspace-context sync (AGENTS.md / CLAUDE.md), whose producer commits its
 *   own first-party `kind: 'agent-instructions'` (`form: 'instructions'`);
 * - tool results, which in V4 are `role: 'tool'` messages (`kind: 'tool'`),
 *   never user-role;
 * - claim/clear splices (empty `inserted`).
 */
export declare function isHumanInputEvent(event: SessionEvent): boolean;
/**
 * One renderer per session id, driven by `session/event` tuples. Cordis-free,
 * so the wiring logic is unit-testable; `index.ts` binds the cordis listeners
 * into an instance and forwards `session.events` (the live log).
 */
export declare class SessionTranscriptObserver {
    private readonly options;
    private readonly renderers;
    /** seedTo lengths issued before a session's renderer existed (KD-5 enable). */
    private readonly pendingSeeds;
    /**
     * Mode latch (KD-N4-5): sessions that have produced ANY `turn/end` event.
     * Once a session emits `turn/end` it is a standard turn-driven session —
     * the new agentic reply-complete gate sleeps for it (verbatim behavior,
     * including spec §4 skip-aborted: a cut-short first turn's unreviewed
     * increment must not be supplementarily reviewed). Agentic/harness
     * sessions never emit `turn/end`, so they never latch and the new gate
     * stays active. Per-session; cleared on dispose.
     */
    private readonly turnEndSessions;
    /** Bounded delta window (KD-3); forwarded to every per-session renderer. */
    private maxDeltaMessages;
    constructor(options: SessionObserverOptions);
    /**
     * Update the bounded delta window (live config — settings onChange, plan
     * dsh-advisor-settings-n2 T1): the observer default AND every live
     * per-session renderer, so existing sessions pick up the new bound without
     * losing their fold state.
     */
    setMaxDeltaMessages(value: number): void;
    /**
     * Feed one session event (mirroring the cordis `session/event` listener:
     * `(session, event)` — `events` is the session's live log, `event` the
     * appended event). Renders (and emits via `onDelta`) on either trigger:
     * a stepped `turn/end` with a reviewable reason (standard sessions), or a
     * human-input arrival with an unreviewed assistant increment (agentic
     * sessions — the reply-complete gate, KD-N4-5). The mode latch keeps the
     * second gate dormant for any session that emits `turn/end`.
     */
    handleEvent(sessionId: string, events: readonly SessionEvent[], event: SessionEvent): void;
    /** Lazy per-session renderer creation, shared by both trigger modes. */
    private rendererFor;
    /** Drop a session's renderer (wiring: `session/disposed` / `agent/disposed`). */
    disposeSession(sessionId: string): void;
    /**
     * KD-5 seed-on-enable: skip existing history for a session's renderer.
     * Issued before the renderer exists (e.g. `/advisor on` before the session
     * produced a stepped turn), the seed is remembered and applied on creation.
     */
    seedTo(sessionId: string, length: number): void;
}
