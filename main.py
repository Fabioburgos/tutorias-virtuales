# main.py

import os
import glob

from src.drive_manager import autenticar_y_obtener_servicio, descargar_video_de_drive
from src.audio_extractor import extraer_audio
from src.audio_chunker import chunk_audio_with_overlap
from src.gcs_manager import subir_archivo_a_gcs
from src.gemini_transcriber import transcribir_con_gemini 
from src.transcript_stitcher import stitch_transcripts
from src.gemini_analyzer import analizar_con_rag_y_citas
from src.report_parser import extraer_calificaciones
from src.pdf_generator import crear_informe_pdf

if __name__ == "__main__":
    # --- 1. CONFIGURACIÓN ---
    # nombre_video_entrada = "Grabación CE OEI 1 - 2025_05_28 07_53 CST - Recording.mp4"
    NOMBRE_VIDEO_EN_DRIVE = "Tutoría lenguaje Nathaly - 2025/05/20 13:54 CST - Recording"
    
    ruta_prompt = "prompts/generacion_diagnostico.txt"
    
    # IMPORTANTE: Debes obtener el ID de la carpeta de tu Drive donde está el video
    # Abre la carpeta en el navegador, la URL será: .../folders/ESTE_ES_EL_ID
    ID_CARPETA_DRIVE = "1cfFL6iOu8-PLSlqOpb_iEs317gYDrZ1b"
    
    ID_PROYECTO = "g-tele-educacion-dev-prj-d18a"
    REGION_GCP = "us-east1"
    GCS_BUCKET_NAME = "ia_tele_educacion"
    RAG_CORPUS_PATH = "projects/g-tele-educacion-dev-prj-d18a/locations/us-central1/ragCorpora/6917529027641081856"
    
    # --- 2. PREPARACIÓN E INICIO DEL PIPELINE ---
    print(f"\n>>> INICIANDO PIPELINE DESDE GOOGLE DRIVE PARA: {NOMBRE_VIDEO_EN_DRIVE} <<<")

    # Autenticación con Google Drive
    servicio_drive = autenticar_y_obtener_servicio()
    if not servicio_drive:
        print("Fallo en la autenticación con Google Drive. Proceso detenido.")
        exit() # Termina el script si no hay autenticación

    # Generación de rutas
    nombre_base = os.path.splitext(NOMBRE_VIDEO_EN_DRIVE)[0]
    ruta_base = os.getcwd()
    ruta_video_local_temp = os.path.join(ruta_base, "temp_videos", NOMBRE_VIDEO_EN_DRIVE)
    
    # --- FASE 0: DESCARGA DEL VIDEO ESPECÍFICO ---
    # Nota: la función 'descargar_video_de_drive' que te di busca por nombre dentro de la carpeta
    ruta_video_descargado = descargar_video_de_drive(
        servicio=servicio_drive,
        nombre_video=NOMBRE_VIDEO_EN_DRIVE,
        id_carpeta_drive=ID_CARPETA_DRIVE,
        ruta_guardado_local=ruta_video_local_temp
    )

    if not ruta_video_descargado:
        print("Fallo en la descarga desde Drive. Proceso detenido.")
        exit()
    
    print(f"\n=====================================================================")
    print(f">>> INICIANDO PIPELINE COMPLETO PARA: {ruta_video_descargado} <<<")
    print(f"=====================================================================")

    ruta_audio_wav_local = os.path.join(ruta_base, "output", "audio", f"{nombre_base}.wav")
    directorio_salida_chunks = os.path.join(ruta_base, "output", "audio_chunks", nombre_base)
    # Cambié el nombre de ruta_informe_final a ruta_texto_salida para que coincida con el guardado
    ruta_informe_final = os.path.join(ruta_base, "output", "analisis_qa", f"ANALISIS - {nombre_base}.md")
    ruta_texto_salida = os.path.join(ruta_base, "output", "transcripciones_finales", f"TRANSCRIPCION - {nombre_base}.txt")
    
    # --- INICIO DEL PIPELINE ---
    print(f"\n>>> INICIANDO PIPELINE COMPLETO PARA: {ruta_video_descargado} <<<")

    audio_extraido_path = extraer_audio(ruta_video_descargado, ruta_audio_wav_local)

    if not audio_extraido_path:
        print("FALLO EN FASE 1: No se pudo extraer el audio. Proceso detenido.")
    else:
        lista_chunks_locales = chunk_audio_with_overlap(
            input_file=ruta_audio_wav_local,
            output_dir=directorio_salida_chunks
        )
        if not lista_chunks_locales:
            print("No se crearon chunks. Terminando el proceso.")
        else:
            transcripciones_de_chunks = []
            for i, chunk_path in enumerate(lista_chunks_locales):
                print(f"\n--- Procesando Chunk {i+1}/{len(lista_chunks_locales)}: {os.path.basename(chunk_path)} ---")
                
                # Ahora la ruta en GCS incluye el nombre base del video para ser única
                ruta_destino_gcs = f"audio_chunks/{nombre_base}/{os.path.basename(chunk_path)}"
                
                gcs_uri = subir_archivo_a_gcs(chunk_path, GCS_BUCKET_NAME, ruta_destino_gcs)
                

                if gcs_uri:
                    texto_chunk = transcribir_con_gemini(ID_PROYECTO, REGION_GCP, gcs_uri)
                    if texto_chunk:
                        transcripciones_de_chunks.append(texto_chunk)
                    else:
                        print(f"El chunk {i+1} no pudo ser transcrito.")
                else:
                    print(f"Fallo al subir el chunk {i+1}.")

            if transcripciones_de_chunks:
                transcripcion_final = stitch_transcripts(transcripciones_de_chunks)
                
                # Usamos la variable ruta_texto_salida definida al principio
                os.makedirs(os.path.dirname(ruta_texto_salida), exist_ok=True)
                
                with open(ruta_texto_salida, "w", encoding="utf-8") as f:
                    f.write(transcripcion_final)
                    
                
                print(f"\nTranscripción completa guardada en: {ruta_texto_salida}")


            # --- NUEVA FASE 5: ANÁLISIS Q&A CON GEMINI ---
            if transcripcion_final:
                respuestas_gemini = analizar_con_rag_y_citas(
                    project_id=ID_PROYECTO,
                    location=REGION_GCP,
                    rag_corpus_path=RAG_CORPUS_PATH,
                    ruta_prompt=ruta_prompt,
                    transcripcion_texto=transcripcion_final
                )

                if not respuestas_gemini:
                    print("FALLO EN FASE 5: No se generó el informe de Gemini.")
                else:
                    # --- NUEVA FASE 6: PARSEAR CALIFICACIONES ---
                    calificaciones, promedio = extraer_calificaciones(respuestas_gemini)

                    # --- NUEVA FASE 7: GENERAR EL INFORME EN PDF ---
                    ruta_informe_pdf = os.path.join(
                        ruta_base, "output", "informes_pdf", f"INFORME - {nombre_base}.pdf"
                    )
                    
                    crear_informe_pdf(
                        titulo=f"Informe de Tutoría: {nombre_base}",
                        informe_texto=respuestas_gemini,
                        calificaciones=calificaciones,
                        promedio=promedio,
                        ruta_salida=ruta_informe_pdf
                    )
                    
                    print(f"\n\n>>> ¡PIPELINE FINALIZADO CON ÉXITO! <<<")
                    print(f"El informe final en PDF ha sido guardado en: {ruta_informe_pdf}")
            else:
                print("No se generaron transcripciones para unir.")