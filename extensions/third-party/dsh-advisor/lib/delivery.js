/**
 * Delivery routing (spec §2 S3, §4 mapping row, §6 delivery semantics,
 * §8.4 KD-4) — the advice delivery channel into the primary agent.
 *
 * One {@link AdvisorDelivery} exists per plugin load and owns:
 *
 * - **The KD-4 per-session agent map**: keyed by `agent.id` (=== `session.id`),
 *   maintained by `index.ts` on `agent/created` / `agent/disposed`, with a
 *   registry fallback (`ctx.agents.get(session.id)`, injected as
 *   `lookupAgent`) that covers agents published before this plugin loaded.
 *   A missing agent at delivery time drops the note with a log — advisory
 *   only, never throw, never stall.
 * - **Severity routing (spec §6)**: nit → `agent.inject` (non-waking, consumed
 *   at the next pre-step boundary); concern/blocker → `agent.steer` (waking —
 *   an idle driver starts a turn, a running driver consumes at its next step
 *   boundary).
 * - **The immuneTurns cooldown (spec §6)**: after a concern/blocker is actually
 *   steered, the next `immuneTurns` stepped primary turns must complete before
 *   another interrupting note may steer; interrupting notes inside the window
 *   downgrade to inject. The fence arms only on a real steer delivery; the
 *   observer's `onSteppedTurnEnd` / `onRewrite` hooks (T3 wiring) drive the
 *   countdown and the KD-5 reset.
 *
 * Message shape (spec §6): a user-role message via `createUserMessage` whose
 * source is this plugin's own producer kind (`kind: 'advisor'`, pinned to the
 * `notice` form; src/kinds.ts) and whose content is self-describing
 * `[advisor:{severity}] {note}` — the only cue the primary model gets about
 * how to treat it ("weigh, don't blindly obey" spirit). The kind is claimed by
 * declaration-merging `MessageSourceMap` in dsh-llm, and the V3→V4 format edge
 * preserves direct source kinds, so this identity is cross-generation-safe —
 * the property the retired `plugin` arm used to be borrowed for.
 *
 * Delivery is synchronous and fire-and-forget; the runtime path (T4 F1) is
 * what contains a throwing `inject`/`steer` — this module lets agent-method
 * throws propagate to that containment seam.
 *
 * @module dsh-advisor/delivery
 */
import { boundContextSummary, createUserMessage } from '@deepseek-ai/dsh-llm';
/**
 * Build the advisor message for one note (spec §6): a user-role message whose
 * source carries this plugin's own producer kind and whose content is
 * self-describing `[advisor:{severity}] {note}`.
 *
 * Bounds (qc3 F-2 / qc2 S-1): the note itself is already capped at
 * `ADVISOR_NOTE_MAX_CHARS` by extraction; the collapsed-row summary is
 * additionally bounded via `boundContextSummary` (120 chars — the platform
 * `CONTEXT_SUMMARY_MAX_CHARS` convention), so the durable log and the
 * collapsed context row never carry an unbounded account.
 */
export function buildAdvisorMessage(note) {
    // One formatter for content and summary: the summary is derived from the
    // same string as the content via a fixed slice of the `[advisor:` marker
    // (`[` + everything after it), so the severity formatting can never drift
    // between the two — and note text mentioning "advisor:" cannot affect it.
    const text = `[advisor:${note.severity}] ${note.note}`;
    const summary = `[${text.slice('[advisor:'.length)}`;
    const source = {
        kind: 'advisor',
        // n4 (user direction): declare the notice form + a collapsed-row summary so
        // the web shell's ContextInjectionRow shows "… · advisor · [nit] <note>"
        // instead of a bare producer label. The severity tag is part of the summary
        // text; per-severity COLOR needs the shell UI (out of plugin reach).
        form: 'notice',
        summary: boundContextSummary(summary),
    };
    return createUserMessage({
        content: [{ type: 'text', text }],
        source,
    });
}
/** True when a note interrupts the primary (concern/blocker — spec §6). */
function isInterrupting(severity) {
    return severity === 'concern' || severity === 'blocker';
}
/**
 * Per-plugin delivery router: severity → channel, the KD-4 agent map, and the
 * immuneTurns cooldown. Cordis-free, so the routing logic is unit-testable.
 */
