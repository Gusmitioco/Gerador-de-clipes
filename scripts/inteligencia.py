#!/usr/bin/env python3
"""
Módulo de Inteligência e Curadoria com IA
Responsável por analisar a transcrição com timestamps e selecionar os melhores
momentos de corte (gancho, clímax e desfecho) respeitando as regras do nicho.
Utiliza a API oficial do Google Gemini com saída estrita em JSON Schema (Pydantic).
Também suporta fallback/alternância para Hermes 3 via OpenRouter.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Carrega variáveis de ambiente
load_dotenv()


# ========================================================
# Modelos Pydantic para Validação Estrita do Retorno da IA
# ========================================================
class ClipeProposto(BaseModel):
    inicio_segundos: float = Field(
        ...,
        description="Segundo exato de início do corte no vídeo, alinhado com o início de uma frase."
    )
    fim_segundos: float = Field(
        ...,
        description="Segundo exato de fim do corte no vídeo, com conclusão de raciocínio."
    )
    duracao_estimada: float = Field(
        ...,
        description="Duração em segundos calculada (fim_segundos - inicio_segundos)."
    )
    titulo: str = Field(
        ...,
        description="Título altamente chamativo, com gatilho de curiosidade ou impacto (máx 60 caracteres)."
    )
    gancho_3s: str = Field(
        ...,
        description="Frase impactante ou resumo do gatilho para os primeiros 3 segundos."
    )
    legenda_post: str = Field(
        ...,
        description="Legenda pronta para publicação em redes sociais (TikTok, Shorts, Reels) com gancho e CTA."
    )
    hashtags: List[str] = Field(
        ...,
        description="Lista de 5 a 8 hashtags relevantes para o nicho (começando com #)."
    )
    motivo_escolha: str = Field(
        ...,
        description="Explicação breve de por que este trecho tem alto potencial de retenção e viralização."
    )


class RespostaCuradoria(BaseModel):
    clipes: List[ClipeProposto] = Field(
        ...,
        description="Lista dos melhores clipes selecionados pela IA ordenados por potencial de engajamento."
    )


def montar_prompt_curadoria(
    transcricao_formatada: str,
    config_conta: Dict[str, Any],
    duracao_total_video: float
) -> str:
    """Monta o prompt estruturado com todas as regras de nicho e monetização."""
    crit = config_conta.get("criterios_ia", {})
    dur_min = config_conta.get("duracao_min_segundos", 25)
    dur_max = config_conta.get("duracao_max_segundos", 60)
    max_clipes = config_conta.get("max_clipes", 3)
    nicho = crit.get("nicho", "Geral")
    publico = crit.get("publico_alvo", "Geral")
    gatilhos = "\n  - " + "\n  - ".join(crit.get("gatilhos_corte", ["Momentos marcantes"]))
    regras_gancho = crit.get("regras_gancho", "Gancho forte nos primeiros 3 segundos.")
    hashtags_sugeridas = ", ".join(crit.get("hashtags_padrao", []))

    prompt = f"""
Você é um editor sênior de redes sociais especializado em retenção, viralização e monetização de vídeos verticais (TikTok, YouTube Shorts e Instagram Reels).

SEU OBJETIVO:
Analisar a transcrição com marcações temporais de um vídeo de {duracao_total_video:.1f} segundos e selecionar EXATAMENTE os {max_clipes} melhores clipes independentes para o seguinte nicho:

=== PERFIL DA CONTA E NICHO ===
- Nicho: {nicho}
- Público-Alvo: {publico}
- Gatilhos de Corte Prioritários:
{gatilhos}
- Regra de Gancho: {regras_gancho}
- Hashtags de Referência: {hashtags_sugeridas}

=== REGRAS OBRIGATÓRIAS DE CORTE ===
1. DURAÇÃO: Cada clipe DEVE ter entre {dur_min} e {dur_max} segundos.
2. SENTIDO COMPLETO: Nunca comece ou termine o corte no meio de uma palavra ou pensamento incompleto. O corte deve ter começo (gancho), meio (desenvolvimento) e fim (desfecho/clímax).
3. TIMESTAMPS EXATOS: Baseie-se nos timestamps fornecidos na transcrição (formato [segundos -> segundos]).
4. NÃO SOBREPOSIÇÃO: Os clipes não devem se sobrepor no tempo.
5. CONTEÚDO TRANSFORMATIVO: O título e a legenda do post devem contextualizar o momento para gerar curiosidade imediata e comentários.

