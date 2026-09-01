export type Finding = {
  rule_id: string;
  title: string;
  severity: string;
  confidence: string;
  owasp: string;
  detail: string;
  recommendation: string;
};

export type IndexEntry = {
  name: string;
  slug: string;
  score: number;
  finding_count: number;
  last_scanned_at: string;
};

export type ServerDetail = {
  name: string;
  score: number;
  finding_count: number;
  computed_at: string;
  findings: Finding[];
};

export type TyposquatNeighbor = {
  identifier: string;
  distance: number;
  server_name: string;
  server_slug: string | null;
};

export type TyposquatCluster = {
  known_name: string;
  known_slug: string;
  neighbors: TyposquatNeighbor[];
};

export type NewlyFlaggedEntry = {
  name: string;
  slug: string | null;
  score: number;
  previous_score: number | null;
  finding_count: number;
  computed_at: string;
};
