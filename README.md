# 🎬 Pipeline Autônomo de Geração e Edição de Clipes com IA

Pipeline modular e automatizado para processar vídeos longos (curadoria manual inicial), transcrever áudio com marcações temporais exatas (timestamps), identificar momentos virais com Modelos de Linguagem (LLMs), reenquadrar para o formato vertical (9:16) via FFmpeg com legendas dinâmicas e organizar lotes prontos para publicação semi-automática (buffer/estoque) em múltiplos nichos.

---

## 1. ⚙️ Ambiente e Infraestrutura

- **Sistema Operacional:** Linux Ubuntu (dual-boot)
- **Hardware Host:** AMD Ryzen 5 5600G (6 Núcleos / 12 Threads, Vega 7 integrada), 16 GB RAM DDR4
- **Ambiente de Desenvolvimento:** Google Antigravity IDE (VS Code-based, focado em agentes autônomos)
- **Ambiente Python:** Python 3.12+ isolado em `venv/` (`/home/gusz/automacoes_ia/gerador_clipes/venv`)
- **Papéis no Desenvolvimento:**
  - **Canal Estratégico (Chat Web Gemini):** Discussão conceitual, arquitetura, regras de negócio, estratégias de nicho e planejamento das sprints.
  - **Canal Operacional (Antigravity IDE):** Execução prática de engenharia, criação de scripts, testes de terminal, depuração e manipulação direta de arquivos no Ubuntu.
- **Divisão Arquitetural:**
  - **Local (Braço Operacional):** Ingestão de mídia (`yt-dlp`), transcrição fonética com timestamps (`faster-whisper` otimizado em CPU `int8`), cortes, filtros visuais e renderização (`ffmpeg`).
  - **Nuvem (Cérebro Agêntico):** Curadoria de minutagem, detecção de ganchos (*hooks*) de retenção (primeiros 3 segundos), geração de títulos/legendas e saída estrita em JSON estruturado via Gemini (`gemini-3.5-flash-lite` / `gemini-3.5-flash`) e Hermes 3 (`nousresearch/hermes-3-llama-3.1-405b` via OpenRouter).
  - **Credenciais:** Gerenciadas de forma segura via `.env` (`GEMINI_API_KEY`, `OPENROUTER_API_KEY`).

---

## 2. 🔄 Fluxo do Pipeline (End-to-End)

```mermaid
flowchart TD
    A[Vídeo Longo / URL de Entrada] --> B[yt-dlp: Extração de Mídia e Áudio]
    B --> C[faster-whisper: Transcrição com Timestamps]
    C --> D[LLM: Gemini / Hermes 3 com Saída em JSON]
    D --> E[Filtros de Nicho e Ganchos Virais de 3s]
    E --> F[FFmpeg: Reenquadramento 9:16 + Blurred BG / Split + Legendas]
    F --> G[Saída Estruturada /saida/{conta}/ + metadados.json]
```

1. **Entrada e Ingestão**: Coleta manual de URLs ou arquivos locais de alta qualidade colocados na pasta `entrada/`.
2. **Transcrição de Alta Precisão**: O `faster-whisper` gera a transcrição com marcação temporal palavra a palavra.
3. **Análise de Conteúdo e Roteiro**: A IA analisa o texto, detecta picos de interesse, define o intervalo (30s a 60s) e redige o gancho de abertura.
4. **Renderização Transformativa**: O `ffmpeg` aplica o layout específico de cada nicho (fundo borrado para 4:3, crop focalizado ou split screen) e queima as legendas sincronizadas.
5. **Buffer de Lotes**: Clipes e metadados (`metadados.json` com título, descrição e hashtags) salvos por conta em `saida/`.

---

## 3. 🎯 Especificação dos Três Nichos / Contas

O pipeline é parametrizado por arquivos de configuração JSON (`config/conta_*.json`) para atender três estratégias distintas:

### 📺 Conta 1: Época de Ouro do YouTube BR (2010–2020)
- **Conteúdo:** Momentos clássicos, quadros icônicos, zoeira e desafios (ex: Cocielo, Bate ou Regaça, Canal Canalha).
- **Tratamento Visual:** Tratamento de vídeos antigos (resoluções mais baixas ou formato 4:3) adicionando **fundo borrado (*blurred background*)** para preenchimento harmônico de 9:16 sem distorção.
- **Critério de Corte:** Piadas espontâneas, momentos nostálgicos e frases cômicas de alto impacto.

### 🧠 Conta 2: Conteúdos Diversos / Curiosidades / Histórias
- **Conteúdo:** Trechos de podcasts, documentários, curiosidades científicas e narrativas intrigantes.
- **Tratamento Visual:** Foco em retenção máxima com **legendas dinâmicas palavra por palavra** centralizadas na tela.
- **Critério de Corte:** Ganchos agressivos nos primeiros 3 segundos, introdução de mistério/fato curioso e resolução completa em até 60 segundos.

