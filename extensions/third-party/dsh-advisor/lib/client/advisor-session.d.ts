/**
 * Advisor session header action (B2 — issue #88 web session control): the
 * entry registered into the shell-declared `conversation.session.header.actions`
 * list slot (title-adjacent Session actions — NOT the singleton
 * primary-model slot, NOT the root plugin card; the global card stays
 * global-only). The slot is session-scoped, so the framework resolves the
 * bound SessionId into the inject factory (src/client/index.ts), which builds
 * ONE {@link AdvisorSessionModelController} per session scope binding — the
 * renderer memoizes that face per (entry × session binding), so the instance
 * lives and dies with the binding and every fetch/write carries its own
 * sessionId (a late response for an old binding can never render another
 * session's state).
 *
 * The control shows the authoritative session snapshot — the effective
 * reviewer pair, its source (`session`/`global`), the live-session lifetime,
 * the effective switch, and the S4 gate reason when blocked — and supports
 * set (provider + model, staged through the shared provider directory) and
 * **Use global default** (reset). It rides ONLY the plugin session endpoints
 * (`/api/advisor/getSession` + `/api/advisor/setSessionModel`); when the
 * surface is unavailable the menu renders a notice and offers NO writes — it
 * never falls back to the global `advisor/set` channel.
 *
 * Fetch discipline: fetch on menu open, on binding change (a new binding gets
 * a fresh controller whose first open fetches), and on refresh signals while
 * open (connection reset / window focus — the epoch store bumps, the watcher
 * refetches). Every response settles through the controller's request fence,
 * so a superseded (stale) response is discarded wholesale. NO push-event
 * contract, NO polling: an open menu is a refreshable snapshot, and the
 * closed trigger is NEUTRAL — the plugin name only, never a model label
 * falsely claiming continuous synchronization.
 */
import { type ReactNode } from 'react';
import type { InjectFace, PropsLocale, PropsRuntime } from '@deepseek-ai/dsh-client-ui-slots';
import type { SnapshotStore } from '@deepseek-ai/dsh-client-store';
import type { AdvisorSessionMenuState, AdvisorSessionModelController, AdvisorSettingsState, AdvisorSettingsStore } from './advisor-store.ts';
/**
 * Injected dependencies of {@link AdvisorSessionAction} (slot `inject`,
 * built per session binding by the registration's inject factory). The
 * `hooks` compartment carries the bare snapshot sources; the renderer binds
 * each as a `use<Name>` selector hook the component consumes.
 */
export interface AdvisorSessionActionInjected {
    /** The session this occurrence is bound to (framework-resolved). */
    readonly sessionId: string;
    /** The per-session session-model controller (one per binding). */
    readonly controller: AdvisorSessionModelController;
    /** The shared provider/model directory (READ-only reuse of the card's store). */
    readonly directory: AdvisorSettingsStore;
    /** Bare snapshot sources the renderer binds as selector hooks. */
    readonly hooks: {
        /** The per-session menu snapshot. */
        readonly snapshot: SnapshotStore<AdvisorSessionMenuState>;
        /** Refresh-signal epoch (bumped on connection reset / window focus). */
        readonly refreshSignal: SnapshotStore<{
            epoch: number;
        }>;
        /** The shared provider/model directory state. */
        readonly directory: SnapshotStore<AdvisorSettingsState>;
    };
}
/**
 * Props the renderer binds for the action: the session-scoped runtime share
 * (the slot's owner is a marker — no owner-specific values), the
 * framework-synthesized `t` seat for the declared `settings.advisor`
 * namespace, and the registrant's per-binding business face.
 */
export type AdvisorSessionActionProps = PropsRuntime<'conversation.session.header.actions'> & PropsLocale<'settings.advisor'> & InjectFace<AdvisorSessionActionInjected>;
/**
 * Render the session header's Advisor action: a neutral trigger plus, when
 * open, a popover panel holding the refreshable snapshot and the pin/reset
 * controls. The panel portals to `document.body` and takes viewport-fixed
 * coordinates from the trigger rect — the session header sits in a clipping
 * column (`overflow: hidden`), so an in-place absolute panel is cut off at the
 * column edge (the same constraint JobListAction's portaled list answers).
 * @param props - slot-delivered injected dependencies and the synthesized t seat.
 * @returns the action.
 */
export declare function AdvisorSessionAction(props: AdvisorSessionActionProps): ReactNode;
