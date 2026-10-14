import { GenerateOptions, HarnessError, StreamChunk } from "@deepseek-ai/dsh-llm";
import z from "@deepseek-ai/schemastery";
import { Context } from "@deepseek-ai/cordis";
//#region src/types.d.ts
/**
 * Public value types: the plugin's input/output specification.
 *
 * Every surface (slash command, model tool, engine API) reads and produces
 * exactly these shapes. The tool's canonical output schema in `tool.ts` is
 * the JSON projection of {@link TestgenReport}; `docs/io-spec.md` documents
 * the same contract for humans.
 * @module dsh-testgen/types
 */
/** Test frameworks the runner adapter can drive. */
type TestRunner = 'auto' | 'vitest' | 'jest' | 'node-test' | 'mocha';
/** Which generator produces the test source. */
type GeneratorMode = 'auto' | 'llm' | 'template';
/** Coarse source language classification, decided by file extension. */
type TargetLanguage = 'typescript' | 'typescript-jsx' | 'javascript' | 'javascript-jsx' | 'unknown';
/** Plugins-level configuration (composition entry + settings namespace). */
interface TestgenConfig {
  /** Test framework to run; `auto` detects from the project. */
  runner: TestRunner;
  /** Generator strategy; `auto` prefers the LLM and falls back to the deterministic template. */
  generator: GeneratorMode;
  /** Upper bound of the generate → run → fix loop; `0` disables fixing. */
  maxIterations: number;
  /** Per-run wall-clock timeout in seconds. */
  timeoutSec: number;
  /** Whether the engine runs the test suite after generation. */
  autoRun: boolean;
  /** Glob patterns selecting candidate source files. */
  includeGlobs: string[];
  /** Glob patterns never selected as targets. */
  excludeGlobs: string[];
  /** Directory (relative to the target's location) that receives generated test files. */
  testDir: string;
  /** Optional provider/model override for generation requests. */
  model?: {
    provider: string;
    model: string;
  };
  /** Cap on source characters fed to the LLM per target. */
  maxSourceChars: number;
}
/** One target resolved from user input (path or glob). */
interface SourceTarget {
  /** Path relative to the workspace root, `/`-separated. */
  path: string;
  /** Absolute filesystem path. */
  absolute: string;
  /** Detected language. */
  language: TargetLanguage;
  /** Source size in bytes (informational). */
  sizeBytes: number;
}
/** One generated (or regenerated) test file. */
interface GeneratedTest {
  /** Test file path relative to the workspace root. */
  path: string;
  /** Framework the emitted source targets. */
  framework: Exclude<TestRunner, 'auto'>;
  /** Which generator produced it. */
  generator: GeneratorMode;
  /** Number of test cases emitted. */
  testCount: number;
  /** Written content size in bytes. */
  contentBytes: number;
}
/** One failure extracted from a runner output. */
interface TestFailure {
  /** Failing test or suite name, when the reporter disclosed one. */
  testName?: string;
  /** Test file the failure belongs to, when the reporter disclosed one. */
  file?: string;
  /** Failure message (possibly multiline). */
  message: string;
}
/** Parsed count summary of one test run, when the reporter disclosed counts. */
interface TestSummary {
  passed: number;
  failed: number;
  skipped?: number;
}
/** One executed runner pass. */
interface TestRun {
  /** Zero-based iteration inside the fix loop. */
  iteration: number;
  /** Framework that ran. */
  framework: Exclude<TestRunner, 'auto'>;
  /** Command line used (informational). */
  command: string;
  /** Exit code; `null` when the process was terminated without one. */
  exitCode: number | null;
  /** Whether the configured timeout killed the run. */
  timedOut: boolean;
  /** Parsed counts, when available. */
  summary?: TestSummary;
  /** Structured failures extracted from the output. */
  failures: TestFailure[];
  /** Wall-clock duration in milliseconds. */
  durationMs: number;
  /** Runner output tail (bounded; kept for the fix loop and diagnostics). */
  output: string;
}
/** Terminal status of one `generate_tests` / `/testgen` execution. */
type TestgenStatus = 'passed' | 'fixed' | 'generated' | 'failed' | 'skipped';
/** Full result of one pipeline execution (the canonical output value). */
interface TestgenReport {
  status: TestgenStatus;
  /** Resolved source targets that entered the pipeline. */
  targets: {
    path: string;
    language: TargetLanguage;
  }[];
  /** Test files the pipeline wrote. */
  generated: GeneratedTest[];
  /** Every runner pass, in execution order. */
  runs: TestRun[];
  /** Non-fatal observations (fallbacks, skipped targets, degradations). */
  warnings: string[];
  /** Aggregate counters for quick consumption. */
  stats: {
    generatedFiles: number;
    passed: number;
    failed: number;
    iterations: number;
  };
  /** Total wall-clock duration in milliseconds. */
  elapsedMs: number;
}
/** User-facing request, shared by the tool arguments and the command parser. */
interface TestgenRequest {
  /** One target path or glob, or several. */
  target: string | string[];
  /** Framework override. */
  runner?: TestRunner;
  /** Generator override. */
  generator?: GeneratorMode;
  /** Fix-loop bound override. */
  maxIterations?: number;
  /** Skip the run phase and only generate. */
  autoRun?: boolean;
  /** Provider/model override, `provider/model` syntax. */
  model?: string;
}
//#endregion
//#region src/engine/generate-llm.d.ts
/** The slice of `ctx.llm` the generator consumes (structurally compatible). */
interface LlmHandle {
  listProviders(): readonly {
    id: string;
  }[];
  listModels(provider: string): Promise<readonly {
    id: string;
  }[]>;
  stream(options: GenerateOptions): AsyncIterable<StreamChunk>;
}
//#endregion
//#region src/schema.d.ts
/** Composition entry config: every field defaults, validated at load. */
declare const Config: z<Schemastery.ObjectS<{
  runner: z<"auto" | "vitest" | "jest" | "node-test" | "mocha", "auto" | "vitest" | "jest" | "node-test" | "mocha">;
  generator: z<"auto" | "llm" | "template", "auto" | "llm" | "template">;
  maxIterations: z<number, number>;
  timeoutSec: z<number, number>;
  autoRun: z<boolean, boolean>;
  includeGlobs: z<string[], string[]>;
  excludeGlobs: z<string[], string[]>;
  testDir: z<string, string>;
  model: z<Schemastery.ObjectS<{
    provider: z<string, string>;
    model: z<string, string>;
  }>, Schemastery.ObjectT<{
    provider: z<string, string>;
    model: z<string, string>;
  }>>;
  maxSourceChars: z<number, number>;
}>, Schemastery.ObjectT<{
  runner: z<"auto" | "vitest" | "jest" | "node-test" | "mocha", "auto" | "vitest" | "jest" | "node-test" | "mocha">;
  generator: z<"auto" | "llm" | "template", "auto" | "llm" | "template">;
  maxIterations: z<number, number>;
  timeoutSec: z<number, number>;
  autoRun: z<boolean, boolean>;
  includeGlobs: z<string[], string[]>;
  excludeGlobs: z<string[], string[]>;
  testDir: z<string, string>;
  model: z<Schemastery.ObjectS<{
    provider: z<string, string>;
    model: z<string, string>;
  }>, Schemastery.ObjectT<{
    provider: z<string, string>;
    model: z<string, string>;
  }>>;
  maxSourceChars: z<number, number>;
}>>;
/** Settings namespace schema: same shape, no requiredness beyond defaults. */
declare const SettingsSchema: z<Schemastery.ObjectS<{
  runner: z<"auto" | "vitest" | "jest" | "node-test" | "mocha", "auto" | "vitest" | "jest" | "node-test" | "mocha">;
  generator: z<"auto" | "llm" | "template", "auto" | "llm" | "template">;
  maxIterations: z<number, number>;
  timeoutSec: z<number, number>;
  autoRun: z<boolean, boolean>;
  includeGlobs: z<string[], string[]>;
  excludeGlobs: z<string[], string[]>;
  testDir: z<string, string>;
  model: z<Schemastery.ObjectS<{
    provider: z<string, string>;
    model: z<string, string>;
  }>, Schemastery.ObjectT<{
    provider: z<string, string>;
    model: z<string, string>;
  }>>;
  maxSourceChars: z<number, number>;
}>, Schemastery.ObjectT<{
  runner: z<"auto" | "vitest" | "jest" | "node-test" | "mocha", "auto" | "vitest" | "jest" | "node-test" | "mocha">;
  generator: z<"auto" | "llm" | "template", "auto" | "llm" | "template">;
  maxIterations: z<number, number>;
  timeoutSec: z<number, number>;
  autoRun: z<boolean, boolean>;
  includeGlobs: z<string[], string[]>;
  excludeGlobs: z<string[], string[]>;
  testDir: z<string, string>;
  model: z<Schemastery.ObjectS<{
    provider: z<string, string>;
    model: z<string, string>;
  }>, Schemastery.ObjectT<{
    provider: z<string, string>;
    model: z<string, string>;
  }>>;
  maxSourceChars: z<number, number>;
}>>;
//#endregion
//#region src/errors.d.ts
declare const ERROR_CODES: {
  /** User input matched no source file under the include/exclude policy. */
  readonly NO_TARGET: "TESTGEN_NO_TARGET";
  /** The target's language has no deterministic template generator (LLM-only). */
  readonly UNSUPPORTED_LANGUAGE: "TESTGEN_UNSUPPORTED_LANGUAGE";
  /** No usable test runner could be detected or selected. */
  readonly NO_RUNNER: "TESTGEN_NO_RUNNER";
  /** The configured runner exists but the invocation itself failed to start. */
  readonly RUNNER_START_FAILED: "TESTGEN_RUNNER_START_FAILED";
  /** Generation was requested from the LLM but no LLM service is composed. */
  readonly LLM_UNAVAILABLE: "TESTGEN_LLM_UNAVAILABLE";
  /** The LLM call failed or produced nothing usable. */
  readonly LLM_FAILED: "TESTGEN_LLM_FAILED";
  /** A configured value failed validation. */
  readonly INVALID_CONFIG: "TESTGEN_INVALID_CONFIG";
};
type TestgenErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES];
/** Plugin error with a stable code and optional cause chain. */
declare class TestgenError extends HarnessError {
  constructor(message: string, code: TestgenErrorCode, options?: ErrorOptions);
}
/** Narrow an arbitrary thrown value to a {@link TestgenError}. */
declare function isTestgenError(value: unknown): value is TestgenError;
/** Human-readable rendering of any thrown value, error chain included. */
declare function renderError(value: unknown): string;
//#endregion
//#region src/engine/runner.d.ts
type ConcreteRunner = Exclude<TestgenConfig['runner'], 'auto'>;
/** Spawn-shaped dependency, replaceable in tests. */
interface SpawnHandle {
  kill(): void;
  on(event: 'exit', listener: (code: number | null) => void): void;
  on(event: 'error', listener: (error: Error) => void): void;
  stdout: {
    on(event: 'data', listener: (chunk: Buffer) => void): void;
  };
  stderr: {
    on(event: 'data', listener: (chunk: Buffer) => void): void;
  };
}
type SpawnImpl = (command: string, argv: string[], options: {
  cwd: string;
  env: NodeJS.ProcessEnv;
}) => SpawnHandle;
interface RunnerOptions {
  cwd: string;
  files: string[];
  framework: ConcreteRunner;
  timeoutMs: number;
  signal?: AbortSignal;
  spawnImpl?: SpawnImpl;
  killDelayMs?: number;
}
/** Detect the concrete framework for a project, honoring an explicit pin. */
declare function detectFramework(cwd: string, requested: TestgenConfig['runner']): ConcreteRunner;
/**
 * Run one test pass and parse it. Resolves with a {@link TestRun}; rejects
 * with {@link TestgenError} only when the runner could not even start.
 */
