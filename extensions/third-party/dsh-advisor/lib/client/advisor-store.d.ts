/**
 * Advisor settings card store (plan dsh-advisor-settings-gateway-n5, task 2).
 * One snapshot over the wire faces the card renders from; the host stays the
 * single fact source — every mutation writes through the host `advisor` config
 * gateway (`connection.rpc.call('/api', 'advisor/get' | 'advisor/set', …)`),
 * and the page re-renders from the next get, pushed or refetched.
 *
 * Data-source split (KD-G3):
 * - the **advisor config** reads/writes ride the gateway RPC channel
 *   (`/api/advisor/get` returns `{ config }`, `/api/advisor/set` accepts
 *   `{ patch }` and returns the new composed config) — the `advisor` settings
 *   namespace is NOT on the apiproxy exposed-namespaces whitelist, so the
 *   old `api.settings.describe`/`mutate` path is dead for it and the gateway
 *   is the only web-visible channel (host side: `src/gateway.ts`, `@Remote`
 *   get/set against the live `AdvisorSettingsBridge` source);
 * - the **provider/model directory** and the settings namespaces ride the
 *   client Remote assembly (`ctx.remote.llm.listConfigurableProviders` /
 *   `ctx.remote.settings.describe` / `ctx.remote.session.modelCatalog` — the
 *   alpha.2 replacement for the removed `connection.api` surface; the
 *   `llm-deepseek` namespaces ARE in the exposed describe set).
 *
 * The returned config is the RESOLVED config (through the host hard gate):
 * absent keys (provider/model/disabledReason) are omitted by the wire
 * normalization, never present-as-undefined — the draft seeds treat them as
 * missing. Apply diffs the draft against the last-read config (the seed) and
 * sends only the changed keys as the `{ patch }`; clearing a provider/model
 * the seed pins stores an explicit `''` override (the gateway merge cannot
 * express an unset, and the resolver treats `''` as absent). Clearing a number
 * input leaves the field empty and omits the key from the patch.
 *
 * The join mirrors the ui-models Models page (store.ts):
 * - **configured** provider = its settings namespace resolves AND its profile
 *   resolves (`settingsPath` empty → whole section, else `getPath` on the
 *   namespace value);
 * - **model options** = the provider profile's declared `models` first
 *   (KD-S2), else the `llm.models` catalog group for that provider, else
 *   empty options + a reason (guidance copy lives in the card);
 * - the **draft** is seeded from the RESOLVED advisor config so the form
 *   always shows the effective configuration (KD-G5: `advisor.get` failure →
 *   the card shows the config-channel notice instead of a writable-looking
 *   form — never a hard load error, and never Apply).
 */
import type { ClientConnectionRpc } from '@deepseek-ai/dsh-client-connection/client';
import type { LlmConfigurableProvider } from '@deepseek-ai/dsh-llm/types';
import type { SettingsDescribeValue, SettingsNamespaceView } from '@deepseek-ai/dsh-settings/types';
import type { ModelCatalog } from '@deepseek-ai/dsh-api-session-controller/types';
import type { RemoteResult } from '@deepseek-ai/dsh-typert-protocol';
import type { SnapshotStore } from '@deepseek-ai/dsh-client-store';
import type { SettingsSchemaService } from '@deepseek-ai/dsh-client-ui-settings/client';
/**
 * The schema face the card store uses: ui-settings owns the immutable
 * path writers (`ctx.settingsSchema`); this narrow pick hides the Cordis
 * service identity from the store and its tests.
 */
export type SettingsSchemaOperations = Pick<SettingsSchemaService, 'getPath' | 'setPath' | 'deletePath'>;
/**
 * The wire face the card store uses (KD-G3, alpha.2): the provider/model
 * directory and the settings describe surface ride the client Remote
 * assembly (`ctx.remote` — `llm.listConfigurableProviders`,
 * `settings.describe`, `session.modelCatalog`); the advisor config itself
 * stays on the gateway RPC channel (`rpc.call('/api', …)`) because the
 * `advisor` namespace is not exposed on the settings describe wire. Narrow
 * pick of the assembled `ClientRemote` so the store and its tests never
 * depend on the generated namespace surface.
 */
