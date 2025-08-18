import os
from PyPDF2 import PdfReader, PdfWriter
from datetime import datetime
import re
from collections import defaultdict

def clean_filename(filename):
    """Limpia el nombre del archivo eliminando caracteres especiales y espacios extra"""
    # Remover extensión
    name = os.path.splitext(filename)[0]
    # Reemplazar caracteres especiales y espacios múltiples
    name = re.sub(r'[^\w\s-]', '_', name)
    name = re.sub(r'\s+', '_', name)
    # Remover guiones bajos múltiples
    name = re.sub(r'_+', '_', name)
    # Remover guiones bajos al inicio y final
    name = name.strip('_')
    return name

def extract_teacher_name(filename):
    """Extrae el nombre del docente del nombre del archivo"""
    # Patrones comunes en los nombres de archivo
    patterns = [
        r'TV\s+([^-]+?)\s+(?:matemática|lenguaje)',  # Para archivos TV
        r'Tutoría\s+(?:Matemáticas|lenguaje)\s+([^-]+)',  # Para tutorías
        r'Tutoría\s+([^-]+?)\s+-'  # Para otros casos de tutoría
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            teacher_name = match.group(1).strip()
            # Limpiar el nombre del docente
            teacher_name = re.sub(r'\s+', ' ', teacher_name)
            return teacher_name
    
    # Si no encuentra patrón, intentar extraer manualmente
    # Buscar nombres conocidos en el texto
    known_teachers = ['Jaime López', 'Nathaly Chica', 'Rafael Menéndez', 'Rhina Barrera', 'IHFB']
    filename_upper = filename.upper()
    
    for teacher in known_teachers:
        if teacher.upper() in filename_upper:
            return teacher
    
    return "Sin_Docente_Identificado"

def has_meaningful_content(text):
    """Verifica si una página tiene contenido significativo"""
    if not text or not text.strip():
        return False
    
    # Remover espacios en blanco y caracteres especiales
    clean_text = re.sub(r'\s+', ' ', text.strip())
    
    # Páginas que solo tienen encabezados pero sin datos reales
    empty_indicators = [
        'Promedio General Final: 0.00 / 10.00',
        'C1 0 / 10 Bajo C2 0 / 10 Bajo C3 0 / 10 Bajo C4 0 / 10 Bajo C5 0 / 10 Bajo C6 0 / 10 Bajo C7 0 / 10 Bajo C8 0 / 10 Bajo',
        'Página 2'  # páginas que solo dicen "Página 2"
    ]
    
    # Si la página solo contiene indicadores de página vacía, no la incluir
    for indicator in empty_indicators:
        if indicator in clean_text and len(clean_text) < 300:
            return False
    
    # Verificar que tenga criterios con puntuaciones reales (no todas en 0)
    # Buscar patrones como "C1 [número] / 10" donde número > 0
    criteria_pattern = r'C\d+\s+(\d+)\s*/\s*10'
    matches = re.findall(criteria_pattern, clean_text)
    
    if matches:
        # Si encuentra criterios, verificar que al menos uno tenga puntuación > 0
        scores = [int(match) for match in matches]
        return any(score > 0 for score in scores)
    
    # Si no encuentra criterios pero tiene contenido suficiente
    return len(clean_text) > 200

def combine_pdfs_by_teacher(folder_path, output_folder="output_por_docente"):
    """
    Combina PDFs agrupándolos por docente y eliminando páginas en blanco
    
    Args:
        folder_path (str): Ruta del folder con los PDFs
        output_folder (str): Folder donde guardar los PDFs por docente
    """
    
    # Verificar que el folder existe
    if not os.path.exists(folder_path):
        print(f"Error: El folder '{folder_path}' no existe.")
        return
    
    # Crear folder de salida si no existe
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Folder de salida creado: {output_folder}")
    
    # Diccionario para agrupar archivos por docente
    files_by_teacher = defaultdict(list)
    
    # Obtener lista de archivos PDF y ordenarlos
    pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
    pdf_files.sort()
    
    if not pdf_files:
        print("No se encontraron archivos PDF en el folder especificado.")
        return
    
    # Agrupar archivos por docente
    print("Agrupando archivos por docente...")
    print("-" * 50)
    
    for filename in pdf_files:
        teacher_name = extract_teacher_name(filename)
        files_by_teacher[teacher_name].append(filename)
        print(f"📁 {filename} → {teacher_name}")
    
    print("-" * 50)
    print(f"Docentes identificados: {len(files_by_teacher)}")
    for teacher, files in files_by_teacher.items():
        print(f"• {teacher}: {len(files)} archivo(s)")
    
    print("\n" + "=" * 60)
    print("PROCESANDO ARCHIVOS POR DOCENTE")
    print("=" * 60)
    
    # Procesar cada docente por separado
    summary = {}
    
    for teacher_name, teacher_files in files_by_teacher.items():
        print(f"\n📚 PROCESANDO: {teacher_name}")
        print("-" * 50)
        
        # Crear escritor para este docente
        teacher_writer = PdfWriter()
        teacher_total_pages = 0
        teacher_pages_added = 0
        teacher_files_processed = 0
        
        for filename in sorted(teacher_files):
            file_path = os.path.join(folder_path, filename)
            
            try:
                reader = PdfReader(file_path)
                file_pages_added = 0
                
                # Procesar cada página del archivo
                for page_num, page in enumerate(reader.pages, 1):
                    teacher_total_pages += 1
                    text = page.extract_text()
                    
                    # Verificar si la página tiene contenido significativo
                    if has_meaningful_content(text):
                        teacher_writer.add_page(page)
                        teacher_pages_added += 1
                        file_pages_added += 1
                
                teacher_files_processed += 1
                print(f"✓ {filename}: {file_pages_added} páginas agregadas de {len(reader.pages)} totales")
                
            except Exception as e:
                print(f"✗ Error procesando {filename}: {str(e)}")
        
        # Guardar PDF del docente
        if teacher_pages_added > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_teacher_name = clean_filename(teacher_name)
            output_filename = f"Informes_{safe_teacher_name}_{timestamp}.pdf"
            output_path = os.path.join(output_folder, output_filename)
            
            try:
                with open(output_path, 'wb') as f:
                    teacher_writer.write(f)
                
                summary[teacher_name] = {
                    'files_processed': teacher_files_processed,
                    'total_pages': teacher_total_pages,
                    'pages_added': teacher_pages_added,
                    'output_file': output_filename
                }
                
                print(f"💾 Archivo generado: {output_filename}")
                print(f"   • Archivos procesados: {teacher_files_processed}")
                print(f"   • Páginas con contenido: {teacher_pages_added}")
                print(f"   • Páginas vacías eliminadas: {teacher_total_pages - teacher_pages_added}")
                
            except Exception as e:
                print(f"✗ Error al guardar archivo de {teacher_name}: {str(e)}")
        else:
            print(f"⚠️  No se encontraron páginas con contenido para {teacher_name}")
    
    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    
    total_files = sum(data['files_processed'] for data in summary.values())
    total_pages = sum(data['total_pages'] for data in summary.values())
    total_pages_added = sum(data['pages_added'] for data in summary.values())
    
    print(f"📊 ESTADÍSTICAS GENERALES:")
    print(f"   • Total de docentes procesados: {len(summary)}")
    print(f"   • Total de archivos procesados: {total_files}")
    print(f"   • Total de páginas encontradas: {total_pages}")
    print(f"   • Total de páginas con contenido: {total_pages_added}")
    print(f"   • Total de páginas vacías eliminadas: {total_pages - total_pages_added}")
    
    print(f"\n📂 ARCHIVOS GENERADOS:")
    for teacher_name, data in summary.items():
        print(f"   • {teacher_name}: {data['output_file']}")
        print(f"     └─ {data['pages_added']} páginas útiles de {data['files_processed']} archivo(s)")
    
    print(f"\n📁 Los archivos se guardaron en: {output_folder}")
    print("✅ ¡Proceso completado exitosamente!")

# Uso del script
if __name__ == "__main__":
    # Configuración
    folder_path = 'output/informes_pdf'
    output_folder = 'output_por_docente'
    
    # Ejecutar el procesamiento por docente
    combine_pdfs_by_teacher(folder_path, output_folder)