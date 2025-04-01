import nltk
from nltk import word_tokenize, pos_tag, ne_chunk

# Download necessary NLTK resources
nltk.download('punkt')
nltk.download('maxent_ne_chunker')
nltk.download('words')
nltk.download('averaged_perceptron_tagger')

def redact_names(text):
    # Tokenize the text into words
    words = word_tokenize(text)

    # Apply POS tagging to the tokens
    pos_tags = pos_tag(words)

    # Perform Named Entity Recognition (NER)
    named_entities = ne_chunk(pos_tags)

    # Redact names (PERSON entities)
    redacted_text = []
    for chunk in named_entities:
        if hasattr(chunk, 'label') and chunk.label() == 'PERSON':
            redacted_text.append("[REDACTED]")
        else:
            redacted_text.append(" ".join(c[0] for c in chunk) if isinstance(chunk, nltk.Tree) else chunk[0])
    return ' '.join(redacted_text)

#Sample text
with open("./redacted_data.txt") as file:
    text = file.read()

# Redact names
redacted_text = redact_names(text)
print(redacted_text)

