import text_utils
import dspy
import web_scraper
from dspyBot import Translator, context_dict, url_dict, ChapterCleaner
from pathlib import Path

def chapter_comparator(path):
    p = str(path)
    index = p.index("_")
    index2 = p.index(".")
    p = str(path)[index + 1:index2]

    return int(p)

chapters = text_utils.split_by_chapter_markers("slackerdemonking.txt", "txttemp")

lm = dspy.LM('openai/gpt-4o')
dspy.configure(lm=lm)


url = str(input("Novel name/url: "))
context = []
if (text_utils.normalize_text(url) in url_dict.keys()):
    url = url_dict[text_utils.normalize_text(url)]

if (url in context_dict.keys()):
    print("Found saved context for this novel")
    context = context_dict[url]
else:
    print("No saved context found for this novel")
    
cc = ChapterCleaner(context)
with open("Loner Outcast Vampire/translated/v1c10(10)_The 12 Knights of the Round Table.txt", 'r', encoding='utf-8') as infile:
    script = infile.read()
    answer = cc(script)

    with open("debug/v1c10(10)_The 12 Knights of the Round Table.txt", "w", encoding="utf-8") as out_file:
        out_file.write(answer.cleaned_chapter)
    
"""rag = Translator(context)
#rag = RAG()

dir_path = Path("txttemp")
txt_files = list(dir_path.glob("*.txt"))
txt_files.sort(key=chapter_comparator)

count = -13
for txt_file in txt_files:
    if (count < 990):
        count += 1
        continue
    with open(txt_file, 'r', encoding='utf-8') as infile:
        script = infile.read()
        answer = rag(script)
    
        with open("txtChapters/"+str(count)+"_"+web_scraper.sanitize_filename(answer.title)+".txt", "w", encoding="utf-8") as out_file:
            out_file.write(answer.translation)
        count += 1"""
cost = sum([x['cost'] for x in lm.history if x['cost'] is not None])  # in USD, as calculated by LiteLLM for certain providers
print(cost)