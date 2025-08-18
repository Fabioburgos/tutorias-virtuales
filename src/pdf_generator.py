# src/pdf_generator.py
import os
import re
import json
from fpdf import FPDF
from datetime import datetime

# Definimos colores para la tabla y el texto
COLOR_GRIS_CLARO = (240, 240, 240)
COLOR_GRIS_OSCURO = (100, 100, 100)
COLOR_VERDE = (40, 167, 69)
COLOR_AMARILLO = (255, 193, 7)
COLOR_ROJO = (220, 53, 69)
COLOR_AZUL_OSCURO = (0, 31, 63)

# Diccionario con las preguntas específicas para cada criterio
PREGUNTAS_CRITERIOS = {
    'C1': '¿El tutor abre la sesión con los docentes identificando objetivos y alcance del espacio?',
    'C2': '¿El tutor menciona evidencias del proceso formativo y hace seguimiento a acciones previamente acordadas?',
    'C3': '¿El tutor menciona o aplica enfoques pedagógicos actualizados durante la sesión?',
    'C4': '¿El tutor utiliza un lenguaje claro, profesional y comprensible?',
    'C5': '¿El tutor desarrolla la sesión a partir de la estructura del guion didáctico?',
    'C6': '¿El tutor brinda retroalimentación específica y constructiva sobre prácticas docentes durante la sesión?',
    'C7': '¿El tutor demuestra dominio del entorno digital o hace referencia al uso adecuado de la plataforma?',
    'C8': '¿El tutor plantea estrategias con base en lo conversado y evaluado durante la sesión?'
}

