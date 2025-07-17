# analizar_transcripcion.py

import os
# Módulos necesarios para la fase de análisis y reporte
from src.gcs_manager import listar_archivos_en_carpeta_gcs, descargar_archivo_de_gcs
from src.doc_reader import leer_texto_de_docx
from src.gemini_analyzer import analizar_con_rag_y_citas
from src.report_parser import extraer_calificaciones
from src.pdf_generator import crear_informe_pdf

if __name__ == "__main__":
    # --- 1. CONFIGURACIÓN ---
    # La configuración ahora apunta a la carpeta en GCS
    GCS_BUCKET_NAME = "ia_tele_educacion"
    CARPETA_TRANSCRIPCIONES_GCS = "tutorias_virtuales/google_docs/"
    
    # Ruta al archivo que contiene el prompt de evaluación
    ruta_prompt = "prompts/generacion_diagnostico.txt"
    
    # Configuración de GCP (necesaria para llamar a Gemini)
    ID_PROYECTO = "g-tele-educacion-dev-prj-d18a"
    REGION_GCP = "us-east1"
    RAG_CORPUS_PATH = "projects/g-tele-educacion-dev-prj-d18a/locations/us-central1/ragCorpora/6917529027641081856"
    
        # --- 2. PREPARACIÓN E INICIO DEL PIPELINE DE ANÁLISIS POR LOTES ---
    print("\n>>> INICIANDO ANÁLISIS POR LOTES DESDE GCS <<<")

    # FASE A: Listar todas las transcripciones en la carpeta de GCS
    lista_de_transcripciones = listar_archivos_en_carpeta_gcs(GCS_BUCKET_NAME, CARPETA_TRANSCRIPCIONES_GCS)

    if not lista_de_transcripciones:
        print("No se encontraron transcripciones en la carpeta de GCS. Proceso terminado.")
        exit()

    # --- BUCLE PRINCIPAL: Procesar cada transcripción encontrada ---
    for blob_transcripcion in lista_de_transcripciones:
        nombre_archivo = os.path.basename(blob_transcripcion.name)
        
        # Omitir archivos que no sean .txt o .docx para evitar procesar archivos no deseados
        if not (nombre_archivo.lower().endswith('.txt') or nombre_archivo.lower().endswith('.docx')):
            print(f"Omitiendo archivo con formato no soportado: {nombre_archivo}")
            continue

        print(f"\n=====================================================================")
        print(f">>> Procesando: {nombre_archivo} <<<")
        print(f"=====================================================================")

        # Generación de rutas locales y de salida
        ruta_base = os.getcwd()
        ruta_local_temp = os.path.join(ruta_base, "temp_transcripciones", nombre_archivo)
        nombre_base = os.path.splitext(nombre_archivo)[0]
        ruta_informe_pdf = os.path.join(ruta_base, "output", "informes_pdf", f"INFORME - {nombre_base}.pdf")

        # FASE B: Descargar la transcripción actual a un archivo temporal
        ruta_descargada = descargar_archivo_de_gcs(blob_transcripcion, ruta_local_temp)
        
        if not ruta_descargada:
            print(f"Fallo al descargar {nombre_archivo}. Saltando al siguiente.")
            continue

        # FASE C: Leer el contenido del archivo descargado
        transcripcion_final = None
        try:
            if ruta_descargada.lower().endswith('.docx'):
                transcripcion_final = leer_texto_de_docx(ruta_descargada)
            elif ruta_descargada.lower().endswith('.txt'):
                with open(ruta_descargada, "r", encoding="utf-8") as f:
                    transcripcion_final = f.read()
            
            if transcripcion_final is None:
                 raise ValueError("No se pudo extraer texto del archivo.")
            print("Archivo de transcripción cargado exitosamente.")

        except Exception as e:
            print(f"Error al leer el archivo local {ruta_descargada}: {e}. Saltando al siguiente.")
            continue
        
        # El resto del pipeline es idéntico, pero dentro del bucle
        if transcripcion_final:
            # FASE D: Analizar con Gemini
            informe_evaluativo_texto = analizar_con_rag_y_citas(
                project_id=ID_PROYECTO,
                location=REGION_GCP,
                rag_corpus_path=RAG_CORPUS_PATH,
                ruta_prompt=ruta_prompt,
                transcripcion_texto=transcripcion_final
            )

            if not informe_evaluativo_texto:
                print(f"FALLO: No se generó el informe para {nombre_archivo}.")
                continue

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
            print(f"Informe para {nombre_archivo} generado con éxito.")
        else:
            print(f"El archivo de transcripción {nombre_archivo} está vacío.")

    print("\n=====================================================================")
    print("TODOS LOS ARCHIVOS HAN SIDO PROCESADOS.")
    print("=====================================================================")