export interface AdvisorStoreRemote {
    llm: {
        listConfigurableProviders(): Promise<RemoteResult<LlmConfigurableProvider[]>>;
    };
    settings: {
        describe(): Promise<RemoteResult<SettingsDescribeValue>>;
    };
    session: {
        modelCatalog(): Promise<RemoteResult<ModelCatalog>>;
    };
}
/**
 * The wire `config` value the host gateway returns — mirror of the node-side
 * `ResolvedAdvisorConfig` (src/config.ts). Kept as a local structural type
 * because the client bundle may not value-import the node-side module: the
 * wire normalization omits absent keys (provider/model/disabledReason are
 * simply missing from the JSON), so every optional key reads as undefined.
 */
export interface AdvisorConfigView {
    /**
     * Read-only wire fact — the post-gate switch (false while the gate blocks).
     * NOT a draft field: there is no config-level `enabled` key (2026-09-26;
     * the plugin-row toggle is the switch), so the draft cannot write it and
     * the card renders it nowhere.
     */
    enabled: boolean;
    /** Provider route; absent when unset. */
    provider?: string;
    /** Model id; absent when unset. */
    model?: string;
    /** System prompt override ('' = built-in reviewer prompt). */
    systemPrompt: string;
    /** Cooldown after a delivered interrupt; integer ≥ 0. */
    immuneTurns: number;
    /** Delta window; integer ≥ 0, 0 = unbounded. */
    maxDeltaMessages: number;
    /**
     * Token budget for one advisor call (KD-I1, issue #102); integer
     * 128..16384. Absent on plain-object entries → the runtime default
     * `ADVISOR_MAX_TOKENS` (768), mirroring src/config.ts.
     */
    maxTokens?: number;
    /**
     * Opt-in prose fallback switch (KD-I2, issue #102). Absent on plain-object
     * entries → the runtime default false, mirroring src/config.ts.
     */
    proseFallback?: boolean;
    /** Present iff the advisor is disabled by the explicit model gate. */
    disabledReason?: string;
}
/** One provider row the card offers (configured providers only, KD-S2). */
export interface ProviderOption {
    /** Provider route id. */
    provider: string;
    /** Human-readable provider name. */
    displayName: string;
    /** Settings namespace whose section configures this provider. */
    settingsNs: string;
    /** Path from that section's root to the provider's profile object. */
    settingsPath: readonly string[];
    /** Whether the profile resolves (always true inside the option list). */
    configured: boolean;
}
/** One model option offered for a provider. */
export interface ModelOption {
    id: string;
    name: string;
    description?: string;
}
/** Why a provider offers no model options (KD-S2 empty case → guidance copy). */
export type ModelsEmptyReason = 
/** The resolved profile declares an (empty) `models` list — profile wins. */
'profile-empty'
/** No profile models; the catalog group exists but is empty. */
 | 'catalog-empty'
/** No profile models; the catalog has no group for this provider. */
 | 'unavailable';
/**
 * The user-layer draft the form edits
 * (provider/model/systemPrompt/immuneTurns/maxDeltaMessages/maxTokens/proseFallback).
 */
