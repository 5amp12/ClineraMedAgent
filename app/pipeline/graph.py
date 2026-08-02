#Assembles the visit-processing pipeline as a LangGraph StateGraph.
#
#Subgraph built here (fetch_board upstream is added later):
#
#   governance_check --(fail)--> halt -> END
#         |
#      (pass)
#         v
#   summarize -> agent_reason --(fetch)--> clinera_get --+
#                     ^                                   |
#                     +-----------------------------------+   (loop, capped by MAX_FETCHES)
#                     |
#                     +--(proceed)--> draft_recommendations -> store_and_gate -> assemble_report -> END

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.pipeline.agent_reason import agent_reason, route_after_reason
from app.pipeline.assemble_report import assemble_report
from app.pipeline.clinera_get import clinera_get
from app.pipeline.draft_recommendations import draft_recommendations
from app.pipeline.governance_check import governance_check, route_after_governance
from app.pipeline.halt import halt
from app.pipeline.state import PipelineState
from app.pipeline.store_and_gate import store_and_gate
from app.pipeline.summarize import summarize


def build_graph():
    g = StateGraph(PipelineState)

    g.add_node("governance_check", governance_check)
    g.add_node("halt", halt)
    g.add_node("summarize", summarize)
    g.add_node("agent_reason", agent_reason)
    g.add_node("clinera_get", clinera_get)
    g.add_node("draft_recommendations", draft_recommendations)
    g.add_node("store_and_gate", store_and_gate)
    g.add_node("assemble_report", assemble_report)

    g.add_edge(START, "governance_check")

    # governance_check decides whether we may process this board at all.
    g.add_conditional_edges(
        "governance_check",
        route_after_governance,
        {"summarize": "summarize", "halt": "halt"},
    )
    g.add_edge("halt", END)

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
    g.add_edge("draft_recommendations", "store_and_gate")
    g.add_edge("store_and_gate", "assemble_report")
    g.add_edge("assemble_report", END)

    return g.compile()
