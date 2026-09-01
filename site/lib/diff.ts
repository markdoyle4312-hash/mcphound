export type DiffOp = {
  type: "equal" | "insert" | "delete" | "replace";
  from: string;
  to: string;
};

/**
 * Character-level Levenshtein alignment between two short identifiers
 * (npm/registry package names). Used to render *why* two names are
 * `distance` edits apart, not just the number — mirrors the DP table the
 * scanner's edit-distance check already computes server-side.
 */
export function charDiff(a: string, b: string): DiffOp[] {
  const rows = a.length + 1;
  const cols = b.length + 1;
  const cost: number[][] = Array.from({ length: rows }, () => new Array(cols).fill(0));
  for (let i = 0; i < rows; i++) cost[i][0] = i;
  for (let j = 0; j < cols; j++) cost[0][j] = j;
  for (let i = 1; i < rows; i++) {
    for (let j = 1; j < cols; j++) {
      if (a[i - 1] === b[j - 1]) {
        cost[i][j] = cost[i - 1][j - 1];
      } else {
        cost[i][j] = 1 + Math.min(cost[i - 1][j - 1], cost[i - 1][j], cost[i][j - 1]);
      }
    }
  }

  const ops: DiffOp[] = [];
  let i = rows - 1;
  let j = cols - 1;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      ops.push({ type: "equal", from: a[i - 1], to: b[j - 1] });
      i--;
      j--;
    } else if (i > 0 && j > 0 && cost[i][j] === cost[i - 1][j - 1] + 1) {
      ops.push({ type: "replace", from: a[i - 1], to: b[j - 1] });
      i--;
      j--;
    } else if (j > 0 && cost[i][j] === cost[i][j - 1] + 1) {
      ops.push({ type: "insert", from: "", to: b[j - 1] });
      j--;
    } else {
      ops.push({ type: "delete", from: a[i - 1], to: "" });
      i--;
    }
  }
  return ops.reverse();
}
