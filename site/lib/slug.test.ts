import { describe, expect, it } from "vitest";
import { nameToPathSegments, pathSegmentsToName, serverHref, typosquatHref } from "./slug";

describe("nameToPathSegments / pathSegmentsToName", () => {
  it("round-trips a registry name through URL path segments", () => {
    const name = "io.github.acme/tool";
    const segments = nameToPathSegments(name);
    expect(segments).toEqual(["io.github.acme", "tool"]);
    expect(pathSegmentsToName(segments)).toBe(name);
  });

  it("handles a name with no slash", () => {
    expect(nameToPathSegments("mcp-server-sqlite")).toEqual(["mcp-server-sqlite"]);
  });
});

describe("serverHref / typosquatHref", () => {
  it("builds a /servers path from a slash-delimited name", () => {
    expect(serverHref("io.github.acme/tool")).toBe("/servers/io.github.acme/tool");
  });

  it("encodes special characters in each path segment", () => {
    expect(serverHref("io.github.acme/tool name")).toBe("/servers/io.github.acme/tool%20name");
  });

  it("builds a /typosquats path from a known package name", () => {
    expect(typosquatHref("@modelcontextprotocol/server-filesystem")).toBe(
      "/typosquats/@modelcontextprotocol/server-filesystem"
    );
  });
});
