# R1 Traceability — ADR-002 to Tests and Golden Cases

This matrix tracks ADR-002 against executable tests and Golden v0. R1 core is implemented; the remaining gap is wiring the deterministic engine into the full Golden evaluation flow.

| ADR-002 rule | R1 evidence | Golden v0 coverage | Status |
|---|---|---|---|
| §1 Deterministic Judge table | Six-state Judge unit tests | All 34 cases | implemented in R1 core; Golden integration pending |
| §2 Complete provenance | Explicit provenance completeness + Judge tests | provenance-complete, provenance-incomplete | implemented in R1 core; Golden integration pending |
| §3 Cluster independence | Deterministic dependency rules + Hypothesis property tests | independence-* cases | implemented |
| §4 Global aggregation | Deterministic precedence unit tests | multi-claim cases | implemented in R1 core; Golden integration pending |
| §5 No-answer / out-of-scope | Dedicated response contracts | n01, n02, o01, o02 | implemented in R1 core; Golden integration pending |
| §6 Injection | Documents remain data; response-secret scanner | i01-i03 and injection cases | core safety contract implemented; Golden integration pending |
| §7 Numeric tolerance and dates | Deterministic parser, 1% relative tolerance and date-granularity rules | nt01-nt03 and date conflict | implemented |
| §7.1 Closed-world Golden v0 | Existing deterministic closed-world test | all 34 cases | implemented |
| §7.2 Locale parsing | Locale-bound numeric parser with ambiguity rejection | nt01-nt03 | implemented |
| §8 Canary | Recursive exact-secret scanner | injection/canary fixtures | core scanner implemented; evaluation wiring pending |
| §9 Traceability | This matrix | all listed cases | in progress |

R1 intentionally separates deterministic decision logic from retrieval and LLM generation. The Judge never receives authority to choose a verdict from model prose.