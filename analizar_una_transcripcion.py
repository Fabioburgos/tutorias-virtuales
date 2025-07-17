# analizar_una_transcripcion_gcs.py

import os
from google.cloud import storage # Importamos la librería de GCS directamente
# Módulos necesarios para el pipeline
from src.gcs_manager import descargar_archivo_de_gcs
from src.doc_reader import leer_texto_de_docx
from src.gemini_analyzer import analizar_con_rag_y_citas
from src.report_parser import extraer_calificaciones
from src.pdf_generator import crear_informe_pdf

if __name__ == "__main__":
    # --- 1. CONFIGURACIÓN ---
    # Aquí defines la transcripción específica que quieres analizar
    GCS_BUCKET_NAME = "ia_tele_educacion"
    RUTA_TRANSCRIPCION_EN_GCS = "tutorias_virtuales/google_docs/Tutoría Matemáticas Jaime - 2025_05_20 15_13 CST - Transcript.docx"
    
    # Ruta al archivo que contiene el prompt de evaluación
    ruta_prompt = "prompts/generacion_diagnostico.txt"
    
    # Configuración de GCP (necesaria para llamar a Gemini)
    ID_PROYECTO = "g-tele-educacion-dev-prj-d18a"
    REGION_GCP = "us-east1"
    RAG_CORPUS_PATH = "projects/g-tele-educacion-dev-prj-d18a/locations/us-central1/ragCorpora/6917529027641081856"
    
    # --- 2. PREPARACIÓN E INICIO DEL PIPELINE DE ANÁLISIS ---
    print(f"\n>>> INICIANDO ANÁLISIS PARA LA TRANSCRIPCIÓN: {os.path.basename(RUTA_TRANSCRIPCION_EN_GCS)} <<<")

    # FASE A: Verificar y obtener el archivo de GCS
    try:
        storage_client = storage.Client(project=ID_PROYECTO)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob_transcripcion = bucket.blob(RUTA_TRANSCRIPCION_EN_GCS)

        if not blob_transcripcion.exists():
            print(f"ERROR: El archivo especificado no existe en la ruta de GCS: gs://{GCS_BUCKET_NAME}/{RUTA_TRANSCRIPCION_EN_GCS}")
            exit()
    except Exception as e:
        print(f"Error al conectar con Google Cloud Storage: {e}")
        exit()

    # Generación de rutas locales y de salida
    nombre_archivo = os.path.basename(blob_transcripcion.name)
    nombre_base = os.path.splitext(nombre_archivo)[0]
    ruta_base = os.getcwd()
    ruta_local_temp = os.path.join(ruta_base, "temp_transcripciones", nombre_archivo)
    ruta_informe_pdf = os.path.join(ruta_base, "output", "informes_pdf", f"INFORME - {nombre_base}.pdf")

    # FASE B: Descargar la transcripción a un archivo temporal
    ruta_descargada = descargar_archivo_de_gcs(blob_transcripcion, ruta_local_temp)
    
    if not ruta_descargada:
        print("Fallo al descargar la transcripción. Proceso detenido.")
        exit()

    # FASE C: Leer el contenido del archivo descargado
    transcripcion_final = None
    try:
        if ruta_descargada.lower().endswith('.docx'):
            print("Archivo .docx detectado. Leyendo contenido...")
            transcripcion_final = leer_texto_de_docx(ruta_descargada)
        elif ruta_descargada.lower().endswith('.txt'):
            print("Archivo .txt detectado. Leyendo contenido...")
            with open(ruta_descargada, "r", encoding="utf-8") as f:
                transcripcion_final = f.read()
        else:
            print(f"Formato de archivo no soportado: {nombre_archivo}")

        if transcripcion_final is None:
             raise ValueError("No se pudo extraer texto del archivo.")
        print("Archivo de transcripción cargado exitosamente.")

    except Exception as e:
        print(f"Error al leer el archivo local {ruta_descargada}: {e}")
        exit()

    # FASE D: Analizar con Gemini
    informe_evaluativo_texto = analizar_con_rag_y_citas(
        project_id=ID_PROYECTO,
        location=REGION_GCP,
        rag_corpus_path=RAG_CORPUS_PATH,
        ruta_prompt=ruta_prompt,
        transcripcion_texto=transcripcion_final
    )

    if not informe_evaluativo_texto:
        print("FALLO: No se generó el informe de Gemini. Proceso detenido.")
        exit()

    # FASE E: Parsear Calificaciones
    calificaciones, promedio = extraer_calificaciones(informe_evaluativo_texto)

    # FASE F: Generar PDF
    crear_informe_pdf(
        titulo=f"Informe de Tutoría: {nombre_base}",
        informe_texto=informe_evaluativo_texto,
        calificaciones=calificaciones,
        promedio=promedio,
        ruta_salida=ruta_informe_pdf
    )
    
    print(f"\n\n>>> ¡ANÁLISIS FINALIZADO CON ÉXITO! <<<")
    print(f"El informe final en PDF ha sido guardado en: {ruta_informe_pdf}")

