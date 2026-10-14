/**
 * dsh-open-in-vscode client plugin: the browser half of the session "..."
 * menu "Open in VSCode" row. Mounts the openInVscode Remote namespace and
 * registers the row into the harness's `sidebar.workspaces.session.menu.item`
 * slot, with zh/en dictionaries. The row's click closes the menu and asks the
 * host to launch the editor on the session's workspace directory.
 */
import type { Context as ClientContext } from '@deepseek-ai/cordis';
/** Required services: slots, the gateway Remote face, locale, and the two snapshot catalogs. */
export declare const inject: string[];
/**
 * Compose the session menu row.
 * @param ctx - client root context.
 */
export declare function apply(ctx: ClientContext): void;
