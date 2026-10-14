/** Workspace indexing, incremental invalidation, embeddings, and ranking. */
import type { Context } from '@deepseek-ai/cordis';
import type { FsObservation, FsTarget } from '@deepseek-ai/dsh-fs';
import type { ToolExecution } from '@deepseek-ai/dsh-tools';
declare module '@deepseek-ai/dsh-jobs' {
    interface JobKindMap {
        'code-index': 'code-index';
    }
}
/** OpenAI-compatible embedding endpoint configuration. */
export interface EmbeddingConfig {
    readonly provider: 'openai-compatible';
    readonly endpoint: string;
    readonly model: string;
    readonly credentialRef: string;
    readonly batchSize: number;
}
/** Fully resolved indexer configuration. */
export interface IndexerConfig {
    readonly indexDir: string;
    readonly include: readonly string[];
    readonly exclude: readonly string[];
    readonly maxFileSize: number;
    readonly maxChunkChars: number;
    readonly maxResults: number;
    readonly watch: boolean;
    readonly embedding?: EmbeddingConfig;
}
/** Search hit returned from hybrid ranking. */
export interface SearchHit {
    readonly path: string;
    readonly line: number;
    readonly endLine: number;
    readonly symbol: string;
    readonly kind: string;
    readonly score: number;
    readonly snippet: string;
}
/** Ready search response with an explicit retrieval mode. */
export interface SearchResponse {
    readonly kind: 'results';
    readonly mode: 'lexical' | 'hybrid';
    readonly indexedFiles: number;
    readonly results: SearchHit[];
}
/** Background-build response returned until a workspace index is ready. */
export interface IndexingResponse {
    readonly kind: 'indexing';
    readonly jobId: string;
    readonly mode: 'lexical' | 'hybrid';
    readonly message: string;
}
/** Owns one local SQLite cache per session workspace. */
export declare class CodeIndexer {
    #private;
    private readonly ctx;
    private readonly config;
    constructor(ctx: Context, config: IndexerConfig);
    /** Mark a successful DSH filesystem observation dirty without blocking or throwing. */
    observe(target: FsTarget, observation: FsObservation): void;
    /** Search the ready index or start its first background build. */
    search(query: string, limit: number, exec: ToolExecution): Promise<SearchResponse | IndexingResponse>;
    /** Return an indexed directory outline or parse one file directly through the DSH filesystem seam. */
    outline(path: string, exec: ToolExecution): Promise<{
        readonly path: string;
        readonly symbols: Omit<SearchHit, 'score'>[];
    } | IndexingResponse>;
    /** Close watchers and SQLite handles on plugin disposal. */
    close(): Promise<void>;
}
