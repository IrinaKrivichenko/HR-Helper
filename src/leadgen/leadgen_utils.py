replacement_dict = {"—": "-"}


def replace_text_with_dict(text):
    for old, new in replacement_dict.items():
        text = text.replace(old, new)
    return text
