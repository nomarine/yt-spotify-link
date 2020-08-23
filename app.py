# Obter playlist do youtube
# Criar playlist no spotify
# Identificar músicas na playlist do youtube
# Adicionar músicas na playlist criada no Spotify
import os
import json
import requests

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

import youtube_dl

from exception import ResponseException
from secrets import spotify_token, spotify_user_id

class CreatePlaylist:
    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.all_songs_info = {}

    def get_youtube_client(self):
        """ Loga no YT """
        # Burla verificação de segurança do protocolo HTTPS da biblioteca oAuth
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        # Detalha as informações da API do YT
        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"

        # Obtem credentials e inicia a API do client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes
        )
        credentials = flow.run_console()
        
        youtube_client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)

        return youtube_client

    def get_liked_videos(self):
        """ Pega playlist de vídeos curtidos """
        request = self.youtube_client.videos().list(
            part="snippet,contentDetails,statistics",
            myRating="like"
        )
        response = request.execute()

        # Popula a lista de músicas com suas informações
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            youtube_url = "https://www.youtube.com/watch?v={}".format(
                item["id"])

            video = youtube_dl.YoutubeDL({}).extract_info(
                youtube_url, download=False)
            song_name = video["track"]
            artist = video["artist"]

            if song_name is not None and artist is not None:
                self.all_songs_info[video_title] = {
                    "youtube_url": youtube_url,
                    "song_name": song_name,
                    "artist": artist,

                    "spotify_uri": self.get_spotify_uri(song_name, artist)
            }

    def create_playlist(self):
        """ Cria uma nova playlist """
        request_body = json.dumps({
            "name": "Vídeos curtidos no YouTube",
            "description": "Foi!",
            "public": False
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(
            spotify_user_id)
        response = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

        response_json = response.json()

        return response_json["id"]

    def get_spotify_uri(self, song_name, artist):
        """ Pesquisar música """
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song_name, 
            artist
        )

        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

        response_json = response.json()
        songs = response_json["tracks"]["items"]

        uri = songs[0]["uri"]

        return uri

    def add_song_to_playlist(self):
        """ Adicionar música à palylist """
        # Popula o dict com as músicas curtidas
        self.get_liked_videos()

        # Obtem todas os endereços de identificação
        uris = [info["spotify_uri"]
                    for song, info in self.all_songs_info.items()]

        # Cria uma nova playlist
        playlist_id = self.create_playlist()

        # Adicionar músicas à playlist
        request_data = json.dumps(uris)
        
        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
            playlist_id)

        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

        if response.status_code != 200:
            raise ResponseException(response.status_code)

        response_json = response.json()

        return response_json

if __name__ == '__main__':
    cp = CreatePlaylist()
    cp.add_song_to_playlist()

