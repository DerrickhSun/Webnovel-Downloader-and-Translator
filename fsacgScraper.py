import dspy
import web_scraper
import requests
from dspyBot import Translator, NameCorrector, context_dict, url_dict, volume_dict, name_dict
from PIL import Image
import os
from text_utils import normalize_text, replace_with_dictionary
from dotenv import load_dotenv
import text_utils

load_dotenv()

lm = dspy.LM('openai/gpt-4o-mini')
dspy.configure(lm=lm, max_tokens=10000)


url = str(input("Novel name/url: "))
context = []
if (normalize_text(url) in url_dict.keys()):
    url = url_dict[normalize_text(url)]

if (url in context_dict.keys()):
    print("Found saved context for this novel")
    context = context_dict[url]
else:
    print("No saved context found for this novel")

last_chapter_summary = ""
trust_ocr = True

l2_index = 0
if (url in volume_dict.keys()):
    l2_index = volume_dict[url]

name = "unrecognized"
if url in name_dict.keys():
    name = name_dict[url]

text_utils.ensure_directory_exists(name)
text_utils.ensure_directory_exists(name+"/translated")
text_utils.ensure_directory_exists(name+"/untranslated")
    
rag = Translator(context)
name_corrector = NameCorrector(context)


#print(characters_dict[url])

def scrape_fsacg_vip_chapter(url):
    global last_chapter_summary, name
    try:
        web_scraper.download_image(img_url, "temp/vipImage"+str(count)+".png", debug=False)
        answer = web_scraper.analyze_image("temp/vipImage"+str(count)+".png", 
            brightness = brightness_factor,
            contrast = contrast_factor,
            split = True,
            prompt="Please extract the exact Chinese text from this image using OCR (optical character recognition). Extract the text and include nothing else.",
            debug = False)
        with open(name+"/untranslated/v"+str(vol)+"c"+str(chap)+"("+str(count)+")_untranslated.txt", "w", encoding="utf-8") as text_file:
            text_file.write(answer)
        
        print("Translating")
        with dspy.context(lm = dspy.LM('openai/gpt-4o-mini')):
            answer = rag(answer, last_chapter_summary)
        chapter = answer.translation
        text_utils.clear_directory_contents("temp")
        

        if (trust_ocr == False):
            with open(name+"/translated/v"+str(vol)+"c"+str(chap)+"("+str(count)+")_raw.txt", "w", encoding="utf-8") as text_file:
                text_file.write(chapter)

            print("Correcting names")
            with dspy.context(lm=dspy.LM('openai/o3-mini', temperature=1.0, max_tokens=20000)):
                answer2 = name_corrector(answer.translation, last_chapter_summary)
                #print(answer2.reasoning)
            chapter = answer2.corrected_chapter #replace_with_dictionary(answer.translation, answer2.unmatched_names)
        
        #generate summary
        with dspy.context(lm=dspy.LM('openai/gpt-4o-mini')):
            last_chapter_summary = dspy.Predict('chapter -> summary')(chapter = chapter).summary

        with open(name+"/translated/v"+str(vol)+"c"+str(chap)+"("+str(count)+")_"+web_scraper.sanitize_filename(answer.title)+".txt", "w", encoding="utf-8") as text_file:
        #with open("translated/v"+str(vol)+"c"+str(chap)+"("+str(count)+")_"+web_scraper.sanitize_filename(answer.title)+".txt", "w", encoding="utf-8") as text_file:
            text_file.write(chapter)
            return 1
    except Exception as e:
        print("Exception:",e)
        return 0



# Set up the cookies from the image
cookies = {
    '276940uvCookieC': '0',  # From the first cookie
    '.SFCommunity': 'CF0790D1A0E46BB23218FDDEF2BEC3200BE02995C9FD106E185D17E4680A931C9A6891AEF921F0ED2AA6AA80593701D652A4419666416FD88B5158CB894FA6BEA0E529896FF0F68CA3B47E50D4127AA5DB66E28D1F972B3F2DC9DD553294BCAA',  # From the second cookie
    'session_PC': '2199FBC38AC5AFFF05A8832AF180469F',  # From the third cookie
    'ttstk': 'gyZtFJNFg6fMDYqtKR7HikgD7J6lrw2wp5yWmjcMlWFL3SKMjmmilxGL3rXN_l4KMWNK1xWajihbU7HmlNlghKiaxPxms1oYh7mRZ_jlqRyZzm1lZfiur-nZHjTscI0IRxnxCO2VFSwZ0m1HKn_l2RPac8o8lm6dAxD-cxg_G2iITxkX1xt1p9hE3C9sljGBOxDDGmibGJ6K3XGjcVNbdfuvWjJsMnUuhftcvOQ9yUEKBVhYSb--FoxoAbsq13tfnA39yRGpcnZUkPd2kf_yKjoi_8MTgg-ZfqUbjDZ1Oii7zWExP0QcQ0eL-z0TJ1txtl4Lvcq1gUy3pfg-xybFsqmT6zlr5w5UN4eurcr593GY55PqzofybfwbUuzo2GdrByw-vgu_quHVdQc-nFBLcE8q5vlKtMRn5MkybvhlKJY2u2DemFEcQETXa3DKZ9m6uEunH'  # From the fourth cookie
}

# Use the set_login_cookies function we added earlier
web_scraper.session_manager.clear_cookies()
web_scraper.session_manager.set_cookies(cookies)

lis = web_scraper.fetch_lists_from_url(url, list_class="clearfix", parent_div_class="catalog-list", debug=False)

vol = 1
chap = 1
count = 1
lis2 = lis[l2_index:]
start_vol = int(input("Volume to start at:"))
start_chap = int(input("Chapter to start at:"))
end_vol = int(input("Volume to end at:"))
end_chap = int(input("Chapter to end at:"))

brightness_factor = 1.1
contrast_factor = 2

while(vol <= len(lis2)):
    chap = 1
    
    
    while(chap <= len(lis2[vol - 1])):
        if (vol < start_vol or (vol == start_vol and chap < start_chap)) :
            chap += 1
            count += 1
            continue
        if (vol > end_vol or (vol == end_vol and chap > end_chap)):
            vol = 999999
            break

        target_url = lis2[vol - 1][chap - 1]['href']
        print("translating volume", vol, "chapter", chap,"(", count, ")")
        img_url = web_scraper.fetch_image_url(target_url, img_id="vipImage", debug=False)

        if (img_url == None):
            print("Public chapter")
            script = web_scraper.fetch_div_content(target_url, "ChapterBody", debug=False)
            print(script)
            answer = rag(script)
            
            with open(name+"/translated/v"+str(vol)+"c"+str(chap)+"("+str(count)+")_"+web_scraper.sanitize_filename(answer.title)+".txt", "w", encoding="utf-8") as text_file:
                text_file.write(answer.translation)
        else:
            print("VIP chapter")
            success = False
            for i in range(4):
                result = scrape_fsacg_vip_chapter(img_url)
                if (result == 1):
                    success = True
                    break
                else:
                    print("Failure", i + 1)
            if (success == False):
                print("Failed to scrape chapter", vol, chap, "("+str(count)+")")
                quit()
                    
        chap += 1
        count += 1
        cost = sum([x['cost'] for x in lm.history if x['cost'] is not None])  # in USD, as calculated by LiteLLM for certain providers
        print(cost)
    vol += 1

cost = sum([x['cost'] for x in lm.history if x['cost'] is not None])  # in USD, as calculated by LiteLLM for certain providers
print(cost)