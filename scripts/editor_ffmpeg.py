#!/usr/bin/env python3
"""
Módulo de Edição e Renderização com FFmpeg
Aplica cortes de alta precisão (-ss, -t), reenquadramento para proporção 9:16 (1080x1920)
com fundo desfocado (blurred background) ou crop central, e queima legendas dinâmicas
estilizadas (estilo TikTok/Shorts) geradas em formato ASS via libass.
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional


def segundos_para_ass_tempo(segundos: float) -> str:
    """Converte segundos float para o formato de tempo do ASS (H:MM:SS.cs)."""
    segundos = max(0.0, segundos)
    m, s = divmod(segundos, 60)
    h, m = divmod(m, 60)
    cs = int(round((s - int(s)) * 100))
    return f"{int(h):d}:{int(m):02d}:{int(s):02d}.{cs:02d}"


def agrupar_palavras_em_linhas(palavras: List[Dict[str, Any]], inicio_corte: float, max_palavras: int = 3) -> List[Dict[str, Any]]:
    """
    Agrupa palavras consecutivas em blocos rápidos (2 a 3 palavras)
    com timestamps relativos ao início do corte para efeito dinâmico.
    """
    blocos = []
    bloco_atual = []

    for p in palavras:
        start_rel = p["start"] - inicio_corte
        end_rel = p["end"] - inicio_corte

        # Pula palavras antes do início do corte
        if end_rel <= 0:
            continue

        start_rel = max(0.0, start_rel)
        bloco_atual.append({
            "word": p["word"],
            "start": start_rel,
            "end": end_rel
        })

        if len(bloco_atual) >= max_palavras:
            inicio_bloco = bloco_atual[0]["start"]
            fim_bloco = bloco_atual[-1]["end"]
            texto_bloco = " ".join([item["word"] for item in bloco_atual]).upper()
            blocos.append({
                "start": inicio_bloco,
                "end": max(inicio_bloco + 0.3, fim_bloco),
                "text": texto_bloco
            })
            bloco_atual = []

    if bloco_atual:
        inicio_bloco = bloco_atual[0]["start"]
        fim_bloco = bloco_atual[-1]["end"]
        texto_bloco = " ".join([item["word"] for item in bloco_atual]).upper()
        blocos.append({
            "start": inicio_bloco,
            "end": max(inicio_bloco + 0.3, fim_bloco),
            "text": texto_bloco
        })

    return blocos


def gerar_arquivo_ass(
    palavras_ou_segmentos: List[Dict[str, Any]],
    caminho_ass: Path,
    inicio_corte: float,
    fim_corte: float,
    config_legenda: Optional[Dict[str, Any]] = None
) -> bool:
    """Gera um arquivo de legendas .ass com estilo moderno, fonte em destaque e contorno preto."""
    cfg = config_legenda or {}
    tamanho_fonte = cfg.get("tamanho_fonte", 52)
    cor_primaria = cfg.get("cor_primaria", "&H0000FFFF")  # Amarelo (&H00BBGGRR)
    cor_borda = cfg.get("cor_borda", "&H00000000")        # Preto
    espessura_borda = cfg.get("espessura_borda", 4)
    posicao = cfg.get("posicao", "centro")

    # Alinhamento ASS: 2 = inferior centro, 5 = centro exato
    alinhamento = 5 if posicao == "centro" else 2
    margin_v = 150 if posicao == "centro" else 420

    cabecalho = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Destaque,DejaVu Sans,{tamanho_fonte},{cor_primaria},&H00FFFFFF,{cor_borda},&H80000000,-1,0,0,0,100,100,0,0,1,{espessura_borda},2,{alinhamento},40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    linhas_dialogo = []

    # Extrai palavras individuais se disponíveis
    todas_palavras = []
    for item in palavras_ou_segmentos:
        if "words" in item and item["words"]:
            for w in item["words"]:
                if inicio_corte <= w["start"] <= fim_corte:
                    todas_palavras.append(w)
        elif "word" in item:
            if inicio_corte <= item["start"] <= fim_corte:
                todas_palavras.append(item)

    if todas_palavras:
        blocos = agrupar_palavras_em_linhas(todas_palavras, inicio_corte, max_palavras=3)
        for b in blocos:
            t_ini = segundos_para_ass_tempo(b["start"])
            t_fim = segundos_para_ass_tempo(b["end"])
            linhas_dialogo.append(f"Dialogue: 0,{t_ini},{t_fim},Destaque,,0,0,0,,{b['text']}")
    else:
        # Fallback para segmentos inteiros caso não haja marcação palavra por palavra
        for s in palavras_ou_segmentos:
            if s.get("end", 0) < inicio_corte or s.get("start", 0) > fim_corte:
                continue
            s_ini = max(0.0, s["start"] - inicio_corte)
            s_fim = min(fim_corte - inicio_corte, s["end"] - inicio_corte)
            if s_fim > s_ini:
                t_ini = segundos_para_ass_tempo(s_ini)
                t_fim = segundos_para_ass_tempo(s_fim)
                texto = s.get("text", "").strip().upper()
                linhas_dialogo.append(f"Dialogue: 0,{t_ini},{t_fim},Destaque,,0,0,0,,{texto}")

    if not linhas_dialogo:
        return False

    conteudo_completo = cabecalho + "\n".join(linhas_dialogo) + "\n"
    caminho_ass.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho_ass, "w", encoding="utf-8") as f:
        f.write(conteudo_completo)

    return True


def escapar_caminho_filtro_ffmpeg(caminho: str) -> str:
    """Escapa caracteres especiais para uso seguro em filtros complexos do FFmpeg no Linux."""
    return caminho.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def montar_filtro_complexo(
    layout_tipo: str = "blurred_background",
    arquivo_ass: Optional[Path] = None,
    largura: int = 1080,
    altura: int = 1920,
    blur_sigma: int = 20
) -> str:
    """
    Constrói a string de filtro do FFmpeg para reenquadramento 9:16.
    Suporta blurred_background (fundo desfocado) e crop_central.
    """
    if layout_tipo == "crop_central":
        # Escala mantendo proporção até preencher altura e corta o centro
        base_filtro = f"[0:v]scale=-2:{altura},crop={largura}:{altura}:(in_w-{largura})/2:0[vbase]"
    else:
        # Padrão: blurred_background (ideal para 16:9 e 4:3 sem cortes bruscos)
        base_filtro = (
            f"[0:v]scale={largura}:{altura}:force_original_aspect_ratio=increase,"
            f"crop={largura}:{altura},boxblur={blur_sigma}:5[bg];"
            f"[0:v]scale={largura}:-2:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[vbase]"
        )

    if arquivo_ass and arquivo_ass.exists():
        ass_escapado = escapar_caminho_filtro_ffmpeg(str(arquivo_ass.resolve()))
        return f"{base_filtro};[vbase]ass='{ass_escapado}'[vout]"
    else:
        return f"{base_filtro};[vbase]null[vout]"


def renderizar_clipe(
    video_origem: str,
    inicio_segundos: float,
    fim_segundos: float,
    pasta_destino_clipe: str,
    nome_arquivo_video: str = "clipe.mp4",
    config_layout: Optional[Dict[str, Any]] = None,
    config_legenda: Optional[Dict[str, Any]] = None,
    segmentos_transcricao: Optional[List[Dict[str, Any]]] = None,
    metadados: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executa o corte e a renderização do clipe em 9:16 com áudio sincronizado.
    Salva o vídeo, o arquivo de legenda .ass e os metadados.json na pasta_destino_clipe.
    """
    caminho_video = Path(video_origem)
    if not caminho_video.is_file():
        raise FileNotFoundError(f"Vídeo de origem não encontrado: {video_origem}")

    pasta_saida = Path(pasta_destino_clipe)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    caminho_saida_video = pasta_saida / nome_arquivo_video
    caminho_ass = pasta_saida / "legenda.ass"
    caminho_metadados = pasta_saida / "metadados.json"

    duracao = max(1.0, fim_segundos - inicio_segundos)
    cfg_lay = config_layout or {}
    tipo_layout = cfg_lay.get("tipo", "blurred_background")
    largura = cfg_lay.get("largura", 1080)
    altura = cfg_lay.get("altura", 1920)
    blur_sigma = cfg_lay.get("blur_sigma", 20)

    # 1. Gera legendas se houver dados de transcrição
    tem_legenda = False
    if segmentos_transcricao and config_legenda and config_legenda.get("ativo", True):
        tem_legenda = gerar_arquivo_ass(
            segmentos_transcricao,
            caminho_ass,
            inicio_segundos,
            fim_segundos,
            config_legenda
        )

    # 2. Monta o filtro complexo do FFmpeg
    filtro_complexo = montar_filtro_complexo(
        layout_tipo=tipo_layout,
        arquivo_ass=caminho_ass if tem_legenda else None,
        largura=largura,
        altura=altura,
        blur_sigma=blur_sigma
    )

    print(f"🎬 Renderizando clipe ({inicio_segundos:.1f}s -> {fim_segundos:.1f}s, dur: {duracao:.1f}s)...")
    print(f"📐 Layout: {tipo_layout} (9:16 - {largura}x{altura}) | Legendas: {'Sim' if tem_legenda else 'Não'}")

    comando = [
        "ffmpeg",
        "-y",
        "-ss", f"{inicio_segundos:.3f}",
        "-t", f"{duracao:.3f}",
        "-i", str(caminho_video),
        "-filter_complex", filtro_complexo,
        "-map", "[vout]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(caminho_saida_video)
    ]

    resultado = subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if resultado.returncode != 0:
        print(f"❌ Erro na renderização com FFmpeg:\n{resultado.stderr}")
        raise RuntimeError("Falha na execução do FFmpeg.")

    # 3. Salva metadados do post
    info_meta = metadados or {}
    dados_finais = {
        "arquivo_video": str(caminho_saida_video.resolve()),
        "arquivo_legenda": str(caminho_ass.resolve()) if tem_legenda else None,
        "inicio_segundos": inicio_segundos,
        "fim_segundos": fim_segundos,
        "duracao_segundos": duracao,
        "titulo": info_meta.get("titulo", "Sem Título"),
        "gancho_3s": info_meta.get("gancho_3s", ""),
        "legenda_post": info_meta.get("legenda_post", ""),
        "hashtags": info_meta.get("hashtags", []),
        "motivo_escolha": info_meta.get("motivo_escolha", "")
    }

    with open(caminho_metadados, "w", encoding="utf-8") as f:
        json.dump(dados_finais, f, ensure_ascii=False, indent=2)

    print(f"✅ Clipe gerado com sucesso: {caminho_saida_video.name}")
    return dados_finais


