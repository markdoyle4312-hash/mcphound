/**
 * Serializes a JSON-LD object for inline embedding in a <script> tag.
 * Escapes "<" so a value sourced from scanned registry data (a server name
 * or finding text mcphound didn't write itself) can't break out of the
 * script tag with a literal "</script>".
 */
export function jsonLdScript(data: unknown): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}
