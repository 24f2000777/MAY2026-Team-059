from prompts import extraction_prompt
from providers import huggingface_llm, parse_huggingface_output

if __name__ == "__main__":
    query = "hey i live in sector 5 dharavi and there is a huge pothole in front of my house"

    chain = extraction_prompt | huggingface_llm
    raw_response = chain.invoke({"user_query": query})

    print("raw response from huggingface:")
    print(raw_response.content)

    result = parse_huggingface_output(raw_response)
    print("\nparsed result:")
    print(result)
