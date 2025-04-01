import docx
import os

for file in os.listdir("input"):
    if (".doc" in file or ".docx" in file):
        doc = docx.Document("input/" + file)
        for para in doc.paragraphs:
            print(para.text)