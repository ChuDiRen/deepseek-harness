// 附件库（宿主 0.1.3 的 ~/.dsh/attachments/v1）是只进不出的黑箱：
// AttachmentStore 只有 save/read 方法面，官方 GC 在 roadmap，模型侧完全
// 不可见。本模块提供只读的存储视图与定位，路径全部由内部拼接——外部输入
// 只允许进入 sha/原名匹配，不参与路径构造。host 侧直读是插件自身行为
// （0.4.x 上传管线同一先例）；模型侧对附件字节的访问仍走 export 工具的
// ctx.fs 沙箱护栏。
import { readdir, stat } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { formatBytes } from "./format.js";
const SHA64_RE = /^[0-9a-f]{64}$/;
const SHA_PREFIX_RE = /^[0-9a-f]{8,64}$/;
const SHA_SHORT_RE = /^[0-9a-f]{2,7}$/;
/**
 * DSH_HOME 覆盖 .dsh 家目录（与 dsh-home-paths 同语义，支持 ~/ 前缀）。
 * 0.5.2 审查建议直接 import 官方 resolveDshHome，但插件运行时树（profile
 * node_modules）不含 @deepseek-ai/dsh-home-paths——官方服务一律 duck-type
 * 注入、不 import 宿主内部包，依赖隔离是刻意的。已知与官方真源的发散：
 * `DSH_HOME=~` 时官方解析为 `~/attachments/v1` 而本实现为
 * `~/.dsh/attachments/v1`（默认部署不设 DSH_HOME，两版一致）。
 */
export function defaultAttachmentsDir() {
    const env = process.env.DSH_HOME;
    if (env === undefined || env.trim() === '')
        return join(homedir(), '.dsh', 'attachments', 'v1');
    const home = env.trim();
    if (home === '~')
        return join(homedir(), '.dsh', 'attachments', 'v1');
    if (home.startsWith('~/'))
        return join(homedir(), home.slice(2), 'attachments', 'v1');
    return join(home, 'attachments', 'v1');
}
/**
 * 列出附件库全部文件，按修改时间降序。附件库目录不存在（新装宿主）按
 * 空清单处理——对「看一眼有什么」的只读场景，缺目录不是错误。
 */
export async function listAttachments(dir) {
    const entries = [];
    const filesRoot = join(dir, 'files');
    let shards;
    try {
        shards = await readdir(filesRoot, { withFileTypes: true });
    }
    catch {
        return entries;
    }
    for (const shard of shards) {
        if (!shard.isDirectory() || !/^[0-9a-f]{2}$/.test(shard.name))
            continue;
        const shardDir = join(filesRoot, shard.name);
        let objects;
        try {
            objects = await readdir(shardDir, { withFileTypes: true });
        }
        catch {
            continue;
        }
        for (const obj of objects) {
            if (!obj.isDirectory() || !SHA64_RE.test(obj.name))
                continue;
            const objDir = join(shardDir, obj.name);
            let names;
            try {
                names = (await readdir(objDir)).filter((n) => !n.startsWith('.')).sort();
            }
            catch {
                continue;
            }
            if (names.length === 0)
                continue;
            // 一个 sha 一个原名目录；出现多个条目时取字典序第一个并如实上报该名。
            const hostPath = join(objDir, names[0]);
            let st;
            try {
                st = await stat(hostPath);
            }
            catch {
                continue;
            }
            if (!st.isFile())
                continue;
            entries.push({ name: names[0], sha: obj.name, bytes: st.size, modifiedMs: st.mtimeMs });
        }
    }
    return entries.sort((a, b) => b.modifiedMs - a.modifiedMs);
}
/**
 * 按标识定位一个附件。标识可以是 sha256 十六进制前缀（8-64 位，来自
 * attachment_list 的 sha 字段）或精确原始文件名；原名可能对应多条 CAS
 * 条目，歧义时报错列出候选让模型加长 sha。
 */
export async function findAttachment(dir, id) {
    const clean = id.trim().toLowerCase();
    const filesRoot = join(dir, 'files');
    // 2-7 位纯 hex 是手滑的短前缀：给明确引导，而不是误导性的「按原名找不到」。
    if (SHA_SHORT_RE.test(clean)) {
        throw new Error(`sha prefix must be at least 8 hex chars, got "${id}" — run attachment_list for full ids`);
    }
    if (SHA_PREFIX_RE.test(clean)) {
        const shardDir = join(filesRoot, clean.slice(0, 2));
        let objects;
        try {
            objects = await readdir(shardDir, { withFileTypes: true });
        }
        catch {
            throw new Error(`no attachment matches sha prefix "${id}" — run attachment_list to see what exists`);
        }
        const matches = [];
        for (const obj of objects) {
            if (obj.isDirectory() && obj.name.startsWith(clean))
                matches.push({ dirent: obj, dir: shardDir });
        }
        return resolveMatches(matches, id);
    }
    // 原名匹配：必须全库扫（原名无分片线索）。
    const all = await listAttachments(dir);
    const byName = all.filter((entry) => entry.name === id.trim());
    if (byName.length === 0) {
        throw new Error(`no attachment named "${id}" — run attachment_list to see what exists`);
    }
    if (byName.length > 1) {
        const list = byName.map((entry) => `${entry.sha.slice(0, 8)} (${formatBytes(entry.bytes)})`).join(', ');
        throw new Error(`"${id}" matches ${byName.length} attachments; re-run with a sha prefix: ${list}`);
    }
    const entry = byName[0];
    return { name: entry.name, sha: entry.sha, bytes: entry.bytes, hostPath: join(filesRoot, entry.sha.slice(0, 2), entry.sha, entry.name) };
}
async function resolveMatches(matches, id) {
    if (matches.length === 0) {
        throw new Error(`no attachment matches sha prefix "${id}" — run attachment_list to see what exists`);
    }
    if (matches.length > 1) {
        const list = matches.map((m) => m.dirent.name.slice(0, 8)).join(', ');
        throw new Error(`sha prefix "${id}" is ambiguous (${matches.length} matches): ${list} — use more hex chars`);
    }
    const sha = matches[0].dirent.name;
    const objDir = join(matches[0].dir, sha);
    const names = (await readdir(objDir)).filter((n) => !n.startsWith('.')).sort();
    if (names.length === 0)
        throw new Error(`attachment object "${sha}" is empty on disk`);
    const hostPath = join(objDir, names[0]);
    const st = await stat(hostPath);
    if (!st.isFile())
        throw new Error(`attachment object "${sha}" is not a regular file`);
    return { name: names[0], sha, bytes: st.size, hostPath };
}
