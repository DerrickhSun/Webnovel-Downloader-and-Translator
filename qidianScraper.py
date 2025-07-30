import dspy
import web_scraper
import requests
from dspyBot import Translator, NameCorrector, context_dict, url_dict, volume_dict, name_dict, manual_name_translation_dict
from PIL import Image
import os
from text_utils import normalize_text, replace_with_dictionary
from dotenv import load_dotenv
import text_utils
import selenium_utils

load_dotenv()

qidian_confirmed_headers = {
    'Host': 'www.qidian.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://book.qidian.com/',
    'Connection': 'keep-alive',
    'Cookie': 'newstatisticUUID=1749074184_557066739; _csrfToken=7a6b5022-bb1e-479e-a64f-e44ba7ad5a5a; fu=138564886; _ga_FZMMH98S83=GS2.1.s1750827610$o20$g1$t1750829182$j60$l0$h0; _ga=GA1.2.1005620528.1749074184; _ga_PFYW0QLV3P=GS2.1.s1750827610$o20$g1$t1750829183$j60$l0$h0; Hm_lvt_f00f67093ce2f38f215010b699629083=1749074186,1749699072; e1=%7B%22pid%22%3A%22qd_P_mycenter%22%2C%22eid%22%3A%22qd_H_mall_bottomaddownload%22%2C%22l7%22%3A%22hddl%22%7D; e2=%7B%22pid%22%3A%22qd_P_mycenter%22%2C%22eid%22%3A%22qd_H_mall_bottomaddownload%22%2C%22l7%22%3A%22hddl%22%7D; _gid=GA1.2.614213141.1750571536; traffic_search_engine=; supportWebp=false; traffic_utm_referer=; se_ref=; Hm_lpvt_f00f67093ce2f38f215010b699629083=1750829183; HMACCOUNT=98ECCFD5575F572E; ywkey=ykata4KHFPdu; ywguid=120482424609; ywopenid=3E4D05BAF58C8A6FA8DFD9D72E930A88; w_tsfp=ltvuV0MF2utBvS0Q7KrhlkKpFjEgcjA4h0wpEaR0f5thQLErU5mA0Y54t8z2MHbW48xnvd7DsZoyJTLYCJI3dwNCQ5+VcoAZ2giZkYB3iogQUBhlEsjUUV9KJ7lwvjgSf3hCNxS00jA8eIUd379yilkMsyN1zap3TO14fstJ019E6KDQmI5uDW3HlFWQRzaLbjcMcuqPr6g18L5a5WrZtAipJQ8mUutG0EPA1XlOBn9y4xO7IO8LNR2kIsr5SqA=',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-site',
    'Sec-Fetch-User': '?1',
    'Priority': 'u=0, i',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache'
}

lm = dspy.LM('openai/gpt-4o-mini', max_tokens=10000, temperature=0.2)
dspy.configure(lm=lm)


url = "https://book.qidian.com/info/1036077914/#Catalog"#str(input("Novel name/url: "))
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

manual_name_translation = {}
if url in manual_name_translation_dict.keys():
    manual_name_translation = manual_name_translation_dict[url]

zero_volume = True


text_utils.ensure_directory_exists(name)
text_utils.ensure_directory_exists(name+"/translated")
text_utils.ensure_directory_exists(name+"/untranslated")
    
rag = Translator(context)
name_corrector = NameCorrector(context)

# Set up the cookies from the image
cookies = {
    'newstatisticUUID': '1749074184_557066739',
    '_csrfToken': '7a6b5022-bb1e-479e-a64f-e44ba7ad5a5a',
    'fu': '138564886',
    '_ga_FZMMH98S83': 'GS2.1.s1750827610$o20$g1$t1750829182$j60$l0$h0',
    '_ga': 'GA1.2.1005620528.1749074184',
    '_ga_PFYW0QLV3P': 'GS2.1.s1750827610$o20$g1$t1750829183$j60$l0$h0',
    'Hm_lvt_f00f67093ce2f38f215010b699629083': '1749074186,1749699072',
    'e1': '%7B%22pid%22%3A%22qd_P_mycenter%22%2C%22eid%22%3A%22qd_H_mall_bottomaddownload%22%2C%22l7%22%3A%22hddl%22%7D',
    'e2': '%7B%22pid%22%3A%22qd_P_mycenter%22%2C%22eid%22%3A%22qd_H_mall_bottomaddownload%22%2C%22l7%22%3A%22hddl%22%7D',

}

