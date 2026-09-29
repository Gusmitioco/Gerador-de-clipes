import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI

load_dotenv()

# ==========================================
# 1. TESTE COM O GEMINI
# ==========================================
def testar_gemini(prompt: str):
    print("\n--- Testando Gemini ---")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Erro: GEMINI_API_KEY não encontrada no .env")
        return

    client = genai.Client(api_key=api_key)
    
    # Configuração que desativa o aviso de AFC (Automatic Function Calling)
    config = types.GenerateContentConfig(
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=config,
    )
    print("Resposta do Gemini:\n", response.text)

# ==========================================
# 2. TESTE COM O HERMES (via OpenRouter)
# ==========================================
def testar_hermes(prompt: str):
    print("\n--- Testando Hermes 3 ---")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Erro: OPENROUTER_API_KEY não encontrada no .env")
        return

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    response = client.chat.completions.create(
        model="nousresearch/hermes-3-llama-3.1-405b",
        messages=[
            {"role": "system", "content": "Você é um assistente focado em automações e dados estruturados."},
            {"role": "user", "content": prompt}
        ]
    )
    print("Resposta do Hermes:\n", response.choices[0].message.content)

if __name__ == "__main__":
    pergunta = "Me dê uma ideia de gancho curto de 3 segundos para um clipe de GTA 6."
    
    testar_gemini(pergunta)
