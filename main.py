import sys
from requests_html import HTMLSession
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
from match_strings import *
from sql_interface import *

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
link_registry={}
prev_link_registry={}
db_connection=connect_to_db()

def scrape_playlist(link):
    songs=[]
    r=session.get(link)
    r.html.render(sleep=1)
    r=r.html.html
    r=r[r.find("video_title")+1:]
    r=r[r.find('href="')+1:]
    r=r[r.find('href="')+1:]
    tot_songs=r.count('href="')
    while r.find('href="')!=-1:
        r=r[r.find('href="')+6:]
        url=r[:r.find('"')]
        title=r[r.find("video_title")+13:]
        title=title[:title.find("<")]
        artist=r[r.find("video_artist")+14:]
        artist=artist[:artist.find("<")]
        if title[0]!=">":
            songs.append({"artist":artist,"title":title,"url":url})
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
    
def convert_playlist(link):
    songs=[]
    attempts=0
    while len(songs)==0 and attempts<20:
        attempts+=1
        songs=scrape_playlist(link)
    if attempts>=20 and len(titles)==0:
        print("Webscraping failed. Try again")
        return
    
    print("Playlist scraped successfully. Starting search.\n")
    
    artistmatch={}
    spotify_songs=[]
    not_found=[]
    for musi_song in songs:
        match=match_song_registry(db_connection,musi_song)
        if len(match)==1:
            if match[0][2]!="":
                song=spotify.track(match[0][2])
                spotify_songs.append(song)
            else:
                not_found.append(musi_song)
            continue
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
            add_song_to_registry(db_connection,musi_song,song['uri'])
            #print("found "+song['name']+" by "+song['artists'][0]['name']+" without artist")
        else:
            not_found.append(musi_song)
            add_song_to_registry(db_connection,musi_song,"")
            #print(musi_song['title']+" not found")
    
    print("\nDone. printing results:\n")
    
    for song in spotify_songs:
        print("found "+song['name']+" by "+song['artists'][0]['name'])
    print()
    for song in not_found:
        print("didn't find "+song['title'])
    print()
    print(str(len(spotify_songs))+" songs found of "+str(len(songs))+" total")
    
    
    
if __name__=="__main__":
    if len(sys.argv)!=2:
        print("Must specify playlist link")
    elif not sys.argv[1].startswith("https://feelthemusi.com/playlist/"):
        print("Not a musi playlist link")
    else:
        convert_playlist(sys.argv[1])