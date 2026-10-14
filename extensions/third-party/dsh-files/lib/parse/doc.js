// Legacy Word 97-2003 (.doc) text extraction. 金标对照（2026-09-05，附件库
// 4 个真实法规 .doc）：两者正文量级相当（注意口径——textutil 用 wc -c 数
// UTF-8 字节、word-extractor 用 JS length 数 UTF-16 码元，中文差 3 倍是口
// 径假象）；实质差异在 word-extractor 会漏文本框内容（如园林绿化条例的
// 「（2019 年 4 月 25 日通过）」日期段），故 macOS 上 textutil 是主路线；
// word-extractor（纯 JS，saxes+yauzl 两个小依赖）只做非 macOS 平台与
// textutil 失败时的兜底，质量以正文条款为限。
//
// textutil 只接受文件路径，因此 bytes 先落临时目录、用后即删——FsTarget
// 没有公开的宿主路径字段，不能依赖内部结构省这次写盘。
import { execFile } from 'node:child_process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';
const execFileP = promisify(execFile);
export async function parseDocViaTextutil(bytes) {
    const dir = await mkdtemp(join(tmpdir(), 'dsh-files-doc-'));
    try {
        const docPath = join(dir, 'input.doc');
        await writeFile(docPath, bytes);
        const { stdout } = await execFileP('textutil', ['-convert', 'txt', '-stdout', docPath], {
            // 100KB 级 .doc 转出的纯文本远小于此；防超大输出把进程打爆。
            maxBuffer: 64 * 1024 * 1024
        });
        return stdout;
    }
    finally {
        await rm(dir, { recursive: true, force: true });
    }
}
export async function parseDocViaWordExtractor(bytes) {
    // 动态 import：只有真正走到 doc 兜底才加载（约 550KB 纯 JS）。
    const mod = (await import('word-extractor'));
    const extractor = new mod.default();
    const doc = await extractor.extract(Buffer.from(bytes));
    return doc.getBody();
}
export async function parseDoc(bytes) {
    if (process.platform === 'darwin') {
        try {
            const text = await parseDocViaTextutil(bytes);
            // 损坏文件 textutil 以非零退出码失败已被 catch；空输出按失败处理走兜底。
            if (text.trim() !== '')
                return text;
        }
        catch {
            // fall through to word-extractor
        }
    }
    try {
        return await parseDocViaWordExtractor(bytes);
    }
    catch (error) {
        const reason = error instanceof Error ? error.message : String(error);
        // OLE 容器同时覆盖老式 .xls/.ppt：头部无法区分，路由到这里后解析失败
        // 要给模型可自纠的提示，而不是裸抛内部错误。
        throw new Error(`cannot parse legacy Office document: ${reason} (OLE containers also cover old .xls/.ppt, which are not supported)`);
    }
}
