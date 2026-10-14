/**
 * Single-file client + ESM host build for dsh-at-file.
 *
 * The web server serves exactly one file per plugin (/plugins/dsh-at-file/client.js),
 * so the client half is one CJS bundle wrapped in the ModuleLoader factory
 * handshake; @deepseek-ai/dsh-* and react stay external (the profile's healed
 * node_modules and the app's module system provide them). The host half is
 * plain ESM for Node, externalizing @deepseek-ai/dsh-* plus cordis while
 * bundling schemastery (the Loader validates Config against the schema).
 */
import { build } from 'esbuild'
import { mkdirSync, readFileSync } from 'node:fs'

mkdirSync('lib', { recursive: true })

const dshExternal = ['@deepseek-ai/cordis', '@deepseek-ai/dsh-*']

const clientStoreCompat = {
  name: 'dsh-client-store-compat',
  setup(build) {
    build.onResolve({ filter: /^@deepseek-ai\/dsh-client-store$/ }, (args) => {
      if (args.namespace === 'dsh-client-store-compat') return { path: args.path, external: true }
      return { path: 'client-store-fallback', namespace: 'dsh-client-store-compat' }
    })
    build.onLoad({ filter: /.*/, namespace: 'dsh-client-store-compat' }, () => ({
      loader: 'js',
      contents: `
        let store
        let usesSplitClientStore = true
        try {
          store = require('@deepseek-ai/dsh-client-store')
        } catch {
          usesSplitClientStore = false
          store = require('@deepseek-ai/dsh-client-runtime/client')
        }
        export const createSnapshotStore = store.createSnapshotStore
        export { usesSplitClientStore }
      `,
    }))
  },
}

await build({
  entryPoints: ['src/index.ts'],
  outfile: 'lib/index.js',
  bundle: true,
  format: 'esm',
  platform: 'node',
  target: ['node22'],
  sourcemap: true,
  external: dshExternal,
  logLevel: 'info',
})


await build({
  entryPoints: ['src/client/index.ts'],
  outfile: 'lib/client.js',
  bundle: true,
  format: 'cjs',
  platform: 'browser',
  target: ['es2022'],
  sourcemap: true,
  jsx: 'automatic',
  external: [...dshExternal, 'react', 'react-dom', 'react/jsx-runtime', 'react/jsx-dev-runtime', 'scheduler'],
  plugins: [clientStoreCompat],
  banner: {
    js: "window.__ModuleLoader__.load({ id: 'dsh-at-file', factory: (require) => { var module = { exports: {} }; var exports = module.exports;",
  },
  footer: {
    js: 'return module.exports; } });',
  },
  logLevel: 'info',
})

const clientBundle = readFileSync('lib/client.js', 'utf8')
if (!clientBundle.includes('@deepseek-ai/dsh-client-store')
  || !clientBundle.includes('@deepseek-ai/dsh-client-runtime/client')) {
  throw new Error('client bundle is missing the 0.1.2/0.1.1 snapshot-store fallback')
}

import { execFileSync } from 'node:child_process'
execFileSync(process.execPath, ['node_modules/typescript/bin/tsc', '-p', 'tsconfig.json'], { stdio: 'inherit' })
