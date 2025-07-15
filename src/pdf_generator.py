                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          # src/pdf_generator.py
import os
import re
from fpdf import FPDF
from datetime import datetime

# Definimos colores para la tabla y el texto
COLOR_GRIS_CLARO = (240, 240, 240)
COLOR_GRIS_OSCURO = (100, 100, 100)
COLOR_VERDE = (40, 167, 69)
COLOR_AMARILLO = (255, 193, 7)
COLOR_ROJO = (220, 53, 69)
COLOR_AZUL_OSCURO = (0, 31, 63)

class PDF(FPDF):
    def header(self):
        # --- Encabezado mejorado con logo y fecha ---
        try:
            self.image('assets/logo.png', x=10, y=8, w=33)
        except FileNotFoundError:
            print("Advertencia: No se encontró 'assets/logo.png'. El PDF se generará sin logo.")
            
        self.set_font('Arial', 'B', 16)
        self.set_text_color(*COLOR_AZUL_OSCURO)
        self.cell(0, 10, self.title, 0, 1, 'C')

        self.set_font('Arial', '', 9)
        self.set_text_color(128)
        self.cell(0, 10, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1, 'C')
        
        self.ln(5)
        self.set_line_width(0.5)
        self.set_draw_color(200)
        self.line(10, 35, 200, 35)
        self.ln(10)
        self.set_text_color(0) # Resetear color de texto

    def footer(self):
        # --- Pie de página estándar ---
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def crear_informe_pdf(titulo: str, informe_texto: str, calificaciones: dict, promedio: float, ruta_salida: str):
    """
    Crea un informe en PDF profesional parseando el texto con formato Markdown de Gemini.
    """
    print("--- [PDF Generator] Creando informe PDF estructurado ---")

    pdf = PDF('P', 'mm', 'Letter')
    
    pdf.title = titulo
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # --- INICIO DE LA CORRECCIÓN ---
    # Función auxiliar para sanitizar todo el texto antes de enviarlo a FPDF
    def sanitize(text):
        return text.encode('latin-1', 'replace').decode('latin-1')
    # --- FIN DE LA CORRECCIÓN ---

    # --- Parsear y escribir el informe línea por línea ---
    in_evaluation_table = False
    for line in informe_texto.split('\n'):
        # Detectar el inicio de la sección de evaluación
        if "Evaluación de la Sesión" in line:
            in_evaluation_table = True
        
        # Ignorar las líneas de formato de la tabla Markdown
        if re.match(r'\| :--- \|', line) or re.match(r'\|\s*\*\*PROMEDIO', line):
            continue

        # Lógica para renderizar la tabla de evaluación
        if in_evaluation_table and line.startswith('| **C'):
            partes = [p.strip() for p in line.split('|')]
            if len(partes) > 3: # Asegurarse de que la fila tiene contenido
                criterio_titulo = partes[1].replace('**', '').strip()
                puntaje = partes[2].strip()
                justificacion = partes[3].strip()
                cita_transcripcion = partes[4].strip() if len(partes) > 4 else "N/A"
                cita_fuente = partes[5].strip() if len(partes) > 5 else "N/A"

                pdf.set_font('Arial', 'B', 11)
                pdf.set_text_color(0)
                pdf.multi_cell(0, 6, sanitize(criterio_titulo))
                
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(*COLOR_VERDE)
                pdf.multi_cell(0, 6, sanitize(f"Puntaje: {puntaje}"))
                
                pdf.set_font('Arial', '', 10)
                pdf.set_text_color(0)
                pdf.multi_cell(0, 5, sanitize(f"Justificación: {justificacion}"))

                pdf.set_font('Arial', 'I', 9)
                pdf.set_text_color(120)
                if cita_transcripcion and cita_transcripcion != "N/A":
                    pdf.multi_cell(0, 5, sanitize(f"Cita de la Transcripción: {cita_transcripcion}"))
                if cita_fuente and cita_fuente != "N/A":
                     pdf.multi_cell(0, 5, sanitize(f"Cita de la Fuente de Datos: {cita_fuente}"))
                pdf.ln(5)
            continue # Pasar a la siguiente línea después de procesar la fila de la tabla

        # Lógica para renderizar otros tipos de líneas
        # Aplicamos la sanitización a cada línea antes de renderizarla
        line_safe = sanitize(line)

        if line.startswith('### **'): # Encabezado principal
            pdf.set_font('Arial', 'B', 14)
            pdf.set_text_color(*COLOR_AZUL_OSCURO)
            pdf.multi_cell(0, 8, line_safe.replace('### **', '').replace('**', '').strip())
            pdf.ln(4)
        elif line.startswith('**'): # Texto en negrita
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(0)
            pdf.multi_cell(0, 6, line_safe.replace('**', '').strip())
            pdf.ln(1)
        elif line.startswith('* '): # Bullet points
            pdf.set_font('Arial', '', 11)
            pdf.set_text_color(0)
            pdf.cell(5, 5, ' -', 0, 0)
            pdf.multi_cell(0, 5, line_safe[2:].strip())
            pdf.ln(1)
        else: # Párrafos normales
            pdf.set_font('Arial', '', 11)
            pdf.set_text_color(0)
            if line_safe.strip(): # Solo escribir si la línea no está vacía
                pdf.multi_cell(0, 6, line_safe.strip())
                pdf.ln(1)

    # --- Añadir la tabla de resumen al final ---
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(*COLOR_AZUL_OSCURO)
    pdf.cell(0, 10, "Resumen Cuantitativo de Calificaciones", 0, 1, 'L')
    pdf.ln(5)
    
    # Encabezados de la tabla
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(*COLOR_GRIS_OSCURO)
    pdf.set_text_color(255)
    pdf.cell(30, 10, 'Criterio', 1, 0, 'C', True)
    pdf.cell(40, 10, 'Puntuación', 1, 0, 'C', True)
    pdf.cell(120, 10, 'Nivel de Desempeño', 1, 1, 'C', True)
    
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0)
    
    # Contenido de la tabla
    if calificaciones:
        for criterio, nota in sorted(calificaciones.items()):
            if nota <= 4: nivel, color = "Bajo", COLOR_ROJO
            elif nota <= 7: nivel, color = "Medio", COLOR_AMARILLO
            else: nivel, color = "Alto", COLOR_VERDE
            
            pdf.cell(30, 10, criterio, 1, 0, 'C')
            pdf.set_text_color(*color)
            pdf.cell(40, 10, f"{nota} / 10", 1, 0, 'C')
            pdf.set_text_color(0)
            pdf.cell(120, 10, nivel, 1, 1, 'C')

    # Promedio General
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*COLOR_AZUL_OSCURO)
    pdf.cell(0, 10, f"Promedio General Final: {promedio:.2f} / 10.00", 0, 1, 'L')

    # Guardar el archivo PDF
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    pdf.output(ruta_salida)
    print(f"PDF profesional guardado exitosamente en: {ruta_salida}")

