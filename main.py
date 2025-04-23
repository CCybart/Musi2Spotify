import sys
from requests_html import HTMLSession
import json
from urllib import parse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re

with open("secrets.env","r") as f:
    secrets=json.loads(f.read())
spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=secrets["APP_CLIENT_ID"],
    client_secret=secrets["APP_CLIENT_SECRET"],
    redirect_uri=secrets["APP_REDIRECT_URI"],
    scope="user-library-read"),
    requests_timeout=10,
    retries=5
)
session=HTMLSession()

def scrape_playlist(link):
    songs=[]
    r=session.get(link)
    r.html.render(sleep=5)
    r=r.html.html
    r=r[r.find("video_title")+1:]
    while r.find("video_title")!=-1:
        r=r[r.find("video_title")+13:]
        title=r[:r.find("<")]
        artist=r[r.find("video_artist")+14:]
        artist=artist[:artist.find("<")]
        if title[0]!=">":
            songs.append({"artist":artist,"title":title})
            #print(artist)
            #print(title)
    return songs

def clean_string(string):
    res=""
    num=0
    if len(string)==0:
        return ""
    s=re.search(r"(\(.*.\))",string)
    if s:
        string=string.replace(s.group(1),"")
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
    res=name.lower().replace("official video","").replace("official music video","").replace("official lyric video","").replace("official audio","").replace("remastered","").replace("ost","").replace("soundtrack","").replace("vevo","").replace("youtube","").replace(" hd "," ").replace(" hd","")
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

def artist_search(artist_name):
    artist_name=clean_artist(artist_name)
    artists_found=spotify.search(q=artist_name, type='artist',limit=5)['artists']['items']
    for artist in artists_found:
        if match(artist_name,clean_artist(artist['name']),max_misses=0):
            return artist
    return None

def artist_search_in_title(song_name):
    song_name=clean_song(song_name)
    search=spotify.search(q=song_name, type='artist,track',limit=5)
    artists_found=search['artists']['items']
    songs_found=search['tracks']['items']
    for artist in artists_found:
        if match(song_name,clean_artist(artist['name']),max_misses=0):
            return artist
    for song in songs_found:
        for artist in song['artists']:
            if match(song_name,artist['name'],max_misses=0):
                return artist
    return None

def song_search_artist(_song_name,artist_name):
    artist_name=clean_artist(artist_name)
    song_name=clean_song(_song_name).replace(artist_name,"").strip()
    songs_found=spotify.search(q=f"{song_name} - {artist_name}", type='track',limit=5)['tracks']['items']
    for song in songs_found:
        for artist in song['artists']:
            if match(song_name,song['name']) and match(artist_name,artist['name']):
                return song
    return None
    
def song_search(song_name):
    song_name=clean_song(song_name)
    songs_found=spotify.search(q=song_name, type='track',limit=5)['tracks']['items']
    for song in songs_found:
        for artist in song['artists']:
            if match(song_name,song['name'],1) or (match(song_name,song['name']) and match(song_name,artist['name'],max_misses=0)) or (match(song_name,song['name'],max_misses=0) and match(song_name,artist['name'],max_misses=0)):
                return song
    return None
    
#(song is close enough to match and artist in song exactly) or (song has exact match and artist has exact match) or song is 1:1 match 
    
def convert_playlist(link):
    songs=[]
    attempts=0
    while len(songs)==0 and attempts<10:
        attempts+=1
        songs=scrape_playlist(link)
    if attempts>=10 and len(titles)==0:
        print("Webscraping failed. Try again")
        return
    
    print("Playlist scraped successfully\n")
    
    songs_found=0
    artistmatch={}
    spotify_songs=[]
    not_found=[]
    for musi_song in songs:
        artist=None
        found_artist=False
        if musi_song['artist'] not in artistmatch:
            for poss_artist in artistmatch.keys():
                if artistmatch[poss_artist] is not None and artistmatch[poss_artist]['name'].lower() in musi_song['title'].lower():
                    artist=artistmatch[poss_artist]
                    found_artist=True
                    print("previously found artist "+artist['name']+" in title")
                    break
            if artist is None:
                artist=artist_search(musi_song['artist'])
                if artist is not None:
                    found_artist=True
                    artistmatch[musi_song['artist']]=artist
                    print("artist "+artist['name'])
                else:
                    artist=artist_search_in_title(musi_song['title'])
                    if artist is not None:
                        found_artist=True
                        print("artist "+artist['name']+" in title")
                    else:
                        artistmatch[musi_song['artist']]=artist
        else:
            artist=artistmatch[musi_song['artist']]
            found_artist=artist is not None
            if found_artist:
                print("previously found artist "+artist['name'])
        
        if found_artist:
            song=song_search_artist(musi_song['title'],artist['name'])
            if song is not None:
                songs_found+=1
                spotify_songs.append(song)
                print("found "+song['name']+" by "+song['artists'][0]['name'])
                continue
            #else:
            #    not_found.append(musi_song)
            #    print(musi_song['title']+" not found")
            #continue
            
        song=song_search(musi_song['title'])
        if song is not None:
            songs_found+=1
            spotify_songs.append(song)
            print("found "+song['name']+" by "+song['artists'][0]['name']+" without artist")
        else:
            not_found.append(musi_song)
            print(musi_song['title']+" not found")
    
    print("\nDone. printing results:\n")
    
    for song in spotify_songs:
        print("found "+song['name']+" by "+song['artists'][0]['name'])
    print()
    for song in not_found:
        print("didn't find "+song['title'])
    print()
    print(str(songs_found)+" songs found of "+str(len(songs))+" total")
    
if __name__=="__main__":
    if len(sys.argv)!=2:
        print("Must specify playlist link")
    elif not sys.argv[1].startswith("https://feelthemusi.com/playlist/"):
        print("Not a musi playlist link")
    else:
        convert_playlist(sys.argv[1])