export class AdvisorDelivery {
    immuneTurns;
    lookupAgent;
    logger;
    /** KD-4 per-session agent map, keyed by `agent.id` (=== session.id). */
    agents = new Map();
    /**
     * immuneTurns latch: remaining stepped primary turns before an interrupting
     * note may steer again (spec §6). A present entry > 0 means armed; the entry
     * is removed when the countdown exhausts.
     */
    cooldown = new Map();
    constructor(options) {
        this.immuneTurns = options.immuneTurns;
        this.lookupAgent = options.lookupAgent ?? (() => undefined);
        this.logger = options.logger ?? console;
    }
    /** KD-4: register an agent on `agent/created` (keyed by `agent.id`). */
    registerAgent(agent) {
        this.agents.set(agent.id, agent);
    }
    /** KD-4: drop an agent — and its cooldown with the session — on `agent/disposed`. */
    unregisterAgent(sessionId) {
        this.agents.delete(sessionId);
        this.cooldown.delete(sessionId);
    }
    /**
     * Update the immuneTurns cooldown length (live config — settings onChange,
     * plan dsh-advisor-settings-n2 T1). The fence is re-armed with the new
     * length on the next real steer; the per-session cooldown countdown itself
     * is untouched, so the delivery semantics (spec §6) never change mid-window.
     */
    setImmuneTurns(value) {
        this.immuneTurns = value;
    }
    /**
     * One completed stepped primary turn (observer `onSteppedTurnEnd`): decrement
     * the immuneTurns countdown. The latch is removed at zero, so the next
     * interrupting note steers again. Total — never throws.
     */
    onSteppedTurnEnd(sessionId) {
        const remaining = this.cooldown.get(sessionId);
        if (remaining === undefined || remaining <= 0)
            return;
        if (remaining <= 1)
            this.cooldown.delete(sessionId);
        else
            this.cooldown.set(sessionId, remaining - 1);
    }
    /**
     * KD-5 reset trigger: a compaction / surface rewrite clears the immuneTurns
     * latch — the session state is being rewritten, so the cooldown's turn-count
     * basis no longer applies. Total — never throws.
     */
    reset(sessionId) {
        this.cooldown.delete(sessionId);
    }
    /**
     * Route one accepted advice note (spec §6, KD-4).
     *
     * Resolves the primary agent via the map, falling back to the registry; a
     * missing agent drops the note with a log (advisory only — never throw,
     * never stall). nit → inject; concern/blocker → steer, unless the
     * immuneTurns fence is armed, in which case they downgrade to inject.
     *
     * @returns the channel delivered on, or `undefined` when dropped (no agent).
     */
    route(sessionId, note) {
        const agent = this.agents.get(sessionId) ?? this.lookupAgent(sessionId);
        if (agent === undefined) {
            this.logger.warn('advisor: note dropped — no agent for session', {
                sessionId,
                severity: note.severity,
            });
            return undefined;
        }
        const message = buildAdvisorMessage(note);
        const cooldown = this.cooldown.get(sessionId) ?? 0;
        if (isInterrupting(note.severity) && cooldown <= 0) {
            // A real steer delivery arms the fence (spec §6). Armed before the call:
            // a failed steer delivery still counts as an attempted interrupt, keeping
            // a throwing agent out of the noise loop — and a downgraded or dropped
            // note never reaches this branch, so the fence never arms on one.
            if (this.immuneTurns > 0)
                this.cooldown.set(sessionId, this.immuneTurns);
            agent.steer(message);
            return 'steer';
        }
        agent.inject(message);
        return 'inject';
    }
}
//# sourceMappingURL=delivery.js.map