from extractor import extract_complaint_info

if __name__ == "__main__":
    query = "hey i live in sector 5 dharavi and there is a huge pothole in front of my house, a scooter fell in it yesterday, please fix it fast"

    result = extract_complaint_info(query)

    print("location:", result["location"])
    print("complaint_category:", result["complaint_category"])
    print("severity:", result["severity"])
