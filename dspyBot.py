import dspy
import web_scraper
import text_utils

context_dict = {
    "https://book.sfacg.com/Novel/276940/MainIndex/":{
        "Huilu": "(Xiaolu, Luzai) is the main character, who became a female Demon Lord one day. She attends high school.",
        "Xiaolu": "A nickname for Huilu.",
        "Youxi": "(佑希) is Huilu's male friend, who attends the same high school as her. They later enter a relationship. He often takes care of Huilu.",
        "Huiya": "(Xiaoya) is Huilu's sister.",
        "Xiaoya": "A nickname for Huiya.",
        "Qiyi": "An online friend of Huilu. They meet during a convention.",
        "Lin Miao": "is Huilu and Huiya's male cousin.",
        "Gulu": "is a large cat.",
        "Huiyuan": "is Huilu and Huiya's father.",
        "Liu Wan": "is Huilu and Huiya's mother.",
        "Jia Qi": "is a childhood friend of Huilu and Huiya. He and Huiya later enter a relationship.",
        "Ziyu": "Huilu's roommates starting from volume 2, until Huilu moves out of the dormitory.",
        "Ji Xian": "Huilu's roommates starting from volume 2, until Huilu moves out of the dormitory.",
        "Yueli": "is Youxi's cousin. She later attends the same high school as Huilu and Youxi.",
        "Yunyue": "is a female classmate of Huilu. She has a crush on Huilu until she learns that Huilu is a girl, after which she becomes Huilu's friend. They later move to different classes but stay friends.",
        "Yunxing": "(玧瑆) is Yunyue's brother. He worries about his sister's well-being, and admires Huilu. Huilu makes him a magical girl to protect his sister.",
        "Yu Qiu": "is a mischievous classmate of Huiya. She is introduced in volume 8. She always has colorful hair. Huilu makes her a magical girl to fight witches.",
    },
    "https://book.sfacg.com/Novel/567122/MainIndex/": {
        "Xia Yi": "the main character. She was formerly the male dragon slayer Wright Schubert, but failed to slay the silver dragon queen. He was cursed by the dragons but survived, at the cost of losing her memories, and was adopted by Xia Lulu as the silver dragon princess and her daughter. She regains her former memories after unlocking her old holy sword, Gram.",
        "Xia Lulu": "the main character's adoptive mother. She is the silver dragon queen, and rules over the dragon kingdom. She appears to be forever young.",
        "Serra": "Xia Yi's maid. She is a red dragon, and she enjoys teasing Xia Yi.",
        "Lucia": "Serra's older sister and fellow maid. She is a red dragon, and is more serious than Serra. She usually attends to Xia Lulu.",
        "Elly": "A young dragon maid who works in the dragon kingdom's palace. She is an acquaintance of Xia Yi.",
        "Gran": "An old sage that works in the dragon kingdom's palace. He is one of Xia Yi's tutors. She finds his teachings to be too boring. Not to be confused with Gram, the holy sword."
    },
    "https://book.qidian.com/info/1036077914/#Catalog": {
        "Lin Yun": "The main character. He is an adult man and the father of Lin Xiaolu. He is also the magical girl Delphinium.",
        "Delphinium": "(Cui Que) The main character. A senior magical girl that mentors Lin Xiaolu, as well as the other magical girls of Fangting City. She holds a Flower certification and is registered as an Investigator of the magical kingdom. She used to be called 'Cornflower'. She is Lin Yun.",
        "Lin Xiaolu": "Lin Yun and Aya's daughter. She is a magical girl that is mentored by Delphinium. Her magical girl form is called 'White Rose'.",
        "Aya": "Lin Yun's wife and Lin Xiaolu's mother. She was a teammate of Delphinium. She died years ago under suspicious circumstances. She was once known as the strongest magical girl 'Sakura'.",
        "Xia Liang": "A classmate of Lin Xiaolu who becomes a young magical girl that is mentored by Delphinium. Her magical girl form is called 'Little Viola'.",
        "Bai Jingxuan": "An orphan girl who becomes a magical girl mentored by Delphinium. Her magical girl form is called 'Bosetsu'.",
        "Moko": "A new Seeder in Fangting City. She is a Fairy that makes magical girls. She is a bit unreliable.",
        "Asou Yuanxing": "A senior magical girl and former teammate of Delphinium. She is training her own team of magical girls in the city of Baian. Her magical girl form is named 'Marguerite'.",
        "Hong Siyu": "A retired magical girl and former teammate of Delphinium. She has a crush on Lin Yun. She works at the Countermeasures Bureau. She later returns to service as magical girl Morning Glory.",
        "magical girl levels": "Magical girls transform with a device called a 'Heart Flower'. There are 5 levels of magical girls: Seed, Sprout, Leaf, Bud, Flower. Going up a level is called 'blooming'. There are also certifications, which are gained by passing a test. There are 3 certifications: Bud, Leaf, and Flower.",
        "Heart Flower": "A gem that magical girls use to transform. It grows along with the magical girl's level.",
        "remnant levels": "Remnants are the monsters magical girls fight. They have levels: Egg, Caterpillar, Chrysalis, Molt.",
        "Countermeasures Bureau": "A government agency manages magical girls. They usually clean up after magical girls.",
        "Seeder": "A type of Fairy that makes magical girls. They are not magical girls themselves, and often take the appearance of a cat or similar animal..",
        "magical girl abilities": "Magical girls of sufficient level gain the abilities 'Domain', 'True Form', and 'Magical Armor'.",
        "True Form": "Magical girls can use their magical energy to create a body out energy.",
        "Magical Armor": "Magical girls can use their magical energy to create items unique to them. Despite the name, they are not always armor. For example, Delphinium's armor is a sewing kit of threads, a scissor, and a ruler.",
        "magical girl names": "Magical girl names are derived from the names of flowers. The exception are members of the royal court, whose names are derived from gemstones.",
        "Rules": "Magical girls of Bud level or higher and remnants of Chrysalis level or higher have 'Domains'. These are areas where all beings are subjected to rules unique to the magical girl or remnant. For example, Delphinium's Domain connects everyone inside it, allowing her to modify the traits of everyone inside it, but her modifications affect everyone equally.",
    },
    "https://novelpia.com/novel/191512": {
        "Main Character": "She became a female Jinjo (true vampire) one day after being attacked by a vampire. She no longer remembers her name, and later takes on the name 'Sutrigen' as a code name as she tries to navigate the world of the supernatural.",
        "Maximillian": "The first knight of the Round Table. He is the one to help introduce the main character to the supernatural world.",
        "Hongryeon": "A vampire hunter that encounters the main character early.",
        "Jinjo": "(Jin-jo). A true vampire. Usually used to refer to the main character, as she does not remember her name.",
        "Jin-jo": "An alternate translation of 'Jinjo'.",
    },
    "https://novelpia.com/novel/310025": {
        "Majia": "The main character, sometimes called Jia or Ji-a. He suddenly became a girl on day. She works at a VTuber group 'Parallel', moderating their streams and handling their equipment. She is also a fan of VTubers, and likes stream sniping them under the username 'Signal Flare'.",
        "Momo": "A VTuber that the main character likes. Her real name is Cheon Do-hee. She is also the president of Parallel, which makes her Majia's boss. Her fans are called 'Mongmong'.",
        "Parallel": "A VTuber agency that Majia and Momo work at.",
        "Aoyagi Rain": "A VTuber that is a member of Parallel. She studied in America before returning to Korea. She can sing and rap.Her fans are called 'puddles'.",
        "Akari Dora": "A VTuber that is a member of Parallel.",
        "Komari": "A VTuber that is a member of Parallel.",
        "Maru": "A VTuber that is a member of Parallel.",
    }
}

