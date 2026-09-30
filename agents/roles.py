from dataclasses import dataclass


@dataclass(frozen=True)
class AgentRole:
    id: str
    name: str
    capability: str


INITIAL_ROLES = [
    AgentRole("planner", "Planner", "planning"),
    AgentRole("researcher", "Researcher", "research"),
    AgentRole("open_search", "Open Search", "search"),
    AgentRole("evidence_collector", "Evidence Collector", "evidence"),
    AgentRole("reasoning", "Reasoning", "reasoning"),
    AgentRole("critic", "Critic", "critique"),
    AgentRole("fact_checker", "Fact Checker", "verification"),
    AgentRole("contradiction_hunter", "Contradiction Hunter", "contradiction"),
    AgentRole("devils_advocate", "Devil's Advocate", "red_team"),
    AgentRole("independent_reviewer", "Independent Reviewer", "review"),
    AgentRole("coding", "Coding", "coding"),
    AgentRole("data_analyst", "Data Analyst", "data"),
    AgentRole("rag", "RAG", "retrieval"),
    AgentRole("technical_architect", "Technical Architect", "architecture"),
    AgentRole("documentation", "Documentation", "documentation"),
    AgentRole("automation", "Automation", "automation"),
    AgentRole("security", "Security", "security"),
    AgentRole("ai_safety", "AI Safety", "safety"),
    AgentRole("red_team", "Red Team", "red_team"),
    AgentRole("compliance", "Compliance", "compliance"),
    AgentRole("image", "Image", "image"),
    AgentRole("video", "Video", "video"),
    AgentRole("audio", "Audio", "audio"),
    AgentRole("music", "Music", "music"),
    AgentRole("local_model", "Local Model Specialist", "local_inference"),
    AgentRole("chief_judge", "Chief Judge", "synthesis"),
]
