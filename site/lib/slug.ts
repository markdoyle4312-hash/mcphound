export function nameToPathSegments(name: string): string[] {
  return name.split("/");
}

export function pathSegmentsToName(segments: string[]): string {
  return segments.join("/");
}

// encodeURIComponent percent-encodes '@' (to "%40"), but '@' is a valid
// RFC 3986 path-segment character and Next's static export writes
// directories using the literal, un-encoded name (e.g.
// "out/typosquats/@modelcontextprotocol/server-filesystem/") — so undo
// just that one substitution to keep hrefs matching the exported paths.
function encodeSegment(segment: string): string {
  return encodeURIComponent(segment).replace(/%40/g, "@");
}

export function serverHref(name: string): string {
  return "/servers/" + nameToPathSegments(name).map(encodeSegment).join("/");
}

export function typosquatHref(knownName: string): string {
  return "/typosquats/" + nameToPathSegments(knownName).map(encodeSegment).join("/");
}
