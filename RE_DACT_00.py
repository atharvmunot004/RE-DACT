from Redactor import *
import os

curr_dir = os.getcwd()
all_files = os.listdir(curr_dir+"\\input")

files = []
print (all_files)

for file in all_files:
    if (".docx" in file or ".txt" in file or ".md" in file or ".doc" in file):
        files.append(file)

print (files)
with open(curr_dir+"\\input\\Test00.md") as file:
    text = file.read()

if ("India" in text):
    print ("Recent File")

redacted_text = Redactor.redact_names(text)
redacted_words = []
for phrases in redacted_text:
    redacted_words+=phrases.split(" ")
redacted_words = set(redacted_words)
print(redacted_words)
optext=[]

with open(files[2]) as file:
    i=0
    text=file.readline()
    text=text[:len(text)-1]
    while (text):
        opttextLine=[]

        for word in text.split(" "):
            for redacted_word in redacted_words:
                if (redacted_word in word):
                    if (word[-1]=='\n'):
                        word="[REDACTED]\n"
                    else:
                        word="[REDACTED]"
            opttextLine.append(word)
        optext.append(opttextLine)
        text=file.readline()
        i+=1
file_data=""
for lines in optext:
    for word in lines:
        file_data += word+" "
with open("output/"+files[2], "w") as file:
    file.write(file_data)