class PDF(FPDF):
    def header(self):

        # LOGO
        try:
            self.image('assets/logo.png', x=7, y=6, w=19)
        except FileNotFoundError:
            print("Advertencia: No se encontró el logo.")
        
        # TÍTULO
        self.set_y(10) 
        self.set_x(25)   
        self.set_font("Arial", "B", 10)
        self.set_text_color(*COLOR_AZUL_OSCURO)
        self.cell(0, 8, self.title, 0, 1, 'C')
        
        # FECHA DE GENERACIÓN
        self.set_font("Arial", "", 9)
        self.set_text_color(128)
        self.cell(0, 6, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1, 'C')
        
        # LÍNEA SEPARADORA
        self.ln(3)
        self.set_line_width(0.5)
        self.set_draw_color(200)
        self.line(10, self.get_y(), 200, self.get_y())  # POSICIÓN DINÁMICA
        self.ln(8)
        self.set_text_color(0)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font("Arial", "B", 12)
        self.set_text_color(*COLOR_AZUL_OSCURO)
        self.cell(0, 10, title, ln=True)
        self.ln(3)

    def clean_text_for_pdf(self, text):
        """Limpia y convierte texto para evitar errores de codificación en PDF"""
        if not text:
            return ""
        
        # Diccionario para reemplazar caracteres problemáticos
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'ñ': 'n', 'Ñ': 'N',
            'ü': 'u', 'Ü': 'U',
            '"': '"', '"': '"', ''': "'", ''': "'",
            '–': '-', '—': '-', '…': '...',
            '•': '-', '●': '-', '▪': '-',
            '°': 'o',
            'ç': 'c', 'Ç': 'C'
        }
        
        # Aplicar reemplazos
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Convertir a latin-1 de forma segura, manteniendo los signos de interrogación
        try:
            # Intentar codificar directamente
            text.encode('latin-1')
            return text
        except UnicodeEncodeError:
            # Si falla, reemplazar solo los caracteres problemáticos
            text_clean = ''
            for char in text:
                try:
                    char.encode('latin-1')
                    text_clean += char
                except UnicodeEncodeError:
                    # Reemplazar caracteres no compatibles con latin-1
                    if char == '¿':
                        text_clean += chr(191)  # Código latin-1 para ¿
                    elif char == '¡':
                        text_clean += chr(161)  # Código latin-1 para ¡
                    else:
                        text_clean += '?'  # Reemplazar otros caracteres problemáticos
            text = text_clean
        
        # Limpiar espacios extra
        text = ' '.join(text.split()).strip()
        
        return text

    def chapter_body(self, text):
        self.set_font("Arial", "", 10)
        self.set_text_color(0)
        # Limpiar texto antes de usarlo
        text_clean = self.clean_text_for_pdf(text)
        self.multi_cell(0, 6, text_clean)
        self.ln(3)

    def add_evaluation_table(self, tabla_evaluacion):
        """Crea tabla profesional con alturas sincronizadas por fila"""
        self.set_font("Arial", "B", 9)
        self.set_fill_color(*COLOR_GRIS_OSCURO)
        self.set_text_color(255)

        ancho_criterio = 30
        ancho_puntaje = 20
        ancho_pregunta = 60
        ancho_justificacion = 80
        altura_linea = 4

        # Encabezado
        self.cell(ancho_criterio, altura_linea * 2, "Criterio", 1, 0, 'C', True)
        self.cell(ancho_puntaje, altura_linea * 2, "Puntaje", 1, 0, 'C', True)
        self.cell(ancho_pregunta, altura_linea * 2, "Pregunta", 1, 0, 'C', True)
        self.cell(ancho_justificacion, altura_linea * 2, "Justificacion", 1, 1, 'C', True)  # Sin tilde

        self.set_font("Arial", "", 8)
        self.set_text_color(0)

        for row in tabla_evaluacion:
            # Limpiar todos los textos antes de usarlos
            criterio = self.clean_text_for_pdf(row['criterio'])
            puntaje = self.clean_text_for_pdf(row['puntaje'])
            justificacion = self.clean_text_for_pdf(row['justificacion'])
            
            codigo_criterio = self.extraer_codigo_criterio(criterio)
            pregunta_original = PREGUNTAS_CRITERIOS.get(codigo_criterio, "Pregunta no disponible")
            pregunta = self.clean_text_for_pdf(pregunta_original)

            # Calcular altura necesaria para cada celda
            h_criterio = self.calculate_cell_height(ancho_criterio, criterio, altura_linea)
            h_pregunta = self.calculate_cell_height(ancho_pregunta, pregunta, altura_linea)
            h_justificacion = self.calculate_cell_height(ancho_justificacion, justificacion, altura_linea)
            
            # Altura total de la fila (mínimo una línea)
            h_total = max(h_criterio, h_pregunta, h_justificacion, altura_linea)

            # Verificar si hay espacio en la página
            if self.get_y() + h_total > self.page_break_trigger:
                self.add_page()

            # Coordenadas de inicio de la fila
            start_x = self.get_x()
            start_y = self.get_y()

            # 1. Celda Criterio
            self.rect(start_x, start_y, ancho_criterio, h_total)
            self.set_xy(start_x + 1, start_y + 1)
            self.multi_cell(ancho_criterio - 2, altura_linea, criterio, 0, 'L')

            # 2. Celda Puntaje (con color)
            try:
                puntaje_num = int(puntaje.split('/')[0])
                if puntaje_num <= 3:
                    color = COLOR_ROJO
                elif puntaje_num <= 6:
                    color = COLOR_AMARILLO
                else:
                    color = COLOR_VERDE
            except:
                color = (0, 0, 0)

            self.rect(start_x + ancho_criterio, start_y, ancho_puntaje, h_total)
            text_y_center = start_y + (h_total - altura_linea) / 2
            self.set_xy(start_x + ancho_criterio, text_y_center)
            self.set_text_color(*color)
            self.cell(ancho_puntaje, altura_linea, puntaje, 0, 0, 'C')
            self.set_text_color(0)

            # 3. Celda Pregunta
            self.rect(start_x + ancho_criterio + ancho_puntaje, start_y, ancho_pregunta, h_total)
            self.set_xy(start_x + ancho_criterio + ancho_puntaje + 1, start_y + 1)
            self.multi_cell(ancho_pregunta - 2, altura_linea, pregunta, 0, 'L')

            # 4. Celda Justificación
            self.rect(start_x + ancho_criterio + ancho_puntaje + ancho_pregunta, start_y, ancho_justificacion, h_total)
            self.set_xy(start_x + ancho_criterio + ancho_puntaje + ancho_pregunta + 1, start_y + 1)
            self.multi_cell(ancho_justificacion - 2, altura_linea, justificacion, 0, 'L')

            # Mover a la siguiente fila
            self.set_xy(start_x, start_y + h_total)

    def calculate_cell_height(self, width, text, line_height):
        """Calcula la altura necesaria para el texto en una celda"""
        if not text:
            return line_height
            
        text_width = width - 2  # Margen interno
        char_width = self.get_string_width('A')  # Ancho promedio por carácter
        chars_per_line = int(text_width / char_width) if char_width > 0 else 50
        
        # Contar líneas aproximadas
        words = text.split()
        lines = 1
        current_line_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 para el espacio
            if current_line_length + word_length > chars_per_line:
                lines += 1
                current_line_length = word_length
            else:
                current_line_length += word_length
        
        return max(line_height, lines * line_height)

    def extraer_codigo_criterio(self, criterio_texto):
        """Extrae el código del criterio (C1, C2, etc.) del texto del criterio"""
        match = re.match(r'(C\d+)', criterio_texto)
        return match.group(1) if match else None

    def add_summary_table(self, calificaciones, promedio):
        """Crea tabla resumen con calificaciones numéricas"""
        self.chapter_title("Resumen Cuantitativo")
        
        self.set_font("Arial", "B", 10)
        self.set_fill_color(*COLOR_GRIS_OSCURO)
        self.set_text_color(255)
        
        self.cell(40, 8, "Criterio", border=1, fill=True, align='C')
        self.cell(30, 8, "Puntuación", border=1, fill=True, align='C')
        self.cell(60, 8, "Nivel de Desempeño", border=1, fill=True, align='C')
        self.ln()
        
        self.set_font("Arial", "", 10)
        self.set_text_color(0)
        
        for criterio, nota in sorted(calificaciones.items()):
            if nota <= 3:
                nivel, color = "Bajo", COLOR_ROJO
            elif nota <= 6:
                nivel, color = "Medio", COLOR_AMARILLO
            else:
                nivel, color = "Alto", COLOR_VERDE
            
            self.cell(40, 8, criterio, border=1, align='C')
            self.set_text_color(*color)
            self.cell(30, 8, f"{nota}/10", border=1, align='C')
            self.set_text_color(0)
            self.cell(60, 8, nivel, border=1, align='C')
            self.ln()
        
        # Promedio final
        self.ln(5)
        self.set_font("Arial", "B", 12)
        self.set_text_color(*COLOR_AZUL_OSCURO)
        self.cell(0, 10, f"Promedio General Final: {promedio:.2f}/10.00", ln=True)

