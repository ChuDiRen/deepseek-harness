#!/usr/bin/env node
/**
 * Wire every extensions/* bundle package into one dsh profile:
 * vendor junction + `file:` dependency + bundle entry + `pnpm install`.
 *
 * Usage: node extensions/install-to-profile.mjs [profile] [--dsh-home <dir>]
 * The profile defaults to `web`; DSH home defaults to `$DSH_HOME` or `~/.dsh`.
 * Windows-only junction linking; re-run safely on an already-wired profile.
 * @module install-to-profile
 */

import { spawnSync } from 'node:child_process'
import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, symlinkSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(scriptDir, '..')

const argv = process.argv.slice(2)
let dshHomeOverride
const positional = []
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--dsh-home') {
    i++
    if (argv[i] === undefined) throw new Error('--dsh-home requires a directory argument')
    dshHomeOverride = argv[i]
  } else {
    positional.push(argv[i])
  }
}
const profileName = positional[0] ?? 'web'
const fromEnv = process.env.DSH_HOME
const dshHome = dshHomeOverride !== undefined
  ? resolve(dshHomeOverride)
  : (fromEnv !== undefined && fromEnv.trim() !== '' ? resolve(fromEnv) : join(homedir(), '.dsh'))
const profileDir = join(dshHome, 'profiles', profileName)

if (!existsSync(join(profileDir, 'package.json'))) {
  throw new Error(`profile not found: ${profileDir} (no package.json)`)
}

/** Enumerate extension bundles: extension directories up to three levels deep
 * holding a package.json with dsh.bundle.patch (covers third-party/<scope>/<name>).
 * Directories without a bundle manifest are just scan waypoints and drop out.
 */
function extensionBundles() {
  const candidates = []
  for (const top of readdirSync(scriptDir, { withFileTypes: true })) {
    if (!top.isDirectory()) continue
    const level1 = join(scriptDir, top.name)
    candidates.push(level1)
    for (const mid of readdirSync(level1, { withFileTypes: true })) {
      if (!mid.isDirectory()) continue
      const level2 = join(level1, mid.name)
      candidates.push(level2)
      for (const leaf of readdirSync(level2, { withFileTypes: true })) {
        if (leaf.isDirectory()) candidates.push(join(level2, leaf.name))
      }
    }
  }
  return candidates.filter(dir => {
    const manifest = join(dir, 'package.json')
    if (!existsSync(manifest)) return false
    const pkg = JSON.parse(readFileSync(manifest, 'utf8'))
    return pkg.dsh?.bundle?.patch !== undefined
  })
}

/**
 * Extension directories without a package manifest (data trees like
 * bigbear-toolkit) are junctioned into the profile's node_modules under their
 * basename, so plugin code resolving a workspace sibling —
 * `node_modules/<sibling>` — finds the repository copy instead of falling back
 * to a historical absolute path on a machine that does not have it.
 */
function siblingDataDirs() {
  const dirs = []
  for (const top of readdirSync(scriptDir, { withFileTypes: true })) {
    if (!top.isDirectory()) continue
    const dir = join(scriptDir, top.name)
    if (!existsSync(join(dir, 'package.json')) && existsSync(dir)) dirs.push(dir)
  }
  return dirs
}

for (const dir of siblingDataDirs()) {
  const link = join(profileDir, 'node_modules', (() => {
    const segments = resolve(dir).slice(repoRoot.length + 1).split(/[\\/]+/)
    return segments.at(-1)
  })())
  const existing = lstatSync(link, { throwIfNoEntry: false })
  if (existing !== undefined) continue
  symlinkSync(resolve(dir), link, 'junction')
  console.log(`junction ${link} -> ${resolve(dir)}`)
}

const wired = []
for (const dir of extensionBundles()) {
  const pkg = JSON.parse(readFileSync(join(dir, 'package.json'), 'utf8'))
  const name = pkg.name
  if (typeof name !== 'string' || name === '') throw new Error(`extension at ${dir} has no package name`)
  const vendorDir = join(profileDir, 'vendor', name)
  const existing = lstatSync(vendorDir, { throwIfNoEntry: false })
  if (existing !== undefined) {
    // lstat, not stat: a junction's stat view is its target, which would
    // misreport an existing link as a plain directory.
    if (!existing.isSymbolicLink()) {
      throw new Error(`${vendorDir} exists and is a real directory; remove it before wiring ${name}`)
    }
  } else {
    // Junction targets must be plain absolute paths; a file:// URL would be
    // taken literally and produce a dead link. Scoped names nest one level.
    mkdirSync(dirname(vendorDir), { recursive: true })
    symlinkSync(resolve(dir), vendorDir, 'junction')
    console.log(`junction ${vendorDir} -> ${resolve(dir)}`)
  }

  const manifestPath = join(profileDir, 'package.json')
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))
  manifest.dependencies ??= {}
  manifest.dependencies[name] = `file:vendor/${name}`
  manifest.dependencies = Object.fromEntries(
    Object.entries(manifest.dependencies).sort(([a], [b]) => a.localeCompare(b)),
  )
  const bundles = manifest.dsh?.profile?.bundles
  if (!Array.isArray(bundles)) throw new Error(`${manifestPath} lacks dsh.profile.bundles`)
  if (!bundles.includes(name)) bundles.push(name)
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n')
  wired.push(name)
}

if (wired.length === 0) {
  console.log('no extension bundles found; nothing to do')
  process.exit(0)
}
console.log(`wired: ${wired.join(', ')}`)

// Single command string with shell: pnpm is a .cmd shim on Windows, and empty
// args with shell avoids the DEP0190 unescaped-args concatenation path.
const install = spawnSync('pnpm install', { cwd: profileDir, stdio: 'inherit', shell: true })
if (install.status !== 0) {
  throw new Error(`pnpm install failed in ${profileDir} (exit ${install.status})`)
}
console.log(`done. restart dsh web/desktop for profile "${profileName}" to pick up: ${wired.join(', ')}`)
