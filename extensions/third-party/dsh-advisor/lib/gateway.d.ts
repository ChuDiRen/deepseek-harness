/**
 * T1 (plan dsh-advisor-settings-gateway-n5) — host-side `advisor` config
 * gateway: the `/api/advisor/get` + `/api/advisor/set` Remote endpoints.
 *
 * Transport: the typertGateway `/api` interceptor is the single host-wide RPC
 * slot (a plugin must NOT `connection.rpc.intercept('/api')` again — it would
 * throw). Instead this service declares a typertGateway binding (via the
 * `TypertRemoteService` base) plus `@Remote` method markers; the gateway's SRC
 * discovery (`claimsEndpoint` — `ctx.reflect.props` + `remoteMethods`) claims
 * `/api/advisor/get` and `/api/advisor/set`, and the payload contract is
 * exactly one plain-object `args` field whose keys are the method parameter
 * names (`get()` → `{ args: {} }`; `set(patch)` → `{ args: { patch } }`).
 *
 * Data: `get` reads the `AdvisorSettingsBridge` source — the same live entry
 * config the runtime reads (volatile references unwrapped), resolved through
 * the `resolveAdvisorConfig` hard gate (the SSOT for enabled-without-pair
 * disabled-with-reason). `set` validates the patch against the `Config`
 * schema first (unknown-key rejection unchanged — the settings service itself
 * is non-strict and would accept the unknown key), then writes the advisor
 * ENTRY config in-process via `settings.update(ADVISOR_SETTINGS_NAMESPACE, ...)`
 * (dsh 0.1.7-rc.1: the namespace key IS the profile entry id — the bundle row
 * id `advisor` — and the write lands through the config editor into the
 * Loader, which commits the volatile fields and emits `loader/volatile-update`,
 * re-applying the runtime through the bridge with no restart), and returns
 * the new composed value.
 *
 * The settings service is OPTIONAL (no settings service → the bridge source
 * stays the entry, `get` still works; `set` fails with a clear error — KD-G5
 * fallback). The gateway captures the service through a conditional
 * `ctx.inject(['settings'], ...)` child, because `ctx.settings` is only
 * resolvable from a fiber that declares it.
 *
 * The returned config is normalized to the typertGateway JSON wire boundary:
 * absent keys (provider/model/disabledReason, and maxTokens/proseFallback
 * when the raw entry omits them on the S1 containment path) are OMITTED,
 * never present-as-undefined (the gateway's result validation rejects
 * undefined values).
 *
 * @module dsh-advisor/gateway
 */
import type { Context } from '@deepseek-ai/cordis';
import type { TypertContribution } from '@deepseek-ai/dsh-typert-registry';
import { TypertRemoteService } from '@deepseek-ai/dsh-typert-protocol';
import type { AdvisorSettingsBridge } from './settings.js';
import type { AdvisorModelSource } from './commands.js';
import type { AdvisorConfig, ResolvedAdvisorConfig } from './config.js';
/** Patch shape accepted by `advisor.set` — any subset of the config keys. */
export type AdvisorConfigPatch = Partial<AdvisorConfig>;
/** An atomic reviewer-route pair on the wire (JSON-safe; never undefined-valued). */
export interface AdvisorPairWire {
    readonly provider: string;
    readonly model: string;
}
/**
 * The authoritative per-session advisor snapshot (spec §5.3) — the wire value
 * of `advisor/getSession` and of a successful `advisor/setSessionModel`.
 * Absent optional keys are OMITTED (the typertGateway result validation
 * rejects undefined values), never present-as-undefined:
 *
 * - `modelOverride` — the session's pinned atomic pair; omitted while the
 *   session inherits the global defaults;
 * - `modelSource` — where the effective route comes from (`session` = the
 *   pin, `global` = the composed global pair); present iff an effective pair
 *   exists at all;
 * - `effectiveModel` — the effective route; omitted when neither level has a
 *   complete pair;
 * - `disabledReason` — the S4 explicit-gate reason when it blocks.
 */
