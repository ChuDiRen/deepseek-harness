/** Language detection and symbol-boundary chunking backed by Tree-sitter WASM. */
/** One symbol or bounded module region persisted in the code index. */
export interface CodeChunk {
    readonly symbol: string;
    readonly kind: string;
    readonly startLine: number;
    readonly endLine: number;
    readonly text: string;
}
/** Extensions parsed into symbol-aware chunks. */
export declare const SUPPORTED_EXTENSIONS: readonly string[];
/** Return the parser language name for a supported path. */
export declare function languageName(path: string): string | undefined;
/** Parse one supported source file into symbols plus bounded module windows. */
export declare function extractCodeChunks(path: string, source: string, maxChunkChars: number): Promise<CodeChunk[]>;
