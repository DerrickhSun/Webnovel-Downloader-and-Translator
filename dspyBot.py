import dspy
import text_utils
import web_scraper
import dict_utils
from dotenv import load_dotenv

load_dotenv()

class Translator(dspy.Module):
    def __init__(self, context=[]):
        self.respond = dspy.ChainOfThought('prompt, context, previous_chapter, glossary,script -> title, translation')
        self.history = []
        self.context = context

    def forward(self, question, last_chapter = "", glossary = {}):
        answer = self.respond(prompt = """Please help me translate this chapter of a story to English using the given context and the previous chapter summary.
        As you translate, please use the glossary to help translate any terms and names.
        Please keep in mind that you have limited output tokens. There should be enough to translate the chapter, but in cases such as slang like 'wowwwwwwwwwwwwwwwwwwww' you should limit it to a reasonable length.""",
            context = self.context, 
            previous_chapter = "Previous chapter: " + last_chapter, 
            glossary = glossary,
            script = question)
        return answer

#experimental
#use to retrieve the new context from the chapter
#class Updater(dspy.Module):
#    def __init__(self):
#        self.chapter_scanner = dspy.ChainOfThought('prompt, character_info: ')

class ChapterCleaner(dspy.Module):
    def __init__(self, character_info={}):
        self.scanner = dspy.ChainOfThought('prompt, character_info: dict[str, str], previous_chapter, chapter -> cleaned_chapter: str')
        
        self.context = character_info
    
    def forward(self, question, last_chapter = ""):
        answer = self.scanner(prompt="""I have translated a chapter of a story, but some of the character names and pronouns are incorrect.
                Using the context, previous chapter summary, and the chapter text, please correct the names and pronouns.
                Please only change the names if they are clearly wrong.
                Please only change the pronouns if they are clearly wrong.
                """,
            character_info=self.context, previous_chapter = "Previous chapter: " + last_chapter, chapter = question)
        return answer

#experimental
#use this when we do not trust the OCR to get the names right
#still in-progress
class NameCorrector(dspy.Module):
    def __init__(self, character_info={}):
        self.scanner = dspy.ChainOfThought('prompt, character_info: dict[str, str], previous_chapter, chapter -> unmatched_names: list[str]')
        #self.scanner2 = dspy.ChainOfThought('prompt, character_info: list[str], previous_chapter, unmatched_names: list[str], chapter -> new_characters: dict[str, str]')
        self.scanner2 = dspy.ChainOfThought('prompt, character_info: dict[str, str], previous_chapter, unmatched_names: list[str], chapter -> match_info: dict[str, str], score: dict[str, int]')
        self.identifier = dspy.ChainOfThought('prompt, character_info: dict[str, str], previous_chapter, chapter -> corrected_chapter: str')
        self.history = []
        self.context = character_info

    def forward(self, question, last_chapter = ""):
        answer = self.scanner(prompt="""I have translated a chapter of a story, but some of the character names are incorrect.
                Please identify all the names that do not match anyone in character info. Exclude non-proper names such as 'deer' or 'sapling'.""",
            character_info=self.context, previous_chapter = "Previous chapter: " + last_chapter, chapter = question)
        print(answer.unmatched_names)

        answer2 = self.scanner2(prompt="""I have translated a chapter of a story, but some of the character names are incorrect.
                Given several unmatched character names, for each unmatched name, identify the character from character info and previous chapter summary that it most likely refers to.
                Also for each unmatched name, return a numerical score of 0 to 10 for how closely they match that existing character.
                Use only contextual information; do not use phonetic similarity.
                Multiple unmatched names may refer to the same character.""",
            character_info=self.context, 
            previous_chapter = "Previous chapter: " + last_chapter, 
            unmatched_names = answer.unmatched_names, 
            chapter = question)
        print(answer2.reasoning)
        print(answer2.match_info)
        print(answer2.score)
        #8 or less is unclear
        #5 or less is likely a new character
        #handling needs to be added

        chapter2 = text_utils.replace_multiple_strings(question, answer.unmatched_names, "[unknown name][?]")
        
        answer = self.identifier(prompt="""I have translated a chapter of a story, but some of the character names were incorrect.
                For each instance of '[unknown name]', please replace it with the name of the character that is most likely to be the correct one using the character info and the previous chapter summary.
                Leave any instances of '[?]' in the text unchanged.""",
            character_info=self.context, previous_chapter = "Previous chapter: " + last_chapter, chapter = chapter2)
        return answer

#chapter_cleaner = ChapterCleaner(context_dict["https://novelpia.com/novel/191512"])


if __name__ == "__main__":
    lm = dspy.LM('openai/gpt-4o-mini')
    dspy.configure(lm=lm)

    url = str(input("Novel name/url: "))
    context = []
    
    # Load dictionaries using dict_utils
    url_dict = dict_utils.load_dict('url_dict')
    context_dict = dict_utils.load_dict('context_dict')
    volume_dict = dict_utils.load_dict('volume_dict')
    
    if (normalize_text(url) in url_dict.keys()):
        url = url_dict[normalize_text(url)]

    if (url in context_dict.keys()):
        print("Found saved context for this novel")
        context = context_dict[url]
    else:
        print("No saved context found for this novel")
        

    l2_index = 0
    if (url in volume_dict.keys()):
        l2_index = volume_dict[url]
        
    rag = Translator(context)

    #rag = Translator(context_dict)

    #url = "https://m.c336.icu/index/101688/"



    while True:
        question = str(input("Chapter:"))
        print("Chapter:"+question)
        if question == "exit":
            break
        script = web_scraper.fetch_div_content(url+question+".html", "chaptercontent", debug=False)
        script2 = web_scraper.fetch_div_content(url+question+"_2.html", "chaptercontent", debug=False)
        answer = rag(script + "\n" + script2)
        print(answer.reasoning)

        
        
        with open("Chapters/"+question+"_"+web_scraper.sanitize_filename(answer.title)+".txt", "w", encoding="utf-8") as text_file:
            text_file.write(answer.translation)
        #print('Response:', answer+"\n"+answer2)
    cost = sum([x['cost'] for x in lm.history if x['cost'] is not None])  # in USD, as calculated by LiteLLM for certain providers
    print(cost)