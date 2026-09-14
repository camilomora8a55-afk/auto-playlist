import os
import json
import re
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def cargar_canciones_del_dia(filepath="canciones.json"):
    if not os.path.exists(filepath):
        print(f"Error: {filepath} no existe.")
        return []
    
    hoy = datetime.now().strftime("%Y-%m-%d")
    print(f"Buscando programación para la fecha de hoy: {hoy}")

    with open(filepath, "r", encoding="utf-8") as f:
        programacion_mensual = json.load(f)

    return programacion_mensual.get(hoy, [])

def extraer_spotify_uri(sp, entrada):
    # Si es un link directo de Spotify
    if "open.spotify.com/track/" in entrada:
        match = re.search(r'track/([a-zA-Z0-9]+)', entrada)
        if match:
            return f"spotify:track:{match.group(1)}"
    
    # Si es búsqueda por texto
    res = sp.search(q=entrada, type='track', limit=1)
    items = res.get('tracks', {}).get('items', [])
    if items:
        return items[0]['uri']
    return None

def extraer_youtube_id(youtube, entrada):
    # Si es un link de YouTube
    if "youtube.com/watch" in entrada or "youtu.be/" in entrada:
        match = re.search(r'(?:v=|\/)([a-zA-Z0-9_-]{11})', entrada)
        if match:
            return match.group(1)
            
    # Si es búsqueda por texto
    search_req = youtube.search().list(q=entrada, part="id", type="video", maxResults=1)
    search_res = search_req.execute()
    videos = search_res.get("items", [])
    if videos:
        return videos[0]["id"]["videoId"]
    return None

def actualizar_spotify(canciones):
    print("\n--- Actualizando Spotify ---")
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
        client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET"),
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="playlist-modify-public playlist-modify-private"
    ))

    track_uris = []
    for item in canciones:
        uri = extraer_spotify_uri(sp, item)
        if uri:
            track_uris.append(uri)
            print(f"[Spotify] Procesado correctamente: {item}")
        else:
            print(f"[Spotify] No encontrado: {item}")

    if track_uris:
        sp.playlist_replace_items(os.environ.get("SPOTIFY_PLAYLIST_ID"), track_uris)
        print("Spotify playlist actualizada exitosamente.")

def actualizar_youtube(canciones):
    print("\n--- Actualizando YouTube ---")
    creds = Credentials(
        token=None,
        refresh_token=os.environ.get("YOUTUBE_REFRESH_TOKEN"),
        client_id=os.environ.get("YOUTUBE_CLIENT_ID"),
        client_secret=os.environ.get("YOUTUBE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token"
    )
    youtube = build('youtube', 'v3', credentials=creds)
    playlist_id = os.environ.get("YOUTUBE_PLAYLIST_ID")

    # Limpiar Playlist
    items_req = youtube.playlistItems().list(part="id", playlistId=playlist_id, maxResults=50)
    items_res = items_req.execute()
    for item in items_res.get("items", []):
        youtube.playlistItems().delete(id=item["id"]).execute()

    # Agregar nuevas canciones
    for item in canciones:
        video_id = extraer_youtube_id(youtube, item)
        if video_id:
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id}
                    }
                }
            ).execute()
            print(f"[YouTube] Añadido video ID: {video_id} ({item})")
        else:
            print(f"[YouTube] No encontrado: {item}")

if __name__ == "__main__":
    lista = cargar_canciones_del_dia()
    if lista:
        actualizar_spotify(lista)
        actualizar_youtube(lista)
    else:
        print("No hay canciones programadas para hoy.")
