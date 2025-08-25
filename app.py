# app.py

import json
import os
import zipfile
from io import BytesIO
import streamlit as st
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from src.doc_reader import leer_texto_de_docx
from src.file_manager import CloudRunFileManager
from src.report_parser import extraer_calificaciones
from src.gemini_analyzer import analizar_con_rag_y_citas
from src.pdf_generator import crear_informe_pdf, crear_informe_pdf_desde_json
from src.gcs_manager import listar_archivos_en_carpeta_gcs, descargar_archivo_de_gcs, subir_archivo_a_gcs

load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title = "Análisis de Tutorías Virtuales",
    page_icon = "📚",
    layout = "wide",
    initial_sidebar_state = "expanded"
)

class TutoriasPipeline:
    def __init__(self):
        """Inicializar el pipeline con configuración"""
        self.REGION_GCP = os.getenv("GCP_REGION")
        self.ruta_prompt = os.getenv("RUTA_PROMPT")
        self.ID_PROYECTO = os.getenv("GCP_PROJECT_ID")
        self.GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
        self.RAG_CORPUS_PATH = os.getenv("RAG_CORPUS_PATH")
        self.CARPETA_TRANSCRIPCIONES_GCS = os.getenv("GCS_TRANSCRIPCIONES_FOLDER")
        
        # Inicializar gestor de archivos para Cloud Run
        self.file_manager = CloudRunFileManager(max_temp_size_mb = 150)
        self.archivos_procesados = []
        
    def subir_archivos_a_gcs(self, uploaded_files) -> List[str]:
        """
        Subir archivos cargados por el usuario a GCS
        
        Args:
            uploaded_files: Lista de archivos subidos por Streamlit
            
        Returns:
            List[str]: Lista de nombres de archivos subidos exitosamente
        """
        archivos_subidos = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Crear directorio temporal para archivos
        temp_dir = self.file_manager.create_temp_directory("upload_")
        
        for i, uploaded_file in enumerate(uploaded_files):
            # Actualizar progreso
            progress = (i + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            status_text.text(f"Subiendo archivo {i+1}/{len(uploaded_files)}: {uploaded_file.name}")
            
            try:
                # Crear archivo temporal
                temp_path = self.file_manager.create_temp_file(
                    content = uploaded_file.getbuffer(), 
                    filename = uploaded_file.name,
                    directory = temp_dir
                )
                
                if temp_path:
                    # Subir a GCS
                    destino_blob = f"{self.CARPETA_TRANSCRIPCIONES_GCS}{uploaded_file.name}"
                    gcs_uri = subir_archivo_a_gcs(temp_path, self.GCS_BUCKET_NAME, destino_blob)
                    
                    if gcs_uri:
                        archivos_subidos.append(uploaded_file.name)
                        st.success(f"✅ {uploaded_file.name} subido correctamente")
                    else:
                        st.error(f"❌ Error al subir {uploaded_file.name}")
                else:
                    st.error(f"❌ Error creando archivo temporal para {uploaded_file.name}")
                    
            except Exception as e:
                st.error(f"❌ Error procesando {uploaded_file.name}: {str(e)}")
        
        progress_bar.progress(1.0)
        status_text.text(f"Proceso completado: {len(archivos_subidos)}/{len(uploaded_files)} archivos subidos")
        
        return archivos_subidos
    
    def cleanup(self):
        """Limpiar archivos temporales"""
        stats = self.file_manager.cleanup_all()
        if stats['directories_cleaned'] > 0 or stats['files_cleaned'] > 0:
            st.info(
                f"🗑️ Limpieza completada: "
                f"{stats['directories_cleaned']} directorios, "
                f"{stats['files_cleaned']} archivos"
            )
        else:
            st.info("No había archivos temporales para limpiar.")
    
    def limpiar_archivos_gcs_entrada(self, nombres_archivos: List[str]):
        """
        Eliminar archivos de entrada de GCS después del procesamiento
        
        Args:
            nombres_archivos: Lista de nombres de archivos a eliminar
        """
        from google.cloud import storage
        
        try:
            client = storage.Client()
            bucket = client.bucket(self.GCS_BUCKET_NAME)
            
            for nombre_archivo in nombres_archivos:
                blob_name = f"{self.CARPETA_TRANSCRIPCIONES_GCS}{nombre_archivo}"
                blob = bucket.blob(blob_name)
                
                if blob.exists():
                    blob.delete()
                    st.info(f"🗑️ Archivo de entrada eliminado: {nombre_archivo}")
                    
        except Exception as e:
            st.warning(f"⚠️ No se pudieron eliminar algunos archivos de entrada: {str(e)}")
    
    def procesar_archivo(self, nombre_archivo: str) -> Dict:
        """
        Procesar un archivo individual siguiendo el pipeline original
        
        Args:
            nombre_archivo: Nombre del archivo a procesar
            
        Returns:
            Dict: Resultado del procesamiento
        """
        resultado = {
            'nombre_archivo': nombre_archivo,
            'exito': False,
            'ruta_pdf_local': None,
            'gcs_pdf_uri': None,
            'error': None
        }
        
        try:
            # Buscar el archivo en GCS
            lista_archivos = listar_archivos_en_carpeta_gcs(self.GCS_BUCKET_NAME, self.CARPETA_TRANSCRIPCIONES_GCS)
            
            blob_archivo = None
            for blob in lista_archivos:
                if os.path.basename(blob.name) == nombre_archivo:
                    blob_archivo = blob
                    break
            
            if not blob_archivo:
                resultado['error'] = f"No se encontró el archivo {nombre_archivo} en GCS"
                return resultado
            
            # Descargar archivo a directorio temporal
            temp_dir = self.file_manager.create_temp_directory(f"proceso_{nombre_archivo}_")
            ruta_local_temp = os.path.join(temp_dir, nombre_archivo)
            
            ruta_descargada = descargar_archivo_de_gcs(blob_archivo, ruta_local_temp)
            if not ruta_descargada:
                resultado['error'] = f"Fallo al descargar {nombre_archivo}"
                return resultado
            
            # Leer contenido del archivo
            transcripcion_final = None
            if ruta_descargada.lower().endswith('.docx'):
                transcripcion_final = leer_texto_de_docx(ruta_descargada)
            elif ruta_descargada.lower().endswith('.txt'):
                with open(ruta_descargada, "r", encoding="utf-8") as f:
                    transcripcion_final = f.read()
            
            if not transcripcion_final:
                resultado['error'] = f"No se pudo extraer texto de {nombre_archivo}"
                return resultado
            
            # Analizar con Gemini
            informe_evaluativo_texto = analizar_con_rag_y_citas(
                project_id=self.ID_PROYECTO,
                location=self.REGION_GCP,
                rag_corpus_path=self.RAG_CORPUS_PATH,
                ruta_prompt=self.ruta_prompt,
                transcripcion_texto=transcripcion_final
            )
            
            if not informe_evaluativo_texto:
                resultado['error'] = f"No se generó el informe para {nombre_archivo}"
                return resultado
            
            # Generar PDF
            nombre_base = os.path.splitext(nombre_archivo)[0]
            ruta_informe_pdf = os.path.join(temp_dir, f"INFORME_{nombre_base}.pdf")
            
            # Detectar formato y procesar
            try:
                json.loads(informe_evaluativo_texto)
                es_json = True
            except json.JSONDecodeError:
                es_json = False
            
            if es_json:
                crear_informe_pdf_desde_json(
                    titulo=f"Informe de Tutoría: {nombre_base}",
                    informe_json=informe_evaluativo_texto,
                    ruta_salida=ruta_informe_pdf
                )
            else:
                calificaciones, promedio = extraer_calificaciones(informe_evaluativo_texto)
                crear_informe_pdf(
                    titulo=f"Informe de Tutoría: {nombre_base}",
                    informe_texto=informe_evaluativo_texto,
                    calificaciones=calificaciones,
                    promedio=promedio,
                    ruta_salida=ruta_informe_pdf
                )
            
            resultado.update({
                'exito': True,
                'ruta_pdf_local': ruta_informe_pdf
            })
            
        except Exception as e:
            resultado['error'] = f"Error procesando {nombre_archivo}: {str(e)}"
        
        return resultado
    
    def procesar_todos_los_archivos(self, nombres_archivos: List[str]) -> List[Dict]:
        """
        Procesar todos los archivos cargados
        
        Args:
            nombres_archivos: Lista de nombres de archivos a procesar
            
        Returns:
            List[Dict]: Lista de resultados del procesamiento
        """
        resultados = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, nombre_archivo in enumerate(nombres_archivos):
            # Actualizar progreso
            progress = (i + 1) / len(nombres_archivos)
            progress_bar.progress(progress)
            status_text.text(f"Procesando archivo {i+1}/{len(nombres_archivos)}: {nombre_archivo}")
            
            # Procesar archivo
            resultado = self.procesar_archivo(nombre_archivo)
            resultados.append(resultado)
            
            # Mostrar resultado
            if resultado['exito']:
                st.success(f"✅ {nombre_archivo} procesado correctamente")
            else:
                st.error(f"❌ Error en {nombre_archivo}: {resultado['error']}")
        
        progress_bar.progress(1.0)
        status_text.text(f"Procesamiento completado: {len([r for r in resultados if r['exito']])}/{len(nombres_archivos)} archivos exitosos")
        
        return resultados

def main():
    """Función principal de la aplicación Streamlit"""
    
    # Título y descripción
    st.title("📚 Pipeline de Análisis de Tutorías Virtuales")
    st.markdown("---")
    
    # Inicializar pipeline
    if 'pipeline' not in st.session_state:
        st.session_state.pipeline = TutoriasPipeline()
    
    pipeline = st.session_state.pipeline
    
    # Sección 1: Carga de Archivos
    st.header("📤 1. Cargar Archivos de Transcripciones")
    
    uploaded_files = st.file_uploader(
        "Selecciona los archivos de transcripciones (.txt, .docx)",
        accept_multiple_files=True,
        type=['txt', 'docx'],
        help="Puedes seleccionar múltiples archivos. Formatos soportados: .txt, .docx"
    )
    
    if uploaded_files:
        st.write(f"**Archivos seleccionados:** {len(uploaded_files)}")
        for file in uploaded_files:
            st.write(f"- {file.name} ({file.size:,} bytes)")
        
        # Botón para subir archivos
        if st.button("📤 Subir Archivos a GCS", type="primary"):
            with st.spinner("Subiendo archivos..."):
                archivos_subidos = pipeline.subir_archivos_a_gcs(uploaded_files)
                st.session_state.archivos_pendientes = archivos_subidos
    
    # Sección 2: Procesamiento
    st.header("⚙️ 2. Procesamiento de Archivos")
    
    if 'archivos_pendientes' in st.session_state and st.session_state.archivos_pendientes:
        st.write(f"**Archivos listos para procesar:** {len(st.session_state.archivos_pendientes)}")
        
        for archivo in st.session_state.archivos_pendientes:
            st.write(f"- {archivo}")
        
        # Botón para iniciar procesamiento
        if st.button("🚀 Iniciar Procesamiento", type="primary"):
            with st.spinner("Procesando archivos..."):
                # Procesar archivos
                resultados = pipeline.procesar_todos_los_archivos(st.session_state.archivos_pendientes)
                
                # Limpiar archivos de entrada de GCS
                pipeline.limpiar_archivos_gcs_entrada(st.session_state.archivos_pendientes)
                
                # Guardar resultados
                st.session_state.archivos_procesados = resultados
                
                # Limpiar archivos pendientes
                del st.session_state.archivos_pendientes
                
                st.success("¡Procesamiento completado!")
                st.rerun()
    
    # Sección 3: Resultados y Descargas
    st.header("📊 3. Resultados y Descargas")
    
    if 'archivos_procesados' in st.session_state:
        resultados = st.session_state.archivos_procesados
        archivos_exitosos = [r for r in resultados if r['exito']]
        
        if archivos_exitosos:
            st.success(f"✅ {len(archivos_exitosos)} informes PDF generados correctamente")
            
            # Mostrar lista de archivos procesados
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader("📋 Archivos Procesados")
                for resultado in archivos_exitosos:
                    with st.expander(f"📄 {resultado['nombre_archivo']}", expanded=False):
                        st.write(f"**Archivo original:** {resultado['nombre_archivo']}")
                        st.write(f"**Estado:** ✅ Procesado exitosamente")
                        if resultado['gcs_pdf_uri']:
                            st.write(f"**PDF en GCS:** {resultado['gcs_pdf_uri']}")
                        
                        # Botón de descarga individual
                        if resultado['ruta_pdf_local'] and os.path.exists(resultado['ruta_pdf_local']):
                            with open(resultado['ruta_pdf_local'], "rb") as pdf_file:
                                pdf_bytes = pdf_file.read()
                                nombre_pdf = f"INFORME_{os.path.splitext(resultado['nombre_archivo'])[0]}.pdf"
                                st.download_button(
                                    label=f"⬇️ Descargar {nombre_pdf}",
                                    data=pdf_bytes,
                                    file_name=nombre_pdf,
                                    mime="application/pdf"
                                )
            
            with col2:
                st.subheader("📦 Descarga Masiva")
                
                # Crear ZIP con todos los PDFs
                if st.button("📦 Descargar Todos (ZIP)", type="secondary"):
                    try:
                        # Crear ZIP en memoria
                        zip_buffer = BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for resultado in archivos_exitosos:
                                if resultado['ruta_pdf_local'] and os.path.exists(resultado['ruta_pdf_local']):
                                    nombre_pdf = f"INFORME_{os.path.splitext(resultado['nombre_archivo'])[0]}.pdf"
                                    zip_file.write(resultado['ruta_pdf_local'], nombre_pdf)
                        
                        zip_buffer.seek(0)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        st.download_button(
                            label="⬇️ Descargar ZIP",
                            data=zip_buffer.getvalue(),
                            file_name=f"Informes_Tutorias_{timestamp}.zip",
                            mime="application/zip"
                        )
                        
                    except Exception as e:
                        st.error(f"Error creando ZIP: {str(e)}")
        
        # Mostrar errores si los hay
        archivos_error = [r for r in resultados if not r['exito']]
        if archivos_error:
            st.error(f"❌ {len(archivos_error)} archivos tuvieron errores")
            
            with st.expander("Ver errores", expanded=False):
                for resultado in archivos_error:
                    st.write(f"**{resultado['nombre_archivo']}:** {resultado['error']}")
    
    else:
        st.info("No hay archivos procesados. Carga algunos archivos y procésalos para ver los resultados aquí.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            <small>Pipeline de Análisis de Tutorías Virtuales - Desarrollado para Cloud Run</small>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()