declare function runTests(options: RunnerOptions): Promise<TestRun>;
interface ParsedOutput {
  summary?: TestSummary;
  failures: TestFailure[];
}
declare function parseRunnerOutput(framework: ConcreteRunner, output: string, exitCode: number | null): ParsedOutput;
//#endregion
//#region src/engine/pipeline.d.ts
/** Logger-shaped dependency; cordis loggers satisfy it structurally. */
interface PipelineLogger {
  info?(format: string, ...args: unknown[]): void;
  warn?(format: string, ...args: unknown[]): void;
  error?(format: string, ...args: unknown[]): void;
}
/** Injectable side effects. */
interface EngineDeps {
  logger?: PipelineLogger;
  llm?: LlmHandle;
  now?: () => number;
  writeFile?: (path: string, data: string) => void;
  fileExists?: (path: string) => boolean;
  readSource?: (path: string) => string;
  runTests?: typeof runTests;
}
/** Normalize request overrides onto the effective config. */
declare function mergeRequest(config: TestgenConfig, request: TestgenRequest): TestgenConfig;
/** Count `it(`/`test(` occurrences as a cheap emitted-test metric. */
declare function countTests(source: string): number;
/**
 * Execute the full pipeline. Never throws for runner/test failures — those
 * are report data; only configuration and LLM-availability problems throw
 * {@link TestgenError}.
 */
