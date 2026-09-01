import { describe, expect, it } from "vitest";
import { scoreCascade } from "./scoring";
import type { Finding } from "./types";

function finding(overrides: Partial<Finding>): Finding {
  return {
    rule_id: "MCP-STATIC-000",
    title: "test finding",
    severity: "medium",
    confidence: "medium",
    owasp: "AST01",
    detail: "",
    recommendation: "",
    ...overrides,
  };
}

describe("scoreCascade", () => {
  it("orders worst severity first regardless of input order", () => {
    const steps = scoreCascade([
      finding({ rule_id: "a", severity: "low", confidence: "low" }),
      finding({ rule_id: "b", severity: "critical", confidence: "high" }),
    ]);
    expect(steps.map((s) => s.finding.rule_id)).toEqual(["b", "a"]);
  });

  it("starts the first cut from 100 and only ever decreases", () => {
    const steps = scoreCascade([
      finding({ severity: "high", confidence: "high" }),
      finding({ severity: "medium", confidence: "medium" }),
    ]);
    expect(steps[0].before).toBe(100);
    expect(steps[1].before).toBe(steps[0].after);
    expect(steps[1].after).toBeLessThan(steps[0].after);
  });

  it("applies weight * confidence as the decay for a single finding", () => {
    // high (0.35) * medium confidence (0.7) = 0.245 decay -> 100 * 0.755 = 75.5
    const steps = scoreCascade([finding({ severity: "high", confidence: "medium" })]);
    expect(steps[0].after).toBeCloseTo(75.5, 5);
  });
});
