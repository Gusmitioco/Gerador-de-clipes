# Diretrizes e Contexto do Projeto: Pipeline Autônomo de Geração e Edição de Clipes com IA

Este arquivo serve como contexto persistente para os agentes Antigravity neste projeto.

## Divisão de Papéis no Desenvolvimento
* **Canal Estratégico (Chat Web Gemini)**: O usuário utiliza o chat web para tirar dúvidas conceituais, refinar a arquitetura, regras de negócio, estratégia dos nichos e organizar o planejamento do projeto.
* **Canal Operacional (Antigravity IDE - Você)**: Responsável por botar a mão na massa e colocar o projeto em prática — engenharia de software, criação e edição de scripts Python, execução de comandos no terminal Ubuntu, depuração, automação FFmpeg e testes de integração.

## Contexto do Repositório & Hardware Host
- **Objetivo**: Automação ponta a ponta para geração de clipes curtos verticais (9:16) para TikTok, YouTube Shorts e Instagram Reels a partir de vídeos longos usando IA.
- **Hardware Host**: AMD Ryzen 5 5600G (6C/12T, Vega 7 integrada), 16 GB RAM DDR4. Processamento local de Whisper e FFmpeg deve ser otimizado para CPU (`faster-whisper` com `compute_type="int8"`).
- **Ambiente Virtual**: `venv/` (ativar com `source venv/bin/activate`).
- **Python**: 3.12+ no Ubuntu.

## Roadmap em Fases
- **Fase 1: MVP Local no Ubuntu (Etapa Atual)**:
  - Pipeline funcional de ponta a ponta na máquina física (AMD Ryzen 5 5600G, 16 GB RAM).
  - Cérebro Atual: Gemini Flash / Flash Lite via SDK oficial `google-genai` (chave no `.env`).
  - Mídia & Transcrição: `yt-dlp` (download), `faster-whisper` (transcrição local na CPU com timestamps `int8`), `ffmpeg` (recorte 9:16 e filtros).
  - Modo: Semi-automático (gera clipes em pastas de buffer por nicho com metadados para revisão rápida).
- **Fase 2: Nuvem Própria & Bot Discord (Futuro Imediato)**:
  - Deploy em VPS Linux leve (2-4 vCPUs, 4-8 GB RAM).
  - Bot no Discord (`discord.py`) para receber links/comandos remotos pelo celular.
  - Alternância/adoção de Hermes 3 via OpenRouter/Groq para custo quase nulo por clipe sem mensalidade fixa.

## Arquitetura e Pilha de Tecnologias
1. **Download & Extração**: `scripts/downloader.py` utilizando `yt-dlp` (MP4 até 1080p, extração de áudio WAV/MP3 leve).
2. **Transcrição Fonética Local**: `scripts/transcritor.py` com `faster-whisper` (modelo `small`/`base`, int8, gerando timestamps por palavra/segmentos).
3. **Curadoria e Ganchos com IA**: `scripts/inteligencia.py`:
   - Google Gemini via SDK `google-genai` (`gemini-3.5-flash-lite` / `gemini-3.5-flash`).
   - JSON Schema estrito para cortes: início/fim em segundos, título, legenda do post, hashtags.
4. **Editor de Vídeo & Renderização**: `scripts/editor_ffmpeg.py` executando cortes precisos com `-ss`/`-to`, filtros 9:16 (blurred background para 4:3, split screen para gameplay) e legendas dinâmicas via `ffmpeg`.
5. **Orquestrador**: `main.py` consumindo parâmetros das contas em `config/conta_*.json` e link/vídeo de entrada.

## Regras de Negócio e Nichos
1. **Conta 1 (Época de Ouro BR 2010-2020)**: Zoeira e nostalgia (Cocielo, Canal Canalha, Bate ou Regaça, Pânico). Fundo borrado (*blurred background*) para vídeos antigos/4:3 sem distorção.
2. **Conta 2 (Curiosidades / Histórias / Podcasts)**: Retenção máxima. Ganchos imediatos nos primeiros 3 segundos, legendas dinâmicas palavra por palavra no centro, conclusão em até 60s.
3. **Conta 3 (GTA 6 e Games)**: Layout gameplay (split screen ou crop focado). Filtrar por gatilhos ("Rockstar", "vazamento", "detalhe", "segredo", "física", "mapa").
4. **Monetização & Conteúdo Transformativo**: Edições ativas obrigatórias (enquadramento, zoom dinâmico, legendagem, tratamento visual) para atender diretrizes de monetização (TikTok Creativity Program / YouTube Shorts).

## Tarefas Imediatas da IDE (Backlog de Implementação)
1. Criar a estrutura de diretórios (`config/`, `entrada/`, `saida/`, `scripts/`).
2. Implementar `scripts/downloader.py`.
3. Implementar `scripts/transcritor.py`.
4. Implementar `scripts/inteligencia.py`.
5. Criar arquivos de configuração `config/conta_antigos.json`, `config/conta_diversos.json`, `config/conta_gta6.json`.
6. Implementar `scripts/editor_ffmpeg.py`.
7. Montar o fluxo integrado no `main.py`.
