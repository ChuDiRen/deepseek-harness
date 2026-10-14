/** Workspace indexing, incremental invalidation, embeddings, and ranking. */
import { credentialRef } from '@deepseek-ai/dsh-credentials';
import { watch } from 'chokidar';
import ignore from 'ignore';
import { existsSync, readFileSync } from 'node:fs';
import { basename, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { extractCodeChunks, languageName } from "./languages.js";
import { CodeIndexStore } from "./store.js";
const DEFAULT_IGNORED_SEGMENTS = new Set([
    '.dsh',
    '.git',
    '.hg',
    '.svn',
    '.turbo',
    '.vite',
    '.vscode-test',
    'build',
    'coverage',
    'dist',
    'node_modules',
    'out',
    'target',
    'vendor',
]);
function normalizePath(path) {
    return path.split(sep).join('/').replace(/^\.\//u, '');
}
function pathInside(root, candidate) {
    const child = relative(root, candidate);
    if (child === '')
        return '';
    if (child === '..' || child.startsWith(`..${sep}`) || isAbsolute(child))
        return undefined;
    return normalizePath(child);
}
function tokenize(value) {
    const expanded = value.replace(/([a-z0-9])([A-Z])/gu, '$1 $2').toLowerCase();
    return expanded.match(/[\p{L}\p{N}_$-]+/gu)?.filter(token => token.length > 1) ?? [];
}
function occurrences(haystack, needle) {
    let count = 0;
    let offset = 0;
    while ((offset = haystack.indexOf(needle, offset)) !== -1 && count < 8) {
        count += 1;
        offset += needle.length;
    }
    return count;
}
function lexicalScore(chunk, query, tokens) {
    const path = chunk.path.toLowerCase();
    const symbol = chunk.symbol.toLowerCase();
    const text = chunk.text.toLowerCase();
    const exact = query.toLowerCase();
    let score = symbol.includes(exact) ? 10 : 0;
    score += path.includes(exact) ? 6 : 0;
    for (const token of tokens) {
        score += symbol.includes(token) ? 5 : 0;
        score += path.includes(token) ? 3 : 0;
        score += Math.min(occurrences(text, token), 4);
    }
    return score;
}
function cosine(left, right) {
    if (left.length !== right.length || left.length === 0)
        return 0;
    let dot = 0;
    let leftMagnitude = 0;
    let rightMagnitude = 0;
    for (let index = 0; index < left.length; index += 1) {
        const a = left[index];
        const b = right[index];
        if (a === undefined || b === undefined)
            return 0;
        dot += a * b;
        leftMagnitude += a * a;
        rightMagnitude += b * b;
    }
    if (leftMagnitude === 0 || rightMagnitude === 0)
        return 0;
    return dot / Math.sqrt(leftMagnitude * rightMagnitude);
}
function embeddingPayload(value, expected) {
    if (typeof value !== 'object' || value === null || Array.isArray(value))
        throw new TypeError('embedding endpoint returned a non-object response');
    const data = value.data;
    if (!Array.isArray(data) || data.length !== expected)
        throw new TypeError(`embedding endpoint returned ${Array.isArray(data) ? data.length : 'invalid'} vectors; expected ${expected}`);
    const ordered = Array.from({ length: expected });
    for (const item of data) {
        if (typeof item !== 'object' || item === null || Array.isArray(item))
            throw new TypeError('embedding endpoint returned an invalid vector record');
        const row = item;
        const index = row.index;
        const vector = row.embedding;
        if (typeof index !== 'number' || !Number.isSafeInteger(index) || index < 0 || index >= expected)
            throw new TypeError('embedding endpoint returned an invalid vector index');
        if (!Array.isArray(vector) || vector.length === 0 || vector.some(number => typeof number !== 'number' || !Number.isFinite(number))) {
            throw new TypeError('embedding endpoint returned an invalid vector');
        }
        ordered[index] = vector;
    }
    if (ordered.some(vector => vector === undefined))
        throw new TypeError('embedding endpoint omitted a vector');
    return ordered;
}
/** Owns one local SQLite cache per session workspace. */
export class CodeIndexer {
    ctx;
    config;
    #states = new Map();
    constructor(ctx, config) {
        this.ctx = ctx;
        this.config = config;
    }
    async #state(exec) {
        const cwd = exec.agent?.session.header.cwd;
        if (cwd === undefined)
            throw new Error('code intelligence requires a session workspace cwd');
        const rootTarget = await this.ctx.fs.resolve(cwd, { signal: exec.signal });
        const rootInfo = await this.ctx.fs.stat(rootTarget, exec.signal);
        if (rootInfo?.type !== 'directory')
            throw new Error(`code intelligence workspace is not a directory: ${cwd}`);
        const rootPath = this.ctx.fs.processPath(rootTarget);
        const existing = this.#states.get(rootPath);
        if (existing !== undefined)
            return existing;
        const databasePath = resolve(rootPath, this.config.indexDir, 'index.sqlite');
        if (pathInside(rootPath, databasePath) === undefined)
            throw new Error('code intelligence indexDir must stay inside the workspace');
        const store = new CodeIndexStore(databasePath);
        const fingerprint = this.config.embedding === undefined
            ? 'lexical:v1'
            : `openai-compatible:v1:${this.config.embedding.endpoint}:${this.config.embedding.model}`;
        if (store.fingerprint() !== fingerprint)
            store.reset(fingerprint);
        const ignored = ignore();
        const gitignore = join(rootPath, '.gitignore');
        if (existsSync(gitignore))
            ignored.add(readFileSync(gitignore, 'utf8'));
        const state = {
            cwd,
            rootPath,
            rootTarget,
            store,
            dirty: new Map(),
            ignored,
            indexing: false,
            ready: store.stats().files > 0,
        };
        this.#states.set(rootPath, state);
        if (state.ready)
            this.#startWatcher(state);
        return state;
    }
    #excluded(state, path, directory) {
        const normalized = normalizePath(path).replace(/\/$/u, '');
        if (normalized === '')
            return false;
        const segments = normalized.split('/');
        if (segments.some(segment => DEFAULT_IGNORED_SEGMENTS.has(segment)))
            return true;
        if (this.config.exclude.some(excluded => normalized === excluded || normalized.startsWith(`${excluded}/`)))
            return true;
        return state.ignored.ignores(directory ? `${normalized}/` : normalized);
    }
    #includedFile(state, path) {
        if (this.#excluded(state, path, false))
            return false;
        return this.config.include.some(extension => path.toLowerCase().endsWith(extension));
    }
    async #secret() {
        const embedding = this.config.embedding;
        if (embedding === undefined)
            return undefined;
        const resolved = await this.ctx.credentials.resolve(credentialRef(embedding.credentialRef));
        if (resolved === undefined)
            throw new Error(`embedding credential ${embedding.credentialRef} is not configured`);
        return resolved.value;
    }
    async #embed(texts, secret, signal) {
        const embedding = this.config.embedding;
        if (embedding === undefined)
            throw new Error('embedding configuration is absent');
        const response = await fetch(embedding.endpoint, {
            method: 'POST',
            headers: { authorization: `Bearer ${secret}`, 'content-type': 'application/json' },
            body: JSON.stringify({ model: embedding.model, input: texts }),
            signal,
        });
        if (!response.ok)
            throw new Error(`embedding endpoint failed with HTTP ${response.status}`);
        return embeddingPayload(await response.json(), texts.length);
    }
    async #chunkEmbeddings(texts, secret, signal) {
        if (secret === undefined || this.config.embedding === undefined)
            return texts.map(() => undefined);
        const output = [];
        for (let offset = 0; offset < texts.length; offset += this.config.embedding.batchSize) {
            signal.throwIfAborted();
            const batch = texts.slice(offset, offset + this.config.embedding.batchSize);
            output.push(...await this.#embed(batch, secret, signal));
        }
        return output;
    }
    async #indexFile(state, path, target, version, size, secret, signal) {
        if (!this.#includedFile(state, path) || size > this.config.maxFileSize) {
            state.store.deleteFile(path);
            return false;
        }
        const prior = state.store.fileVersion(path);
        if (prior?.version === version && prior.size === size)
            return false;
        const source = await this.ctx.fs.readText(target, signal);
        const language = languageName(path);
        if (language === undefined)
            return false;
        const chunks = await extractCodeChunks(path, source, this.config.maxChunkChars);
        const embeddings = await this.#chunkEmbeddings(chunks.map(chunk => chunk.text), secret, signal);
        state.store.replaceFile(path, version, size, language, chunks, embeddings);
        return true;
    }
    async #build(state, signal) {
        const secret = await this.#secret();
        const seen = new Set();
        let changed = 0;
        const walk = async (directory, prefix) => {
            signal.throwIfAborted();
            for (const entry of await this.ctx.fs.listDir(directory, signal)) {
                const path = prefix === '' ? entry.name : `${prefix}/${entry.name}`;
                if (entry.type === 'directory') {
                    if (!this.#excluded(state, path, true))
                        await walk(entry.target, path);
                    continue;
                }
                if (entry.type !== 'file' || !this.#includedFile(state, path))
                    continue;
                seen.add(path);
                const info = entry.version === undefined || entry.size === undefined
                    ? await this.ctx.fs.stat(entry.target, signal)
                    : { version: entry.version, size: entry.size, type: 'file' };
                if (info?.type !== 'file')
                    continue;
                if (await this.#indexFile(state, path, entry.target, String(info.version), info.size ?? 0, secret, signal))
                    changed += 1;
            }
        };
        await walk(state.rootTarget, '');
        for (const path of state.store.filePaths()) {
            if (!seen.has(path))
                state.store.deleteFile(path);
        }
        return { ...state.store.stats(), changed };
    }
    #startWatcher(state) {
        if (!this.config.watch || state.watcher !== undefined)
            return;
        const watcher = watch(state.rootPath, {
            ignoreInitial: true,
            ignored: (candidate, stats) => {
                const path = pathInside(state.rootPath, candidate);
                return path === undefined || this.#excluded(state, path, stats?.isDirectory() ?? false);
            },
        });
        watcher.on('add', path => this.#markAbsolute(state, path, 'present'));
        watcher.on('change', path => this.#markAbsolute(state, path, 'present'));
        watcher.on('unlink', path => this.#markAbsolute(state, path, 'absent'));
        watcher.on('error', (error) => {
            this.ctx.logger.warn(`[code-intel] workspace watcher failed for ${state.cwd}: ${String(error)}`);
        });
        state.watcher = watcher;
    }
    #markAbsolute(state, absolutePath, kind) {
        const path = pathInside(state.rootPath, absolutePath);
        if (path !== undefined && this.#includedFile(state, path))
            state.dirty.set(path, kind);
    }
    #startBuild(state, exec) {
        if (state.indexJob !== undefined && state.indexing)
            return state.indexJob;
        const controller = new AbortController();
        const id = this.ctx.jobs.start({
            kind: 'code-index',
            label: `index code in ${basename(state.rootPath)}`,
            ...exec.agent === undefined ? {} : { owner: exec.agent },
            run: () => {
                state.indexing = true;
                const done = this.#build(state, controller.signal).then((stats) => {
                    state.ready = true;
                    this.#startWatcher(state);
                    return { status: 'completed', output: `Indexed ${stats.files} files and ${stats.chunks} chunks (${stats.changed} changed).` };
                }, (error) => {
                    return controller.signal.aborted
                        ? { status: 'killed', detail: 'cancelled' }
                        : { status: 'failed', detail: error instanceof Error ? error.message : String(error) };
                }).finally(() => { state.indexing = false; });
                return { cancel: () => controller.abort(), done };
            },
        });
        state.indexJob = id;
        return id;
    }
    async #refreshDirty(state, signal) {
        if (state.dirty.size === 0)
            return;
        const secret = await this.#secret();
        const dirty = [...state.dirty];
        state.dirty.clear();
        for (const [path, observed] of dirty) {
            signal.throwIfAborted();
            if (observed === 'absent') {
                state.store.deleteFile(path);
                continue;
            }
            const target = await this.ctx.fs.resolve(path, { cwd: state.cwd, signal });
            const info = await this.ctx.fs.stat(target, signal);
            if (info?.type !== 'file') {
                state.store.deleteFile(path);
                continue;
            }
            await this.#indexFile(state, path, target, String(info.version), info.size ?? 0, secret, signal);
        }
    }
    /** Mark a successful DSH filesystem observation dirty without blocking or throwing. */
    observe(target, observation) {
        for (const state of this.#states.values()) {
            if (!this.ctx.fs.contains(state.rootTarget, target))
                continue;
            const path = pathInside(state.rootPath, this.ctx.fs.processPath(target));
            if (path !== undefined && this.#includedFile(state, path))
                state.dirty.set(path, observation.kind);
        }
    }
    /** Search the ready index or start its first background build. */
    async search(query, limit, exec) {
        const state = await this.#state(exec);
        if (!state.ready) {
            const jobId = this.#startBuild(state, exec);
            return {
                kind: 'indexing',
                jobId: String(jobId),
                mode: this.config.embedding === undefined ? 'lexical' : 'hybrid',
                message: 'The workspace index is building in the background. Use jobs to inspect it, then call code_search again.',
            };
        }
        await this.#refreshDirty(state, exec.signal);
        const chunks = state.store.chunks();
        const tokens = tokenize(query);
        if (tokens.length === 0)
            throw new TypeError('code_search query must contain a letter or number');
        const secret = await this.#secret();
        const queryVector = secret === undefined ? undefined : (await this.#embed([query], secret, exec.signal))[0];
        const scored = chunks.map((chunk) => {
            const lexical = lexicalScore(chunk, query, tokens);
            const semantic = queryVector === undefined || chunk.embedding === undefined ? 0 : cosine(queryVector, chunk.embedding);
            const score = queryVector === undefined ? lexical : semantic * 0.65 + Math.min(lexical / 20, 1) * 0.35;
            return { chunk, lexical, score };
        }).filter(item => item.lexical > 0 || item.score > 0.08)
            .sort((left, right) => right.score - left.score || left.chunk.path.localeCompare(right.chunk.path) || left.chunk.startLine - right.chunk.startLine);
        const unique = [];
        const seen = new Set();
        for (const item of scored) {
            const key = `${item.chunk.path}:${item.chunk.startLine}`;
            if (seen.has(key))
                continue;
            seen.add(key);
            unique.push(item);
            if (unique.length === Math.min(limit, this.config.maxResults))
                break;
        }
        return {
            kind: 'results',
            mode: queryVector === undefined ? 'lexical' : 'hybrid',
            indexedFiles: state.store.stats().files,
            results: unique.map(({ chunk, score }) => ({
                path: chunk.path,
                line: chunk.startLine,
                endLine: chunk.endLine,
                symbol: chunk.symbol,
                kind: chunk.kind,
                score: Number(score.toFixed(4)),
                snippet: chunk.text.slice(0, 800),
            })),
        };
    }
    /** Return an indexed directory outline or parse one file directly through the DSH filesystem seam. */
    async outline(path, exec) {
        const state = await this.#state(exec);
        const target = await this.ctx.fs.resolve(path, { cwd: state.cwd, signal: exec.signal });
        if (!this.ctx.fs.contains(state.rootTarget, target))
            throw new Error('code_outline path must stay inside the workspace');
        const info = await this.ctx.fs.stat(target, exec.signal);
        if (info === undefined)
            throw new Error(`code_outline path not found: ${path}`);
        const processPath = this.ctx.fs.processPath(target);
        const relativePath = pathInside(state.rootPath, processPath);
        if (relativePath === undefined)
            throw new Error('code_outline provider path is outside the workspace');
        if (info.type === 'file') {
            if (!this.#includedFile(state, relativePath))
                throw new Error(`code_outline does not support ${relativePath}`);
            if ((info.size ?? 0) > this.config.maxFileSize)
                throw new Error(`code_outline file exceeds maxFileSize: ${relativePath}`);
            const source = await this.ctx.fs.readText(target, exec.signal);
            const symbols = (await extractCodeChunks(relativePath, source, this.config.maxChunkChars)).filter(chunk => chunk.kind !== 'module');
            return {
                path: relativePath,
                symbols: symbols.map(symbol => ({
                    path: relativePath,
                    line: symbol.startLine,
                    endLine: symbol.endLine,
                    symbol: symbol.symbol,
                    kind: symbol.kind,
                    snippet: symbol.text.split('\n', 1)[0] ?? '',
                })),
            };
        }
        if (info.type !== 'directory')
            throw new Error(`code_outline path is not a file or directory: ${path}`);
        if (!state.ready) {
            const jobId = this.#startBuild(state, exec);
            return {
                kind: 'indexing',
                jobId: String(jobId),
                mode: this.config.embedding === undefined ? 'lexical' : 'hybrid',
                message: 'The workspace index is building in the background. Use jobs to inspect it, then call code_outline again.',
            };
        }
        await this.#refreshDirty(state, exec.signal);
        return {
            path: relativePath || '.',
            symbols: state.store.symbols(relativePath).map(symbol => ({
                path: symbol.path,
                line: symbol.startLine,
                endLine: symbol.endLine,
                symbol: symbol.symbol,
                kind: symbol.kind,
                snippet: symbol.text.split('\n', 1)[0] ?? '',
            })),
        };
    }
    /** Close watchers and SQLite handles on plugin disposal. */
    async close() {
        for (const state of this.#states.values()) {
            if (state.watcher !== undefined)
                await state.watcher.close();
            state.store.close();
        }
        this.#states.clear();
    }
}
//# sourceMappingURL=indexer.js.map