### 🎮 Conta 3: GTA 6 e Hype de Games
- **Conteúdo:** Análises de trailers, vazamentos confirmados, teorias da comunidade e, pós-lançamento, gameplays e momentos inusitados.
- **Tratamento Visual:** Layout adaptado para gameplay (**split screen** com facecam/reação no topo e gameplay embaixo, ou crop focalizado na ação).
- **Critério de Corte:** Palavras-chave de alto gatilho (*"segredo"*, *"vazamento"*, *"detalhe"*, *"física"*, *"Rockstar"*).

---

## 4. 💰 Diretrizes de Monetização e Conteúdo Transformativo

Para atender aos requisitos de monetização do **TikTok Creativity Program** e **YouTube Shorts AdSense**, evitando punições por *conteúdo reutilizado*:
- **Edição Ativa Obrigatória:** Todo clipe gerado recebe tratamento visual único (reenquadramento, zoom dinâmico, animação de legendas, tratamento de áudio).
- **Ganchos Personalizados:** Adição de títulos e textos de abertura que contextualizam a cena.
- **Fluxo Semi-Automático (Validação Humana Inicial):**
  - O sistema processa os clipes em lote e os organiza em pastas `/saida/{conta}/`.
  - Cada clipe vem acompanhado de seu arquivo `metadados.json`.
  - O usuário faz a revisão de qualidade antes de publicar ou de integrar APIs diretas de upload.

---

## 5. 📁 Estrutura do Repositório

```text
gerador_clipes/
├── config/
│   ├── conta_antigos.json      # Parâmetros visuais e de corte da Conta 1
│   ├── conta_diversos.json     # Parâmetros e legendas da Conta 2
│   └── conta_gta6.json         # Layouts split/gameplay da Conta 3
├── entrada/                    # Vídeos brutos ou listas de URLs a baixar
├── saida/                      # Clipes renderizados prontos para publicação
│   ├── antigos/
│   ├── diversos/
│   └── gta6/
├── scripts/
│   ├── downloader.py           # Ingestão de áudio/vídeo via yt-dlp
│   ├── transcritor.py          # Transcrição com timestamps via faster-whisper
│   ├── inteligencia.py         # Chamadas Gemini / Hermes com saída estrita em JSON
│   └── editor_ffmpeg.py        # Edição visual 9:16, blurred background e legendas
├── .env                        # Chaves de API (GEMINI_API_KEY, OPENROUTER_API_KEY)
├── CONTEXT.md                  # Alinhamento conceitual, fases e especificações
├── GEMINI.md                   # Contexto persistente e diretrizes para o agente Antigravity
├── README.md                   # Documentação mestre do projeto
├── testar_ias.py               # Validação e teste de conexão dos modelos de IA
├── main.py                     # Orquestrador central do pipeline
└── venv/                       # Ambiente virtual Python com dependências instaladas
```

---

## 6. 🚀 Como Configurar e Executar

### 1. Pré-requisitos do Sistema (Ubuntu)
```bash
sudo apt update && sudo apt install -y python3-venv ffmpeg git
```

### 2. Ativação do Ambiente Virtual
```bash
cd ~/automacoes_ia/gerador_clipes
source venv/bin/activate
```

### 3. Configuração do `.env`
Crie ou edite o arquivo `.env` na raiz do projeto:
```env
GEMINI_API_KEY=sua_chave_do_google_gemini
OPENROUTER_API_KEY=sua_chave_do_openrouter
```

### 4. Teste de Conexão com as IAs
```bash
python testar_ias.py
```

---

## 7. 📋 Status Atual e Roadmap

- [x] Ambiente base Ubuntu homologado com `python3`, `ffmpeg` e `git`.
- [x] Ambiente virtual isolado `venv/` com dependências essenciais instaladas (`faster-whisper`, `google-genai`, `openai`, `yt-dlp`, `python-dotenv`).
- [x] Conexão com Google Gemini (`gemini-3.5-flash-lite`) e OpenRouter (Hermes 3) testada e funcional.
- [x] Unificação da arquitetura, diretrizes de nicho e documentação técnica.
- [ ] Criação do módulo `scripts/downloader.py` (download inteligente via `yt-dlp`).
- [ ] Criação do módulo `scripts/transcritor.py` (transcrição local rápida com `faster-whisper`).
- [ ] Criação do módulo `scripts/inteligencia.py` (seleção de momentos virais com output JSON estrito).
- [ ] Criação dos arquivos de configuração por nicho em `config/`.
- [ ] Criação do módulo `scripts/editor_ffmpeg.py` (filtros 9:16, blurred BG e queima de legendas).
- [ ] Implementação do orquestrador `main.py` para execução de ponta a ponta.
