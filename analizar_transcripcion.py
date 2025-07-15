# analizar_transcripcion.py

import os
# Módulos necesarios para la fase de análisis y reporte
from src.gemini_analyzer import analizar_con_rag_y_citas
from src.report_parser import extraer_calificaciones
from src.pdf_generator import crear_informe_pdf

if __name__ == "__main__":
    # --- 1. CONFIGURACIÓN ---
    # La única línea que necesitas cambiar es la ruta al archivo de transcripción.
    ruta_transcripcion_existente = r"output\transcripciones_finales\TRANSCRIPCION - Tutoría lenguaje Nathaly - 2025_05_20 13_54 CST - Recording.txt"
    
    # Ruta al archivo que contiene el prompt de evaluación
    ruta_prompt = "prompts/generacion_diagnostico.txt"
    
    # Configuración de GCP (necesaria para llamar a Gemini)
    ID_PROYECTO = "g-tele-educacion-dev-prj-d18a"
    REGION_GCP = "us-east1"
    RAG_CORPUS_PATH = "projects/g-tele-educacion-dev-prj-d18a/locations/us-central1/ragCorpora/6917529027641081856"
    
    # --- 2. PREPARACIÓN E INICIO DEL PIPELINE DE ANÁLISIS ---
    print(f"\n>>> INICIANDO ANÁLISIS PARA LA TRANSCRIPCIÓN: {os.path.basename(ruta_transcripcion_existente)} <<<")

    # Generación de rutas de salida
    # Extraemos el nombre base del archivo de transcripción para nombrar el PDF
    nombre_base_sucio = os.path.splitext(os.path.basename(ruta_transcripcion_existente))[0]
    # Limpiamos el prefijo "TRANSCRIPCION - " para un título más limpio
    nombre_base = nombre_base_sucio.replace("TRANSCRIPCION - ", "")
    
    ruta_base = os.getcwd()
    ruta_informe_pdf = os.path.join(ruta_base, "output", "informes_pdf", f"INFORME - {nombre_base}.pdf")

    # --- FASE A: LEER EL ARCHIVO DE TRANSCRIPCIÓN ---
    try:
        with open(ruta_transcripcion_existente, "r", encoding="utf-8") as f:
            transcripcion_final = f.read()
        print("Archivo de transcripción cargado exitosamente.")
    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo de transcripción en la ruta: {ruta_transcripcion_existente}")
        exit() # Termina el script si no se encuentra el archivo

    # --- FASE B: ANALIZAR CON GEMINI (FASE 5 del pipeline original) ---
    if transcripcion_final:
        informe_evaluativo_texto = analizar_con_rag_y_citas(
            project_id=ID_PROYECTO,
            location=REGION_GCP,
            rag_corpus_path=RAG_CORPUS_PATH,
            ruta_prompt=ruta_prompt,
            transcripcion_texto=transcripcion_final
        )

        if not informe_evaluativo_texto:
            print("FALLO: No se generó el informe de Gemini. Proceso detenido.")
        else:
            # --- FASE C: PARSEAR CALIFICACIONES (FASE 6 del pipeline original) ---
            calificaciones, promedio = extraer_calificaciones(informe_evaluativo_texto)

            # --- FASE D: GENERAR EL INFORME EN PDF (FASE 7 del pipeline original) ---
            crear_informe_pdf(
                titulo=f"Informe de Tutoría: {nombre_base}",
                informe_texto=informe_evaluativo_texto,
                calificaciones=calificaciones,
                promedio=promedio,
                ruta_salida=ruta_informe_pdf
            )
            
            print(f"\n\n>>> ¡ANÁLISIS FINALIZADO CON ÉXITO! <<<")
            print(f"El informe final en PDF ha sido guardado en: {ruta_informe_pdf}")
    else:
        print("El archivo de transcripción está vacío. Proceso detenido.")

