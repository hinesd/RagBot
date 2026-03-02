import time

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    status: str
    step: int


def step_one(state: State):
    print(">>> STEP ONE EXECUTING", flush=True)
    return {
        "messages": [AIMessage(content="Step 1 complete")],
        "status": "analyzed",
        "step": 1
    }


def step_two(state: State):
    print(">>> STEP TWO EXECUTING", flush=True)
    time.sleep(5)  # Simulate some processing delay

    return {
        "messages": [AIMessage(content="Step 2 complete")],
        "status": "processed", 
        "step": 2
    }


def step_three(state: State):
    print(">>> STEP THREE EXECUTING", flush=True)
    return {
        "messages": [AIMessage(content="Step 3 complete")],
        "status": "finished",
        "step": 3
    }


graph = (
    StateGraph(State)
    .add_node("step_one", step_one)
    .add_node("step_two", step_two)
    .add_node("step_three", step_three)
    .add_edge(START, "step_one")
    .add_edge("step_one", "step_two")
    .add_edge("step_two", "step_three")
    .add_edge("step_three", END)
    .compile()
)