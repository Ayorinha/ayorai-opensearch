# Integrated verification pipeline

The verification core now has an explicit deterministic composition boundary:

Claims + Evidence + Stance edges -> ADR-002 Judge -> claim/global verdict -> R6 grounding gate -> cited answer or ABSTAIN.

The Judge remains authoritative for verification. The synthesis layer cannot promote a claim: it only checks that generated claim text has known evidence identifiers and emits citations. When grounding fails, the final answer is an explicit ABSTAIN response.

This composition keeps retrieval, stance analysis, verification, and answer generation separate while making the end-to-end contract directly testable.
