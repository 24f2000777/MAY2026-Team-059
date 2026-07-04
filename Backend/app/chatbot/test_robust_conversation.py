from conversation_graph import safe_send_message, BOT_NAME

if __name__ == "__main__":
    thread_id = "test-robust-1"

    def send(message):
        reply = safe_send_message(message, thread_id)
        print(f"you: {message}")
        print(f"{BOT_NAME}: {reply}\n")

    print("--- turn 1: chitchat ---")
    send("hi there, how are you")

    print("--- turn 2: complaint with no location ---")
    send("there is a huge pothole causing accidents, please fix it")

    print("--- turn 3: giving the location as a follow up ---")
    send("it's near sector 5 dharavi")

    print("--- turn 4: a question ---")
    send("what is the BMC helpline number")