export interface AdvisorDraft {
    /** Provider route; required (non-empty). */
    provider?: string;
    /** Model id; required (non-empty). */
    model?: string;
    /** Optional system prompt override; '' = built-in reviewer prompt. */
    systemPrompt: string;
    /** Cooldown after a delivered interrupt; integer ≥ 0, default 3. Cleared input → undefined (left unchanged on apply). */
    immuneTurns?: number;
    /** Delta window; integer ≥ 0, default 60, 0 = unbounded. Cleared input → undefined (left unchanged on apply). */
    maxDeltaMessages?: number;
    /**
     * Token budget for one advisor call (KD-I1, issue #102); integer
     * 128..16384, default 768. Cleared input → undefined (left unchanged on
     * apply).
     */
    maxTokens?: number;
    /** Opt-in prose fallback (KD-I2, issue #102); default false. */
    proseFallback?: boolean;
}
/** Why an Apply failed (copy keys resolve in the card; raw text passes through). */
export type ApplyFailure = {
    kind: 'gate';
    reason: 'provider' | 'model';
} | {
    kind: 'message';
    message: string;
};
/** Apply lifecycle feedback the form renders. */
export type ApplyState = {
    kind: 'idle';
} | {
    kind: 'saving';
} | {
    kind: 'saved';
} | {
    kind: 'error';
    failure: ApplyFailure;
};
/** Page snapshot. */
export interface AdvisorSettingsState {
    status: 'idle' | 'loading' | 'ready' | 'error';
    /** Whole-load failure text; write failures stay in the apply state. */
    error: string | null;
    /** Whether the settings provider accepts writes. */
    writable: boolean;
    /** Configured provider options (KD-S2: configured providers only). */
    providers: readonly ProviderOption[];
    /** Model options per provider route, once resolved. */
    modelsByProvider: Readonly<Record<string, readonly ModelOption[]>>;
    /** Empty-options reason per provider route (KD-S2 guidance). */
    modelsEmptyReason: Readonly<Record<string, ModelsEmptyReason>>;
    /** Namespace views by ns, for the provider join. */
    namespaces: Readonly<Record<string, SettingsNamespaceView>>;
    /**
     * Whether the `advisor.get` gateway endpoint was reachable on the last load
     * (KD-G3/G5): success = a writable form; failure (gateway not ready, no
     * settings service on the host) = the card shows the config-channel
     * notice instead of a writable-looking form and never offers Save.
     */
    advisorPresent: boolean;
    /**
     * Latch of the last SETTLED readiness: true iff the last ready update
     * resolved `config === undefined` (qc1 S-2 fix wave). The snapshot cannot
     * tell a "refresh of a degraded card" from a "first mount not yet settled"
     * while `status === 'loading'` (both read loading + advisorPresent=false),
     * so the card derives its degraded notice from this latch during loading —
     * keeping the config-channel notice visible through a background refresh
     * of a degraded card. Set ONLY in the ready update (the load-error path
     * leaves it alone — the error state has its own always-on branch).
     */
    degraded: boolean;
    /**
     * Whether the draft holds edits a save would write — the save/discard
     * disabled semantics (upstream CardShell.dirty). Derived as
     * `patchFor(draft)` non-empty (KD-U2, plan
     * dsh-advisor-plugin-config-card-ux task 2), recomputed on load (seed
     * settled, real config resolved only), every draft mutation, discard and a
     * successful apply — always inside the same `store.update` callback that
     * mutates the draft/seed, never via a snapshot read + second write.
     */
    dirty: boolean;
    /** The form draft (seeded from the resolved config; never re-seeded by refreshes). */
    draft: AdvisorDraft;
    /** Apply lifecycle feedback. */
    applyState: ApplyState;
}
/**
 * The advisor settings card controller (one per settings surface).
 */
