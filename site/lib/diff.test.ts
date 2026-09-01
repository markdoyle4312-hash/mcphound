import { describe, expect, it } from "vitest";
import { charDiff } from "./diff";

describe("charDiff", () => {
  it("marks a single inserted character", () => {
    const ops = charDiff("server-filesystem", "server-filesystemx");
    expect(ops.filter((o) => o.type !== "equal")).toEqual([{ type: "insert", from: "", to: "x" }]);
  });

  it("marks a single replaced character", () => {
    const ops = charDiff("server-postgres", "server-postgres5");
    expect(ops.filter((o) => o.type === "insert")).toHaveLength(1);
  });

  it("returns only equal ops for identical strings", () => {
    const ops = charDiff("same-name", "same-name");
    expect(ops.every((o) => o.type === "equal")).toBe(true);
  });

  it("reconstructs both strings from the op sequence", () => {
    const a = "@modelcontextprotocol/server-filesystem";
    const b = "@modelcontextprotocol/server-filesystemx";
    const ops = charDiff(a, b);
    expect(ops.map((o) => o.from).join("")).toBe(a);
    expect(ops.map((o) => o.to).join("")).toBe(b);
  });
});
