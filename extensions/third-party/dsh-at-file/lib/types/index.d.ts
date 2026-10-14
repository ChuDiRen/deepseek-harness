/**
 * dsh-at-file host plugin: mounts the `atFile` Typert Remote service
 * (workspace index search for the browser's @file picker), registers its
 * strict Typert manifest, registers the settings enable switch, and marks
 * validated `@path` references at each agent's pre-step boundary. The plugin
 * never reads mentioned file contents. The client half
 * ships in the same package (`./client`); the web server serves it under
 * /plugins/dsh-at-file/client.js.
 */
import type { Context } from '@deepseek-ai/cordis';
import z from '@deepseek-ai/schemastery';
/** Cordis plugin name (the Loader entry and client bundle id). */
export declare const name = "dsh-at-file";
/** Services required before load: the Typert registry, the settings provider, and the agent registry. */
export declare const inject: string[];
export { DEFAULT_IGNORE_DIRS, DEFAULT_IGNORE_FILES } from './defaults.ts';
/** Host plugin configuration, validated at load by the Loader. */
export interface Config {
    /** Hard cap on indexed files per workspace; the walk stops and reports truncation. */
    maxIndexedFiles: number;
    /** Directory basenames the index walk skips entirely. */
    ignoreDirs: string[];
    /** Whether the @file surface is enabled; false hides picker, dock, and reference injection. */
    enabled: boolean;
    /** Global Exact and Regex basename filters; legacy strings are insensitive Exact rules. */
    ignoreFiles: (string | {
        kind: 'exact' | 'regex';
        pattern: string;
        caseSensitive: boolean;
    })[];
    /** Whether an empty global filter list was explicitly saved by a current client. */
    ignoreFilesConfigured: boolean;
    /** Workspace-specific filters added to the global filters. */
    workspaceIgnoreFiles: {
        workspace: string;
        ignoreFiles: (string | {
            kind: 'exact' | 'regex';
            pattern: string;
            caseSensitive: boolean;
        })[];
    }[];
    /** Whether @ tokens inserted through paste stay ordinary text. */
    ignorePastedMentions: boolean;
}
/**
 * Configuration schema: deployment-varying bounds stay tunable from
 * the profile patch. The inferred schema type keeps the callable form accepting
 * partial input, so `Config({})` yields the defaults (what the Loader does
 * for Loader compositions).
 */
export declare const Config: z<Schemastery.ObjectS<NoInfer<{
    maxIndexedFiles: z<number, number, "defined">;
    ignoreDirs: z<string[], string[], "defined">;
    enabled: z<boolean, boolean, "defined">;
    ignoreFiles: z<(string | ({
        kind?: "exact" | "regex" | null | undefined;
        pattern?: string | null | undefined;
        caseSensitive?: boolean | null | undefined;
    } & import("@deepseek-ai/cosmokit").Dict))[], (string | Schemastery.ObjectT<NoInfer<{
        kind: z<"exact" | "regex", "exact" | "regex", "plain">;
        pattern: z<string, string, "plain">;
        caseSensitive: z<boolean, boolean, "plain">;
    }>>)[], "defined">;
    ignoreFilesConfigured: z<boolean, boolean, "defined">;
    workspaceIgnoreFiles: z<({
        workspace?: string | null | undefined;
        ignoreFiles?: (string | ({
            kind?: "exact" | "regex" | null | undefined;
            pattern?: string | null | undefined;
            caseSensitive?: boolean | null | undefined;
        } & import("@deepseek-ai/cosmokit").Dict))[] | null | undefined;
    } & import("@deepseek-ai/cosmokit").Dict)[], Schemastery.ObjectT<NoInfer<{
        workspace: z<string, string, "plain">;
        ignoreFiles: z<(string | ({
            kind?: "exact" | "regex" | null | undefined;
            pattern?: string | null | undefined;
            caseSensitive?: boolean | null | undefined;
        } & import("@deepseek-ai/cosmokit").Dict))[], (string | Schemastery.ObjectT<NoInfer<{
            kind: z<"exact" | "regex", "exact" | "regex", "plain">;
            pattern: z<string, string, "plain">;
            caseSensitive: z<boolean, boolean, "plain">;
        }>>)[], "plain">;
    }>>[], "defined">;
    ignorePastedMentions: z<boolean, boolean, "defined">;
}>>, Schemastery.ObjectT<NoInfer<{
    maxIndexedFiles: z<number, number, "defined">;
    ignoreDirs: z<string[], string[], "defined">;
    enabled: z<boolean, boolean, "defined">;
    ignoreFiles: z<(string | ({
        kind?: "exact" | "regex" | null | undefined;
        pattern?: string | null | undefined;
        caseSensitive?: boolean | null | undefined;
    } & import("@deepseek-ai/cosmokit").Dict))[], (string | Schemastery.ObjectT<NoInfer<{
        kind: z<"exact" | "regex", "exact" | "regex", "plain">;
        pattern: z<string, string, "plain">;
        caseSensitive: z<boolean, boolean, "plain">;
    }>>)[], "defined">;
    ignoreFilesConfigured: z<boolean, boolean, "defined">;
    workspaceIgnoreFiles: z<({
        workspace?: string | null | undefined;
        ignoreFiles?: (string | ({
            kind?: "exact" | "regex" | null | undefined;
            pattern?: string | null | undefined;
            caseSensitive?: boolean | null | undefined;
        } & import("@deepseek-ai/cosmokit").Dict))[] | null | undefined;
    } & import("@deepseek-ai/cosmokit").Dict)[], Schemastery.ObjectT<NoInfer<{
        workspace: z<string, string, "plain">;
        ignoreFiles: z<(string | ({
            kind?: "exact" | "regex" | null | undefined;
            pattern?: string | null | undefined;
            caseSensitive?: boolean | null | undefined;
        } & import("@deepseek-ai/cosmokit").Dict))[], (string | Schemastery.ObjectT<NoInfer<{
            kind: z<"exact" | "regex", "exact" | "regex", "plain">;
            pattern: z<string, string, "plain">;
            caseSensitive: z<boolean, boolean, "plain">;
        }>>)[], "plain">;
    }>>[], "defined">;
    ignorePastedMentions: z<boolean, boolean, "defined">;
}>>, "plain">;
/**
 * Mount the atFile service and the pre-step path-reference marker.
 * @param ctx - host cordis context.
 * @param config - validated plugin configuration (schema defaults applied).
 */
export declare function apply(ctx: Context, config?: Config): void;
