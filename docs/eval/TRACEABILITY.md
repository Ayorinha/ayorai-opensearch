# R1 Traceability — ADR-002 to Tests and Golden Cases

This matrix tracks ADR-002 against executable tests and Golden v0. R1 is incremental; planned entries identify rules not implemented yet.

| ADR-002 rule | R1 evidence | Golden v0 coverage | Status |
|---|---|---|---|
| §1 Deterministic Judge table | Exact six Verdict states tested | All 34 cases | planned for R1-e |
| §2 Complete provenance | Evidence provenance shape tested | provenance-complete, provenance-incomplete | partial — R1-a contract |
| §3 Cluster independence | Deterministic dependency rules + Hypothesis property tests | independence-* cases | implemented in R1-b |
| §4 Global aggregation | Golden runner exists; Judge test pending | multi-claim cases | planned for R1-e |
| §5 No-answer / out-of-scope | Current API tests; dedicated contract pending | n01, n02, o01, o02 | planned for R1-f |
| §6 Injection | Security/golden tests pending | i01-i03 and injection cases | planned for R1-d/e |
| §7 Numeric tolerance and dates | Deterministic parser, 1% relative tolerance and date-granularity rules | nt01-nt03 and date conflict | implemented in R1-c |
| §7.1 Closed-world Golden v0 | Existing deterministic closed-world test | all 34 cases | implemented |
| §7.2 Locale parsing | Locale-bound numeric parser with ambiguity rejection | nt01-nt03 | implemented in R1-c |
| §8 Canary | Pending | injection/canary fixtures | planned for R1-d/e |
| §9 Traceability | This matrix | all listed cases | in progress |

R1-b adds only deterministic cluster identity/independence logic and property tests. No Judge decision function is introduced.