export declare class AdvisorSettingsStore {
    private readonly remote;
    private readonly rpc;
    private readonly schema;
    /** The snapshot the card renders from (uSES-safe store). */
    readonly store: SnapshotStore<AdvisorSettingsState>;
    /** Latest load wins; an older response never overwrites a newer one. */
    private generation;
    /** Host-scoped model catalog; cached only on success (a transient failure stays uncached and is refetched). */
    private catalog;
    /** In-flight host-scoped catalog fetch; one promise shared across providers. */
    private catalogPromise;
    /**
     * Bumped by every successful load(): an in-flight catalog fetch started
     * before a bump is stale (the connection/reset invalidation that triggered
     * the reload happened mid-fetch) and caches nothing (qc1 W-1 / qc3 S-1).
     */
    private catalogGeneration;
    /** In-flight model resolutions (one per provider). */
    private inflightModels;
    /** The draft is seeded once (first load); refreshes never clobber edits. */
    private draftSeeded;
    /** The resolved advisor config at the last get/apply (patch diff baseline). */
    private seed;
    /**
     * @param remote - the client Remote assembly face (llm/settings/session
     *   namespaces) for the provider/model directory (the advisor namespace is
     *   NOT on that wire).
     * @param rpc - the connection's generic RPC caller for the host gateway
     *   channel (`/api`), injected from the connection handle.
     */
    constructor(remote: AdvisorStoreRemote, rpc: ClientConnectionRpc, schema: SettingsSchemaOperations);
    /** Profile-declared models (the provider's `models` directory), when the profile has one. */
    private profileModels;
    /**
     * Refresh the whole page snapshot: the provider directory and the settings
     * namespaces in parallel, then the advisor config over the gateway channel,
     * then the provider join and the draft seed. A provider-directory failure
     * keeps the last good rows and surfaces the error; an `advisor.get` failure
     * is NOT a page error (KD-G5 — the card shows the config-channel notice,
     * the provider directory stays usable). The draft is seeded only on the
     * first load — pushed refreshes never discard in-progress edits (mirror the
     * ProviderEditor draft lifetime).
     * @returns nothing; the snapshot carries the outcome.
     */
    load(): Promise<void>;
    /**
     * Resolve the model options for one provider (KD-S2): profile-declared
     * `models` win; otherwise the `session.modelCatalog` group for that
     * provider; neither → empty options + a reason. The host-scoped catalog is
     * fetched at most once (concurrent first resolutions share one in-flight
     * fetch) and cached only on success. No-op for unconfigured providers.
     * @param provider - provider route id.
     * @returns nothing; the snapshot carries the outcome.
     */
    ensureModels(provider: string): Promise<void>;
    /**
     * Fetch the host-scoped model catalog. A failure (wire rejection or throw)
     * leaves the cache empty so the next resolution refetches — a transient
     * failure is never sticky for the store lifetime. A fetch started before a
     * load() bumped `catalogGeneration` is stale (the invalidation that caused
     * the reload happened mid-fetch) and caches nothing.
     */
    private fetchCatalog;
    /** Set or clear the provider ('' clears); switches invalidate the chosen model. */
    setProvider(provider: string): void;
    /** Set or clear the model ('' clears). */
    setModel(model: string): void;
    /** Set the system prompt override. */
    setSystemPrompt(prompt: string): void;
    /** Set the immune-turns cooldown (int ≥ 0; non-numeric input keeps the current value; undefined clears → omitted from patch). */
    setImmuneTurns(value: number | undefined): void;
    /** Set the delta-message window (int ≥ 0; non-numeric input keeps the current value; undefined clears → omitted from patch). */
    setMaxDeltaMessages(value: number | undefined): void;
    /**
     * Set the advisor token budget (KD-I1, issue #102: int clamped into
     * 128..16384 — the schema bounds; non-numeric input keeps the current
     * value; undefined clears → omitted from patch).
     */
    setMaxTokens(value: number | undefined): void;
    /** Set the opt-in prose fallback (KD-I2, issue #102). */
    setProseFallback(value: boolean): void;
    /**
     * Refuse in a read-only environment (store-side defense-in-depth for the
     * W-1 invariant — a write must never be issued when the UI declares the
     * settings service read-only), then validate the draft (KD-S4 gate) and
     * write the changed keys as a config patch through the gateway channel
     * (`/api/advisor/set`). Any failure (business rejection or transport)
     * surfaces the message failure and keeps the form for retry — the gateway
     * merge has no revision guard, so the old settings-conflict branch is
     * replaced by plain error handling (KD-G3). Nothing to write → the apply
     * reports saved without a call.
     * @returns nothing; the apply state carries the outcome.
     */
    apply(): Promise<void>;
    /**
     * Drop the current draft edits and rewind the form to the last-known host
     * config (the seed from the last get/apply). The card chrome mirrors the
     * upstream plugin cards' Save/Discard pair (KD-4): unlike the upstream
     * staged CardForm, this store's edits mutate the draft in place, so discard
     * rewinds the draft instead of dropping a staging layer. Pure client-side
     * revert — no gateway write (the host stays the single fact source; a
     * follow-up apply diffs against the restored seed and sends nothing).
     *
     * Invariant (qc3 N-2): a mid-apply discard is UNGUARDED at the store level
     * BY DESIGN — the UI disables Discard while a save is in flight
     * (`disabled={busy}` on the card, `busy = !writable || saving`), so the
     * interleaving cannot occur from the UI and no behavior guard is added
     * here. A programmatic mid-apply discard would only rewind the draft before
     * the in-flight apply adopts the returned config as the new seed — the
     * host write is unaffected.
     */
    discard(): void;
    /**
     * The minimal config patch making the effective config match the draft —
     * only keys whose value differs from the last-read seed are sent, so a
     * stale read never clobbers concurrent changes to untouched keys and base
     * (plugin-row) values stay in place. A cleared provider/model the seed pins
     * becomes an explicit `''` override (the gateway merge cannot express an
     * unset, and the resolver treats '' as absent); a cleared number field is
     * omitted (the stored value stays unchanged).
     */
    private patchFor;
    /**
     * The dirty derivation (KD-U2, plan dsh-advisor-plugin-config-card-ux task
     * 2): the draft holds edits a save would write iff the minimal patch
     * against the current seed is non-empty. Takes the DRAFT being mutated and
     * reads `this.seed` — it must be called INSIDE the same `store.update`
     * callback that mutates the draft/seed, never via a snapshot read + second
     * write (the frozen-snapshot write would be dropped by the snapshot store).
     */
    private recomputeDirty;
    /** Edit one always-present draft field via the settings schema path writer. */
    private setField;
    /** Remove one optional draft field via the settings schema path writer. */
    private clearField;
    /** A bounded integer clamp (int ≥ min, ≤ max); a non-finite input keeps the fallback. */
    private clampInt;
}
/**
 * Refetch the card snapshot only after its first load: an unopened Advisor
 * card must not fetch on background invalidations.
 * @param controller - the card store.
 */
