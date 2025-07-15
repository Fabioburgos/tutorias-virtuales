# src/drive_manager.py
import os
import io
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def autenticar_y_obtener_servicio():
    """Maneja el flujo de autenticación OAuth 2.0 para la API de Drive."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return build('drive', 'v3', credentials=creds)

def listar_videos_en_carpeta(servicio, id_carpeta: str) -> list:
    """Obtiene una lista de todos los videos MP4 de una carpeta específica de Drive."""
    print(f"--- [Drive Manager] Buscando videos .mp4 en la carpeta de Drive... ---")
    try:
        query = f"mimeType='video/mp4' and '{id_carpeta}' in parents and trashed = false"
        results = servicio.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        return results.get('files', [])
    except Exception as e:
        print(f"Ocurrió un error al listar los archivos de Drive: {e}")
        return []

def descargar_video_de_drive(servicio, file_id: str, file_name: str, ruta_guardado_local: str):
    """Descarga un solo video por su ID."""
    print(f"--- [Drive Manager] Descargando '{file_name}'... ---")
    try:
        request = servicio.files().get_media(fileId=file_id)
        os.makedirs(os.path.dirname(ruta_guardado_local), exist_ok=True)
        fh = io.FileIO(ruta_guardado_local, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Progreso de descarga: {int(status.progress() * 100)}%")
            
        print(f"¡Éxito! Video descargado en: {ruta_guardado_local}")
        return ruta_guardado_local
    except Exception as e:
        print(f"Ocurrió un error al descargar el archivo '{file_name}': {e}")
        return None