#!/usr/bin/env python3
"""
Módulo de Transcrição Fonética Local
Utiliza faster-whisper otimizado para CPU (AMD Ryzen 5 5600G) em int8
com suporte a timestamps por segmento e palavra por palavra para legendagem.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from faster_whisper import WhisperModel


def segundos_para_tempo_str(segundos: float) -> str:
    """Converte segundos em formato MM:SS ou HH:MM:SS."""
    m, s = divmod(int(segundos), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def transcrever_audio(
    audio_path: str,
    modelo_nome: str = "base",
    idioma: str = "pt",
    forcar_novo: bool = False,
    num_threads: int = 6
) -> Dict[str, Any]:
    """
    Transcreve um arquivo de áudio utilizando faster-whisper na CPU.
    Gera timestamps por segmento e por palavra.
    Salva/reutiliza cache JSON na mesma pasta do áudio.
    """
    caminho_audio = Path(audio_path)
    if not caminho_audio.is_file():
        raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_path}")

    # Arquivo de cache da transcrição
    arquivo_cache = caminho_audio.parent / f"{caminho_audio.stem}_transcricao_{modelo_nome}.json"

    if arquivo_cache.exists() and not forcar_novo:
        print(f"⚡ Carregando transcrição existente do cache: {arquivo_cache.name}")
        with open(arquivo_cache, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"🎙️ Inicializando WhisperModel ('{modelo_nome}', device='cpu', compute_type='int8', threads={num_threads})...")
    model = WhisperModel(
        modelo_nome,
        device="cpu",
        compute_type="int8",
        cpu_threads=num_threads,
        num_workers=2
    )

    print(f"🗣️ Transcrevendo áudio ({caminho_audio.name})... Aguarde.")
    segments, info = model.transcribe(
        str(caminho_audio),
        language=idioma if idioma else None,
        word_timestamps=True,
        beam_size=5,
        vad_filter=True, # Filtra trechos sem voz para acelerar
        vad_parameters=dict(min_silence_duration_ms=500)
    )

    lista_segmentos: List[Dict[str, Any]] = []
    texto_completo = []

    for seg in segments:
        palavras = []
        if seg.words:
            for w in seg.words:
                palavras.append({
                    "word": w.word.strip(),
                    "start": round(w.start, 2),
                    "end": round(w.end, 2),
                    "probability": round(w.probability, 2)
                })

        item_segmento = {
            "id": seg.id,
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "tempo_formatado": f"{segundos_para_tempo_str(seg.start)} - {segundos_para_tempo_str(seg.end)}",
            "text": seg.text.strip(),
            "words": palavras
        }
        lista_segmentos.append(item_segmento)
        texto_completo.append(seg.text.strip())

    resultado = {
        "arquivo_audio": str(caminho_audio.resolve()),
        "idioma": info.language,
        "probabilidade_idioma": round(info.language_probability, 2),
        "duracao_segundos": round(info.duration, 2),
        "modelo": modelo_nome,
        "texto_completo": " ".join(texto_completo),
        "segmentos": lista_segmentos
    }

    # Salva cache
    with open(arquivo_cache, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"💾 Transcrição salva em: {arquivo_cache.name} ({len(lista_segmentos)} segmentos)")
    return resultado


def formatar_transcricao_para_ia(dados_transcricao: Dict[str, Any]) -> str:
    """
    Formata a lista de segmentos em texto com marcações [MM:SS - MM:SS]
    otimizado para o Gemini entender a linha do tempo e encontrar ganchos.
    """
    linhas = []
    for seg in dados_transcricao.get("segmentos", []):
        linhas.append(f"[{seg['start']:06.1f}s -> {seg['end']:06.1f}s] {seg['text']}")
    return "\n".join(linhas)


def main():
    parser = argparse.ArgumentParser(description="Transcreve áudio com faster-whisper e timestamps.")
    parser.add_argument("audio", help="Caminho do arquivo de áudio (ex: entrada/audio.wav).")
    parser.add_argument("--modelo", default="base", choices=["tiny", "base", "small", "medium", "large-v3"], help="Tamanho do modelo.")
    parser.add_argument("--idioma", default="pt", help="Código do idioma (padrão: pt).")
    parser.add_argument("--forcar", action="store_true", help="Força nova transcrição ignorando cache.")
    args = parser.parse_args()

    try:
        dados = transcrever_audio(args.audio, modelo_nome=args.modelo, idioma=args.idioma, forcar_novo=args.forcar)
        print(f"\n✅ Transcrição finalizada com sucesso! Total de segmentos: {len(dados['segmentos'])}")
        print("\n--- Primeiros 5 Segmentos ---")
        for s in dados["segmentos"][:5]:
            print(f"[{s['start']}s -> {s['end']}s] {s['text']}")
    except Exception as e:
        print(f"❌ Erro na transcrição: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
