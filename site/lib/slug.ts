export function nameToPathSegments(name: string): string[] {
  return name.split("/");
}

export function pathSegmentsToName(segments: string[]): string {
  // Next's static export percent-encodes generateStaticParams() segment
  // values (e.g. "@modelcontextprotocol" -> "%40modelcontextprotocol")
  // internally, but hands the *encoded* string back as params.slug at
  // render time instead of decoding it first — so undo that here rather
  // than compare a decoded name against an encoded one and 404.
  return segments.map(decodeURIComponent).join("/");
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
