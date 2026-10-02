// Mirrors parse_url / is_telegram_url in backend/ingestors/telegram.py - keep them in sync.
// Used by the upload dialog to show the "Posts to fetch" field for Telegram links.

export const TELEGRAM_DEFAULT_POSTS = 200; // backend DEFAULT_MAX_POSTS
export const TELEGRAM_MAX_POSTS = 2000; // backend MAX_POSTS_LIMIT

const HOSTS = new Set(["t.me", "www.t.me", "telegram.me", "www.telegram.me"]);
const CHANNEL_RE = /^[A-Za-z][A-Za-z0-9_]{3,31}$/;
// first path segments that are not public channels (invites, private links, ...)
const RESERVED_PATHS = new Set([
  "joinchat", "c", "addstickers", "addemoji", "addlist", "addtheme", "share",
  "proxy", "socks", "login", "iv", "setlanguage", "boost", "contact", "invoice",
]);

export interface TelegramLink {
  channel: string;
  postId: number | null; // set for post links, ingestion counts back from that post
}

/**
 * Accepts t.me/<ch>, t.me/s/<ch>, t.me/<ch>/<id>, t.me/s/<ch>/<id> (also telegram.me,
 * with or without scheme). Returns null for anything else, including private links.
 */
export function parseTelegramUrl(input: string): TelegramLink | null {
  const raw = input.trim();
  if (!raw) return null;

  let url: URL;
  try {
    url = new URL(raw.includes("://") ? raw : `https://${raw}`);
  } catch {
    return null;
  }
  if (!HOSTS.has(url.hostname.toLowerCase())) return null;

  let parts = url.pathname.split("/").filter(Boolean);
  if (parts[0] === "s") parts = parts.slice(1);
  if (parts.length < 1 || parts.length > 2) return null;

  const [channel, post] = parts;
  if (RESERVED_PATHS.has(channel.toLowerCase()) || !CHANNEL_RE.test(channel)) {
    return null;
  }
  if (post === undefined) return { channel, postId: null };
  if (!/^\d+$/.test(post)) return null;
  return { channel, postId: Number(post) };
}