def parsear_respuesta_json_gemini(informe_json: str):
    """
    Parsea la respuesta JSON estructurada de Gemini y extrae las secciones principales
    """
    try:
        # Si es string, parsearlo como JSON
        if isinstance(informe_json, str):
            data = json.loads(informe_json)
        else:
            data = informe_json
        
        # Acceder al informe_evaluacion
        informe = data.get('informe_evaluacion', {})
        
        resultado = {
            'titulo': 'Informe de Evaluación de Tutoría Virtual',
            'identificacion': '',
            'tabla_evaluacion': [],
            'sintesis': '',
            'recomendaciones': ''
        }
        
        # 1. Construir identificación básica
        metadatos = informe.get('metadatos', {})
        participantes = informe.get('participantes', {})
        
        identificacion_lines = []
        if metadatos.get('titulo_sesion'):
            identificacion_lines.append(f"Titulo de sesion: {metadatos['titulo_sesion']}")
        if metadatos.get('fecha_analisis'):
            identificacion_lines.append(f"Fecha de analisis: {metadatos['fecha_analisis']}")
        if metadatos.get('hora_inicio') and metadatos.get('hora_cierre'):
            identificacion_lines.append(f"Duracion: {metadatos['hora_inicio']} - {metadatos['hora_cierre']}")
        
        # Tutor
        tutor = participantes.get('tutor', {})
        if tutor.get('nombre'):
            identificacion_lines.append(f"Tutor: {tutor['nombre']}")
        
        # Docentes
        docentes = participantes.get('docentes', [])
        if docentes:
            docentes_nombres = [doc.get('nombre', 'N/A') for doc in docentes]
            identificacion_lines.append(f"Docentes participantes: {', '.join(docentes_nombres)}")
        
        resultado['identificacion'] = '\n'.join(identificacion_lines)
        
        # 2. Construir tabla de evaluación
        evaluacion_criterios = informe.get('evaluacion_criterios', {})
        for criterio_id, criterio_data in evaluacion_criterios.items():
            # Extraer el código del criterio (C1, C2, etc.)
            codigo_criterio = criterio_id.split('_')[0].upper()
            descripcion = criterio_data.get('descripcion', '')
            puntaje = criterio_data.get('puntaje', 0)
            analisis = criterio_data.get('analisis', 'Sin análisis disponible')
            
            # Formato del criterio similar al anterior
            criterio_texto = f"{codigo_criterio}. {descripcion}"
            puntaje_texto = f"{puntaje}/10"
            
            resultado['tabla_evaluacion'].append({
                'criterio': criterio_texto,
                'puntaje': puntaje_texto,
                'justificacion': analisis
            })
        
        # 3. Construir síntesis evaluativa
        resumen = informe.get('resumen_evaluativo', {})
        sintesis_lines = []
        
        if resumen.get('promedio_general'):
            promedio = resumen['promedio_general']
            sintesis_lines.append(f"Promedio General: {promedio}/10")
        
        if resumen.get('conclusion_general'):
            sintesis_lines.append(f"\nConclusión General:\n{resumen['conclusion_general']}")
        
        # Aspectos destacados
        aspectos_destacados = resumen.get('aspectos_destacados', [])
        if aspectos_destacados:
            sintesis_lines.append(f"\nAspectos Destacados:")
            for aspecto in aspectos_destacados:
                sintesis_lines.append(f"• {aspecto}")
        
        # Areas de mejora
        areas_mejora = resumen.get('areas_mejora', [])
        if areas_mejora:
            sintesis_lines.append(f"\nAreas de Mejora:")
            for area in areas_mejora:
                sintesis_lines.append(f"• {area}")
        
        resultado['sintesis'] = '\n'.join(sintesis_lines)
        
        # 4. Construir recomendaciones
        recomendaciones = informe.get('recomendaciones', [])
        if recomendaciones:
            recomendaciones_lines = []
            for i, rec in enumerate(recomendaciones, 1):
                criterio = rec.get('criterio', '')
                recomendacion = rec.get('recomendacion', '')
                prioridad = rec.get('prioridad', 'media')
                
                # Mapear criterio a nombre más legible
                criterio_nombre = {
                    'C1_estructura_objetivos': 'Estructura y Objetivos',
                    'C2_seguimiento_formativo': 'Seguimiento Formativo',
                    'C3_enfoques_pedagogicos': 'Enfoques Pedagogicos',
                    'C4_claridad_profesionalismo': 'Claridad y Profesionalismo',
                    'C5_guion_didactico': 'Guion Didactico',
                    'C6_retroalimentacion_pedagogica': 'Retroalimentacion Pedagogica',
                    'C7_dominio_digital': 'Dominio Digital',
                    'C8_cierre': 'Cierre de Sesion'
                }.get(criterio, criterio)
                
                recomendaciones_lines.append(f"• {criterio_nombre} (Prioridad: {prioridad.upper()}):")
                recomendaciones_lines.append(f"  {recomendacion}")
                if i < len(recomendaciones):
                    recomendaciones_lines.append("")
            
            resultado['recomendaciones'] = '\n'.join(recomendaciones_lines)
        
        return resultado
        
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error al parsear JSON de Gemini: {e}")
        # Devolver estructura vacía en caso de error
        return {
            'titulo': 'Informe de Evaluación de Tutoría Virtual',
            'identificacion': 'Error al procesar datos de identificación',
            'tabla_evaluacion': [],
            'sintesis': 'Error al procesar síntesis evaluativa',
            'recomendaciones': 'Error al procesar recomendaciones'
        }

