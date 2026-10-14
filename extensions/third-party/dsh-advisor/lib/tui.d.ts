/**
 * dsh-tui client surface (plan dsh-advisor-tui-client-n8, T1) — the
 * `tuiCommandTrees` /advisor provider.
 *
 * In a `dsh --profile dsh-tui` terminal session the plugin's `/advisor`
 * command (registered through the conditional `ctx.inject(['commands'], ...)`
 * child) already lands in the TUI `/` menu via the command-registry merge.
 * What the TUI cannot infer is the LOCALIZED row description and the typed
 * subcommand COMPLETION — those come from the optional `tuiCommandTrees`
 * host service (`src/dsh-adapter/command-trees.ts` in dsh-TUI): a provider
 * declares `root`, zh/en `descriptions`, and a `children(canonicalPath)`
 * completion tree (root at index 0; the TUI asks at depth 2 when completing
 * `/advisor <sub> ⋯`).
 *
 * This module is the advisor's TUI seam: `installTuiClient` conditionally
 * injects `tuiCommandTrees` and registers the `/advisor` tree when the
 * service exists; a profile without the `dsh-tui-command-trees` row (or any
 * non-TUI host) gets a clean no-op. The provider shapes are minimal LOCAL
 * structural copies of the dsh-TUI types — the advisor MUST NOT import
 * `@deepseek-harness-tui/dsh-tui` (zero new peers, plan Global Constraint),
 * so drift against the upstream shape is bounded to the structural cast at
 * the inject boundary and pinned by `tests/tui-client.test.ts`.
 *
 * @module dsh-advisor/tui
 */
import type { Context } from '@deepseek-ai/cordis';
/** Localized (zh/en) descriptions — structural mirror of dsh-TUI's
 * `LocalizedDescriptions` (the TUI `/` row + completion descriptions). */
export type TuiLocalizedDescriptions = Readonly<Partial<Record<'zh' | 'en', string>>>;
/** One completion node — structural mirror of dsh-TUI's
 * `CommandCompletionNode` (`src/commands.ts` in dsh-TUI). */
export interface TuiCommandCompletionNode {
    name: string;
    aliases?: readonly string[];
    description: string;
    descriptions?: TuiLocalizedDescriptions;
    tag?: string;
    descriptionKey?: string;
}
/** A `/`-menu command tree provider — structural mirror of dsh-TUI's
 * `TuiCommandTreeProvider`. `children` receives the canonical path with the
 * root at index 0. */
export interface TuiCommandTreeProvider {
    root: string;
    descriptions?: TuiLocalizedDescriptions;
    children(canonicalPath: readonly string[]): readonly TuiCommandCompletionNode[];
}
/** The `/advisor` tree root (matches the command registry name). */
export declare const ADVISOR_TUI_ROOT = "advisor";
/**
 * Install the advisor's TUI client surface: register the `/advisor`
 * `tuiCommandTrees` provider when the host service exists (conditional
 * inject; absent service → clean no-op). Called from `apply()` AFTER the
 * single-reviewer claim, so the tree registers at most once per process
 * (a duplicate-root registration would throw in the host registry). The
 * structural accessor keeps the inject key in the standard position: the
 * cordis Context has no `tuiCommandTrees` augmentation in this repo, so the
 * service is read through a local structural cast.
 */
export declare function installTuiClient(ctx: Context): void;
