#!/usr/bin/env python3
"""
Módulo de Download e Extração de Mídia
Responsável por baixar vídeos do YouTube (via yt-dlp) ou receber arquivos locais,
extraindo uma faixa de áudio otimizada (WAV mono 16kHz) para o faster-whisper.
"""

import os
import sys
import re
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import yt_dlp


def sanitizar_nome_arquivo(nome: str, max_len: int = 60) -> str:
    """Remove caracteres especiais e espaços para nomes de arquivos seguros no Linux."""
    nome_limpo = re.sub(r'[\\/*?:"<>|]', "", nome)
    nome_limpo = re.sub(r"\s+", "_", nome_limpo.strip())
    # Remove emojis e caracteres fora do padrão comum
    nome_limpo = re.sub(r"[^\w\-_.]", "", nome_limpo)
    return nome_limpo[:max_len]


def extrair_audio_16k_mono(video_path: Path, audio_path: Path) -> bool:
    """
    Extrai o áudio do vídeo no formato WAV PCM 16kHz mono.
    Este é o formato nativo e mais rápido para consumo pelo faster-whisper.
    """
    print(f"🎵 Extraindo áudio otimizado para Whisper: {audio_path.name}...")
    comando = [
        "ffmpeg",
        "-y",               # Sobrescreve sem perguntar
        "-i", str(video_path),
        "-vn",              # Sem vídeo
        "-acodec", "pcm_s16le",
        "-ar", "16000",     # 16 kHz
        "-ac", "1",         # Mono
        str(audio_path)
    ]
    
    resultado = subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    if resultado.returncode != 0:
        print(f"❌ Erro ao extrair áudio com FFmpeg:\n{resultado.stderr}")
        return False
        
    return True


def baixar_ou_preparar_video(origem: str, pasta_destino: str = "entrada") -> Dict[str, Any]:
    """
    Baixa o vídeo se 'origem' for URL ou valida o arquivo se for caminho local.
    Extrai o áudio otimizado (WAV 16kHz mono) para a transcrição.

    Retorna um dicionário com:
        - id
        - titulo
        - duracao_segundos
        - video_path
        - audio_path
        - canal (se disponível)
    """
    caminho_destino = Path(pasta_destino)
    caminho_destino.mkdir(parents=True, exist_ok=True)

    # 1. Caso seja arquivo local existente
    origem_path = Path(origem)
    if origem_path.is_file():
        print(f"📁 Processando arquivo local: {origem_path.resolve()}")
        nome_base = origem_path.stem
        audio_path = caminho_destino / f"{nome_base}_audio_16k.wav"

        # Obter duração via ffprobe
        cmd_dur = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(origem_path)
        ]
        duracao = 0.0
        try:
            res_dur = subprocess.run(cmd_dur, stdout=subprocess.PIPE, text=True, check=True)
            duracao = float(res_dur.stdout.strip())
        except Exception:
            duracao = 0.0

        if not audio_path.exists():
            if not extrair_audio_16k_mono(origem_path, audio_path):
                raise RuntimeError("Falha ao extrair áudio do arquivo local.")
        else:
            print(f"ℹ️ Áudio já existente em cache: {audio_path.name}")

        return {
            "id": nome_base,
            "titulo": nome_base.replace("_", " "),
            "duracao_segundos": duracao,
            "video_path": str(origem_path.resolve()),
            "audio_path": str(audio_path.resolve()),
            "canal": "Local",
        }

    # 2. Caso seja URL do YouTube / Web
    print(f"🌐 Extraindo informações do vídeo: {origem}...")
    ydl_opts_info = {
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        try:
            info = ydl.extract_info(origem, download=False)
        except Exception as e:
            raise RuntimeError(f"Não foi possível obter dados da URL: {e}")

    video_id = info.get("id", "video")
    titulo_bruto = info.get("title", "video_sem_titulo")
    titulo_sanitizado = sanitizar_nome_arquivo(titulo_bruto)
    duracao_segundos = float(info.get("duration", 0.0))
    canal = info.get("uploader", "Desconhecido")

    nome_arquivo_video = f"{video_id}_{titulo_sanitizado}.mp4"
    video_path = caminho_destino / nome_arquivo_video
    audio_path = caminho_destino / f"{video_id}_{titulo_sanitizado}_audio_16k.wav"

    # Se o vídeo já foi baixado previamente, pula o download
    if not video_path.exists():
        print(f"📥 Baixando vídeo: {titulo_bruto} (Duração: {duracao_segundos:.0f}s)...")
        ydl_opts_download = {
            # Qualidade máxima até 1080p, preferindo MP4 (h264/aac)
            "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "merge_output_format": "mp4",
            "outtmpl": str(caminho_destino / f"{video_id}_{titulo_sanitizado}.%(ext)s"),
            "quiet": False,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            ydl.download([origem])
    else:
        print(f"ℹ️ Vídeo já encontrado em disco: {video_path.name}")

    # Garante a extração do áudio 16kHz mono para o Whisper
    if not audio_path.exists():
        if not extrair_audio_16k_mono(video_path, audio_path):
            raise RuntimeError("Falha ao extrair áudio com FFmpeg após download.")
    else:
        print(f"ℹ️ Áudio já disponível em cache: {audio_path.name}")

    return {
        "id": video_id,
        "titulo": titulo_bruto,
        "duracao_segundos": duracao_segundos,
        "video_path": str(video_path.resolve()),
        "audio_path": str(audio_path.resolve()),
        "canal": canal,
    }


def main():
    parser = argparse.ArgumentParser(description="Baixa vídeo do YouTube e extrai áudio para o Whisper.")
    parser.add_argument("origem", help="URL do YouTube ou caminho de arquivo local.")
    parser.add_argument("--saida", default="entrada", help="Pasta onde salvar os arquivos baixados.")
    args = parser.parse_args()

    try:
        dados = baixar_ou_preparar_video(args.origem, args.saida)
        print("\n✅ Concluído com sucesso!")
        print(f"📌 Título: {dados['titulo']}")
        print(f"⏱️ Duração: {dados['duracao_segundos']:.1f} segundos")
        print(f"🎬 Vídeo: {dados['video_path']}")
        print(f"🎧 Áudio Whisper: {dados['audio_path']}")
    except Exception as e:
        print(f"❌ Erro: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