def crear_informe_pdf_desde_json(titulo: str, informe_json: str, ruta_salida: str):
    """
    Genera un PDF profesional parseando la respuesta JSON estructurada de Gemini
    """
    print("--- [PDF Generator] Creando informe PDF desde JSON ---")
    
    # Parsear la respuesta JSON de Gemini
    datos = parsear_respuesta_json_gemini(informe_json)
    
    # Extraer calificaciones para la tabla resumen
    calificaciones = {}
    promedio = 0.0
    
    try:
        if isinstance(informe_json, str):
            data = json.loads(informe_json)
        else:
            data = informe_json
            
        informe = data.get('informe_evaluacion', {})
        evaluacion_criterios = informe.get('evaluacion_criterios', {})
        
        for criterio_id, criterio_data in evaluacion_criterios.items():
            codigo_criterio = criterio_id.split('_')[0].upper()
            puntaje = criterio_data.get('puntaje', 0)
            calificaciones[codigo_criterio] = puntaje
        
        resumen = informe.get('resumen_evaluativo', {})
        promedio = resumen.get('promedio_general', 0.0)
        
    except Exception as e:
        print(f"Error al extraer calificaciones: {e}")
    
    # Crear PDF
    pdf = PDF()
    pdf.title = titulo
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # 1. Identificación Básica
    if datos['identificacion']:
        pdf.chapter_title("1. Identificación Básica")
        pdf.chapter_body(datos['identificacion'])
    
    # 2. Evaluación de la Sesión
    if datos['tabla_evaluacion']:
        pdf.chapter_title("2. Evaluación de la Sesión")
        pdf.add_evaluation_table(datos['tabla_evaluacion'])
        pdf.ln(5)
    
    # 3. Síntesis Evaluativa
    if datos['sintesis']:
        pdf.chapter_title("3. Síntesis Evaluativa")
        pdf.chapter_body(datos['sintesis'])
    
    # 4. Recomendaciones
    if datos['recomendaciones']:
        pdf.chapter_title("4. Recomendaciones de Mejora")
        pdf.chapter_body(datos['recomendaciones'])
    
    # 5. Tabla resumen cuantitativo (nueva página)
    if calificaciones:
        pdf.add_page()
        pdf.add_summary_table(calificaciones, promedio)
    
    # Guardar PDF
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    pdf.output(ruta_salida)
    print(f"PDF profesional generado exitosamente en: {ruta_salida}")