export declare function refreshIfLoaded(controller: AdvisorSettingsStore): void;
/**
 * The wire `snapshot` value of `/api/advisor/getSession` and of a successful
 * `/api/advisor/setSessionModel` — client mirror of the node-side
 * `AdvisorSessionSnapshotWire` (src/gateway.ts). Kept as a local structural
 * type because the client bundle may not value-import the node-side module;
 * the wire normalization omits absent keys (modelOverride / modelSource /
 * effectiveModel / disabledReason are simply missing from the JSON).
 */
export interface AdvisorSessionSnapshotView {
    /** The session the snapshot describes (echoes the request's binding). */
    sessionId: string;
    /** Effective switch for this session (session override ?? global). */
    enabled: boolean;
    /** Live-session lifetime marker — the snapshot is never durable. */
    lifetime: 'live-session';
    /** The session's pinned atomic pair; absent while it inherits. */
    modelOverride?: {
        provider: string;
        model: string;
    };
    /** Where the effective route comes from; present iff a pair exists. */
    modelSource?: 'session' | 'global';
    /** The effective route; absent when neither level has a complete pair. */
    effectiveModel?: {
        provider: string;
        model: string;
    };
    /** Present iff the S4 explicit gate blocks model calls. */
    disabledReason?: string;
}
/** One `setSessionModel` selection on the wire: an atomic pair, or null (= reset). */
export type AdvisorSessionSelection = {
    readonly provider: string;
    readonly model: string;
} | null;
/**
 * The RPC result union of the session endpoints: a snapshot, or a
 * plugin-domain tagged error carried in the returned data (never a thrown
 * coded failure — the dsh failure vocabulary stays frozen).
 */
