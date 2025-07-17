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
    
    def sanitize(text):
        """Reemplaza caracteres no soportados para prevenir errores de codificación."""
        return text.replace('•', '-').replace('●', '-').encode('latin-1', 'replace').decode('latin-1')

    # --- Parsear y escribir el informe por secciones ---
    # Usamos regex para encontrar el contenido de cada sección principal
    seccion_identificacion_match = re.search(r'### \*\*1\. Identificación Básica\*\*(.*?)(?=### \*\*2\. Evaluación de la Sesión\*\*)', informe_texto, re.DOTALL)
    seccion_evaluacion_match = re.search(r'### \*\*2\. Evaluación de la Sesión\*\*(.*?)(?=### \*\*3\. Síntesis evaluativa\*\*)', informe_texto, re.DOTALL)
    seccion_sintesis_match = re.search(r'### \*\*3\. Síntesis evaluativa\*\*(.*?)(?=### \*\*4\. Recomendaciones de Mejora\*\*)', informe_texto, re.DOTALL)
    seccion_recomendaciones_match = re.search(r'### \*\*4\. Recomendaciones de Mejora\*\*(.*)', informe_texto, re.DOTALL)

    def render_seccion_texto(titulo_seccion, contenido_match):
        """Función auxiliar para renderizar secciones de texto genéricas."""
        if not contenido_match: return
        
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(*COLOR_AZUL_OSCURO)
        pdf.multi_cell(0, 8, sanitize(titulo_seccion))
        pdf.ln(2)

        for line in contenido_match.group(1).strip().split('\n'):
            line_safe = sanitize(line.strip())
            if not line_safe: continue
            
            # --- INICIO DE LA CORRECCIÓN ---
            # Se simplifica la lógica para manejar viñetas de forma más robusta.
            if line_safe.startswith('* '):
                pdf.set_font('Arial', '', 11)
                pdf.set_text_color(0)
                # Se combina la viñeta y el texto en una sola llamada a multi_cell
                # Se añaden espacios para simular la indentación.
                texto_con_vineta = "    - " + line_safe.lstrip('* ').strip()
                pdf.multi_cell(0, 5, texto_con_vineta)
            # --- FIN DE LA CORRECCIÓN ---
            elif line_safe.startswith('**'):
                pdf.set_font('Arial', 'B', 11)
                pdf.set_text_color(0)
                pdf.multi_cell(0, 6, line_safe.replace('**', ''))
            else:
                pdf.set_font('Arial', '', 11)
                pdf.set_text_color(0)
                pdf.multi_cell(0, 6, line_safe)
        pdf.ln(5)

    # Renderizar las secciones de texto
    render_seccion_texto("1. Identificación Básica", seccion_identificacion_match)
    
    # Renderizar la sección de Evaluación de forma especial
    if seccion_evaluacion_match:
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(*COLOR_AZUL_OSCURO)
        pdf.cell(0, 10, "2. Evaluación de la Sesión", 0, 1, 'L')
        pdf.ln(2)
        
        # Iterar sobre cada línea de la sección de evaluación
        for line in seccion_evaluacion_match.group(1).strip().split('\n'):
            if not line.strip().startswith('| **C'): continue
            
            partes = [p.strip() for p in line.strip('|').split('|')]
            if len(partes) >= 3:
                criterio_titulo = partes[0].replace('**', '').strip()
                puntaje = partes[1].strip()
                justificacion = partes[2].strip()
                
                pdf.set_font('Arial', 'B', 11)
                pdf.set_text_color(0)
                pdf.multi_cell(0, 6, sanitize(criterio_titulo))
                
                pdf.set_font('Arial', '', 10)
                pdf.multi_cell(0, 5, sanitize(f"Puntaje Otorgado: {puntaje}"))
                pdf.multi_cell(0, 5, sanitize(f"Justificación: {justificacion}"))
                pdf.ln(4)

    render_seccion_texto("3. Síntesis Evaluativa", seccion_sintesis_match)
    render_seccion_texto("4. Recomendaciones de Mejora", seccion_recomendaciones_match)

    # --- Añadir la tabla de resumen cuantitativo al final ---
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(*COLOR_AZUL_OSCURO)
    pdf.cell(0, 10, "Resumen Cuantitativo de Calificaciones", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(*COLOR_GRIS_OSCURO)
    pdf.set_text_color(255)
    pdf.cell(30, 10, 'Criterio', 1, 0, 'C', True)
    pdf.cell(40, 10, 'Puntuación', 1, 0, 'C', True)
    pdf.cell(120, 10, 'Nivel de Desempeño', 1, 1, 'C', True)
    
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0)
    
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

    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*COLOR_AZUL_OSCURO)
    pdf.cell(0, 10, f"Promedio General Final: {promedio:.2f} / 10.00", 0, 1, 'L')

    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    pdf.output(ruta_salida)
    print(f"PDF profesional guardado exitosamente en: {ruta_salida}")
