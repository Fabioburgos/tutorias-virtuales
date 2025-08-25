# src/gcs_manager.py

import os
from google.cloud import storage
from google.api_core import exceptions
from typing import List, Optional

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

def eliminar_archivo_de_gcs(bucket_nombre: str, blob_nombre: str) -> bool:
    """
    Elimina un archivo específico de GCS.
    
    Args:
        bucket_nombre: El nombre del bucket.
        blob_nombre: El nombre completo del blob (incluyendo carpeta).
    
    Returns:
        True si se eliminó exitosamente, False en caso contrario.
    """
    print(f"--- [GCS Manager] Eliminando '{blob_nombre}' de GCS... ---")
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_nombre)
        blob = bucket.blob(blob_nombre)
        
        if blob.exists():
            blob.delete()
            print(f"Archivo eliminado exitosamente: {blob_nombre}")
            return True
        else:
            print(f"El archivo no existe: {blob_nombre}")
            return False
            
    except Exception as e:
        print(f"Error al eliminar el archivo {blob_nombre}: {e}")
        return False

def eliminar_archivos_de_carpeta_gcs(bucket_nombre: str, prefijo_carpeta: str, nombres_archivos: Optional[List[str]] = None) -> List[str]:
    """
    Elimina archivos específicos de una carpeta en GCS.
    
    Args:
        bucket_nombre: El nombre del bucket.
        prefijo_carpeta: El prefijo de la carpeta.
        nombres_archivos: Lista de nombres específicos a eliminar. Si es None, elimina todos.
    
    Returns:
        Lista de archivos eliminados exitosamente.
    """
    print(f"--- [GCS Manager] Eliminando archivos de la carpeta '{prefijo_carpeta}'... ---")
    
    archivos_eliminados = []
    
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_nombre)
        
        # Obtener lista de archivos en la carpeta
        blobs = list(storage_client.list_blobs(bucket_nombre, prefix=prefijo_carpeta))
        
        for blob in blobs:
            # Saltar carpetas virtuales
            if blob.name.endswith('/'):
                continue
                
            nombre_archivo = os.path.basename(blob.name)
            
            # Si se especificaron nombres específicos, verificar si este archivo está incluido
            if nombres_archivos is not None and nombre_archivo not in nombres_archivos:
                continue
            
            try:
                blob.delete()
                archivos_eliminados.append(nombre_archivo)
                print(f"Archivo eliminado: {nombre_archivo}")
                
            except Exception as e:
                print(f"Error al eliminar {nombre_archivo}: {e}")
        
        print(f"Total de archivos eliminados: {len(archivos_eliminados)}")
        return archivos_eliminados
        
    except Exception as e:
        print(f"Error general al eliminar archivos de la carpeta: {e}")
        return archivos_eliminados

def limpiar_carpeta_gcs(bucket_nombre: str, prefijo_carpeta: str) -> bool:
    """
    Elimina todos los archivos de una carpeta específica en GCS.
    
    Args:
        bucket_nombre: El nombre del bucket.
        prefijo_carpeta: El prefijo de la carpeta a limpiar.
    
    Returns:
        True si se limpiaron todos los archivos exitosamente.
    """
    print(f"--- [GCS Manager] Limpiando carpeta '{prefijo_carpeta}'... ---")
    
    try:
        archivos_eliminados = eliminar_archivos_de_carpeta_gcs(bucket_nombre, prefijo_carpeta)
        return len(archivos_eliminados) > 0
        
    except Exception as e:
        print(f"Error al limpiar la carpeta: {e}")
        return False

def verificar_archivo_existe_gcs(bucket_nombre: str, blob_nombre: str) -> bool:
    """
    Verifica si un archivo existe en GCS.
    
    Args:
        bucket_nombre: El nombre del bucket.
        blob_nombre: El nombre completo del blob.
    
    Returns:
        True si el archivo existe, False en caso contrario.
    """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_nombre)
        blob = bucket.blob(blob_nombre)
        
        return blob.exists()
        
    except Exception as e:
        print(f"Error al verificar la existencia del archivo: {e}")
        return False