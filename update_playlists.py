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

    canciones = programacion_mensual.get(hoy, [])
    print(f"Canciones encontradas para hoy: {len(canciones)}")
    return canciones

def extraer_spotify_uri(sp, entrada):
    if "open.spotify.com/track/" in entrada:
        match = re.search(r'track/([a-zA-Z0-9]+)', entrada)
        if match:
            return f"spotify:track:{match.group(1)}"
    
    res = sp.search(q=entrada, type='track', limit=1)
    items = res.get('tracks', {}).get('items', [])
    if items:
        return items[0]['uri']
    return None

def extraer_youtube_id(youtube, entrada):
    if "youtube.com/watch" in entrada or "youtu.be/" in entrada:
        match = re.search(r'(?:v=|\/)([a-zA-Z0-9_-]{11})', entrada)
        if match:
            return match.group(1)
            
    search_req = youtube.search().list(q=entrada, part="id", type="video", maxResults=1)
    search_res = search_req.execute()
    videos = search_res.get("items", [])
    if videos:
        return videos[0]["id"]["videoId"]
    return None

def actualizar_spotify(canciones):
    print("\n--- Actualizando Spotify ---")
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    refresh_token = os.environ.get("SPOTIFY_REFRESH_TOKEN")
    playlist_id = os.environ.get("SPOTIFY_PLAYLIST_ID")

    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="playlist-modify-public playlist-modify-private"
    )
    
    # Obtener un access token válido usando el refresh_token de GitHub Secrets
    token_info = sp_oauth.refresh_access_token(refresh_token)
    sp = spotipy.Spotify(auth=token_info['access_token'])

    track_uris = []
    for item in canciones:
        uri = extraer_spotify_uri(sp, item)
        if uri:
            track_uris.append(uri)
            print(f"[Spotify] Procesado: {item}")
        else:
            print(f"[Spotify] No encontrado: {item}")

    if track_uris:
        sp.playlist_replace_items(playlist_id, track_uris)
        print("Spotify playlist actualizada exitosamente.")

def actualizar_youtube(canciones):
    print("\n--- Actualizando YouTube ---")
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    playlist_id = os.environ.get("YOUTUBE_PLAYLIST_ID")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token"
    )
    youtube = build('youtube', 'v3', credentials=creds)

    # Vaciar Playlist
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
