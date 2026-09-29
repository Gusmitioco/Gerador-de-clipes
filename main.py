#!/usr/bin/env python3
"""
Orquestrador Principal do Pipeline Autônomo de Geração de Clipes
Coordena o fluxo completo:
1. Ingestão e Download (yt-dlp)
2. Transcrição Fonética Local (faster-whisper int8 na CPU)
3. Curadoria e Detecção de Ganchos com IA (Gemini / Hermes 3)
4. Edição e Renderização 9:16 com Legendas Dinâmicas (FFmpeg)
5. Organização em Lotes (saida/{conta}/[lote]/) com metadados.json
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Importação dos módulos do pipeline
from scripts.downloader import baixar_ou_preparar_video, sanitizar_nome_arquivo
from scripts.transcritor import transcrever_audio
from scripts.inteligencia import selecionar_clipes
from scripts.editor_ffmpeg import renderizar_clipe


def carregar_config_conta(identificador_conta: str) -> Dict[str, Any]:
    """Carrega as diretrizes do nicho a partir do arquivo config/conta_{id}.json."""
    caminho = Path(identificador_conta)
    if not caminho.is_file():
        caminho = Path(f"config/conta_{identificador_conta}.json")

    if not caminho.is_file():
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado para '{identificador_conta}'. "
            f"Verifique se existe config/conta_{identificador_conta}.json"
        )

    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def executar_pipeline(
    origem: str,
    id_conta: str,
    modelo_whisper: str = "base",
    provedor_ia: str = "gemini",
    max_clipes: Optional[int] = None,
    renderizar: bool = True,
    com_legendas: bool = True
) -> Dict[str, Any]:
    """Executa o pipeline completo de ponta a ponta."""
    print("=" * 65)
    print("🚀 INICIANDO PIPELINE DE GERAÇÃO DE CLIPES VERTICAIS (9:16)")
    print("=" * 65)

    # 1. Carrega configuração da conta
    config_conta = carregar_config_conta(id_conta)
    if max_clipes:
        config_conta["max_clipes"] = max_clipes

    print(f"🎯 Conta Alvo: {config_conta['nome']} (ID: {config_conta['id_conta']})")
    print(f"📁 Pasta de Saída Base: {config_conta['pasta_saida']}")

    # 2. Ingestão de mídia
    print("\n--- ETAPA 1: Ingestão de Vídeo e Extração de Áudio ---")
    dados_midia = baixar_ou_preparar_video(origem, pasta_destino="entrada")
    print(f"✔️ Vídeo pronto: {dados_midia['video_path']}")
    print(f"✔️ Áudio 16kHz pronto: {dados_midia['audio_path']}")

    # 3. Transcrição fonética
    print("\n--- ETAPA 2: Transcrição Fonética Local (faster-whisper) ---")
    inicio_transc = time.time()
    dados_transcricao = transcrever_audio(
        audio_path=dados_midia["audio_path"],
        modelo_nome=modelo_whisper,
        idioma="pt"
    )
    tempo_transc = time.time() - inicio_transc
    print(f"✔️ Transcrição concluída em {tempo_transc:.1f}s ({len(dados_transcricao['segmentos'])} segmentos identificados).")

    # 4. Curadoria com IA
    print("\n--- ETAPA 3: Curadoria e Ganchos com IA ---")
    config_temp_path = f"config/conta_{config_conta['id_conta']}.json"
    clipes_selecionados = selecionar_clipes(
        dados_transcricao=dados_transcricao,
        caminho_config_conta=config_temp_path,
        provedor=provedor_ia
    )

    if not clipes_selecionados:
        print("⚠️ Nenhum clipe foi retornado pela IA.")
        return {"sucesso": False, "mensagem": "Nenhum clipe selecionado."}

    # 5. Renderização dos cortes via FFmpeg
    clipes_gerados = []
    if not renderizar:
        print("\nℹ️ Modo somente curadoria ativado (--somente-curadoria). Renderização pulada.")
        return {
            "sucesso": True,
            "midia": dados_midia,
            "clipes_propostos": clipes_selecionados
        }

    print("\n--- ETAPA 4: Edição e Renderização 9:16 com FFmpeg ---")
    pasta_base_saida = Path(config_conta.get("pasta_saida", f"saida/{id_conta}"))
    timestamp_lote = datetime.now().strftime("%Y%m%d_%H%M%S")

    cfg_layout = config_conta.get("layout", {"tipo": "blurred_background", "largura": 1080, "altura": 1920})
    cfg_legenda = config_conta.get("legendas", {"ativo": True, "posicao": "centro"})
    if not com_legendas:
        cfg_legenda["ativo"] = False

    for idx, clipe in enumerate(clipes_selecionados, 1):
        slug_titulo = sanitizar_nome_arquivo(clipe["titulo"], max_len=40)
        pasta_clipe = pasta_base_saida / f"{timestamp_lote}_clipe_{idx}_{slug_titulo}"
        pasta_clipe.mkdir(parents=True, exist_ok=True)

        print(f"\n🎬 Processando [{idx}/{len(clipes_selecionados)}]: {clipe['titulo']}")
        print(f"⏱️ Intervalo: {clipe['inicio_segundos']:.1f}s até {clipe['fim_segundos']:.1f}s (Duração: {clipe['duracao_estimada']:.1f}s)")
        print(f"🎯 Gancho 3s: {clipe['gancho_3s']}")

        resultado_render = renderizar_clipe(
            video_origem=dados_midia["video_path"],
            inicio_segundos=float(clipe["inicio_segundos"]),
            fim_segundos=float(clipe["fim_segundos"]),
            pasta_destino_clipe=str(pasta_clipe),
            nome_arquivo_video="clipe.mp4",
            config_layout=cfg_layout,
            config_legenda=cfg_legenda,
            segmentos_transcricao=dados_transcricao.get("segmentos", []),
            metadados=clipe
        )

        clipes_gerados.append(resultado_render)

    # 6. Relatório final
    print("\n" + "=" * 65)
    print("🎉 PIPELINE FINALIZADO COM SUCESSO!")
    print(f"📦 Total de Clipes Prontos: {len(clipes_gerados)}")
    print(f"📁 Localização: {pasta_base_saida.resolve()}")
    print("=" * 65)
    for i, c in enumerate(clipes_gerados, 1):
        print(f"\n[{i}] {c['titulo']}")
        print(f"   🎥 Vídeo: {c['arquivo_video']}")
        print(f"   📝 Legenda do post: {c['legenda_post']}")
        print(f"   🏷️ Tags: {' '.join(c['hashtags'])}")

    return {
        "sucesso": True,
        "clipes": clipes_gerados,
        "pasta_saida": str(pasta_base_saida.resolve())
    }


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline Autônomo de Geração de Clipes 9:16 com IA."
    )
    parser.add_argument(
        "--conta",
        required=True,
        choices=["antigos", "diversos", "gta6"],
        help="Identificador da conta / nicho (antigos, diversos, gta6)."
    )
    grupo_origem = parser.add_mutually_exclusive_group(required=True)
    grupo_origem.add_argument("--link", help="URL do vídeo no YouTube.")
    grupo_origem.add_argument("--arquivo", help="Caminho de arquivo de vídeo local.")

    parser.add_argument(
        "--modelo-whisper",
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Modelo do faster-whisper na CPU (padrão: base)."
    )
    parser.add_argument(
        "--provedor",
        default="gemini",
        choices=["gemini", "hermes"],
        help="Provedor de inteligência artificial (padrão: gemini)."
    )
    parser.add_argument(
        "--max-clipes",
        type=int,
        default=None,
        help="Quantidade máxima de clipes a gerar."
    )
    parser.add_argument(
        "--somente-curadoria",
        action="store_true",
        help="Executa download e curadoria da IA sem renderizar o vídeo final."
    )
    parser.add_argument(
        "--sem-legenda",
        action="store_true",
        help="Renderiza o clipe sem queimar legendas dinâmicas."
    )

    args = parser.parse_args()
    origem = args.link if args.link else args.arquivo

    try:
        executar_pipeline(
            origem=origem,
            id_conta=args.conta,
            modelo_whisper=args.modelo_whisper,
            provedor_ia=args.provedor,
            max_clipes=args.max_clipes,
            renderizar=not args.somente_curadoria,
            com_legendas=not args.sem_legenda
        )
    except Exception as e:
        print(f"\n❌ ERRO NO PIPELINE: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