export interface AdvisorSessionSnapshotWire {
    readonly sessionId: string;
    readonly enabled: boolean;
    /** Live-session lifetime marker (spec §5.3 — the snapshot is never durable). */
    readonly lifetime: 'live-session';
    readonly modelOverride?: AdvisorPairWire;
    readonly modelSource?: AdvisorModelSource;
    readonly effectiveModel?: AdvisorPairWire;
    readonly disabledReason?: string;
}
/**
 * Plugin-domain error tags carried in RETURNED DATA (`{ error: { tag,
 * message } }`) — never new RemoteError codes (dsh's failure vocabulary stays
 * frozen) and never a thrown coded failure for these business outcomes:
 *
 * - `advisor/session-unknown` — the target session is not (or no longer)
 *   live; rejected without allocating any state;
 * - `advisor/unavailable` — this gateway fiber holds no elected owner (no
 *   controller face); the endpoints stay inert rather than guessing;
 * - `advisor/rejected` — the selection failed pair validation (nothing was
 *   written);
 * - `advisor/failed` — the pre-commit `resolveModelInfo` validation failed
 *   (previous selection untouched);
 * - `advisor/superseded` — a newer set/reset superseded the attempt;
 * - `advisor/cancelled` — the attempt was cancelled before commit.
 */
export type AdvisorSessionErrorTag = 'advisor/session-unknown' | 'advisor/unavailable' | 'advisor/rejected' | 'advisor/failed' | 'advisor/superseded' | 'advisor/cancelled';
/** One `advisor/getSession` / `advisor/setSessionModel` result: snapshot or tagged data error. */
export type AdvisorSessionRpcResult = {
    readonly snapshot: AdvisorSessionSnapshotWire;
} | {
    readonly error: {
        readonly tag: AdvisorSessionErrorTag;
        readonly message: string;
    };
};
/** Build one tagged data error (keeps every call site's shape identical). */
export declare function advisorSessionError(tag: AdvisorSessionErrorTag, message: string): AdvisorSessionRpcResult;
/**
 * The elected owner's session face — implemented by the wiring (`index.ts`)
 * against the SAME `AdvisorCommandController` the `/advisor model` commands
 * drive (spec §5.3: one controller, no second state store, no divergence
 * between the command face and the web face). The gateway consults it lazily
 * per request: only the reviewer-claiming fiber assigns it, so a gateway on a
 * non-owner fiber stays inert (`advisor/unavailable`) instead of guessing.
 */
export interface AdvisorSessionGatewayFace {
    /** Authoritative snapshot for one live session (unknown → tagged error). */
    getSession(sessionId: string): AdvisorSessionRpcResult;
    /** Validate + commit a pair through the command controller (same fencing). */
    setSessionModel(sessionId: string, provider: string, model: string): Promise<AdvisorSessionRpcResult>;
    /** Drop the pin and re-inherit (selection: null); never touches the enable override. */
    resetSessionModel(sessionId: string): AdvisorSessionRpcResult;
}
/**
 * The host-side `advisor` config gateway (`/api/advisor/get` +
 * `/api/advisor/set`). Registered as the cordis service key `'advisor'`
 * (namespace defaults to the service key). The `TypertRemoteService` base is
 * kept ONLY for its `typertRemote` binding — the typertGateway's dispatch
 * `validateBinding` requires the visible binding on the live service (a pure
 * instance property, no module-private state). Endpoints are registered
 * EXPLICITLY through `ctx.typert.register(advisorTypertContribution())`
 * (see `apply` in `src/index.ts`) instead of the `@Remote` SRC markers:
 * SRC discovery reads `remoteMethods()` — a module-private WeakMap in
 * `@deepseek-ai/dsh-typert-protocol` — so a locally-linked plugin whose
 * peers resolve outside the host installation never shares that table with
 * the host typertGateway (zero claimed endpoints, `/api/advisor/*` 404).
 * The explicit `TypertRegistry.register` path writes the invocation
 * descriptors into `ctx.typert.local`, which `claimsEndpoint` checks FIRST,
 * so claim + dispatch work regardless of module identity.
 */
