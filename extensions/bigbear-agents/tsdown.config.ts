/**
 * Builds both halves of the extension. The shapes mirror the repository's
 * shared client-bundle preset (packages/client/tsdown.client.ts) minus its
 * workspace-manifest lookups, which only know packages under the workspace
 * globs: the Node face bundles the host plugin, and the browser face wraps
 * the settings page into the module-table closure factory the dsh client
 * parser loads (externals resolve through the injected require; platform
 * modules come from the seed table).
 */
import { isBuiltin } from 'node:module'
import { clientBuildEnvironmentDefines } from '../../scripts/client-build-environment.ts'
import { PLATFORM_MODULES } from '../../packages/client/web/src/platform.ts'

const id = 'dsh-bigbear-agents'

/** Seed-table specifiers every client bundle may require instead of inlining. */
const clientExternals = new Set<string>(PLATFORM_MODULES)

const node = {
  name: id,
  entry: { index: 'src/index.ts' },
  outDir: 'lib',
  format: ['esm'],
  platform: 'node',
  target: 'es2024',
  fixedExtension: false,
  dts: false,
  sourcemap: true,
  clean: false,
  // The host half imports node builtins only; everything non-builtin would be
  // a bundled mistake, so inline non-builtins and let tsdown own builtins.
  deps: {
    neverBundle: () => false,
    alwaysBundle: (specifier: string) => !isBuiltin(specifier),
  },
}

const client = {
  name: `${id}/client`,
  entry: { client: 'src/client/index.ts' },
  // Browser bundle lands next to the node half (single lib artifact dir); the
  // entryFileNames pin keeps it exactly lib/client.js. clean stays off — a
  // default clean would wipe the node-half output emitted alongside.
  outDir: 'lib',
  format: 'cjs',
  platform: 'browser',
  dts: false,
  sourcemap: true,
  clean: false,
  deps: {
    neverBundle: (specifier: string) => clientExternals.has(specifier),
    // A require() the module table cannot answer is a guaranteed runtime
    // throw, so everything not requested stays inlined.
    alwaysBundle: (specifier: string) => !clientExternals.has(specifier),
  },
  inputOptions: {
    resolve: {
      conditionNames: [
        (process.env.NODE_ENV ?? 'production') === 'development' ? 'development' : 'production',
        'browser', 'import', 'module', 'default',
      ],
    },
  },
  define: {
    ...clientBuildEnvironmentDefines(process.env),
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV ?? 'production'),
    'import.meta.env.MODE': JSON.stringify(process.env.NODE_ENV ?? 'production'),
    'import.meta.env': JSON.stringify({ MODE: process.env.NODE_ENV ?? 'production' }),
  },
  // Single entry, no dynamic chunks: the registration is always the bare
  // entry form. banner/footer/intro are rolldown output options — top-level
  // banner/footer would work, but intro is honored only here.
  outputOptions: {
    // The cjs format would name the artifact client.cjs under the package's
    // type:module; the loader contract pins exactly lib/client.js.
    entryFileNames: 'client.js',
    banner: () =>
      `window.__ModuleLoader__.load({ id: ${JSON.stringify(id)}, factory: (require) => {`,
    footer: 'return module.exports; } });',
    intro: 'var module = { exports: {} }; var exports = module.exports;',
  },
}

export default [node, client]
