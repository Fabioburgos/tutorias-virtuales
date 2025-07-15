# src/gcs_manager.py

import os
from google.cloud import storage
from google.api_core import exceptions

def subir_archivo_a_gcs(ruta_archivo_local, bucket_nombre, destino_blob_nombre):
    """Sube un archivo local a un bucket de Google Cloud Storage con un timeout extendido."""
    print(f"--- [GCS Manager] Subiendo '{os.path.basename(ruta_archivo_local)}' a GCS... ---")
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_nombre)
        blob = bucket.blob(destino_blob_nombre)
        blob.upload_from_filename(ruta_archivo_local, timeout=3600)
        gcs_uri = f"gs://{bucket_nombre}/{destino_blob_nombre}"
        print(f"¡Éxito! Archivo disponible en: {gcs_uri}")
        return gcs_uri
    except Exception as e:
        print(f"Ocurrió un error al subir el archivo a GCS: {e}")
        return None

def listar_archivos_en_carpeta_gcs(bucket_nombre: str, prefijo_carpeta: str) -> list:
    """
    Obtiene una lista de todos los archivos en una carpeta específica de GCS.
    
    Args:
        bucket_nombre: El nombre de tu bucket.
        prefijo_carpeta: La ruta de la carpeta dentro del bucket (ej. "tutorias/").

    Returns:
        Una lista de objetos Blob de GCS.
    """
    print(f"--- [GCS Manager] Listando archivos en 'gs://{bucket_nombre}/{prefijo_carpeta}'... ---")
    try:
        storage_client = storage.Client()
        # list_blobs devuelve un iterador, lo convertimos a lista
        blobs = list(storage_client.list_blobs(bucket_nombre, prefix=prefijo_carpeta))
        # Filtramos para excluir las "carpetas" vacías que GCS a veces muestra
        archivos = [blob for blob in blobs if not blob.name.endswith('/')]
        print(f"Se encontraron {len(archivos)} archivos.")
        return archivos
    except Exception as e:
        print(f"Ocurrió un error al listar archivos en GCS: {e}")
        return []

def descargar_archivo_de_gcs(blob, destino_ruta_local: str) -> str:
    """
    Descarga un archivo (Blob) desde GCS a una ruta local.
    
    Args:
        blob: El objeto Blob de GCS a descargar.
        destino_ruta_local: La ruta en tu disco duro donde se guardará el archivo.
    
    Returns:
        La ruta al archivo local descargado, o None si falla.
    """
    print(f"--- [GCS Manager] Descargando '{blob.name}'... ---")
    try:
        os.makedirs(os.path.dirname(destino_ruta_local), exist_ok=True)
        blob.download_to_filename(destino_ruta_local)
        print("Descarga completada.")
        return destino_ruta_local
    except Exception as e:
        print(f"Ocurrió un error al descargar el archivo: {e}")
        return None
