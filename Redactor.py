# Yet to ad the dictionary upgrade

import nltk
from nltk import word_tokenize, pos_tag, ne_chunk

class Redactor:
        
    def redact_names(text) -> list:
        # Tokenize the text into words
        words = word_tokenize(text)

        # Apply POS tagging to the tokens
        pos_tags = pos_tag(words)

        # Perform Named Entity Recognition (NER)
        named_entities = ne_chunk(pos_tags)

        # print (named_entities)

        # Redact names (PERSON entities)
        redacted_text = []
        for chunk in named_entities:
            if hasattr(chunk, 'label') and chunk.label() == 'PERSON':
                # print ("Label: ", chunk)
                redacted_text.append(" ".join(c[0] for c in chunk))

        with open('common_words.txt') as file:
            common_words = list(file.readlines())

        redacted_words = []
        for phrases in redacted_text:
            redacted_words+=phrases.split(" ")
        redacted_words = set(redacted_words)

        result = []

        for word in redacted_words:
            if (word.lower() not in common_words):
                result.append(word)
        
        return (result)

