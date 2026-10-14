import { BlockAssembler, HarnessError, createUserMessage, errorChain } from "@deepseek-ai/dsh-llm";
import z from "@deepseek-ai/schemastery";
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { dirname, extname, isAbsolute, join, relative, resolve } from "node:path";
import { spawn } from "node:child_process";
import picomatch from "picomatch";
import { defineTool } from "@deepseek-ai/dsh-tools";
//#region src/errors.ts
/**
* Stable machine-routable error taxonomy for the plugin.
*
* Codes are the contract: surfaces render {@link TestgenError.message} for
* humans and route on `code` for machines. The class extends the shared
* harness base so tool results and logs keep the failure class.
* @module dsh-testgen/errors
*/
const ERROR_CODES = {
	/** User input matched no source file under the include/exclude policy. */
	NO_TARGET: "TESTGEN_NO_TARGET",
	/** The target's language has no deterministic template generator (LLM-only). */
	UNSUPPORTED_LANGUAGE: "TESTGEN_UNSUPPORTED_LANGUAGE",
	/** No usable test runner could be detected or selected. */
	NO_RUNNER: "TESTGEN_NO_RUNNER",
	/** The configured runner exists but the invocation itself failed to start. */
	RUNNER_START_FAILED: "TESTGEN_RUNNER_START_FAILED",
	/** Generation was requested from the LLM but no LLM service is composed. */
	LLM_UNAVAILABLE: "TESTGEN_LLM_UNAVAILABLE",
	/** The LLM call failed or produced nothing usable. */
	LLM_FAILED: "TESTGEN_LLM_FAILED",
	/** A configured value failed validation. */
	INVALID_CONFIG: "TESTGEN_INVALID_CONFIG"
};
/** Plugin error with a stable code and optional cause chain. */
var TestgenError = class extends HarnessError {
	constructor(message, code, options) {
		super(message, code, options);
		this.name = "TestgenError";
	}
};
/** Narrow an arbitrary thrown value to a {@link TestgenError}. */
function isTestgenError(value) {
	return value instanceof TestgenError;
}
/** Human-readable rendering of any thrown value, error chain included. */
function renderError(value) {
	if (value instanceof Error) return errorChain(value);
	return String(value);
}
//#endregion
//#region src/report.ts
const STATUS_LABELS = {
	passed: "PASSED",
	fixed: "FIXED",
	generated: "GENERATED",
	failed: "FAILED",
	skipped: "SKIPPED"
};
/** Plain multi-line rendering, shown as the `/testgen` command result. */
function renderReportPlain(report) {
	const lines = [];
	const status = report.status === "fixed" ? "FIXED (passing after fixes)" : STATUS_LABELS[report.status];
	lines.push(`Testgen ${status} in ${(report.elapsedMs / 1e3).toFixed(1)}s`);
	if (report.targets.length > 0) lines.push(`Targets (${report.targets.length}): ${report.targets.map((target) => target.path).join(", ")}`);
	if (report.generated.length > 0) for (const test of report.generated) lines.push(`  wrote ${test.path} (${test.generator}, ${test.testCount} tests, ${test.framework})`);
	for (const run of report.runs) {
		const head = run.timedOut ? "TIMEOUT" : run.exitCode === 0 ? "PASS" : `FAIL (exit ${String(run.exitCode)})`;
		const counts = run.summary ? ` — ${run.summary.passed} passed, ${run.summary.failed} failed${run.summary.skipped ? `, ${run.summary.skipped} skipped` : ""}` : "";
		lines.push(`Run #${run.iteration} ${run.framework}: ${head} in ${(run.durationMs / 1e3).toFixed(1)}s${counts}`);
		const shown = run.failures.slice(0, 10);
		for (const failure of shown) {
			const name = failure.testName ? ` ${failure.testName}` : "";
			lines.push(`  ✗${name}`);
			for (const messageLine of failure.message.split("\n").slice(0, 4)) lines.push(`    ${messageLine}`);
		}
		if (run.failures.length > shown.length) lines.push(`  … and ${run.failures.length - shown.length} more failure(s)`);
	}
	if (report.stats.iterations > 1) lines.push(`Summary: ${report.stats.generatedFiles} file(s), ${report.stats.iterations} run(s), ${report.stats.passed} passing, ${report.stats.failed} failing`);
	for (const warning of report.warnings) lines.push(`Warning: ${warning}`);
	return lines.join("\n");
}
/** Compact JSON rendering (the tool already returns the raw value; this is for `--json`). */
function renderReportJson(report) {
	return JSON.stringify(report, null, 2);
}
//#endregion
//#region src/schema.ts
/**
* Configuration schemas: the composition entry (schemastery) and the
* user-facing settings namespace layered on top of it.
*
* Layering is schema defaults → composition `base` → user section
* (`$DSH_HOME/settings.yaml` under the `testgen:` key), hot-reloaded by
* `dsh-settings-file`; see `docs/config.md`.
* @module dsh-testgen/schema
*/
const RUNNERS = [
	"auto",
	"vitest",
	"jest",
	"node-test",
	"mocha"
];
const GENERATORS = [
	"auto",
	"llm",
	"template"
];
const RUNNER_VALUES = RUNNERS;
const GENERATOR_VALUES = GENERATORS;
/** Shared shape for both the entry config and the settings namespace. */
function baseSchema() {
	return z.object({
		runner: z.union([
			z.const("auto"),
			z.const("vitest"),
			z.const("jest"),
			z.const("node-test"),
			z.const("mocha")
		]).default("auto").description("Test framework: auto-detect or pin one."),
		generator: z.union([
			z.const("auto"),
			z.const("llm"),
			z.const("template")
		]).default("auto").description("Generator: LLM when available, deterministic template, or auto."),
		maxIterations: z.number().min(0).max(20).default(3).description("Upper bound of the generate → run → fix loop."),
		timeoutSec: z.number().min(1).max(600).default(120).description("Per-run wall-clock timeout in seconds."),
		autoRun: z.boolean().default(true).description("Run the test suite after generation."),
		includeGlobs: z.array(z.string()).default(["**/*.{ts,tsx,js,jsx}"]).description("Candidate source globs."),
		excludeGlobs: z.array(z.string()).default([
			"**/node_modules/**",
			"**/dist/**",
			"**/build/**",
			"**/.git/**",
			"**/*.test.*",
			"**/*.spec.*",
			"**/__tests__/**"
		]).description("Globs that are never targets."),
		testDir: z.string().default("__tests__").description("Directory receiving generated test files, relative to the target."),
		model: z.object({
			provider: z.string().description("Provider route for generation calls."),
			model: z.string().description("Model id for generation calls.")
		}).description("Optional provider/model override for generation requests."),
		maxSourceChars: z.number().min(1e3).max(2e5).default(6e4).description("Source characters fed to the LLM per target.")
	});
}
/** Composition entry config: every field defaults, validated at load. */
const Config = baseSchema();
/** Settings namespace schema: same shape, no requiredness beyond defaults. */
const SettingsSchema = baseSchema();
/** Normalize a partially-overridden resolved section into a full config. */
function resolveConfig(value) {
	const parsed = Config(value);
	if (parsed.model && !parsed.model.provider && !parsed.model.model) parsed.model = void 0;
	return parsed;
}
//#endregion
//#region src/command.ts
const USAGE = [
	"Usage: /testgen [options] <file-or-glob> [more targets…]",
	"",
	"Generate unit tests for the given files, run the project test runner,",
	"and fix failures until they pass (bounded by maxIterations).",
	"",
	"Options:",
	"  --runner <vitest|jest|node-test|mocha|auto>  framework (default: auto)",
	"  --generator <llm|template|auto>              generator (default: auto)",
	"  --iterations <n>                             fix-loop bound (default: 3)",
	"  --model <provider/model>                     generation model override",
	"  --no-run                                     generate only, do not run",
	"  --json                                       machine-readable report",
	"  -h, --help                                   show this help",
	"",
	"Examples:",
	"  /testgen src/utils/math.ts",
	"  /testgen --runner vitest \"src/**/*.ts\"",
	"  /testgen --generator template --no-run src/app.ts"
].join("\n");
/** Parse the command's own grammar; unknown options and bad values fail loud. */
function parseTestgenInput(rawInput) {
	const tokens = rawInput.trim().split(/\s+/u).filter((token) => token.length > 0);
	const target = [];
	const request = {};
	let help = false;
	let json = false;
	let noRun = false;
	for (let i = 0; i < tokens.length; i++) {
		const token = tokens[i];
		switch (token) {
			case "--help":
			case "-h":
				help = true;
				break;
			case "--json":
				json = true;
				break;
			case "--no-run":
				noRun = true;
				break;
			case "--runner": {
				const value = tokens[++i];
				if (value === void 0 || !RUNNER_VALUES.includes(value)) return {
					help: false,
					json: false,
					error: `invalid --runner value: ${value ?? "(missing)"}; expected one of ${RUNNER_VALUES.join(", ")}`
				};
				request.runner = value;
				break;
			}
			case "--generator": {
				const value = tokens[++i];
				if (value === void 0 || !GENERATOR_VALUES.includes(value)) return {
					help: false,
					json: false,
					error: `invalid --generator value: ${value ?? "(missing)"}; expected one of ${GENERATOR_VALUES.join(", ")}`
				};
				request.generator = value;
				break;
			}
			case "--iterations": {
				const value = tokens[++i];
				const parsed = value === void 0 ? NaN : Number(value);
				if (!Number.isInteger(parsed) || parsed < 0) return {
					help: false,
					json: false,
					error: `invalid --iterations value: ${value ?? "(missing)"}; expected a non-negative integer`
				};
				request.maxIterations = parsed;
				break;
			}
			case "--model": {
				const value = tokens[++i];
				if (value === void 0) return {
					help: false,
					json: false,
					error: "missing value after --model; expected provider/model"
				};
				request.model = value;
				break;
			}
			default:
				if (token.startsWith("--")) return {
					help: false,
					json: false,
					error: `unknown option: ${token}`
				};
				target.push(token);
		}
	}
	if (noRun) request.autoRun = false;
	if (help) return {
		help: true,
		json: false
	};
	if (target.length === 0) return {
		help: false,
		json: false,
		error: "no target given"
	};
	return {
		help: false,
		json,
		request: {
			target,
			...request
		}
	};
}
/** Register the global `/testgen` command; returns the exact disposer. */
function registerCommand(ctx, deps) {
	return ctx.commands.register({
		name: "testgen",
		description: "Generate unit tests for a file or glob, run them, and fix failures until they pass.",
		input: { hint: "[options] <file-or-glob>" },
		handler: async (invocation) => {
			const parsed = parseTestgenInput(invocation.rawInput);
			if (parsed.help) return {
				kind: "success",
				text: USAGE
			};
			if (parsed.error || !parsed.request) return {
				kind: "error",
				text: `${parsed.error ?? "missing target"}\n\n${USAGE}`
			};
			const logger = ctx.logger?.("testgen");
			logger?.info("/testgen %s", invocation.rawInput.trim());
			try {
				const report = await deps.run(deps.cwd(), parsed.request, invocation.signal);
				logger?.info("/testgen finished: %s (%d file(s), %d run(s))", report.status, report.stats.generatedFiles, report.stats.iterations);
				return {
					kind: "success",
					text: parsed.json ? renderReportJson(report) : renderReportPlain(report)
				};
			} catch (error) {
				if (error instanceof TestgenError) return {
					kind: "error",
					text: `${error.message}\n\n${USAGE}`
				};
				logger?.error("/testgen failed: %s", renderError(error));
				return {
					kind: "error",
					text: renderError(error)
				};
			}
		}
	});
}
//#endregion
//#region src/engine/runner.ts
/**
* Test-runner adapter: detects the project's framework, executes one test
* run as a managed child process, and parses the output into structured
* failures. Pure Node — the host process owns spawning policy; the optional
* `ctx.subprocess` seam is used by the plugin entry when composed.
* @module dsh-testgen/engine/runner
*/
const MAX_CAPTURE_BYTES = 262144;
const MAX_OUTPUT_TAIL = 3e4;
const MAX_FAILURES = 50;
/** Walk up from `cwd` to the nearest directory containing `package.json`. */
function findProjectRoot(cwd) {
	let dir = cwd;
	for (;;) {
		if (existsSync(join(dir, "package.json"))) return dir;
		const parent = dirname(dir);
		if (parent === dir) return cwd;
		dir = parent;
	}
}
function readPackage(dir) {
	try {
		return JSON.parse(readFileSync(join(dir, "package.json"), "utf8"));
	} catch {
		return {};
	}
}
function dependencyNames(pkg) {
	const names = /* @__PURE__ */ new Set();
	for (const key of [
		"dependencies",
		"devDependencies",
		"peerDependencies"
	]) {
		const section = pkg[key];
		if (section && typeof section === "object") for (const name of Object.keys(section)) names.add(name);
	}
	return names;
}
/** Detect the concrete framework for a project, honoring an explicit pin. */
function detectFramework(cwd, requested) {
	if (requested !== "auto") return requested;
	const deps = dependencyNames(readPackage(findProjectRoot(cwd)));
	if (deps.has("vitest")) return "vitest";
	if (deps.has("jest")) return "jest";
	if (deps.has("mocha")) return "mocha";
	return "node-test";
}
/** Resolve the runner's entry file inside the nearest `node_modules`. */
function resolveRunnerEntry(cwd, framework) {
	if (framework === "node-test") return {
		argv: [],
		command: "node --test"
	};
	const pkg = framework === "vitest" ? "vitest" : framework === "jest" ? "jest" : "mocha";
	const entryRel = framework === "vitest" ? "vitest.mjs" : framework === "jest" ? "bin/jest.js" : "bin/mocha.js";
	let dir = findProjectRoot(cwd);
	for (;;) {
		const candidate = join(dir, "node_modules", pkg, entryRel);
		if (existsSync(candidate)) return {
			argv: [candidate],
			command: `node ${candidate}`
		};
		const parent = dirname(dir);
		if (parent === dir) break;
		dir = parent;
	}
	throw new TestgenError(`${pkg} is declared by the project but its package is not installed — run the project's install first`, ERROR_CODES.RUNNER_START_FAILED);
}
/** Build the full argument vector for one run. */
function buildRunArgv(framework, entryArgv, files) {
	const base = [...entryArgv];
	switch (framework) {
		case "node-test": return ["--test", ...files];
		case "vitest": return [
			...base,
			"run",
			...files,
			"--reporter=basic"
		];
		case "jest": return [
			...base,
			...files,
			"--runInBand"
		];
		case "mocha": return [...base, ...files];
	}
}
const defaultSpawn = (command, argv, options) => spawn(command, argv, {
	cwd: options.cwd,
	env: options.env,
	stdio: [
		"ignore",
		"pipe",
		"pipe"
	]
});
/**
* Run one test pass and parse it. Resolves with a {@link TestRun}; rejects
* with {@link TestgenError} only when the runner could not even start.
*/
async function runTests(options) {
	const started = Date.now();
	const { framework } = options;
	const spawnImpl = options.spawnImpl ?? defaultSpawn;
	const argv = buildRunArgv(framework, resolveRunnerEntry(options.cwd, framework).argv, options.files);
	const env = {
		...process.env,
		CI: "1",
		FORCE_COLOR: "0",
		NO_COLOR: "1",
		NODE_ENV: process.env.NODE_ENV ?? "test"
	};
	let stdout = "";
	let stderr = "";
	const child = spawnImpl(process.execPath, argv, {
		cwd: options.cwd,
		env
	});
	child.stdout.on("data", (chunk) => {
		if (stdout.length < MAX_CAPTURE_BYTES) stdout += chunk.toString();
	});
	child.stderr.on("data", (chunk) => {
		if (stderr.length < MAX_CAPTURE_BYTES) stderr += chunk.toString();
	});
	const killDelay = options.killDelayMs ?? 5e3;
	let timedOut = false;
	let killed = false;
	const kill = () => {
		if (killed) return;
		killed = true;
		child.kill();
		const timer = setTimeout(() => {
			try {
				if (process.platform === "win32") spawn("taskkill", [
					"/pid",
					String(child.pid ?? ""),
					"/T",
					"/F"
				], { stdio: "ignore" });
				else child.kill();
			} catch {}
			clearTimeout(timer);
		}, killDelay);
		if (timer.unref) timer.unref();
	};
	const timer = setTimeout(() => {
		timedOut = true;
		kill();
	}, options.timeoutMs);
	if (timer.unref) timer.unref();
	const onAbort = () => kill();
	options.signal?.addEventListener("abort", onAbort, { once: true });
	const exitCode = await new Promise((resolve, reject) => {
		child.on("exit", (code) => resolve(code));
		child.on("error", (error) => reject(new TestgenError(`failed to start ${framework} runner: ${error.message}`, ERROR_CODES.RUNNER_START_FAILED, { cause: error })));
	});
	clearTimeout(timer);
	options.signal?.removeEventListener("abort", onAbort);
	if (killed && exitCode !== null && exitCode !== 0 && !timedOut) timedOut = options.signal?.aborted === true ? false : timedOut;
	const output = tail(`${stdout}\n${stderr}`.trim(), MAX_OUTPUT_TAIL);
	const parsed = parseRunnerOutput(framework, output, exitCode);
	return {
		iteration: 0,
		framework,
		command: displayCommand(framework, options.files),
		exitCode,
		timedOut,
		summary: parsed.summary,
		failures: parsed.failures,
		durationMs: Date.now() - started,
		output
	};
}
function displayCommand(framework, files) {
	const shown = files.map((file) => JSON.stringify(file)).join(" ");
	switch (framework) {
		case "vitest": return `vitest run ${shown}`;
		case "jest": return `jest ${shown} --runInBand`;
		case "mocha": return `mocha ${shown}`;
		case "node-test": return `node --test ${shown}`;
	}
}
function tail(text, max) {
	return text.length <= max ? text : `…(truncated)…\n${text.slice(-max)}`;
}
function parseRunnerOutput(framework, output, exitCode) {
	let parsed;
	switch (framework) {
		case "vitest":
			parsed = parseVitest(output);
			break;
		case "jest":
			parsed = parseJest(output);
			break;
		case "mocha":
			parsed = parseMocha(output);
			break;
		case "node-test": parsed = parseNodeTest(output);
	}
	parsed.failures = parsed.failures.slice(0, MAX_FAILURES);
	if (exitCode !== 0 && parsed.failures.length === 0) parsed.failures.push({ message: `runner exited with code ${String(exitCode)}:\n${tail(output, 4e3)}` });
	return parsed;
}
const VITEST_FAILURE_HEADER = /^\s*(?:[❯×✗]|×)\s+(.+?\.(?:test|spec)\.(?:ts|tsx|js|jsx|mts|cts|mjs|cjs))\s*>\s*(.+)$/u;
function parseVitest(output) {
	const failures = [];
	let current;
	const push = () => {
		if (current) failures.push(current);
		current = void 0;
	};
	for (const line of output.split("\n")) {
		const header = VITEST_FAILURE_HEADER.exec(line);
		if (header) {
			push();
			current = {
				file: header[1],
				testName: header[2].trim(),
				message: ""
			};
			continue;
		}
		if (current) {
			const trimmed = line.trim();
			if (/^(?:AssertionError|TypeError|RangeError|ReferenceError|Error|expected)/u.test(trimmed)) current.message = trimmed.slice(0, 500);
			else if (trimmed.length === 0) push();
			else if (!current.message && /:\d+:\d+/u.test(line)) continue;
			else if (current.message && trimmed.startsWith("❯") && /:\d+:\d+/u.test(line)) push();
		}
	}
	push();
	return {
		summary: parseVitestSummary(output),
		failures: failures.filter((failure) => failure.message !== "")
	};
}
function parseVitestSummary(output) {
	const line = output.split("\n").find((value) => /^\s*Tests\s+\d+/u.test(value));
	if (!line) return void 0;
	const failed = /Tests\s+(\d+)\s+failed/u.exec(line);
	const passed = /(\d+)\s+passed/u.exec(line);
	const skipped = /(\d+)\s+skipped/u.exec(line);
	if (!failed && !passed) return void 0;
	return {
		failed: failed ? Number(failed[1]) : 0,
		passed: passed ? Number(passed[1]) : 0,
		skipped: skipped ? Number(skipped[1]) : void 0
	};
}
function parseJest(output) {
	const failures = [];
	const lines = output.split("\n");
	let current;
	const push = () => {
		if (current) failures.push(current);
		current = void 0;
	};
	for (const line of lines) {
		const header = /^\s*[●●]\s+(.+)$/u.exec(line);
		if (header) {
			push();
			current = {
				testName: header[1].replaceAll("›", ">").trim(),
				message: ""
			};
			continue;
		}
		if (current) {
			if (/^Tests:/u.test(line)) {
				push();
				continue;
			}
			const trimmed = line.trim();
			if (trimmed.length > 0 && !trimmed.startsWith("at ")) {
				if (current.message.length < 500) current.message += `${current.message ? "\n" : ""}${trimmed}`;
			}
		}
	}
	push();
	const summaryLine = lines.find((value) => /^Tests:/u.test(value));
	let summary;
	if (summaryLine) {
		const failed = /(\d+)\s+failed/u.exec(summaryLine);
		const passed = /(\d+)\s+passed/u.exec(summaryLine);
		const skipped = /(\d+)\s+skipped/u.exec(summaryLine);
		summary = {
			failed: failed ? Number(failed[1]) : 0,
			passed: passed ? Number(passed[1]) : 0,
			skipped: skipped ? Number(skipped[1]) : void 0
		};
	}
	return {
		summary,
		failures
	};
}
function parseNodeTest(output) {
	const failures = [];
	const lines = output.split("\n");
	let current;
	let inErrorBlock = false;
	let pendingDiagnostics = [];
	const push = () => {
		if (current) {
			if (current.message === "" && pendingDiagnostics.length > 0) current.message = pendingDiagnostics.slice(0, 12).join("\n");
			failures.push(current);
		}
		current = void 0;
		inErrorBlock = false;
		pendingDiagnostics = [];
	};
	for (const line of lines) {
		const notOk = /^not ok\s+\d+\s+-\s+(.+)$/u.exec(line);
		if (notOk) {
			push();
			current = {
				testName: notOk[1].trim(),
				message: ""
			};
			continue;
		}
		if (!current && /^#\s/u.test(line)) {
			const trimmed = line.replace(/^#\s?/u, "").trim();
			if (trimmed.length > 0) pendingDiagnostics.push(trimmed);
			continue;
		}
		if (current && /^\s+(?:error|message):/u.test(line)) {
			inErrorBlock = true;
			continue;
		}
		if (current && inErrorBlock && /^\s{4,}/u.test(line)) {
			const trimmed = line.trim();
			if (trimmed.length > 0 && current.message.length < 500) current.message += `${current.message ? "\n" : ""}${trimmed}`;
			continue;
		}
		if (current && /^(?:ok\s+\d+|#\s|\d+\.\.\d+)/u.test(line)) push();
	}
	push();
	const count = (pattern) => {
		const line = lines.find((value) => pattern.test(value));
		const match = line ? pattern.exec(line) : void 0;
		return match ? Number(match[1]) : 0;
	};
	const tests = count(/^#\s+tests\s+(\d+)/u);
	const passed = count(/^#\s+pass\s+(\d+)/u);
	const failed = count(/^#\s+fail\s+(\d+)/u);
	const skipped = count(/^#\s+skip\s+(\d+)/u);
	return {
		summary: tests > 0 ? {
			passed,
			failed,
			skipped: skipped > 0 ? skipped : void 0
		} : void 0,
		failures
	};
}
function parseMocha(output) {
	const failures = [];
	const lines = output.split("\n");
	let current;
	const push = () => {
		if (current) failures.push(current);
		current = void 0;
	};
	for (const line of lines) {
		const header = /^\s+\d+\)\s+(.+)$/u.exec(line);
		if (header) {
			push();
			current = {
				testName: header[1].trim().replace(/:$/, ""),
				message: ""
			};
			continue;
		}
		if (current && current.message === "" && /^\s+.+:$/u.test(line)) {
			current.testName = `${current.testName} ${line.trim().replace(/:$/, "")}`;
			continue;
		}
		if (current) {
			if (/^\s+\d+\)\s/u.test(line)) {
				push();
				continue;
			}
			const trimmed = line.trim();
			if (/^\d+\s+(?:passing|failing|pending)/u.test(trimmed)) {
				push();
				continue;
			}
			if (trimmed.length > 0 && current.message.length < 500) current.message += `${current.message ? "\n" : ""}${trimmed}`;
		}
	}
	push();
	const passing = /(\d+)\s+passing/u.exec(output);
	const failing = /(\d+)\s+failing/u.exec(output);
	const pending = /(\d+)\s+pending/u.exec(output);
	return {
		summary: passing || failing ? {
			passed: passing ? Number(passing[1]) : 0,
			failed: failing ? Number(failing[1]) : 0,
			skipped: pending ? Number(pending[1]) : void 0
		} : void 0,
		failures
	};
}
//#endregion
//#region src/engine/generate-llm.ts
/**
* LLM generator: prompt, stream, and extract complete test files from the
* harness's `ctx.llm` seam. The LLM is optional — when it is absent the
* deterministic template generator takes over; this module only defines the
* LLM path and its error contract.
* @module dsh-testgen/engine/generate-llm
*/
function generationSystem(framework, role) {
	const base = [
		"You are an expert unit-test author for a coding-agent harness.",
		`You write ${framework} test files. Rules:`,
		"- Emit ONE complete test file, nothing else.",
		"- Output the entire file inside a single fenced code block tagged with the file language (ts/js/tsx/jsx).",
		"- Cover exported APIs: happy paths, edge cases, and error paths where cheap.",
		"- Do not modify production source. Only the test file exists in your answer.",
		"- No prose outside the code block; no markdown headers."
	];
	if (role === "fix") base.push("- The runner reported failures: keep passing tests untouched and rewrite only what is wrong.");
	return base.join("\n");
}
/** Resolve the provider/model used for generation, or throw when none exists. */
async function resolveModel(llm, config) {
	if (config.model?.model) {
		const provider = config.model.provider || llm.listProviders()[0]?.id;
		if (!provider) throw new TestgenError("no LLM adapter composed — the LLM generator cannot run", ERROR_CODES.LLM_UNAVAILABLE);
		return {
			provider,
			model: config.model.model
		};
	}
	const providers = llm.listProviders();
	if (providers.length === 0) throw new TestgenError("no LLM adapter composed — the LLM generator cannot run", ERROR_CODES.LLM_UNAVAILABLE);
	const provider = providers[0].id;
	let model = "";
	try {
		model = (await llm.listModels(provider))[0]?.id ?? "";
	} catch {
		model = "";
	}
	return {
		provider,
		model: model || "deepseek-chat"
	};
}
/** Extract one code block (or the whole text) from a model answer. */
function extractCodeBlock(text) {
	const fence = /```(?:ts|typescript|tsx|js|javascript|jsx)?\s*\r?\n([\s\S]*?)```/u.exec(text);
	if (fence?.[1]) return {
		code: fence[1].trim(),
		fenced: true
	};
	return {
		code: text.trim(),
		fenced: false
	};
}
async function streamText(llm, options) {
	const assembler = new BlockAssembler();
	for await (const chunk of llm.stream(options)) assembler.push(chunk);
	const finish = assembler.finish;
	if (finish.kind === "error" || finish.kind === "aborted") throw new TestgenError(`generation request failed: ${finish.failure.message} (${finish.failure.code})`, ERROR_CODES.LLM_FAILED);
	const text = assembler.blocks().filter((block) => block.type === "text").map((block) => block.text).join("\n").trim();
	if (text.length === 0) throw new TestgenError("model returned no test code", ERROR_CODES.LLM_FAILED);
	return text;
}
/**
* Generate one test file for a target through the LLM.
* @returns the extracted test source.
*/
async function generateTestSource(llm, resolved, framework, target, source, config, signal) {
	const truncated = source.length > config.maxSourceChars ? `${source.slice(0, config.maxSourceChars)}\n// … source truncated by dsh-testgen (maxSourceChars) …` : source;
	return extractCodeBlock(await streamText(llm, {
		provider: resolved.provider,
		model: resolved.model,
		system: generationSystem(framework, "generate"),
		messages: [createUserMessage({
			content: [{
				type: "text",
				text: `Target: ${target.path} (${target.language})\n\nWrite a complete ${framework} unit-test file for this module:\n\n${truncated}`
			}],
			source: { kind: "user" }
		})],
		temperature: .2,
		signal
	})).code;
}
/**
* Regenerate a failing test file through the LLM.
* @returns the corrected test source.
*/
async function fixTestSource(llm, resolved, framework, testPath, currentSource, run, config, signal) {
	const failureText = run.failures.slice(0, 20).map((failure) => {
		return `${failure.testName ? `- ${failure.testName}` : "- (unnamed test)"}\n${failure.message}`;
	}).join("\n\n");
	return extractCodeBlock(await streamText(llm, {
		provider: resolved.provider,
		model: resolved.model,
		system: generationSystem(framework, "fix"),
		messages: [createUserMessage({
			content: [{
				type: "text",
				text: [
					`The test file ${testPath} failed under ${framework}.`,
					"Current test file:",
					"```",
					currentSource.slice(0, config.maxSourceChars),
					"```",
					"Runner failures:",
					failureText || `exit code ${String(run.exitCode)}`,
					"",
					"Return the corrected COMPLETE test file in one fenced code block."
				].join("\n")
			}],
			source: { kind: "user" }
		})],
		temperature: .2,
		signal
	})).code;
}
//#endregion
//#region src/engine/template.ts
/**
* Deterministic template generator: structural smoke tests scaffolded from
* a file's exported symbols, with zero LLM involvement.
*
* The scanner is deliberately a heuristic (comment/string stripping plus
* regexes over the residue) — it must never throw on arbitrary source, only
* degrade to fewer (or zero) discovered symbols. Emitted tests are smoke
* tests: they prove the module imports and its exports still exist, which
* is exactly what a first scaffold should guarantee. The LLM generator
* replaces them with behavioral tests when composed.
* @module dsh-testgen/engine/template
*/
const IDENT = String.raw`[A-Za-z_$][\w$]*`;
/** Replace comments and string/template literals with spaces, keeping newlines. */
function stripNoise(source) {
	const out = source.split("");
	let i = 0;
	while (i < source.length) {
		const char = source[i];
		if (char === "/" && source[i + 1] === "/") {
			while (i < source.length && source[i] !== "\n") out[i++] = " ";
			continue;
		}
		if (char === "/" && source[i + 1] === "*") {
			out[i] = " ";
			out[i + 1] = " ";
			i += 2;
			while (i < source.length && !(source[i] === "*" && source[i + 1] === "/")) {
				if (source[i] !== "\n") out[i] = " ";
				i++;
			}
			if (i < source.length) {
				out[i] = " ";
				out[i + 1] = " ";
				i += 2;
			}
			continue;
		}
		if (char === "\"" || char === "'" || char === "`") {
			const quote = char;
			out[i++] = " ";
			while (i < source.length) {
				const current = source[i];
				if (current === "\\") {
					out[i] = " ";
					out[i + 1] = " ";
					i += 2;
					continue;
				}
				if (current === quote) {
					out[i++] = " ";
					break;
				}
				if (current !== "\n") out[i] = " ";
				i++;
			}
			continue;
		}
		i++;
	}
	return out.join("");
}
const PATTERNS = [
	{
		kind: "function",
		regex: new RegExp(String.raw`export\s+(?:default\s+)?(?:async\s+)?function\s+(${IDENT})`, "gu")
	},
	{
		kind: "function",
		regex: new RegExp(String.raw`export\s+const\s+(${IDENT})\s*=\s*(?:async\s*)?(?:\([^)]*\)\s*=>|function(?:\s+${IDENT})?\s*\()`, "gu")
	},
	{
		kind: "class",
		regex: new RegExp(String.raw`export\s+(?:default\s+)?class\s+(${IDENT})`, "gu")
	}
];
/**
* Discover exported symbols in source order. Deduplicates by name (first
* occurrence wins); never throws — malformed input simply yields fewer
* symbols.
*/
function parseExports(source) {
	const stripped = stripNoise(source);
	const seen = /* @__PURE__ */ new Set();
	const found = [];
	for (const { kind, regex } of PATTERNS) for (const match of stripped.matchAll(regex)) {
		const name = match[1];
		if (seen.has(name)) continue;
		seen.add(name);
		found.push({
			index: match.index,
			symbol: {
				kind,
				name
			}
		});
	}
	return found.sort((a, b) => a.index - b.index).map((entry) => entry.symbol);
}
/** File extension for a generated test file, per framework and language. */
function testFileExtensionFor(framework, language) {
	if (framework === "node-test") return language === "typescript" || language === "typescript-jsx" ? ".test.mts" : ".test.mjs";
	switch (language) {
		case "typescript": return ".test.ts";
		case "typescript-jsx": return ".test.tsx";
		case "javascript": return ".test.js";
		case "javascript-jsx": return ".test.jsx";
		case "unknown": return ".test.js";
	}
}
/** Final path component (basename) of a path, `/`- or `\`-separated. */
function basename(path) {
	const idx = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
	return idx === -1 ? path : path.slice(idx + 1);
}
/** Import specifier from a generated test file back to its target module. */
function importSpecifierFor(target, testFileAbsolute) {
	const spec = relative(dirname(testFileAbsolute), target.absolute).replaceAll("\\", "/");
	return spec.startsWith(".") ? spec : `./${spec}`;
}
/** Render one generated test file's source. */
function renderTestFile(target, symbols, framework, importSpecifier) {
	const expectApi = framework === "vitest" || framework === "jest";
	const lines = [
		"// Generated by dsh-testgen (template generator). Structural smoke tests:",
		"// they prove the module imports and its exports still exist.",
		"// Run /testgen with an LLM composed for behavioral tests."
	];
	if (framework === "vitest") lines.push(`import { it, expect } from 'vitest'`);
	else if (framework === "jest") lines.push(`import { it, expect } from '@jest/globals'`);
	else lines.push(`import { it } from 'node:test'`);
	if (!expectApi) lines.push(`import assert from 'node:assert/strict'`);
	lines.push(`import * as mod from ${JSON.stringify(importSpecifier)}`, "");
	if (symbols.length === 0) {
		lines.push(`it('module loads', () => {`);
		lines.push(`  ${expectApi ? "expect(mod).toBeDefined()" : "assert.ok(mod !== undefined)"}`);
		lines.push(`})`);
		return `${lines.join("\n")}\n`;
	}
	symbols.forEach((symbol, index) => {
		if (index > 0) lines.push("");
		lines.push(`it('exports ${symbol.name}', () => {`);
		lines.push(`  ${expectApi ? `expect(typeof mod.${symbol.name}).toBe('function')` : `assert.equal(typeof mod.${symbol.name}, 'function')`}`);
		lines.push(`})`);
	});
	return `${lines.join("\n")}\n`;
}
/** Absolute path of the test file for a target under a given `testDir`. */
function testFilePathFor(target, testDir, framework) {
	const dot = target.absolute.lastIndexOf(".");
	const stem = dot === -1 ? target.absolute : target.absolute.slice(0, dot);
	return join(dirname(target.absolute), testDir, `${basename(stem)}${testFileExtensionFor(framework, target.language)}`);
}
/**
* Generate one template test file for a target.
* @returns absolute test path, rendered source, and emitted test count.
*/
function generateTemplateTest(target, testDir, framework) {
	const filePath = testFilePathFor(target, testDir, framework);
	let source = "";
	try {
		source = readFileSync(target.absolute, "utf8");
	} catch {
		source = "";
	}
	const symbols = parseExports(source);
	return {
		path: filePath,
		source: renderTestFile(target, symbols, framework, importSpecifierFor(target, filePath)),
		testCount: Math.max(symbols.length, 1)
	};
}
//#endregion
//#region src/engine/resolve.ts
/**
* Target resolution: turns user input (paths and globs) into concrete
* source files, classifying each by language. Pure functions — no cordis
* types — so the whole module is trivially unit-testable.
* @module dsh-testgen/engine/resolve
*/
const LANGUAGE_BY_EXT = {
	".ts": "typescript",
	".tsx": "typescript-jsx",
	".mts": "typescript",
	".cts": "typescript",
	".js": "javascript",
	".jsx": "javascript-jsx",
	".mjs": "javascript",
	".cjs": "javascript"
};
/** Detect the coarse language of a file path by extension. */
function languageOf(path) {
	return LANGUAGE_BY_EXT[extname(path).toLowerCase()] ?? "unknown";
}
/** Whether the path contains glob magic. */
function hasGlobMagic(path) {
	return /[*?[\]{}!()@+]/u.test(path);
}
/**
* Walk `dir` depth-first, collecting file paths (relative to `root`,
* `/`-separated) that match `include` and not `exclude`. Bounded by
* {@link MAX_WALKED_FILES}; returns `{ files, truncated }`.
*/
function walkFiles(root, include, exclude) {
	const out = [];
	let truncated = false;
	const visit = (dir, rel) => {
		if (out.length >= 2e4) {
			truncated = true;
			return;
		}
		let entries;
		try {
			entries = readdirSync(dir, { withFileTypes: true });
		} catch {
			return;
		}
		for (const entry of entries) {
			if (out.length >= 2e4) {
				truncated = true;
				return;
			}
			const childRel = rel === "" ? entry.name : `${rel}/${entry.name}`;
			if (entry.isDirectory()) {
				if (exclude(`${childRel}/`)) continue;
				visit(join(dir, entry.name), childRel);
			} else if (entry.isFile()) {
				if (exclude(childRel)) continue;
				if (include(childRel)) out.push(childRel);
			}
		}
	};
	visit(root, "");
	return {
		files: out,
		truncated
	};
}
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
function resolveTargets(cwd, raw, config) {
	const inputs = (Array.isArray(raw) ? raw : [raw]).map((value) => value.trim()).filter((value) => value.length > 0);
	if (inputs.length === 0) throw new TestgenError("no target given: pass a file path, directory, or glob", ERROR_CODES.NO_TARGET);
	const include = picomatch(config.includeGlobs, { dot: true });
	const exclude = picomatch(config.excludeGlobs, { dot: true });
	const matches = (matcher, rel) => Boolean(matcher(rel));
	const found = /* @__PURE__ */ new Map();
	let truncated = false;
	for (const input of inputs) {
		const absoluteInput = isAbsolute(input) ? input : resolve(cwd, input);
		if (hasGlobMagic(input)) {
			const root = globRoot(absoluteInput);
			const rootRel = normalize(relative(cwd, root));
			let patternRel = input.replaceAll("\\", "/");
			if (rootRel !== "." && rootRel !== "" && patternRel.startsWith(`${rootRel}/`)) patternRel = patternRel.slice(rootRel.length + 1);
			const matcher = picomatch(patternRel, { dot: true });
			const walk = walkFiles(root, (rel) => matches(matcher, rel) && matches(include, rel), (rel) => matches(exclude, rel));
			truncated ||= walk.truncated;
			for (const rel of walk.files) addTarget(found, cwd, join(root, rel));
			continue;
		}
		let stat;
		try {
			stat = statSync(absoluteInput);
		} catch {
			throw new TestgenError(`target not found: ${input}`, ERROR_CODES.NO_TARGET);
		}
		if (stat.isFile()) addTarget(found, cwd, absoluteInput, (rel) => matches(exclude, rel));
		else if (stat.isDirectory()) {
			const walk = walkFiles(absoluteInput, (rel) => matches(include, rel), (rel) => matches(exclude, rel));
			truncated ||= walk.truncated;
			for (const rel of walk.files) addTarget(found, cwd, join(absoluteInput, rel));
		} else throw new TestgenError(`target is not a regular file or directory: ${input}`, ERROR_CODES.NO_TARGET);
	}
	if (found.size === 0) throw new TestgenError(`no source files matched ${inputs.map((input) => JSON.stringify(input)).join(", ")} under the include/exclude policy (see /testgen --help)`, ERROR_CODES.NO_TARGET);
	return [...found.values()].sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
}
function addTarget(found, cwd, absolute, exclude) {
	if (exclude) {
		if (exclude(normalize(relative(cwd, absolute)))) return;
	}
	if (found.has(absolute)) return;
	found.set(absolute, {
		path: normalize(relative(cwd, absolute)),
		absolute,
		language: languageOf(absolute),
		sizeBytes: safeSize(absolute)
	});
}
function safeSize(path) {
	try {
		return statSync(path).size;
	} catch {
		return 0;
	}
}
/**
* Root directory for a glob: the prefix before the first magic segment.
* Preserves POSIX leading separators and Windows drive letters — `path.join`
* silently drops both.
*/
function globRoot(absoluteGlob) {
	const segments = absoluteGlob.split(/[\\/]+/u).filter((segment) => segment.length > 0);
	const root = [];
	for (const segment of segments) {
		if (hasGlobMagic(segment)) break;
		root.push(segment);
	}
	if (root.length === 0) return resolve(".");
	const joined = root.join("/");
	if (absoluteGlob.startsWith("/")) return `/${joined}`;
	if (/^[A-Za-z]:/u.test(absoluteGlob)) return joined;
	return resolve(joined);
}
function normalize(path) {
	return path.replaceAll("\\", "/");
}
//#endregion
//#region src/engine/pipeline.ts
/**
* The pipeline: target resolution → generation → run → bounded fix loop →
* report. One function drives the slash command and the model tool alike.
* All side effects (file writes, runner spawns) are injectable so the whole
* orchestration is unit-testable without a real project or LLM.
* @module dsh-testgen/engine/pipeline
*/
const realDeps = {
	now: () => Date.now(),
	writeFile: (path, data) => {
		mkdirSync(dirname(path), { recursive: true });
		writeFileSync(path, data, "utf8");
	},
	fileExists: (path) => existsSync(path),
	readSource: (path) => {
		try {
			return readFileSync(path, "utf8");
		} catch {
			return "";
		}
	},
	runTests
};
/** Normalize request overrides onto the effective config. */
function mergeRequest(config, request) {
	const merged = { ...config };
	if (request.runner !== void 0) merged.runner = request.runner;
	if (request.generator !== void 0) merged.generator = request.generator;
	if (request.maxIterations !== void 0) merged.maxIterations = request.maxIterations;
	if (request.autoRun !== void 0) merged.autoRun = request.autoRun;
	if (request.model !== void 0) {
		const slash = request.model.indexOf("/");
		if (slash === -1) merged.model = {
			provider: merged.model?.provider ?? "",
			model: request.model
		};
		else merged.model = {
			provider: request.model.slice(0, slash),
			model: request.model.slice(slash + 1)
		};
	}
	if (merged.maxIterations < 0 || !Number.isFinite(merged.maxIterations)) throw new TestgenError(`invalid maxIterations: ${merged.maxIterations}`, ERROR_CODES.INVALID_CONFIG);
	return merged;
}
function relPath(cwd, absolute) {
	return relative(cwd, absolute).replaceAll("\\", "/");
}
/** Count `it(`/`test(` occurrences as a cheap emitted-test metric. */
function countTests(source) {
	return source.match(/\b(?:it|test)\(/gu)?.length ?? 0;
}
/**
* Execute the full pipeline. Never throws for runner/test failures — those
* are report data; only configuration and LLM-availability problems throw
* {@link TestgenError}.
*/
async function runTestgen(cwd, request, baseConfig, deps = {}, signal) {
	const start = (deps.now ?? realDeps.now)();
	const writeFile = deps.writeFile ?? realDeps.writeFile;
	const fileExists = deps.fileExists ?? realDeps.fileExists;
	const readSource = deps.readSource ?? realDeps.readSource;
	const spawn = deps.runTests ?? realDeps.runTests;
	const log = deps.logger;
	const config = mergeRequest(baseConfig, request);
	const warnings = [];
	const targets = resolveTargets(cwd, request.target, config);
	const framework = detectFramework(cwd, config.runner);
	const supported = targets.filter((target) => target.language !== "unknown");
	for (const skipped of targets.filter((target) => target.language === "unknown")) warnings.push(`skipped ${skipped.path}: unsupported language for this dsh-testgen version (TypeScript/JavaScript only)`);
	const runnable = supported.filter((target) => !(framework === "node-test" && (target.language === "typescript-jsx" || target.language === "javascript-jsx")));
	for (const skipped of supported.filter((target) => !runnable.includes(target))) warnings.push(`skipped ${skipped.path}: node:test cannot execute JSX — pin a vitest or jest runner to test this target`);
	if (runnable.length === 0) return {
		status: "skipped",
		targets: [],
		generated: [],
		runs: [],
		warnings,
		stats: {
			generatedFiles: 0,
			passed: 0,
			failed: 0,
			iterations: 0
		},
		elapsedMs: (deps.now ?? realDeps.now)() - start
	};
	let mode = config.generator === "template" ? "template" : config.generator === "llm" ? "llm" : "template";
	if (config.generator === "llm" && !deps.llm) throw new TestgenError("generator is pinned to `llm` but no LLM service is composed in this profile", ERROR_CODES.LLM_UNAVAILABLE);
	if (config.generator === "auto") {
		mode = deps.llm && deps.llm.listProviders().length > 0 ? "llm" : "template";
		if (mode === "template") warnings.push("no LLM adapter composed — using the deterministic template generator (structural smoke tests)");
	}
	log?.info?.("testgen: %d target(s), framework %s, generator %s", runnable.length, framework, mode);
	const generated = [];
	const ownedPaths = /* @__PURE__ */ new Set();
	let resolved;
	if (mode === "llm" && deps.llm) {
		resolved = await resolveModel(deps.llm, config);
		log?.info?.("testgen: generating with %s/%s", resolved.provider, resolved.model);
	}
	for (const target of runnable) {
		const testPath = testFilePathFor(target, config.testDir, framework);
		if (fileExists(testPath) && !ownedPaths.has(testPath)) {
			warnings.push(`skipped ${target.path}: test file already exists at ${relPath(cwd, testPath)} (refusing to overwrite user code)`);
			continue;
		}
		let source;
		if (mode === "template") {
			const result = generateTemplateTest(target, config.testDir, framework);
			source = result.source;
			generated.push({
				path: relPath(cwd, result.path),
				framework,
				generator: "template",
				testCount: result.testCount,
				contentBytes: Buffer.byteLength(result.source)
			});
		} else {
			source = await generateTestSource(deps.llm, resolved, framework, {
				path: target.path,
				language: target.language
			}, readSource(target.absolute), config, signal);
			if (source.length === 0) {
				warnings.push(`skipped ${target.path}: model returned empty test code`);
				continue;
			}
			generated.push({
				path: relPath(cwd, testPath),
				framework,
				generator: "llm",
				testCount: countTests(source),
				contentBytes: Buffer.byteLength(source)
			});
		}
		writeFile(testPath, source);
		ownedPaths.add(testPath);
		log?.info?.("testgen: wrote %s", relPath(cwd, testPath));
	}
	if (generated.length === 0) return {
		status: "skipped",
		targets: runnable.map((target) => ({
			path: target.path,
			language: target.language
		})),
		generated: [],
		runs: [],
		warnings,
		stats: {
			generatedFiles: 0,
			passed: 0,
			failed: 0,
			iterations: 0
		},
		elapsedMs: (deps.now ?? realDeps.now)() - start
	};
	const runs = [];
	let status = "failed";
	const runFiles = generated.map((test) => test.path);
	if (!config.autoRun) status = "generated";
	else {
		const maxIterations = config.maxIterations;
		for (let iteration = 0; iteration <= maxIterations; iteration++) {
			const run = await spawn({
				cwd,
				files: runFiles,
				framework,
				timeoutMs: config.timeoutSec * 1e3,
				signal
			});
			run.iteration = iteration;
			runs.push(run);
			log?.info?.("testgen: run %d exit %s in %d ms", iteration, String(run.exitCode), run.durationMs);
			if (signal?.aborted) {
				warnings.push("aborted by the caller");
				status = "failed";
				break;
			}
			if (run.exitCode === 0) {
				status = iteration === 0 ? "passed" : "fixed";
				break;
			}
			if (mode === "template" || !deps.llm) {
				warnings.push("tests failed and the template generator cannot self-fix — switch to the LLM generator for behavioral fixups");
				status = "failed";
				break;
			}
			if (iteration >= maxIterations) {
				warnings.push(`iteration limit reached (maxIterations: ${maxIterations})`);
				status = "failed";
				break;
			}
			for (const test of generated) {
				const absolute = resolve(cwd, test.path);
				const current = readSource(absolute);
				const fixed = await fixTestSource(deps.llm, resolved, framework, test.path, current, run, config, signal);
				if (fixed.length > 0) {
					writeFile(absolute, fixed);
					log?.info?.("testgen: fixed %s", test.path);
				}
			}
		}
	}
	const last = runs.at(-1);
	return {
		status,
		targets: runnable.map((target) => ({
			path: target.path,
			language: target.language
		})),
		generated,
		runs,
		warnings,
		stats: {
			generatedFiles: generated.length,
			passed: last?.summary?.passed ?? 0,
			failed: last?.summary?.failed ?? (status === "failed" && last ? last.failures.length || 1 : 0),
			iterations: runs.length
		},
		elapsedMs: (deps.now ?? realDeps.now)() - start
	};
}
//#endregion
//#region src/settings.ts
/**
* Hot-reloadable configuration: registers the `testgen` settings namespace
* with the harness settings seam when a provider is composed. Layering is
* schema defaults → composition entry → the user's `settings.yaml` section,
* so edits take effect live without restarting dsh.
* @module dsh-testgen/settings
*/
const SETTINGS_NAMESPACE = "testgen";
/**
* Register the settings namespace opportunistically: when no settings
* provider is composed the plugin still runs, resolving from the
* composition entry alone — matching the dsh-settings seam contract.
*/
function setupSettings(ctx, config) {
	return { effective() {
		return resolveConfig(config);
	} };
}
function countChangedFields(prev, next) {
	if (!prev || !next || typeof prev !== "object" || typeof next !== "object") return 0;
	const keys = /* @__PURE__ */ new Set([...Object.keys(prev), ...Object.keys(next)]);
	let count = 0;
	for (const key of keys) if (JSON.stringify(prev[key]) !== JSON.stringify(next[key])) count++;
	return count;
}
//#endregion
//#region src/tool.ts
/** Canonical output schema — the JSON projection of {@link TestgenReport}. */
const REPORT_SCHEMA = {
	type: "object",
	additionalProperties: false,
	properties: {
		status: {
			type: "string",
			required: true,
			enum: [
				"passed",
				"fixed",
				"generated",
				"failed",
				"skipped"
			]
		},
		targets: {
			type: "array",
			required: true,
			items: {
				type: "object",
				additionalProperties: false,
				properties: {
					path: {
						type: "string",
						required: true
					},
					language: {
						type: "string",
						required: true
					}
				}
			}
		},
		generated: {
			type: "array",
			required: true,
			items: {
				type: "object",
				additionalProperties: false,
				properties: {
					path: {
						type: "string",
						required: true
					},
					framework: {
						type: "string",
						required: true
					},
					generator: {
						type: "string",
						required: true
					},
					testCount: {
						type: "integer",
						required: true
					},
					contentBytes: {
						type: "integer",
						required: true
					}
				}
			}
		},
		runs: {
			type: "array",
			required: true,
			items: {
				type: "object",
				additionalProperties: false,
				properties: {
					iteration: {
						type: "integer",
						required: true
					},
					framework: {
						type: "string",
						required: true
					},
					command: {
						type: "string",
						required: true
					},
					exitCode: { oneOf: [{ type: "integer" }, { type: "null" }] },
					timedOut: {
						type: "boolean",
						required: true
					},
					summary: {
						type: "object",
						additionalProperties: false,
						properties: {
							passed: {
								type: "integer",
								required: true
							},
							failed: {
								type: "integer",
								required: true
							},
							skipped: { type: "integer" }
						}
					},
					failures: {
						type: "array",
						required: true,
						items: {
							type: "object",
							additionalProperties: false,
							properties: {
								testName: { type: "string" },
								file: { type: "string" },
								message: {
									type: "string",
									required: true
								}
							}
						}
					},
					durationMs: {
						type: "integer",
						required: true
					}
				}
			}
		},
		warnings: {
			type: "array",
			required: true,
			items: { type: "string" }
		},
		stats: {
			type: "object",
			required: true,
			additionalProperties: false,
			properties: {
				generatedFiles: {
					type: "integer",
					required: true
				},
				passed: {
					type: "integer",
					required: true
				},
				failed: {
					type: "integer",
					required: true
				},
				iterations: {
					type: "integer",
					required: true
				}
			}
		},
		elapsedMs: {
			type: "integer",
			required: true
		}
	}
};
/** Drop the bulky raw runner output before the value crosses the wire. */
function sanitizeReport(report) {
	return {
		status: report.status,
		targets: report.targets,
		generated: report.generated,
		runs: report.runs.map((run) => ({
			iteration: run.iteration,
			framework: run.framework,
			command: run.command,
			exitCode: run.exitCode,
			timedOut: run.timedOut,
			summary: run.summary,
			failures: run.failures,
			durationMs: run.durationMs
		})),
		warnings: report.warnings,
		stats: report.stats,
		elapsedMs: report.elapsedMs
	};
}
/** Register the `generate_tests` tool; returns the exact disposer. */
function registerTool(ctx, deps) {
	const logger = ctx.logger?.("testgen");
	return ctx.tools.register(defineTool({
		name: "generate_tests",
		description: ["Generate unit tests for source files in the agent workspace. Scaffolds test files (behavioral tests through the LLM when available, deterministic structural smoke tests otherwise), runs the project test runner, and fixes failures up to maxIterations. Returns a structured report; does not modify production source."].join(" "),
		parameters: {
			target: {
				type: "string",
				required: true,
				description: "File path, directory, or glob relative to the workspace root, e.g. \"src/utils/math.ts\" or \"src/**/*.ts\"."
			},
			runner: {
				type: "string",
				enum: [...RUNNER_VALUES],
				description: "Test framework to run; default auto-detects from the project (vitest, jest, mocha, else node:test)."
			},
			generator: {
				type: "string",
				enum: [...GENERATOR_VALUES],
				description: "llm (behavioral tests), template (deterministic smoke tests), or auto."
			},
			maxIterations: {
				type: "integer",
				description: "Upper bound of the generate-run-fix loop; defaults to the configured value."
			},
			autoRun: {
				type: "boolean",
				description: "Whether to run the suite after generation; defaults to true."
			},
			model: {
				type: "string",
				description: "Provider/model override for generation calls, e.g. \"deepseek-official/deepseek-chat\"."
			}
		},
		output: {
			schema: REPORT_SCHEMA,
			render: (_args, value) => [{
				type: "text",
				text: renderReportPlain(value)
			}]
		},
		timeoutMs: 3e5,
		isConcurrencySafe: () => false,
		presentCall: (args) => ({
			card: "generic",
			title: "Generate tests",
			kind: "other",
			rawInput: args.target
		}),
		async execute(args, exec) {
			const request = {
				target: args.target,
				runner: args.runner,
				generator: args.generator,
				maxIterations: args.maxIterations,
				autoRun: args.autoRun,
				model: args.model
			};
			logger?.info("generate_tests(%s) from agent workspace", args.target);
			try {
				const report = await deps.run(deps.cwd(exec.agent), request, exec.signal);
				logger?.info("generate_tests finished: %s", report.status);
				return sanitizeReport(report);
			} catch (error) {
				logger?.error("generate_tests failed: %s", renderError(error));
				throw error;
			}
		}
	}));
}
//#endregion
//#region src/index.ts
const name = "testgen";
const inject = ["commands", "tools"];
const version = "1.0.0";
/**
* Cordis plugin entry. The loader imports this module by package name and
* calls `apply` with the composition entry's config.
*/
function apply(ctx, rawConfig) {
	const config = resolveConfig(rawConfig);
	const logger = ctx.logger?.(name);
	logger?.info("dsh-testgen v%s loading", version);
	const settings = setupSettings(ctx, config);
	const active = /* @__PURE__ */ new Set();
	const engineDeps = () => ({
		logger,
		llm: ctx.get("llm")
	});
	/** Workspace root for the slash command (the invoking directory). */
	const commandCwd = () => process.cwd();
	/** Workspace root for the model tool (the agent session's cwd). */
	const toolCwd = (agent) => agent?.session.header.cwd ?? process.cwd();
	/**
	* Run the pipeline under a dispose-aware abort: an in-flight test run can
	* never outlive the plugin's fiber.
	*/
	const run = async (cwd, request, external) => {
		const controller = new AbortController();
		active.add(controller);
		const onExternalAbort = () => controller.abort();
		external?.addEventListener("abort", onExternalAbort, { once: true });
		try {
			return await runTestgen(cwd, request, settings.effective(), engineDeps(), controller.signal);
		} finally {
			active.delete(controller);
			external?.removeEventListener("abort", onExternalAbort);
		}
	};
	const disposeCommand = registerCommand(ctx, {
		effective: () => settings.effective(),
		run: (cwd, request, signal) => run(cwd, request, signal),
		cwd: commandCwd
	});
	const disposeTool = registerTool(ctx, {
		effective: () => settings.effective(),
		run: (cwd, request, signal) => run(cwd, request, signal),
		cwd: toolCwd
	});
	ctx.effect(() => () => {
		logger?.info("dsh-testgen disposing: aborting %d in-flight run(s)", active.size);
		for (const controller of active) controller.abort();
		disposeCommand();
		disposeTool();
	});
	logger?.info("dsh-testgen ready: /testgen command and generate_tests tool registered");
}
//#endregion
export { Config, ERROR_CODES, SettingsSchema, TestgenError, apply, countTests, detectFramework, inject, isTestgenError, languageOf, mergeRequest, name, parseExports, parseRunnerOutput, renderError, renderTestFile, resolveTargets, runTestgen, runTests, stripNoise, testFilePathFor, version, walkFiles };

//# sourceMappingURL=index.mjs.map