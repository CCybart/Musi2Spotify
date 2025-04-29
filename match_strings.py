import re

def clean_string(string):
    res=""
    num=0
    if len(string)==0:
        return ""
    s=re.sub(r"([(,[,{,【]f.*t.*.[),\],},】])","",string)
    for c in string.lower():
        if c.isnumeric() or c==" ":
            num+=1
    num=num>len(string)*.5
    start_numeric=False
    if not num:
        start_numeric=string[0].isnumeric()
    for c in string.lower():
        if (num and c.isalnum()) or (not num and (c.isalpha() or (c.isnumeric() and not start_numeric))) or c==" ":
            res+=c
            if start_numeric and not c.isnumeric():
                start_numeric=False
        if not c.isalnum() and c!=" ":
            res+=" "
    if not num:
        s=re.search(r"(\d{4})",res)
        if s:
            res=res.replace(s.group(1),"")
    return res.strip()

def clean_artist(name):
    res=name.lower().replace(" - topic","").replace("official","").replace("vevo","").replace("youtube","")
    return clean_string(res)

def clean_song(name):
    res=name.lower().replace("official video","").replace("official music video","").replace("official lyric video","").replace("lyric video","").replace("official audio","").replace("remastered","").replace("ost","").replace("soundtrack","").replace("vevo","").replace("youtube","").replace(" hd "," ").replace(" hd","")
    return clean_string(res)

def get_word_list(string):
    res=clean_string(string)
    res=res.split()
    if "the" in res:
        res.remove("the")
    if "a" in res:
        res.remove("a")
    return res

def match(string, test_match,threshold=.5,max_misses=1):
    l_string=get_word_list(string)
    l_test=get_word_list(test_match)
    if len(l_string)==0 or len(l_test)==0:
        return False
    misses=0
    for word in l_test:
        if word not in l_string:
            misses+=1
            if misses>max_misses:
                return False
    if max_misses==0:
        return True
    ratio=(len(l_test)-misses)/float(len(l_string))
    return ratio>=threshold or len(l_test)>len(l_string)