export declare class AdvisorConfigGateway extends TypertRemoteService {
    private readonly bridge;
    /** The live settings service once the optional inject child activates. */
    private settings;
    /**
     * The elected owner's session face, resolved LAZILY per request. The
     * reviewer-claiming fiber assigns it after its controller exists (the
     * gateway is constructed before the single-reviewer claim); a `undefined`
     * answer means this fiber owns the service key but not the reviewer role —
     * the session endpoints answer `advisor/unavailable` in data and stay
     * inert (no second controller, no surviving-fiber promotion).
     */
    private readonly sessionControl;
    /**
     * @param ctx - owning context (the plugin fiber's ctx inside `apply`).
     * @param bridge - the same `AdvisorSettingsBridge` the runtime reads, so
     *   get/set always operate on the live composed config.
     * @param sessionControl - lazy access to the elected owner's session face
     *   (B2); defaults to "absent" so a direct construction without the wiring
     *   keeps the session endpoints cleanly unavailable.
     */
    constructor(ctx: Context, bridge: AdvisorSettingsBridge, sessionControl?: () => AdvisorSessionGatewayFace | undefined);
    /**
     * Read the current composed config (schema defaults → entry base → settings
     * user layer) through the hard gate.
     * @returns the resolved config (incl. disabledReason when the gate blocks).
     */
    get(): {
        config: ResolvedAdvisorConfig;
    };
    /**
     * B2 — the authoritative snapshot for one live session
     * (`/api/advisor/getSession`, args `{ sessionId }`). Read-only: never
     * allocates override state (the snapshot rides the wiring's `sessionStatus`
     * readback). Unknown/disposed targets answer `advisor/session-unknown`
     * without touching the controller; a gateway without an elected owner
     * answers `advisor/unavailable`. Business outcomes live in the returned
     * data (plugin-domain tags) — nothing here throws coded failures and the
     * dsh failure vocabulary stays frozen.
     */
    getSession(sessionId: string): AdvisorSessionRpcResult;
    /**
     * B2 — set (or reset) the per-session reviewer route for one live session
     * (`/api/advisor/setSessionModel`, args `{ sessionId, selection }`).
     * `selection: null` = reset (re-inherit the CURRENT global defaults; never
     * touches the enable override). A non-null selection must be the atomic
     * `{ provider, model }` pair and passes the SAME validation as the command
     * face (`parseModelPair` — spec §5.3); the write itself routes through the
     * elected owner's `AdvisorCommandController` (`setModel`/`resetModel`), so
     * pre-commit `resolveModelInfo` validation (60 s, cancellable, no retry),
     * per-session generation fencing, and the route-change semantics are
     * INHERITED, not reimplemented. Unknown/disposed targets are rejected
     * BEFORE the controller runs — no generation is allocated for a dead
     * session. Returns the post-commit snapshot on success.
     */
    setSessionModel(sessionId: string, selection: unknown): Promise<AdvisorSessionRpcResult>;
    /**
     * Validate a config patch and write it to the advisor ENTRY config (live —
     * the Loader commits the volatile fields and the runtime re-applies through
     * the bridge `onChange`; no restart needed).
     * @param patch - any subset of the config keys; unknown keys are rejected
     *   by the `Config` schema before anything is written. The legacy `enabled`
     *   key is the one tolerated exception (config.ts LEGACY_KEYS): it passes
     *   validation but is STRIPPED from the write payload — accepted, never
     *   persisted.
     * @returns the NEW composed config after the write.
     * @throws when the patch fails `Config` validation, or when no settings
     *   service is composed (KD-G5: the write channel is unavailable).
     */
    set(patch: AdvisorConfigPatch): Promise<{
        config: ResolvedAdvisorConfig;
    }>;
    /**
     * Resolve the live entry config through the hard gate. Containment
     * (qc2 W-1): an entry config the resolver rejects (e.g. an unknown key
     * that survived the non-strict schemastery object merge) resolves to
     * disabled-with-reason carrying the message — the gateway never fails the
     * RPC on a bad config, and gate semantics hold (no model call can start).
     * S1: when the raw source is still readable, the fallback seeds its scalar
     * latches (systemPrompt / immuneTurns / maxDeltaMessages / maxTokens /
     * proseFallback) instead of hardcoded defaults, so an invalid config only
     * drops the offending keys.
     */
    private readConfig;
}
/**
 * The explicit typert contribution for the `advisor` gateway endpoints —
 * registered via `ctx.typert.register(...)` (see `apply` in `src/index.ts`).
 * The descriptors mirror exactly what the former SRC discovery derived from
 * the `@Remote` markers (`src:advisor#<endpoint>` identity shape, direct
 * receiver, JSON wire params with `src-json` codec), so the host
 * typertGateway claim + dispatch behavior is byte-for-byte the same — the
 * only difference is the registration does not depend on the module-private
 * `remoteMethods` marker table, which a locally-linked plugin can never
 * share with the host installation.
 */
export declare function advisorTypertContribution(): TypertContribution;
