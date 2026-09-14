import os
import json
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

    canciones_hoy = programacion_mensual.get(hoy, [])

    if canciones_hoy:
        print(f"Cargadas {len(canciones_hoy)} canciones para hoy.")
    else:
        print(f"No hay canciones programadas para el día de hoy ({hoy}).")

    return canciones_hoy

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
    token_info = sp_oauth.refresh_access_token(refresh_token)
    sp = spotipy.Spotify(auth=token_info['access_token'])

    track_uris = []
    for cancion in canciones:
        res = sp.search(q=cancion, type='track', limit=1)
        items = res.get('tracks', {}).get('items', [])
        if items:
            uri = items[0]['uri']
            track_uris.append(uri)
            print(f"[Spotify] Encontrada: {items[0]['name']} - {items[0]['artists'][0]['name']}")
        else:
            print(f"[Spotify] No encontrada: {cancion}")

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

    # 1. Vaciar playlist existente
    items_req = youtube.playlistItems().list(part="id", playlistId=playlist_id, maxResults=50)
    items_res = items_req.execute()
    for item in items_res.get("items", []):
        youtube.playlistItems().delete(id=item["id"]).execute()
    print("[YouTube] Playlist limpiada.")

    # 2. Buscar y agregar canciones
    for cancion in canciones:
        search_req = youtube.search().list(q=cancion, part="id", type="video", maxResults=1)
        search_res = search_req.execute()
        videos = search_res.get("items", [])
        if videos:
            video_id = videos[0]["id"]["videoId"]
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id}
                    }
                }
            ).execute()
            print(f"[YouTube] Añadido video ID: {video_id} ({cancion})")
        else:
            print(f"[YouTube] No encontrado: {cancion}")

if __name__ == "__main__":
    lista = cargar_canciones_del_dia()
    if lista:
        actualizar_spotify(lista)
        actualizar_youtube(lista)
    else:
        print("No se realizaron cambios en las playlists.")