manual_name_translation_dict = {
    'https://book.qidian.com/info/1036077914/#Catalog': {
        "Cui Que": "Delphinium",
        "Bai Mei": "White Rose",
        "Patrol Envoy": "Inspector",
        "Yachirabana": "Cornflower",
        "Little Jin": "Little Viola",
        "Asagao": "Morning Glory",
        "Cuìquè": "Delphinium",
        "Zǔmǔlǜ": "Emerald",
    },
    "https://novelpia.com/novel/191512": {
        #"Jinjo": "true vampire",
    }
}
url_dict = {
    "although shes a demon king she likes slacking off":"https://book.sfacg.com/Novel/276940/MainIndex/",
    "slacker demon king":"https://book.sfacg.com/Novel/276940/MainIndex/",
    "is it funny that the dragon slayer failed and became the dragon princess?":"https://book.sfacg.com/Novel/567122/MainIndex/",
    "dragon slayer became dragon princess":"https://book.sfacg.com/Novel/567122/MainIndex/",
    "loner outcast vampire":"https://novelpia.com/novel/191512",
    "i became a member of my favorite group":"https://novelpia.com/novel/282408",
    "devil maiden":"https://novelpia.com/novel/1606",
    "i may be a vtuber but i still go to work":"https://novelpia.com/novel/310025",
    "our s rank hunter is open for business":"https://novelpia.com/novel/29037",
    "since i became a woman im becoming a vtuber":"https://novelpia.com/novel/194441",
    "becoming a vtuber":"https://novelpia.com/novel/194441",
    "the protector of the heavenly demon cult is trying to put a skirt on me":"https://novelpia.com/novel/363192",
    "i became a spoiler fox" : "https://novelpia.com/novel/234549",
    "former hero prefers solo play":"https://novelpia.com/novel/280312",
    "became a girl" : "https://novelpia.com/novel/6259",
    "blue archive the fallen angel lives out her life in the disciplinary committee" : "https://novelpia.com/novel/363216",
    "blue archive that teacher had a halo" : "https://novelpia.com/novel/230027",
    "blue archive makoto hanuma going to trinity" : "https://novelpia.com/novel/296481",
    "blue archive release princess mika" : "https://novelpia.com/novel/212746",
    "fluffy guild master" : "https://novelpia.com/novel/350139",
    "i became a terminally ill villainess beauty" : "https://novelpia.com/novel/240632",
    "im a magical girl at the academy" : "https://novelpia.com/novel/28964",
    "the most vicious archvillain is actually a pretty girl" : "https://novelpia.com/novel/324968",
    "chaotic magical girl magical rampage" : "https://novelpia.com/novel/163302",
    "shut in loser vtuber" : "https://novelpia.com/novel/129829",
    "im not becoming a pro gamer" : "https://novelpia.com/novel/182571",
    "theres no way a temp magical girl like me could be cute right" : "https://novelpia.com/novel/893",
}
volume_dict = {
    "https://book.sfacg.com/Novel/276940/MainIndex/":4,
    "https://book.sfacg.com/Novel/567122/MainIndex/":1,
}

