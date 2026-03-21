from typing import Dict, Any
from langgraph.graph import StateGraph, END
from .state import AgentState

class SupervisorNode:
    """
    Supervisor 노드는 AgentState를 확인하여 라우팅 결정(Condition Edge)을 수행합니다.
    """
    def __init__(self):
        self.members = ["Agent-1", "Agent-2", "Agent-3"]

    def orchestrator_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Orchestrator(Supervisor) 로직을 모사.
        (이 MVP에서는 상태 체크만 하고 넘어감)
        """
        return {"messages": []}

    def route_handoff(self, state: AgentState) -> str:
        """
        Conditional Edge (라우터) 함수
        """
        handoff = state.get("current_handoff")
        if not handoff:
            return END
            
        target = handoff.to_agent
        if target == "FINISH" or target not in self.members:
            return END
        
        return target

def build_graph():
    workflow = StateGraph(AgentState)
    return workflow
