import re
def normalize(text: str) -> str:
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text

if __name__ == "__main__":
    text = "عيدك بالمبارك يا محبوب، عساك في أنس ومسرات، حبك."
    print(normalize(text))  