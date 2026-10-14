// dsh-files 0.6 — browser-trust fence for the attachment routes.
//
// Same semantics as the host's `--trusted-host` fence and the LAN gateway:
// the requests' Host header must name the loopback authority or an
// operator-trusted authority. The fence is the first gate on every route;
// content and reference validation follow.
/** Bare hostname without port or brackets: `[::1]:3080` → `::1`, `localhost:3080` → `localhost`. */
export function hostnameOf(authority) {
    const trimmed = authority.trim();
    // IPv6 literal: [::1]:3080 or [::1]
    if (trimmed.startsWith('[')) {
        const end = trimmed.indexOf(']');
        if (end > 0)
            return trimmed.slice(1, end);
    }
    const colon = trimmed.lastIndexOf(':');
    // A single colon with digits after it is a port separator; bare IPv6 without
    // brackets has many colons and is treated as host-only (never loopback-matching).
    if (colon > 0 && /^\d+$/.test(trimmed.slice(colon + 1)))
        return trimmed.slice(0, colon);
    return trimmed;
}
/** Loopback hostnames the fence accepts: localhost, 127.0.0.0/8, ::1. */
export function isLoopbackHostname(host) {
    const h = host.toLowerCase();
    if (h === 'localhost' || h === 'localhost.localdomain')
        return true;
    if (h === '::1')
        return true;
    if (/^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(h)) {
        const parts = h.split('.').map(Number);
        return parts.every((part) => part >= 0 && part <= 255);
    }
    return false;
}
/**
 * Decide whether one request is trusted to reach attachment routes.
 *
 * `trustedHosts` entries are either a bare host (matches any port) or
 * `host:port` (exact authority match). The Host header may contain a port;
 * `host` alone accepts any port. Loopback is always trusted.
 */
export function isTrustedRequest(req, trustedHosts) {
    const raw = req.headers.host;
    const authority = Array.isArray(raw) ? raw[0] : raw;
    if (authority === undefined || authority === '')
        return false;
    const host = hostnameOf(authority);
    if (isLoopbackHostname(host))
        return true;
    for (const entry of trustedHosts) {
        if (entry === '')
            continue;
        const entryHost = hostnameOf(entry);
        if (host !== entryHost)
            continue;
        // Entries with a port must match the request authority exactly.
        const entryPort = entry.split(':').slice(-1)[0];
        if (/^\d+$/.test(entryPort) && entry.includes(':')) {
            if (authority === entry)
                return true;
            continue;
        }
        // Bare host: any port passes.
        return true;
    }
    return false;
}
