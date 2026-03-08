from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from .prompt import rule_book

llm = ChatOllama(model="phi4-mini", base_url="http://ollama:11434")


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    status: str
    step: int
    system_prompt: Optional[str]


def step_one(state: State):
    print(">>> STEP ONE EXECUTING", flush=True)
    return {
        "status": "analyzed",
        "step": 1
    }


def step_two(state: State):
    print(">>> STEP TWO EXECUTING", flush=True)

    last_message = state["messages"][-1]
    
    prompt = f"""
    You are an assistant that processes user messages. Analyze the following message and respond with a helpful answer.
    
    Message: {last_message}

    rule_book: {rule_book}    

    """    

    response = llm.invoke(prompt)

    return {
        "messages": [response],
        "status": "processed",
        "step": 2
    }


def step_three(state: State):
    print(">>> STEP THREE EXECUTING", flush=True)
    return {
        "messages": [AIMessage(content="Step 3 complete\n\n")],
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