name_dict = {
    "https://book.sfacg.com/Novel/276940/MainIndex/": "Although Shes a Demon King She Likes Slacking Off",
    "https://book.sfacg.com/Novel/567122/MainIndex/": "Is It Funny That the Dragon Slayer Failed and Became the Dragon Princess",
    'https://book.qidian.com/info/1036077914/#Catalog': "Off Work Then I Become a Magical Girl",
    "https://novelpia.com/novel/191512": "Loner Outcast Vampire",
    "https://novelpia.com/novel/282408": "I Became a Member of My Favorite Group",
    "https://novelpia.com/novel/1606": "Devil Maiden",
    "https://novelpia.com/novel/310025": "I May Be a VTuber but I Still Go to Work",
    "https://novelpia.com/novel/29037": "Our S Rank Hunter Is Open for Business",
    "https://novelpia.com/novel/194441": "Since I Became a Woman Im Becoming a VTuber",
    "https://novelpia.com/novel/363192": "The Protector of the Heavenly Demon Cult is Trying to Put a Skirt On Me",
    "https://novelpia.com/novel/234549": "I Became a Spoiler Fox",
    "https://novelpia.com/novel/280312": "Former Hero Prefers Solo Play",
    "https://novelpia.com/novel/6259": "I Became a Girl",
    "https://novelpia.com/novel/363216": "Blue Archive - The Fallen Angel Lives Out Her Life in the Disciplinary Committee",
    "https://novelpia.com/novel/230027": "Blue Archive - That Teacher Had a Halo",
    "https://novelpia.com/novel/296481": "Blue Archive - Makoto Hanuma Going to Trinity",
    "https://novelpia.com/novel/212746": "Blue Archive - Release Princess Mika",
    "https://novelpia.com/novel/350139": "Fluffy Guild Master",
    "https://novelpia.com/novel/240632": "I Became a Terminally Ill Villainess Beauty",
    "https://novelpia.com/novel/28964": "Im a Magical Girl at the Academy",
    "https://novelpia.com/novel/324968": "The Most Vicious Archvillain Is Actually a Pretty Girl",
    "https://novelpia.com/novel/163302": "Chaotic Magical Girl Magical Rampage",
    "https://novelpia.com/novel/129829": "Shut In Loser VTuber",
    "https://novelpia.com/novel/182571": "Im Not Becoming a Pro Gamer",
    "https://novelpia.com/novel/893": "Theres No Way a Temp Magical Girl Like Me Could Be Cute Right",
}

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