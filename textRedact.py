import spacy

# Load the spaCy English model
nlp = spacy.load("en_core_web_sm")

# Function to redact entities
def redact_text(text):
    doc = nlp(text)
    redacted_tokens = []

    for token in doc:
        # Check if token is an entity and redact it
        if token.ent_type_ in ["PERSON", "ORG", "GPE", "DATE"]:  # You can add more types
            redacted_tokens.append("[REDACTED]")
        else:
            redacted_tokens.append(token.text)
    # Join tokens back into a string
    return " ".join(redacted_tokens)

# Example usage
text = "John Doe works at OpenAI, and he was born on January 1st in San Francisco."
redacted_text = redact_text(text)
print(redacted_text)
