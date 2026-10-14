// 字节与时间的单一显示真源。服务端（attachment_list 工具、附件路由）与
// 客户端（附件库面板）共用同一实现，保证「同一个文件，两处报同一个数」；
// 客户端侧经 esbuild 打进 bundle，无额外运行时依赖。
/** 1024 进制人性化字节：B / KB / MB 一位小数，≥1 GiB 进 GB 两位小数。 */
export function formatBytes(bytes) {
    if (bytes < 1024)
        return `${bytes} B`;
    if (bytes < 1024 * 1024)
        return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024)
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
const pad2 = (n) => String(n).padStart(2, '0');
/** 全量时间戳 `YYYY-MM-DD HH:mm`（本地时区）。模型清单与导出确认用。 */
export function formatTime(timeMs) {
    const d = new Date(timeMs);
    return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}
/** 面板行的短时间戳：今年 `MM-DD HH:mm`，往年 `YYYY-MM-DD`（本地时区）。 */
export function formatTimeShort(timeMs) {
    const d = new Date(timeMs);
    if (d.getFullYear() === new Date().getFullYear()) {
        return `${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
    }
    return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}