export interface AdvisorSessionRpcPayload {
    snapshot?: AdvisorSessionSnapshotView;
    error?: {
        tag: string;
        message: string;
    };
}
/** The session header action's menu snapshot. */
export interface AdvisorSessionMenuState {
    /** idle → loading (first fetch) → ready; refreshes keep `snapshot` visible. */
    phase: 'idle' | 'loading' | 'ready';
    /** The authoritative snapshot; null until the first successful load. */
    snapshot: AdvisorSessionSnapshotView | null;
    /** Last failure text for display (null when healthy). */
    error: string | null;
    /**
     * Latch: the session control surface is unavailable (no elected owner on
     * the host, the target session is unknown/disposed, or the channel failed).
     * An unavailable menu offers NO writes — it never falls back to the global
     * `advisor/set` channel. Recovered by a later successful refresh.
     */
    unavailable: boolean;
    /** A set/reset write is in flight. */
    pending: boolean;
}
/**
 * Per-session controller for the session header's Advisor action (one
 * instance per session — the slot renderer memoizes the inject face per
 * entry × session scope binding, so the instance lives and dies with the
 * binding). Every call sends ITS OWN `sessionId` and commits only into its
 * own store: a late response for an old binding can never mutate another
 * session's state (the structural binding fence). Ordering within one session
 * is fenced by a monotonic `requestSeq` — a newer open/refresh/write
 * supersedes an unresolved older op, whose settle is discarded wholesale
 * (the same generation-fence shape the host controller uses).
 */
export declare class AdvisorSessionModelController {
    private readonly rpc;
    readonly sessionId: string;
    /** The snapshot the menu renders from (uSES-safe store). */
    readonly store: SnapshotStore<AdvisorSessionMenuState>;
    /** Fence token: a newer op makes every older settle stale. */
    private requestSeq;
    /** Last consumed refresh-signal epoch (reconnect / focus bumps). */
    private lastSignal;
    constructor(sessionId: string, rpc: ClientConnectionRpc);
    /**
     * Record the refresh-signal epoch and report whether it is NEW. The open
     * handler always refetches and merely marks the signal current; the render
     * watcher calls this while open and refetches only on a true return (a
     * reconnect/focus bump). Idempotent per epoch, so a re-render never
     * double-fetches.
     */
    takeSignal(epoch: number): boolean;
    /**
     * Fetch the authoritative snapshot (`/api/advisor/getSession`). Called on
     * menu open and on every refresh signal while open. A stale settle (a newer
     * op superseded this fetch) touches nothing. An `advisor/unavailable` /
     * `advisor/session-unknown` tag or a transport failure latches
     * `unavailable` (writes stay off until a later successful refresh); other
     * tagged outcomes leave the surface usable with the error shown.
     */
    refresh(): Promise<void>;
    /**
     * Pin the atomic `{provider, model}` pair for THIS session
     * (`/api/advisor/setSessionModel`, selection = the pair). Refuses outright
     * while `unavailable` (store-side defense-in-depth — an unavailable menu
     * must never issue a write, and must never fall back to the global
     * `advisor/set` channel). The host validates the pair through the same
     * rules as the `/advisor model set` command face.
     */
    setSessionModel(provider: string, model: string): Promise<void>;
    /**
     * Drop the session pin and re-inherit the CURRENT global defaults
     * (`selection: null`). Never touches the enable override; reset to a
     * missing global pair still succeeds — the returned snapshot reports the
     * gate-blocked/no-call state, which the menu renders truthfully.
     */
    resetSessionModel(): Promise<void>;
    /** Shared write path (both arms ride the same endpoint + fence + outcome mapping). */
    private write;
    /**
     * Commit one settled outcome. Guards (seq checked by the callers before
     * reaching here): tagged `advisor/unavailable` / `advisor/session-unknown`
     * and transport failures latch `unavailable` (no writes offered, last good
     * snapshot kept for context); other tagged outcomes keep the surface usable
     * and surface the message (the host left the previous selection untouched);
     * a snapshot commits as the new authoritative state.
     */
    private applyOutcome;
}
