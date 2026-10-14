/** DeepSeek Harness tools for symbol outlines and hybrid code search. */
import type { Context } from '@deepseek-ai/cordis';
import z from '@deepseek-ai/schemastery';
import type { IndexerConfig } from './indexer.ts';
/** Loader-facing plugin name. */
export declare const name = "code-intel";
/** Runtime services required for indexing and model-facing tools. */
export declare const inject: string[];
/** Optional OpenAI-compatible embedding configuration. */
export interface EmbeddingConfigInput {
    readonly provider: 'openai-compatible';
    readonly endpoint: string;
    readonly model: string;
    readonly credentialRef: string;
    readonly batchSize?: number;
}
/** Deployment configuration for code intelligence. */
export interface Config {
    readonly indexDir?: string;
    readonly include?: string[];
    readonly exclude?: string[];
    readonly maxFileSize?: number;
    readonly maxChunkChars?: number;
    readonly maxResults?: number;
    readonly watch?: boolean;
    readonly embedding?: false | EmbeddingConfigInput;
}
/** Loader validation for code-intelligence configuration. */
export declare const Config: z<Config>;
/** Resolve defaults and reject unsafe or unsupported indexing configuration. */
export declare function resolveConfig(config?: Config): IndexerConfig;
/** Register search, outline, invalidation, and lifecycle cleanup. */
export declare function apply(ctx: Context, config?: Config): void;
export { CodeIndexer } from './indexer.ts';
export type { IndexerConfig, IndexingResponse, SearchHit, SearchResponse } from './indexer.ts';
export { extractCodeChunks, languageName, SUPPORTED_EXTENSIONS } from './languages.ts';
export type { CodeChunk } from './languages.ts';
