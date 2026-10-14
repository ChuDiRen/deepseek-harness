/** SQLite persistence for file versions, symbol chunks, and optional embeddings. */
import type { CodeChunk } from './languages.ts';
/** Persisted chunk returned to ranking and outline callers. */
export interface StoredChunk extends CodeChunk {
    readonly id: number;
    readonly path: string;
    readonly language: string;
    readonly embedding?: readonly number[];
}
interface FileVersion {
    readonly version: string;
    readonly size: number;
}
/** Synchronous local cache store; all source reads remain on the DSH filesystem seam. */
export declare class CodeIndexStore {
    #private;
    /** Open or initialize an index database at an already validated local cache path. */
    constructor(path: string);
    /** Return the retrieval configuration fingerprint stored with this cache. */
    fingerprint(): string | undefined;
    /** Clear derived data and bind the empty cache to one retrieval configuration. */
    reset(fingerprint: string): void;
    /** Return the stored version and size for one workspace-relative path. */
    fileVersion(path: string): FileVersion | undefined;
    /** Return every indexed workspace-relative file path. */
    filePaths(): string[];
    /** Atomically replace one file and all of its derived chunks. */
    replaceFile(path: string, version: string, size: number, language: string, chunks: readonly CodeChunk[], embeddings: readonly (readonly number[] | undefined)[]): void;
    /** Remove one absent or excluded file and its chunks. */
    deleteFile(path: string): void;
    /** Return all chunks, optionally constrained to a file or directory prefix. */
    chunks(pathPrefix?: string): StoredChunk[];
    /** Return symbol chunks only for an outline projection. */
    symbols(pathPrefix?: string): StoredChunk[];
    /** Return persisted file and chunk counts. */
    stats(): {
        readonly files: number;
        readonly chunks: number;
    };
    /** Close the SQLite handle. */
    close(): void;
}
export {};