declare function runTestgen(cwd: string, request: TestgenRequest, baseConfig: TestgenConfig, deps?: EngineDeps, signal?: AbortSignal): Promise<TestgenReport>;
//#endregion
//#region src/engine/template.d.ts
/** One symbol discovered in a source file. */
interface ParsedSymbol {
  kind: 'function' | 'class';
  name: string;
}
/** Replace comments and string/template literals with spaces, keeping newlines. */
declare function stripNoise(source: string): string;
/**
 * Discover exported symbols in source order. Deduplicates by name (first
 * occurrence wins); never throws — malformed input simply yields fewer
 * symbols.
 */
declare function parseExports(source: string): ParsedSymbol[];
/** Render one generated test file's source. */
declare function renderTestFile(target: SourceTarget, symbols: ParsedSymbol[], framework: 'vitest' | 'jest' | 'node-test' | 'mocha', importSpecifier: string): string;
/** Absolute path of the test file for a target under a given `testDir`. */
declare function testFilePathFor(target: SourceTarget, testDir: string, framework: 'vitest' | 'jest' | 'node-test' | 'mocha'): string;
//#endregion
//#region src/engine/resolve.d.ts
/** Detect the coarse language of a file path by extension. */
declare function languageOf(path: string): TargetLanguage;
/**
 * Walk `dir` depth-first, collecting file paths (relative to `root`,
 * `/`-separated) that match `include` and not `exclude`. Bounded by
 * {@link MAX_WALKED_FILES}; returns `{ files, truncated }`.
 */
