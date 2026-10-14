// dsh-files 0.6.1 — attachment loop helpers: reference normalization,
// download filename sanitation and display formatting. Pure functions, no I/O.
/** 64-hex content address (the `sha` field attachment_list reports). */
const SHA64_RE = /^[0-9a-f]{64}$/;
/** Maximum length of a sanitized download / export filename (UTF-16 code units). */
export const MAX_SAFE_NAME = 120;
/**
 * Normalize one user-supplied attachment reference to the canonical
 * `sha256:<64hex>` shape. Accepts a bare 64-hex sha (what attachment_list
 * reports and the UI passes) or the full `sha256:`-prefixed form.
 */
export function normalizeAttachmentRef(raw) {
    const value = raw.trim().toLowerCase();
    if (SHA64_RE.test(value))
        return `sha256:${value}`;
    if (value.startsWith('sha256:')) {
        const sha = value.slice('sha256:'.length);
        if (SHA64_RE.test(sha))
            return value;
    }
    return undefined;
}
/** Extract the bare 64-hex sha from a normalized or raw reference. */
export function shaOf(raw) {
    const normalized = normalizeAttachmentRef(raw);
    return normalized === undefined ? undefined : normalized.slice('sha256:'.length);
}
/**
 * Sanitize a download filename for `Content-Disposition`: strip path
 * separators, control characters, quotes and backslashes so the quoted
 * filename can never break the header or invite response splitting.
 * The sanitized name is never empty.
 */
export function sanitizeDownloadName(raw) {
    const cleaned = raw
        .replace(/[\\/]/g, '_')
        .replace(/[\u0000-\u001f\u007f-\u009f"']/g, '_')
        .replace(/\s+/g, ' ')
        .trim();
    const candidate = (cleaned === '' ? 'download' : cleaned).slice(0, MAX_SAFE_NAME);
    if (/^[\x20-\x7e]+$/.test(candidate))
        return candidate;
    const ascii = candidate.replace(/[^\x20-\x7e]/g, '_');
    const fallback = ascii.trim();
    return fallback === '' ? 'download' : fallback;
}
/**
 * Sanitize a name for a filesystem path (export to workspace): control
 * characters, separators and dangerous leading dots removed, Unicode kept
 * (Chinese names stay intact). Never empty; capped by code units.
 */
export function sanitizeFileNameForPath(raw) {
    const cleaned = raw
        .replace(/[\\/]/g, '_')
        .replace(/[\u0000-\u001f\u007f-\u009f]/g, '_')
        .replace(/\s+/g, ' ')
        .trim()
        .replace(/^[._]+/, '');
    const candidate = cleaned.slice(0, MAX_SAFE_NAME);
    if (candidate !== '')
        return candidate;
    return `attachment-${Date.now().toString(36)}`;
}
/** Short sha prefix for UI display: first 8 hex chars. */
export function shortSha(sha) {
    return sha.length > 8 ? sha.slice(0, 8) : sha;
}
