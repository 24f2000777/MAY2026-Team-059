from langchain_core.messages import HumanMessage
from conversation_graph import conversation_graph

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "test-conversation-1"}}

    print("--- turn 1: filing a complaint ---")
    result = conversation_graph.invoke(
        {"messages": [HumanMessage(content="hey there is a huge pothole near my house in sector 5 dharavi, a scooter fell in it yesterday")]},
        config=config,
    )
    print(result["messages"][-1].content)
    print("\nintent detected:", result["intent"])

    print("\n--- turn 2: asking a question ---")
    result = conversation_graph.invoke(
        {"messages": [HumanMessage(content="what is the helpline number if my complaint is not resolved")]},
        config=config,
    )
    print(result["messages"][-1].content)
    print("\nintent detected:", result["intent"])

    print("\n--- total messages in memory for this thread ---")
    print(len(result["messages"]))
