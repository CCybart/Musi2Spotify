import mysql.connector
from mysql.connector import Error
import json

def connect_to_db():
    with open("secrets.env","r") as f:
        secrets=json.loads(f.read())
    connection=None
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd=secrets["SQL_PW"],
            database="musi2spotify"
        )
        print("Connected to link registry")
    except Error as e:
        print(f"{e}")
    return connection
    
def execute(connection, query):
    try:
        connection.cursor().execute(query)
        connection.commit()
    except Error as err:
        print(f"Execute error: '{err}'")

def read(connection, query):
    res=None
    cursor=connection.cursor()
    try:
        cursor.execute(query)
        res=cursor.fetchall()
    except Error as err:
        print(f"Read error: '{err}'")
    return res

def match_song_registry(connection, musi):
    query=f'SELECT * FROM link_registry WHERE url="{musi["url"]}"'
    res=None
    if connection is not None:
        res=read(connection,query)
    return res

def add_song_to_registry(connection, musi,sp_uri):
    query=f'INSERT INTO link_registry VALUES ("{musi["url"]}",0,"{sp_uri}");'
    if connection is not None:
        execute(connection,query)
    else:
        print(f"Failed to add song {sp["name"]}")