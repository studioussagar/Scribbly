import sys
path = r"d:\Project2.0\Django Blog & Translator\static\css\style1.css"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

marker = "        box-shadow: none !important;\n    }\n}"
index = text.find(marker)
if index != -1:
    end_index = index + len(marker)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text[:end_index] + "\n")
