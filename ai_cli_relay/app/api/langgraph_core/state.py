from pydantic import BaseModel, Field
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

class HandoffPayload(BaseModel):
    from_agent: str = Field(description="핸드오프 발신 에이전트")
    to_agent: str = Field(description="명시적인 다음 라우팅 대상 에이전트 이름 (예: Agent-1, Agent-2, Verifier, FINISH)")
    objective: str = Field(description="이관되는 핵심 목표")
    context_links: list[str] = Field(description="이 작업에 필요한 최소한의 연관 파일 경로 및 링크")
    deliverables: str = Field(description="반드시 다음 에이전트가 도출해야 할 세부 산출물 명세")
    constraints: str = Field(default="", description="기타 제약 사항들")

def add_messages(left: Sequence[BaseMessage], right: Sequence[BaseMessage]):
    return list(left) + list(right)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_handoff: HandoffPayload
