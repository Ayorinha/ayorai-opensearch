# Initial Agent Swarm

The registry in `src/ayorai_attractor/agents/roles.py` declares 26 initial role entries. These entries are registry metadata, not 26 implemented or operational agents:

1. Planner
2. Researcher
3. Open Search
4. Evidence Collector
5. Reasoning
6. Critic
7. Fact Checker
8. Contradiction Hunter
9. Devil's Advocate
10. Independent Reviewer
11. Coding
12. Data Analyst
13. RAG
14. Technical Architect
15. Documentation
16. Automation
17. Security
18. AI Safety
19. Red Team
20. Compliance
21. Image
22. Video
23. Audio
24. Music
25. Local Model Specialist
26. Chief Judge

The code in `src/ayorai_attractor/agents/core.py` currently defines five concrete `Agent` subclasses: `PlannerAgent`, `ResearchAgent`, `CriticAgent`, `FactCheckerAgent` and `JudgeAgent`. They are basic implementations and this count does not establish that each role is fully integrated or independently verified. The other registry entries are extension points, not dedicated implementations. The Q2 scope boundary in [TRACEABILITY-MASTER](TRACEABILITY-MASTER.md) remains authoritative for verification status.