def main():
    parser = argparse.ArgumentParser(description="Editor e Renderizador de Clipes 9:16 com FFmpeg.")
    parser.add_argument("video", help="Vídeo original a ser cortado.")
    parser.add_argument("--inicio", type=float, required=True, help="Segundo de início do corte.")
    parser.add_argument("--fim", type=float, required=True, help="Segundo de término do corte.")
    parser.add_argument("--saida-pasta", default="saida/teste", help="Pasta onde salvar o clipe.")
    parser.add_argument("--layout", default="blurred_background", choices=["blurred_background", "crop_central"], help="Tipo de reenquadramento 9:16.")
    parser.add_argument("--transcricao", help="Arquivo JSON de transcrição para gerar legendas.")
    args = parser.parse_args()

    segmentos = None
    if args.transcricao and Path(args.transcricao).is_file():
        with open(args.transcricao, "r", encoding="utf-8") as f:
            dados_tr = json.load(f)
            segmentos = dados_tr.get("segmentos", [])

    cfg_layout = {"tipo": args.layout, "largura": 1080, "altura": 1920, "blur_sigma": 20}
    cfg_legenda = {"ativo": True if segmentos else False, "posicao": "centro"}

    try:
        res = renderizar_clipe(
            video_origem=args.video,
            inicio_segundos=args.inicio,
            fim_segundos=args.fim,
            pasta_destino_clipe=args.saida_pasta,
            config_layout=cfg_layout,
            config_legenda=cfg_legenda,
            segmentos_transcricao=segmentos
        )
        print(f"\n🎉 Concluído: {res['arquivo_video']}")
    except Exception as e:
        print(f"❌ Erro: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
