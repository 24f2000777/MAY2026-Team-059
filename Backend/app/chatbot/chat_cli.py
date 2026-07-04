import uuid

from conversation_graph import safe_send_message, BOT_NAME

if __name__ == "__main__":
    thread_id = str(uuid.uuid4())

    print(f"chatting with {BOT_NAME}. type exit or quit to stop.\n")

    while True:
        message = input("you: ").strip()
        if message.lower() in ("exit", "quit"):
            print("bye!")
            break
        if not message:
            continue

        reply = safe_send_message(message, thread_id)
        print(f"{BOT_NAME}: {reply}\n")
