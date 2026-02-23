import re


def extract_claim(text: str):

    if not text:
        return ""

    # remove urls
    text = re.sub(r"http\S+", "", text)

    # remove hashtags/mentions
    text = re.sub(r"[@#]\w+", "", text)

    # split sentences
    sentences = re.split(r'[.!?]', text)

    # choose longest meaningful sentence
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    if not sentences:
        return text

    return max(sentences, key=len)