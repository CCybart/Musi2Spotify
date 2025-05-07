from flask import *
from threading import Thread
from requests_html import HTMLSession
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
from match_strings import *
from sql_interface import *

app = Flask(__name__)

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
link_registry={}
prev_link_registry={}
session=HTMLSession()
session.browser

total_songs=0
scraped_songs=0
matched_songs=0
playlist_name=""
currently_loading=False
load_error="Unknown error"
not_found=[]
youtube_songs=[]
spotify_songs=[]
matches=[]

def scrape_playlist(link):
    global total_songs, scraped_songs, playlist_name, currently_loading
    songs=[]
    scraped_songs=0
    r=session.get(link)
    try:
        r.html.render(sleep=1)
    except:
        load_error="Failed to connect to HTMLSession"
        currently_loading=False
        return
    r=r.html.html
    playlist_name=r[r.find('playlist_header_title">')+23:]
    playlist_name=playlist_name[:playlist_name.find("</div>")]
    r=r[r.find("video_title")+1:]
    r=r[r.find('href="')+1:]
    r=r[r.find('href="')+1:]
    total_songs=r.count('href="')
    while r.find('href="')!=-1:
        r=r[r.find('href="')+6:]
        url=r[:r.find('"')]
        title=r[r.find("video_title")+13:]
        title=title[:title.find("</div>")]
        artist=r[r.find("video_artist")+14:]
        artist=artist[:artist.find("</div>")]
        if title[0]!=">":
            songs.append({"artist":artist,"title":title,"url":url})
            scraped_songs+=1
            #print(artist)
            #print(title)
    return songs

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
    
def add_match(musi,sp,index=0,remove=False):
    global matches
    res={
        "yt_title":truncate(musi["title"],27),
        "yt_author":truncate(musi["artist"]),
        "yt_url":musi["url"],
        "sp_title":truncate(sp["name"],27),
        "sp_artist":truncate(sp["artists"][0]["name"]),
        "sp_id":sp["id"]
    }
    for match in matches:
        if match["yt_url"]==musi["url"]:
            matches.remove(match)
            break
    if not remove:
        matches.insert(index,res)
    
def convert_playlist(link):
    global matched_songs, scraped_songs, total_songs, playlist_name, currently_loading, load_error, youtube_songs, spotify_songs, not_found, matches
    attempts=0
    
    if not link.startswith("https://feelthemusi.com/playlist/") and not link.startswith("feelthemusi.com/playlist/"):
        load_error="Not a valid musi playlist. Copy the link found in the musi app.\nExample: https://feelthemusi.com/playlist/ABCDEF"
        currently_loading=False
        return
    
    youtube_songs=[]
    
    while len(youtube_songs)==0 and attempts<20:
        attempts+=1
        youtube_songs=scrape_playlist(link)
        if not currently_loading:
            return
    if attempts>=20 and len(youtube_songs)==0:
        load_error="Webscraping failed. Please try again"
        currently_loading=False
        return
    
    print("Playlist scraped successfully. Starting search.\n")
    
    artistmatch={}
    spotify_songs=[]
    not_found=[]
    db_connection=connect_to_db()
    for musi_song in youtube_songs:
        if not currently_loading:
            load_error="Unknown error"
            return
        match=match_song_registry(db_connection,musi_song)
        if match is not None and len(match)==1:
            if match[0][2]!="":
                song=json.loads(match[0][3])
                matched_songs+=1
                add_match(musi_song,song)
                spotify_songs.append(song)
            else:
                matched_songs+=1
                res={
                    'title': truncate(musi_song['title'],27),
                    'url': musi_song['url'],
                    'artist': truncate(musi_song['artist'])
                }
                not_found.insert(0,res)
            continue
        elif match is None:
            load_error="Disconnected from link registry database. Please try again later."
            currently_loading=False
            return
        artist=None
        if musi_song['artist'] not in artistmatch:
            for poss_artist in artistmatch.keys():
                if artistmatch[poss_artist] is not None and artistmatch[poss_artist]['name'].lower() in musi_song['title'].lower():
                    artist=artistmatch[poss_artist]
                    #print("previously found artist "+artist['name']+" in title")
                    break
            if artist is None:
                artist=artist_search(musi_song['artist'])
                if artist is not None:
                    artistmatch[musi_song['artist']]=artist
                    #print("artist "+artist['name'])
                else:
                    artist=artist_search_in_title(musi_song['title'])
                    if artist is not None:
                        pass
                        #print("artist "+artist['name']+" in title")
                    else:
                        artistmatch[musi_song['artist']]=artist
        else:
            artist=artistmatch[musi_song['artist']]
            #if artist is not None:
                #print("previously found artist "+artist['name'])
        
        if artist is not None:
            song=song_search_artist(musi_song['title'],artist['name'])
            if song is not None:
                spotify_songs.append(song)
                matched_songs+=1
                add_match(musi_song,song)
                add_song_to_registry(db_connection,musi_song,song)
                #print("found "+song['name']+" by "+song['artists'][0]['name'])
                continue
            #else:
            #    not_found.append(musi_song)
            #    print(musi_song['title']+" not found")
            #continue
        
        song=song_search(musi_song['title'])
        if song is not None:
            spotify_songs.append(song)
            matched_songs+=1
            add_match(musi_song,song)
            add_song_to_registry(db_connection,musi_song,song)
            #print("found "+song['name']+" by "+song['artists'][0]['name']+" without artist")
        else:
            res={
                'title': truncate(musi_song['title'],27),
                'url': musi_song['url'],
                'artist': truncate(musi_song['artist'])
            }
            not_found.insert(0,res)
            matched_songs+=1
            add_song_to_registry(db_connection,musi_song,{})
            #print(musi_song['title']+" not found")
    
    print("\nDone. printing results:\n")
    
    #for song in spotify_songs:
    #    print("found "+song['name']+" by "+song['artists'][0]['name'])
    #print()
    #for song in not_found:
    #    print("didn't find "+song['title'])
    #print()
    print(str(len(spotify_songs))+" songs found of "+str(len(youtube_songs))+" total")
    
    currently_loading=False
    