# Función de compatibilidad para mantener la interfaz anterior
def crear_informe_pdf(titulo: str, informe_texto: str, calificaciones: dict, promedio: float, ruta_salida: str):
    """
    Función de compatibilidad - detecta automáticamente si es JSON o Markdown
    """
    try:
        # Intentar parsear como JSON
        json.loads(informe_texto)
        print("Detectado formato JSON - usando parser JSON")
        crear_informe_pdf_desde_json(titulo, informe_texto, ruta_salida)
    except json.JSONDecodeError:
        print("Detectado formato Markdown - usando parser original")
        # Usar la función original para Markdown
        parsear_respuesta_gemini_markdown(informe_texto, titulo, calificaciones, promedio, ruta_salida)

def parsear_respuesta_gemini_markdown(informe_texto: str, titulo: str, calificaciones: dict, promedio: float, ruta_salida: str):
    """
    Función original para parsear Markdown (mantenida para compatibilidad)
    """
    resultado = {
        'titulo': titulo,
        'identificacion': '',
        'tabla_evaluacion': [],
        'sintesis': '',
        'recomendaciones': ''
    }
    
    # 1. Extraer título (si existe)
    titulo_match = re.search(r"### \*\*(.*?Informe.*?)\*\*", informe_texto)
    if titulo_match:
        resultado['titulo'] = titulo_match.group(1).strip()
    
    # 2. Extraer identificación básica (SIN ###, solo con **)
    identificacion_match = re.search(r"\*\*Identificación básica\*\*(.*?)---", informe_texto, re.DOTALL)
    if identificacion_match:
        texto_id = identificacion_match.group(1).strip()
        # Procesar las viñetas con asteriscos de forma más flexible
        lineas_procesadas = []
        for linea in texto_id.split('\n'):
            linea = linea.strip()
            if linea.startswith('*   **') and ':**' in linea:
                # Formato flexible: "*   **Campo:** Valor"
                partes = linea.replace('*   **', '').split(':**', 1)
                if len(partes) == 2:
                    campo = partes[0].strip()
                    valor = partes[1].strip()
                    lineas_procesadas.append(f"{campo}: {valor}")
            elif linea.startswith('*   **') and '**: ' in linea:
                # Formato alternativo: "*   **Campo**: Valor"  
                partes = linea.replace('*   **', '').split('**: ', 1)
                if len(partes) == 2:
                    lineas_procesadas.append(f"{partes[0]}: {partes[1]}")
            elif linea and not linea.startswith('*') and lineas_procesadas:
                # Continuación de línea anterior
                lineas_procesadas[-1] += f" {linea}"
        
        resultado['identificacion'] = '\n'.join(lineas_procesadas)
    
    # 3. Extraer tabla de evaluación
    tabla_pattern = r"\|\s*\*\*(C\d+\..*?)\*\*\s*\|\s*(\d+/10)\s*\|\s*(.*?)\s*\|"
    matches = re.findall(tabla_pattern, informe_texto, re.DOTALL)
    
    for match in matches:
        criterio = match[0].strip()
        puntaje = match[1].strip()
        justificacion = match[2].strip()
        
        resultado['tabla_evaluacion'].append({
            'criterio': criterio,
            'puntaje': puntaje,
            'justificacion': justificacion
        })
    
    # 4. Extraer síntesis evaluativa (formato específico de Gemini)
    sintesis_match = re.search(r"### \*\*Síntesis Evaluativa\*\*(.*?)---", informe_texto, re.DOTALL)
    if sintesis_match:
        sintesis_texto = sintesis_match.group(1).strip()
        
        # Buscar promedio en formato "*   **Promedio General de la Sesión**: **0/10**"
        promedio_match = re.search(r"Promedio General.*?\*\*(\d+(?:\.\d+)?)/10\*\*", sintesis_texto)
        conclusion_match = re.search(r"\*\*Conclusión General\*\*:\s*(.*)", sintesis_texto, re.DOTALL)
        
        lineas_sintesis = []
        if promedio_match:
            promedio = promedio_match.group(1)
            lineas_sintesis.append(f"Promedio General: {promedio}/10")
        
        if conclusion_match:
            conclusion = conclusion_match.group(1).strip()
            lineas_sintesis.append(f"\nConclusión General:\n{conclusion}")
        
        resultado['sintesis'] = '\n'.join(lineas_sintesis) if lineas_sintesis else sintesis_texto
    
    # 5. Extraer recomendaciones (con numeración 1., 2., 3.)
    recomendaciones_match = re.search(r"### \*\*Recomendaciones de Mejora\*\*(.*?)(?=---|$)", informe_texto, re.DOTALL)
    if recomendaciones_match:
        recomendaciones_texto = recomendaciones_match.group(1).strip()
        
        # Procesar las recomendaciones numeradas
        lineas_procesadas = []
        lineas = recomendaciones_texto.split('\n')
        
        for linea in lineas:
            linea = linea.strip()
            if re.match(r'^\d+\.\s+\*\*.*?\*\*:', linea):
                # Es una recomendación numerada como "1.  **Preparación Técnica**:"
                linea_limpia = re.sub(r'^\d+\.\s+\*\*(.*?)\*\*:', r'• \1:', linea)
                lineas_procesadas.append(linea_limpia)
            elif linea.startswith('*   **Cita'):
                # Es una cita, la dejamos tal como está pero con mejor formato
                linea_limpia = linea.replace('*   **', '    • ').replace('**:', ':')
                lineas_procesadas.append(linea_limpia)
            elif linea and not linea.startswith('*') and not re.match(r'^\d+\.', linea):
                # Es continuación de texto
                lineas_procesadas.append(f"  {linea}")
            elif linea:
                lineas_procesadas.append(linea)
        
        resultado['recomendaciones'] = '\n'.join(lineas_procesadas)
    
    # Crear PDF usando la estructura parseada
    pdf = PDF()
    pdf.title = resultado['titulo']
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # 1. Identificación Básica
    if resultado['identificacion']:
        pdf.chapter_title("1. Identificación Básica")
        pdf.chapter_body(resultado['identificacion'])
    
    # 2. Evaluación de la Sesión
    if resultado['tabla_evaluacion']:
        pdf.chapter_title("2. Evaluación de la Sesión")
        pdf.add_evaluation_table(resultado['tabla_evaluacion'])
        pdf.ln(5)
    
    # 3. Síntesis Evaluativa
    if resultado['sintesis']:
        pdf.chapter_title("3. Síntesis Evaluativa")
        pdf.chapter_body(resultado['sintesis'])
    
    # 4. Recomendaciones
    if resultado['recomendaciones']:
        pdf.chapter_title("4. Recomendaciones de Mejora")
        pdf.chapter_body(resultado['recomendaciones'])
    
    # 5. Tabla resumen cuantitativo (nueva página)
    if calificaciones:
        pdf.add_page()
        pdf.add_summary_table(calificaciones, promedio)
    
    # Guardar PDF
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    pdf.output(ruta_salida)
    print(f"PDF profesional generado exitosamente en: {ruta_salida}")