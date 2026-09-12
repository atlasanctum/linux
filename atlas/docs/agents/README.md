# Atlas AI Agents

Atlas agents are autonomous reasoning units that operate within the perceive → plan → act loop.

## Agent Architecture

```
AgentRuntime
    ↓
dispatch(AgentTask)
    ↓
Agent.perceive(context) → observations
    ↓
Agent.plan(observations) → plan
    ↓
Agent.act(plan) → AgentResult
```

Every agent extends the `Agent` base class and implements three methods. The runtime dispatches tasks by agent name.

## Built-in Agents

### OpportunityScoutAgent
Scans the knowledge graph for unused resources and unmet needs. Produces a ranked list of opportunities with scores and descriptions.

### ImpactReporterAgent
Queries the impact ledger and produces a structured summary of outcomes by domain, node, and time window.

## Writing a Custom Agent

```python
from atlas.core.agents.runtime import Agent
from atlas.schemas.phase2 import AgentTask, AgentResult, AgentStatus

class MyAgent(Agent):
    name = "my_agent"

    def perceive(self, context: dict) -> dict:
        return {"observed": context.get("data", [])}

    def plan(self, observations: dict) -> dict:
        return {"action": "process", "items": observations["observed"]}

    def act(self, plan: dict) -> AgentResult:
        result = [item.upper() for item in plan["items"]]
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.SUCCESS,
            output={"processed": result},
        )
```

## Phase VI Extensions

- LLM-backed agents: natural language reasoning over knowledge graph
- Multi-agent coordination: agents that delegate to sub-agents
- Persistent agent memory: long-horizon planning across sessions
- Reinforcement learning agents: policy-optimised through simulation
