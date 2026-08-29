---
name: New detection rule proposal
about: Propose a new mcphound static/dynamic detection rule before writing the PR
title: "rule: <short description>"
labels: rule-proposal
---

## Attack pattern

<!-- What does this catch? What would a compromised/malicious server look like
     that this rule flags? -->

## Reference

<!-- A primary source: disclosure, CVE, research note, RFC. Per CLAUDE.md, prefer
     primary sources (Invariant Labs, CSA, OWASP, CVEs) over blog paraphrases. -->

## Proposed detection

<!-- Roughly what field it inspects (command/env/url/raw) and what pattern or logic
     it keys on. Doesn't need to be the final regex — this is about the approach. -->

## Would this ever false-positive on a legitimate server?

<!-- Think about this up front — a benign fixture that's a strawman doesn't count
     as a false-positive guard when the PR lands. -->