# Use the set_login_cookies function we added earlier
web_scraper.session_manager.clear_cookies()
web_scraper.session_manager.set_cookies(cookies)

#lis = web_scraper.fetch_div_content(url, div_class="volume", debug=True)
lis = web_scraper.fetch_lists_from_url(url, list_class="cf", parent_div_class="volume", debug=False)

vol = 0 if zero_volume else 1
chap = 1
start_vol = 0
start_chap = 1
end_vol = 99
end_chap = 999999
count = 1
lis2 = lis#update later

while(vol <= len(lis2)):
    chap = 1
    
    
    while(chap <= len(lis2[vol if zero_volume else vol - 1])):
        if (vol < start_vol or (vol == start_vol and chap < start_chap)) :
            chap += 1
            count += 1
            continue
        if (vol > end_vol or (vol == end_vol and chap > end_chap)):
            vol = 999999
            break

        target_url = lis2[vol if zero_volume else vol - 1][chap - 1]['href']
        print("translating volume", vol, "chapter", chap,"(", count, ")")
        index = target_url.find("www.qidian.com")
        
        # Use robust connection handling for better error recovery
        chapter_text = web_scraper.fetch_with_robust_connection('https://' + target_url[index:], 
                qidian_confirmed_headers, main_class="content", debug=False)
        
        # Use robust connection handling for title as well
        try:
            title = dspy.Predict('prompt, title -> translation')(prompt="Please translate this title.", title=web_scraper.fetch_h1_with_confirmed_headers('https://' + target_url[index:], h1_class="title", debug=False)).translation
        except Exception as e:
            print(f"Connection error fetching title: {str(e)}")
            # Fallback to original method
            title = dspy.Predict('prompt, title -> translation')(prompt="Please translate this title.", title=web_scraper.fetch_h1_with_confirmed_headers('https://' + target_url[index:], h1_class="title", debug=False)).translation
        
        if not chapter_text:
            flag = False
            print("VIP chapter, using selenium")
            for i in range(1):
                print("Attempting to fetch chapter text, attempt", i + 1)
                try:
                    chapter_text = selenium_utils.fetch_with_exact_headers('https://' + target_url[index:], 
                            qidian_confirmed_headers, main_class="content", wait_time=20, debug=False)
                    flag = True
                    break
                except:
                    print("Failed to fetch chapter text, retrying...")
            if (flag == False):
                print("Failed to fetch chapter text, quitting...")
                quit()
        else:
            print("Public chapter")
        answer = rag(chapter_text, last_chapter_summary)

        with dspy.context(lm=dspy.LM('openai/gpt-4o-mini')):
            last_chapter_summary = dspy.Predict('chapter -> summary')(chapter = answer.translation).summary

        chapter_text = replace_with_dictionary(answer.translation, manual_name_translation, confident=True)

        with open(name+"/translated/v"+str(vol)+"c"+str(chap)+"("+str(count)+")_"+web_scraper.sanitize_filename(title)+".txt", "w", encoding="utf-8") as text_file:
                text_file.write(chapter_text)
                    
        chap += 1
        count += 1
        cost = sum([x['cost'] for x in lm.history if x['cost'] is not None])  # in USD, as calculated by LiteLLM for certain providers
        print(cost)
    vol += 1

cost = sum([x['cost'] for x in lm.history if x['cost'] is not None])  # in USD, as calculated by LiteLLM for certain providers
print(cost)

