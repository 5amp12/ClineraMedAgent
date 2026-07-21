#Assembles the visit-processing pipeline as a LangGraph StateGraph.
#
#Subgraph built here (fetch_board / governance_check upstream + store_and_gate downstream are
#added in later tasks):
#
#   summarize -> agent_reason --(fetch)--> clinera_get --+
#                     ^                                   |
#                     +-----------------------------------+   (loop, capped by MAX_FETCHES)
#                     |
#                     +--(proceed)--> draft_recommendations -> END

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.pipeline.agent_reason import agent_reason, route_after_reason
from app.pipeline.clinera_get import clinera_get
from app.pipeline.draft_recommendations import draft_recommendations
from app.pipeline.state import PipelineState
from app.pipeline.summarize import summarize


def build_graph():
    g = StateGraph(PipelineState)

    g.add_node("summarize", summarize)
    g.add_node("agent_reason", agent_reason)
    g.add_node("clinera_get", clinera_get)
    g.add_node("draft_recommendations", draft_recommendations)

    g.add_edge(START, "summarize")
    g.add_edge("summarize", "agent_reason")

    # agent_reason decides the branch; route_after_reason maps decision -> next node.
    g.add_conditional_edges(
        "agent_reason",
        route_after_reason,
        {
            "clinera_get": "clinera_get",
            "draft_recommendations": "draft_recommendations",
        },
    )

    g.add_edge("clinera_get", "agent_reason")  # loop back to re-reason after a fetch
    g.add_edge("draft_recommendations", END)

    return g.compile()