declare function walkFiles(root: string, include: (rel: string) => boolean, exclude: (rel: string) => boolean): {
  files: string[];
  truncated: boolean;
};
/**
 * Resolve user input to concrete, deduplicated source targets.
 *
 * - A bare file path bypasses `includeGlobs` (the user named it explicitly)
 *   but still honors `excludeGlobs`.
 * - A directory walks recursively under the include/exclude policy.
 * - A glob expands under the include/exclude policy.
 *
 * @param cwd - workspace root; relative input resolves against it.
 * @param raw - one target or several, as the user/agent typed them.
 * @param config - effective configuration.
 * @returns sorted, deduplicated targets; throws {@link TestgenError} with
 *   code `TESTGEN_NO_TARGET` when nothing matches.
 */
declare function resolveTargets(cwd: string, raw: string | string[], config: TestgenConfig): SourceTarget[];
//#endregion
//#region src/index.d.ts
declare const name = "testgen";
declare const inject: readonly ["commands", "tools"];
declare const version = "1.0.0";
/** Services the plugin consumes opportunistically (never hard-injected). */
interface TestgenApplyDeps {
  /** Optional LLM seam; when absent the template generator takes over. */
  llm?: LlmHandle;
}
/**
 * Cordis plugin entry. The loader imports this module by package name and
 * calls `apply` with the composition entry's config.
 */
declare function apply(ctx: Context, rawConfig: unknown): void;
//#endregion
export { type ConcreteRunner, Config, ERROR_CODES, type EngineDeps, type GeneratedTest, type GeneratorMode, type ParsedSymbol, type PipelineLogger, SettingsSchema, type SourceTarget, type TargetLanguage, type TestFailure, type TestRun, type TestRunner, type TestSummary, TestgenApplyDeps, type TestgenConfig, TestgenError, type TestgenReport, type TestgenRequest, type TestgenStatus, apply, countTests, detectFramework, inject, isTestgenError, languageOf, mergeRequest, name, parseExports, parseRunnerOutput, renderError, renderTestFile, resolveTargets, runTestgen, runTests, stripNoise, testFilePathFor, version, walkFiles };
//# sourceMappingURL=index.d.mts.map