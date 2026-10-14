import type { ISessions } from '@deepseek-ai/dsh-api-session-controller/client';
import type { SessionId } from '@deepseek-ai/dsh-session';
import type { OpenInVscodeKey } from './locales.ts';
/** The row's business face: the host Remote call plus the sessions catalog. */
export interface OpenInVscodeInjected {
    /**
     * Open one absolute directory in the configured editor.
     * @param path - absolute directory path.
     * @returns fulfillment after the editor launch is accepted.
     */
    open: (path: string) => Promise<void>;
    /** The client sessions catalog; resolves the session's working directory. */
    sessions: ISessions;
}
declare module '@deepseek-ai/dsh-client-ui-slots' {
    interface LocaleNamespaceMap {
        /** The session menu row copy. */
        'open-in-vscode': OpenInVscodeKey;
    }
}
/** The menu open-state hook the slot's hookContext hands every entry. */
export type UseMenuOpenState = () => readonly [open: boolean, setOpen: (open: boolean) => void];
/** Full row props: the slot's owner share + the locale seat + the flat inject face. */
export interface OpenInVscodeRowProps extends OpenInVscodeInjected {
    /** Session whose working directory the row opens. */
    sessionId: SessionId;
    /** Row display title from the owner share. */
    displayTitle: string;
    /** Dismiss the session menu before launching the editor. */
    useMenuOpenState: UseMenuOpenState;
    /** Locale-bound translation seat for this package's namespace. */
    t: (key: OpenInVscodeKey, params?: Record<string, unknown>) => string;
}
/**
 * Render the locale-following editor row for one Session's directory.
 * @param props - owner share, locale seat, and the flat inject face.
 * @returns the menu row, or nothing while the directory is unresolved.
 */
export declare function OpenInVscodeRow({ sessionId, useMenuOpenState, t, open, sessions }: OpenInVscodeRowProps): import("react").JSX.Element | null;
