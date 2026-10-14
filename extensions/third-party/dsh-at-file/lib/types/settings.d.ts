/**
 * The `at-file` settings face: the durable enable switch, pasted-mention
 * policy, and file-name filters. 0.2 settings pages generate from the
 * plugin's Config schema, so the fields ride the entry's `Config`; this
 * store serves the runtime live reads from an in-memory overlay and
 * persists every write into the entry's profile Config through the
 * settings forms service, keeping the page, restarts, and the running
 * plugin consistent.
 */
import type { Context } from '@deepseek-ai/cordis';
import type { AtFileSettings } from './contract.ts';
/** The profile entry id whose Config section carries the at-file settings. */
export declare const AT_FILE_ENTRY_ID = "dsh-at-file";
/**
 * Live settings store over the entry Config.
 * @param ctx - the plugin context reading the settings forms service.
 * @param initial - settings resolved from the entry Config at load.
 */
export declare class AtFileSettingsStore {
    private readonly ctx;
    private value;
    constructor(ctx: Context, initial: AtFileSettings);
    /** Current live value. */
    get(): AtFileSettings;
    /**
     * Apply one patch immediately and persist it into the entry's profile Config.
     * @param patch - settings fields to change.
     * @returns the merged live value.
     */
    update(patch: Partial<AtFileSettings>): Promise<AtFileSettings>;
}