@app.route('/')
def homepage():
    global currently_loading
    currently_loading=False
    print("loaded homepage")
    return render_template("index.html")
    
@app.route("/error",methods=["GET","POST"])
def error():
    global load_error
    return render_template("error.html", ERROR=load_error)
    
@app.route('/link', methods = ["GET","POST"])
def link():
    global currently_loading, matched_songs, scraped_songs, total_songs, playlist_name, matches, not_found
    if request.method == 'POST':
        currently_loading=True
        matched_songs=0
        scraped_songs=0
        total_songs=0
        playlist_name=""
        matches=[]
        not_found=[]
        t=Thread(target=convert_playlist,args=(request.form["link"],))
        t.start()
        return redirect("/load_playlist", code=307)
    return redirect("/")
    
@app.route('/load_playlist', methods = ["GET","POST"])
def load_playlist():
    if request.method == "POST":
        return render_template("playlist.html")
    return redirect("/")

@app.route("/get_live_info",methods=["GET","POST"])
def get_live_info():
    global total_songs, scraped_songs, matched_songs, playlist_name, currently_loading, matches, not_found
    if request.method == 'GET':
        return {"name":playlist_name,"songs":total_songs,"matched":matched_songs,"scraped":scraped_songs,"loading":currently_loading,"matches":matches,"not_found":not_found}
    return redirect("/")

@app.route("/get_song",methods=["GET","POST"])
def get_song():
    global youtube_songs, spotify_songs
    if request.method=="POST":
        body=json.loads(request.data)
        url=body["url"]
        res={"yt_title":"Not found"}
        for song in youtube_songs:
            if song["url"]==url:
                res["yt_title"]=song["title"]
                break
        return res
    return redirect("/")

@app.route("/update_match",methods=["GET","POST"])
def update_match():
    global youtube_songs, spotify_songs, matches
    if request.method=="POST":
        body=json.loads(request.data)
        yt_url=body["yt_url"]
        sp_url=body["sp_url"]
        remove=body["remove"]
        if not remove:
            for match in matches:
                if match["yt_url"]==yt_url:
                    if match["sp_id"]==sp_url.replace("open.spotify.com/track/","").replace("https://","").replace("http://",""):
                        return {"message":"Link specified is already matched to the same song"}
                    break
        yt_song={}
        sp_song={}
        index=-1
        for i in range(0,len(youtube_songs)):
            song=youtube_songs[i]
            if song["url"]==yt_url:
                yt_song=song
                index=i
                break
        if i==-1:
            return {"message":"Video not found in original playlist. Try again."}
        try:
            sp_song=spotify.track(sp_url)
        except:
            return {"message":"Error searching for Spotify track.\nAre you sure this link is valid?"}
        try:
            if not remove:
                add_song_to_registry(connect_to_db(),yt_song,sp_song,1)
            else:
                add_song_to_registry(connect_to_db(),yt_song,{},1)
        except:
            return {"message":"Error adding match to registry. Please try again."}
        nf_song={
            'title': truncate(yt_song['title'],27),
            'url': yt_song['url'],
            'artist': truncate(yt_song['artist'])
        }
        if not remove:
            if nf_song in not_found:
                not_found.remove(nf_song)
            spotify_songs.insert(index,sp_song)
            add_match(yt_song,sp_song,len(youtube_songs)-index-1)
        else:
            not_found.insert(0,nf_song)
            for song in spotify_songs:
                if song["id"]==sp_url.replace("open.spotify.com/track/","").replace("https://","").replace("http://",""):
                    spotify_songs.remove(song)
                    break
            add_match(yt_song,sp_song,len(youtube_songs)-index-1,True)
        
        print(len(spotify_songs))
        print(len(not_found))
        print(len(matches))
        
        return {"message":"Success"}
    return redirect("/")

if __name__=="__main__":
    app.run(debug=True, host="0.0.0.0")