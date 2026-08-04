#Assembles the visit-processing pipeline as a LangGraph StateGraph.
#
#Graph built here (input is just {"board_id": ...}; fetch_board seeds the rest):
#
#   fetch_board -> governance_check --(fail)--> halt -> END
#         |
#      (pass)
#         v
#   summarize -> agent_reason -> draft_recommendations -> store_and_gate -> assemble_report -> END
#
#The path after summarize is linear. It used to branch into a clinera_get fetch loop, but Clinera
#has no FHIR endpoint to fetch from — the whole clinical record arrives in fetch_board's single
#board-context call, so the loop only ever recycled canned data.

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.pipeline.agent_reason import agent_reason
from app.pipeline.assemble_report import assemble_report
from app.pipeline.draft_recommendations import draft_recommendations
from app.pipeline.fetch_board import fetch_board
from app.pipeline.governance_check import governance_check, route_after_governance
from app.pipeline.halt import halt
from app.pipeline.state import PipelineState
from app.pipeline.store_and_gate import store_and_gate
from app.pipeline.summarize import summarize


def build_graph():
    g = StateGraph(PipelineState)

    g.add_node("fetch_board", fetch_board)
    g.add_node("governance_check", governance_check)
    g.add_node("halt", halt)
    g.add_node("summarize", summarize)
    g.add_node("agent_reason", agent_reason)
    g.add_node("draft_recommendations", draft_recommendations)
    g.add_node("store_and_gate", store_and_gate)
    g.add_node("assemble_report", assemble_report)

    g.add_edge(START, "fetch_board")
    g.add_edge("fetch_board", "governance_check")

    # governance_check decides whether we may process this board at all.
    g.add_conditional_edges(
        "governance_check",
        route_after_governance,
        {"summarize": "summarize", "halt": "halt"},
    )
    g.add_edge("halt", END)

    g.add_edge("summarize", "agent_reason")
    g.add_edge("agent_reason", "draft_recommendations")
    g.add_edge("draft_recommendations", "store_and_gate")
    g.add_edge("store_and_gate", "assemble_report")
    g.add_edge("assemble_report", END)

    return g.compile()
