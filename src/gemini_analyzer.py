# src/gemini_analyzer.py

from google import genai
from google.genai import types
import os
import json

def analizar_con_rag_y_citas(project_id: str, location: str, rag_corpus_path: str, ruta_prompt: str, transcripcion_texto: str) -> str:    
    """
    Usa RAG de Vertex AI para analizar una transcripción, cargando el prompt desde un archivo.

    Args:
        project_id: ID de tu proyecto de GCP.
        location: Región de tu proyecto.
        rag_corpus_path: Ruta completa a tu corpus de RAG.
        ruta_prompt: Ruta al archivo .txt que contiene el prompt.
        transcripcion_texto: texto con la transcripcion obtenida.

    Returns:
        El informe generado por Gemini, incluyendo las citas.
    """
    print("--- [Módulo Gemini] Analizando transcripción con apoyo de RAG ---")

    # Inicializar Vertex AI
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
        )
    
    model = "gemini-2.5-pro"
    contents = [
        types.Content(
        role="user",
        parts=[
        ]
        )
    ]
    tools = [
        types.Tool(
        retrieval=types.Retrieval(
            vertex_rag_store=types.VertexRagStore(
            rag_resources=[
                types.VertexRagStoreRagResource(
                rag_corpus=rag_corpus_path
                )
            ],
            )
        )
        )
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature = 0.5,
        top_p = 0.95,
        response_mime_type = "application/json",
        seed = 0,
        max_output_tokens = 65535,
        safety_settings = [types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="OFF"
        ),types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="OFF"
        ),types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="OFF"
        ),types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="OFF"
        )],
        tools = tools,
        thinking_config=types.ThinkingConfig(
        thinking_budget=-1,
        ),
    )

    # Construimos un prompt muy específico para forzar al modelo a basarse solo en el texto.
    try:
        with open(ruta_prompt, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        print(f"Plantilla de prompt cargada desde: {ruta_prompt}")
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de prompt en la ruta: {ruta_prompt}")
        return None
    
    prompt = prompt_template.replace("{transcripcion_texto}", transcripcion_texto)

    text1 = types.Part.from_text(text=prompt)
    
    contents = [
        types.Content(
        role="user",
        parts=[
            text1
        ]
        )
    ]
    
    print("Enviando transcripción y preguntas a Gemini...")
    
    try:
        # Generar la respuesta
        response = client.models.generate_content(
            model = model,
            contents = contents,
            config = generate_content_config,
        )
        print("Respuesta recibida de Gemini.")
        print(response.text)
        
        # Validar que es JSON válido
        resultado_json = json.loads(response.text)
        
        # Si hay citas RAG, agregarlas al JSON
        try:
            citations = response.candidates[0].citation_metadata.citation_sources
            citas_rag = []
            for citation in citations:
                citas_rag.append({
                    "segmento_index": citation.segment_index,
                    "uri": citation.uri,
                    "inicio_index": citation.start_index,
                    "fin_index": citation.end_index
                })
            
            # Agregar las citas al JSON
            resultado_json["informe_evaluacion"]["citas_fuentes_rag"] = citas_rag
            
            # Devolver JSON actualizado
            return json.dumps(resultado_json, indent=2, ensure_ascii=False)
            
        except (AttributeError, IndexError):
            # Sin citas, devolver JSON original
            return response.text
            
    except json.JSONDecodeError:
        print("Error: Gemini no retornó JSON válido")
        return None
    except Exception as e:
        print(f"Ocurrió un error al contactar a la API de Gemini: {e}")
        return None