# src/doc_reader.py
import docx

def leer_texto_de_docx(ruta_archivo: str) -> str:
    """
    Lee todo el texto de un archivo .docx y lo devuelve como un solo string.

    Args:
        ruta_archivo: La ruta al archivo .docx local.

    Returns:
        Un string con el contenido de texto del documento, o None si ocurre un error.
    """
    try:
        documento = docx.Document(ruta_archivo)
        texto_completo = []
        for parrafo in documento.paragraphs:
            texto_completo.append(parrafo.text)
        
        # Unimos todos los párrafos con un salto de línea
        return '\n'.join(texto_completo)
    except Exception as e:
        print(f"Ocurrió un error al leer el archivo .docx: {e}")
        return None
