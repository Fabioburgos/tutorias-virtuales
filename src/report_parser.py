# src/report_parser.py
import re

def extraer_calificaciones(informe_texto: str) -> tuple[dict, float]:
    """
    Extrae las calificaciones de un informe en formato de tabla Markdown
    generado por Gemini y calcula el promedio.

    Args:
        informe_texto: El texto completo generado por Gemini.

    Returns:
        Una tupla conteniendo:
        - Un diccionario con las calificaciones por criterio (ej. {'C1': 9, 'C2': 10}).
        - El promedio general de las calificaciones.
    """
    print("--- [Parser] Extrayendo calificaciones de la tabla Markdown ---")

    # Expresión regular mejorada para ser más flexible.
    # Busca: | **C<numero>... | <puntaje>/10 |
    # Captura el número del criterio y el número del puntaje en la siguiente celda.
    patron_criterios = re.compile(r"\|\s*\*\*C(\d+).*?\|\s*(\d+)\s*/\s*10\s*\|", re.DOTALL)

    calificaciones = {}
    puntuaciones = []

    for match in patron_criterios.finditer(informe_texto):
        criterio_num = int(match.group(1))
        puntuacion = int(match.group(2))
        
        calificaciones[f"C{criterio_num}"] = puntuacion
        puntuaciones.append(puntuacion)
    
    # También buscamos el promedio final que Gemini calcula
    promedio_match = re.search(r"Promedio General\*\*.*?([\d\.]+)\s*/\s*10", informe_texto)
    if promedio_match:
        promedio = float(promedio_match.group(1))
        print(f"Promedio extraído directamente de la respuesta de Gemini: {promedio:.2f}")
    elif puntuaciones:
        promedio = sum(puntuaciones) / len(puntuaciones)
        print(f"Promedio calculado a partir de las calificaciones encontradas: {promedio:.2f}")
    else:
        print("ADVERTENCIA: No se encontraron calificaciones ni un promedio en el texto.")
        return {}, 0.0

    print(f"Calificaciones extraídas: {calificaciones}")
    
    return calificaciones, promedio
