/**
 * Copy dictionaries for the Advisor settings card (namespace
 * `settings.advisor`). The English dictionary is the key-set source of truth
 * for the pair; the Chinese dictionary mirrors it exactly.
 *
 * Flat rebuild (2026-09-26): the page title/intro moved to the plugin meta
 * locale files (`locale/en.json` / `locale/zh.json` — the host plugin manager
 * renders them), and the collapsible chrome copy (`collapse`/`expand`/
 * `unsaved`) and the `enabled` checkbox label died with the config-level
 * switch. `providerRequired`/`modelRequired` are unconditional now — there is
 * no enable checkbox to make the pair gate conditional.
 */
/** English strings (the key-set source of truth for this pair). */
export declare const en: {
    loadFailed: string;
    retry: string;
    provider: string;
    providerPlaceholder: string;
    providerRequired: string;
    model: string;
    modelPlaceholder: string;
    modelRequired: string;
    noProviders: string;
    noModels: string;
    staleProvider: string;
    staleModel: string;
    systemPrompt: string;
    systemPromptHint: string;
    immuneTurns: string;
    maxDeltaMessages: string;
    maxTokens: string;
    maxTokensHint: string;
    proseFallback: string;
    proseFallbackHint: string;
    save: string;
    saving: string;
    discard: string;
    saved: string;
    readOnly: string;
    namespaceUnavailable: string;
    sessionTrigger: string;
    sessionExpand: string;
    sessionCollapse: string;
    sessionLoading: string;
    sessionModelHeading: string;
    sessionSourceSession: string;
    sessionSourceGlobal: string;
    sessionNoPair: string;
    sessionLifetime: string;
    sessionAdvisorOff: string;
    sessionGateBlocked: string;
    sessionPinAction: string;
    sessionPending: string;
    sessionReset: string;
    sessionUnavailable: string;
};
/** The settings.advisor namespace key union. */
export type AdvisorKey = keyof typeof en;
/** Chinese strings (same keys as {@link en}). */
export declare const zh: typeof en;
