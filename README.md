# Herramienta de Observabilidad Docente con IA

## 1. Descripción General

Este proyecto es un pipeline automatizado de análisis de datos diseñado para procesar grabaciones de sesiones de tutoría virtual, extraer información valiosa y generar informes evaluativos de alta calidad. Utilizando una combinación de tecnologías de Google Cloud y modelos de lenguaje avanzados como Gemini, la herramienta transforma un video en crudo en un reporte pedagógico estructurado, basado en una rúbrica de evaluación personalizable (inspirada en la metodología TEACH).

El objetivo principal es ofrecer a coordinadores y formadores una manera eficiente y objetiva de realizar la observabilidad docente, identificando fortalezas y áreas de oportunidad en las prácticas pedagógicas de los tutores.

---

## 2. Características Principales

* **Entrada Flexible:** Procesa videos desde una carpeta local o directamente desde una carpeta en Google Drive.
* **Procesamiento de Audio Avanzado:**
    * Extracción automática de audio desde archivos de video (`.mp4`).
    * Limpieza de audio mediante filtros (reducción de ruido, compresión) para maximizar la calidad.
* **Transcripción de Alta Precisión:**
    * Utiliza la API **Speech-to-Text v2 de Google Cloud** para una transcripción precisa.
    * Soporta **diarización** para identificar y etiquetar a los diferentes hablantes.
    * Maneja audios largos dividiéndolos en fragmentos con traslape para garantizar la continuidad.
* **Análisis Pedagógico con IA:**
    * Utiliza **Gemini 1.5 Pro** para realizar un análisis cualitativo de la transcripción.
    * El análisis se basa en un **prompt personalizable** guardado en un archivo externo (`.txt`).
    * Capacidad de usar **RAG (Retrieval-Augmented Generation)** de Vertex AI para consultar guías de referencia (ej. manuales de metodología) y enriquecer el análisis.
* **Generación de Reportes Profesionales:**
    * Extrae calificaciones numéricas del análisis de Gemini.
    * Genera un **informe final en formato PDF**, con un diseño limpio, encabezado con logo, resumen de calificaciones y el análisis detallado.

---

## 3. Estructura del Proyecto

El repositorio está organizado de la siguiente manera para mantener la modularidad y la claridad:


/
├── main.py                     # Orquestador principal para el pipeline completo (video -> PDF)
├── analizar_lote_gcs.py        # Script para analizar transcripciones ya existentes en GCS
├── prompts/
│   └── generacion_diagnostico.txt # Plantilla del prompt para el análisis de Gemini
├── assets/
│   └── logo.png                # Logo para los reportes en PDF
├── data/
│   └── recordings/             # Carpeta para colocar los videos .mp4 a procesar
├── output/
│   ├── audio/                  # Audios .wav/.flac extraídos
│   ├── audio_chunks/           # Fragmentos de audio generados
│   ├── transcripciones_finales/ # Transcripciones completas en .txt
│   └── informes_pdf/           # Reportes finales en .pdf
├── src/
│   ├── audio_processor.py      # Módulo para extraer y limpiar audio (FFmpeg)
│   ├── audio_chunker.py        # Módulo para dividir el audio en fragmentos
│   ├── gcs_manager.py          # Módulo para interactuar con Google Cloud Storage
│   ├── google_speech_v2.py     # Módulo para la transcripción con Speech-to-Text v2
│   ├── transcript_stitcher.py  # Módulo para unir las transcripciones de los fragmentos
│   ├── gemini_analyzer.py      # Módulo para el análisis con Gemini
│   ├── report_parser.py        # Módulo para extraer calificaciones del informe
│   └── pdf_generator.py        # Módulo para crear el reporte final en PDF
└── requirements.txt            # Lista de dependencias de Python


---

## 4. Configuración del Entorno

Sigue estos pasos para configurar y ejecutar el proyecto:

### Prerrequisitos
* Python 3.9 o superior.
* FFmpeg instalado en tu sistema y accesible desde la línea de comandos.
* Una cuenta de Google Cloud con un proyecto activo y facturación habilitada.

### Pasos de Instalación
1.  **Clona el repositorio:**
    ```bash
    git clone [URL_DEL_REPO]
    cd [NOMBRE_DEL_REPO]
    ```

2.  **Crea y activa un entorno virtual:**
    ```bash
    python -m venv .venv
    # En Windows
    .venv\Scripts\activate
    # En macOS/Linux
    source .venv/bin/activate
    ```

3.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuración de Google Cloud:**
    * **Habilita las APIs necesarias** en tu proyecto de GCP:
        * Speech-to-Text API
        * Vertex AI API
    * **Autentica la CLI de gcloud:**
        ```bash
        gcloud auth application-default login
        gcloud config set project [TU_ID_DE_PROYECTO]
        ```
    * **Crea un Reconocedor de Speech-to-Text V2** (solo una vez) con la configuración deseada (idioma, diarización, etc.).
    * **Configura un RAG Corpus** en Vertex AI si deseas usar la funcionalidad de RAG.

5.  **Configura los Scripts:**
    * Abre los scripts principales (`main.py`, `analizar_lote_gcs.py`) y ajusta las variables de configuración en la sección `if __name__ == "__main__":` (IDs de proyecto, nombres de bucket, rutas, etc.).
    * Personaliza el prompt de análisis en `prompts/generacion_diagnostico.txt`.
    * (Opcional) Reemplaza `assets/logo.png` con tu propio logo.

---

## 5. Modo de Uso

### A. Pipeline Completo (Video a PDF)
Este script procesa todos los videos `.mp4` que se encuentren en la carpeta `data/` especificada.

1.  Coloca tus archivos de video en la carpeta `data/[subcarpeta_fuente]`.
2.  Asegúrate de que las variables en `main.py` estén configuradas correctamente.
3.  Ejecuta el script:
    ```bash
    python main.py
    ```
4.  Los reportes en PDF se generarán en la carpeta `output/informes_pdf/`.

### B. Solo Análisis (Transcripción a PDF)
Este script procesa todas las transcripciones (`.txt` o `.docx`) que se encuentren en una carpeta de Google Cloud Storage.

1.  Asegúrate de que tus transcripciones estén subidas a la carpeta de GCS especificada.
2.  Configura las variables en `analizar_lote_gcs.py`.
3.  Ejecuta el script:
    ```bash
    python analizar_lote_gcs.py
    ```
4.  Los reportes en PDF se generarán en la carpeta `output/informes_pdf/`.

---

## 6. Licencia

Este proyecto se distribuye bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.