=== TRANSCRIÇÃO COM TIMESTAMPS ===
{transcricao_formatada}
"""
    return prompt.strip()


def curar_clipes_gemini(
    prompt: str,
    api_key: Optional[str] = None,
    modelo: str = "gemini-3.5-flash-lite"
) -> RespostaCuradoria:
    """Executa a curadoria usando Google Gemini com Schema JSON estrito."""
    from google import genai
    from google.genai import types

    chave = api_key or os.getenv("GEMINI_API_KEY")
    if not chave:
        raise ValueError("Chave GEMINI_API_KEY não encontrada no .env ou parâmetros.")

    client = genai.Client(api_key=chave)

    print(f"🤖 Solicitando curadoria ao Gemini ({modelo})...")
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=RespostaCuradoria,
        temperature=0.2, # Baixa temperatura para precisão nos timestamps
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )

    response = client.models.generate_content(
        model=modelo,
        contents=prompt,
        config=config
    )

    if not response.text:
        raise RuntimeError("Gemini retornou resposta vazia.")

    # Converte o JSON estruturado diretamente para o modelo Pydantic
    dados_json = json.loads(response.text)
    return RespostaCuradoria.model_validate(dados_json)


def curar_clipes_hermes(
    prompt: str,
    api_key: Optional[str] = None,
    modelo: str = "nousresearch/hermes-3-llama-3.1-405b"
) -> RespostaCuradoria:
    """Executa a curadoria usando Hermes 3 via OpenRouter."""
    from openai import OpenAI

    chave = api_key or os.getenv("OPENROUTER_API_KEY")
    if not chave:
        raise ValueError("Chave OPENROUTER_API_KEY não encontrada no .env ou parâmetros.")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=chave
    )

    print(f"🦹 Solicitando curadoria ao Hermes 3 via OpenRouter ({modelo})...")
    sistema = (
        "Você é um editor profissional de vídeos virais. Responda SOMENTE um JSON válido "
        "seguindo estritamente a estrutura solicitada, sem nenhum markdown ou texto explicativo extra."
    )

    response = client.chat.completions.create(
        model=modelo,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": sistema},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    conteudo = response.choices[0].message.content
    dados_json = json.loads(conteudo)
    return RespostaCuradoria.model_validate(dados_json)


def selecionar_clipes(
    dados_transcricao: Dict[str, Any],
    caminho_config_conta: str,
    provedor: str = "gemini"
) -> List[Dict[str, Any]]:
    """
    Função principal de curadoria.
    Recebe a transcrição, carrega o arquivo de configuração da conta
    e chama a IA para retornar a lista de cortes validados.
    """
    config_path = Path(caminho_config_conta)
    if not config_path.is_file():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {caminho_config_conta}")

    with open(config_path, "r", encoding="utf-8") as f:
        config_conta = json.load(f)

    # Formata transcrição com marcações de tempo
    linhas = []
    for seg in dados_transcricao.get("segmentos", []):
        linhas.append(f"[{seg['start']:.1f}s -> {seg['end']:.1f}s] {seg['text']}")
    transcricao_formatada = "\n".join(linhas)

    duracao_total = float(dados_transcricao.get("duracao_segundos", 0.0))
    prompt = montar_prompt_curadoria(transcricao_formatada, config_conta, duracao_total)

    if provedor == "hermes":
        resposta = curar_clipes_hermes(prompt)
    else:
        try:
            resposta = curar_clipes_gemini(prompt)
        except Exception as e:
            print(f"⚠️ Erro ao chamar Gemini: {e}")
            if os.getenv("OPENROUTER_API_KEY"):
                print("🔄 Tentando fallback para Hermes 3 via OpenRouter...")
                resposta = curar_clipes_hermes(prompt)
            else:
                raise e

    clipes_dict = [c.model_dump() for c in resposta.clipes]
    print(f"✨ IA selecionou com sucesso {len(clipes_dict)} clipes candidatos!")
    return clipes_dict


def main():
    parser = argparse.ArgumentParser(description="Curadoria de clipes com IA a partir da transcrição.")
    parser.add_argument("transcricao", help="Arquivo JSON de transcrição gerado pelo transcritor.")
    parser.add_argument("--config", required=True, help="Arquivo de configuração da conta (ex: config/conta_antigos.json).")
    parser.add_argument("--provedor", default="gemini", choices=["gemini", "hermes"], help="Provedor de IA.")
    args = parser.parse_args()

    try:
        with open(args.transcricao, "r", encoding="utf-8") as f:
            dados_trans = json.load(f)

        clipes = selecionar_clipes(dados_trans, args.config, provedor=args.provedor)
        print("\n--- Clipes Selecionados ---")
        for i, c in enumerate(clipes, 1):
            print(f"\n[Clipe {i}] {c['titulo']}")
            print(f"⏱️ Intervalo: {c['inicio_segundos']}s até {c['fim_segundos']}s (Duração: {c['duracao_estimada']:.1f}s)")
            print(f"🎯 Gancho 3s: {c['gancho_3s']}")
            print(f"🏷️ Hashtags: {' '.join(c['hashtags'])}")
    except Exception as e:
        print(f"❌ Erro na curadoria: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
