import json
import text_utils

# context_dict: {url: {character/term: description}}
# name_dict: {url: main title}
# volume_dict: {title: starting volume}, not always used
# url_dict: {title: url}
# manual_name_translation_dict: {url: {character/term: translation}}

def save_dict(dict, filename):
    with open('data/' + filename + '.json', 'w') as f:
        json.dump(dict, f, indent=4)

def load_dict(filename):
    return json.load(open('data/' + filename + '.json'))

def add_novel():
    context_dict = load_dict('context_dict')
    name_dict = load_dict('name_dict')
    volume_dict = load_dict('volume_dict')
    url_dict = load_dict('url_dict')
    manual_name_translation_dict = load_dict('manual_name_translation_dict')

    title = str(input("Novel name: "))
    title = text_utils.normalize_text(title)
    url = str(input("Novel url: "))
    if url in url_dict.keys():
        set_output = bool(input("Set this name as main name? (y/n): ").lower().strip() == 'y')
        if set_output:
            name_dict[url] = title
    else:
        print("New novel")
        name_dict[url] = title
    
    if title in url_dict.keys():
        warn = bool(input("This title already exists. Overwrite? (y/n): ").lower().strip() == 'y')
        if warn:
            url_dict[title] = url
    else:
        url_dict[title] = url

    save_dict(context_dict, 'context_dict')
    save_dict(name_dict, 'name_dict')
    save_dict(volume_dict, 'volume_dict')
    save_dict(url_dict, 'url_dict')
    save_dict(manual_name_translation_dict, 'manual_name_translation_dict')

def remove_title():
    context_dict = load_dict('context_dict')
    name_dict = load_dict('name_dict')
    volume_dict = load_dict('volume_dict')
    url_dict = load_dict('url_dict')
    manual_name_translation_dict = load_dict('manual_name_translation_dict')

    title = str(input("Title: "))
    title = text_utils.normalize_text(title)

    if title in url_dict.keys():
        del url_dict[title]
    else:
        print("Title not found")
    
    save_dict(context_dict, 'context_dict')
    save_dict(name_dict, 'name_dict')
    save_dict(volume_dict, 'volume_dict')
    save_dict(url_dict, 'url_dict')
    save_dict(manual_name_translation_dict, 'manual_name_translation_dict')

if __name__ == "__main__":
    operation = str(input("Operation: "))
    match operation:
        case "add":
            add_novel()
        case "remove":
            remove_title()
    
    
    
    

