# Projeto: Pipeline Autônomo de Geração e Edição de Clipes com IA

## 1. Visão Geral e Filosofia do Projeto
Pipeline automatizado para processar vídeos longos (curadoria manual do usuário), transcrever áudio com marcações temporais (timestamps), identificar momentos virais/engajantes utilizando Modelos de Linguagem (LLMs), recortar/enquadrar para proporção vertical (9:16) via FFmpeg com legendas estilizadas, e organizar lotes prontos para publicação (estratégia inicial semi-automática para estoque/buffer).

### Papéis no Desenvolvimento
* **Canal Estratégico (Chat Web):** Discussão conceitual, arquitetura, regras de negócio e planejamento das sprints.
* **Canal Operacional (Antigravity IDE):** Execução prática de engenharia, criação de scripts, testes de terminal, depuração e manipulação direta de arquivos no Ubuntu.

---

## 2. Roadmap em Fases

### Fase 1: MVP Local no Ubuntu (Etapa Atual)
* **Objetivo:** Construir o pipeline funcional de ponta a ponta na máquina física (AMD Ryzen 5 5600G, 16 GB RAM).
* **Cérebro Atual:** Gemini Flash / Gemini Flash Lite via API oficial (`google-genai` com chave no `.env`), aproveitando a assinatura e janela de contexto massiva para vídeos longos.
* **Mídia & Transcrição:** `yt-dlp` (download), `faster-whisper` (transcrição local leve na CPU com timestamps), `ffmpeg` (recorte 9:16 e filtros visuais).
* **Modo de Operação:** Semi-automático. O pipeline gera os clipes em pastas organizadas junto com arquivos de metadados (`titulo`, `legenda`, `hashtags`), prontos para revisão rápida e agendamento manual.

### Fase 2: Transição para Ecossistema Próprio & Bot no Discord (Futuro Imediato)
* **Objetivo:** Eliminar dependência de assinaturas de chat e desonerar o computador pessoal.
* **Migração para Nuvem:** Deploy da esteira em uma VPS Linux leve (2-4 vCPUs, 4-8 GB RAM, ~US$ 4-6/mês).
* **Interface via Discord:** Um bot pessoal no Discord gerenciado com `discord.py` com canais dedicados para receber links e comandos de corte do celular ou qualquer lugar.
* **Adoção do Hermes 3:** Substituição/alternância do Gemini para modelos abertos (Hermes 3 via Groq/OpenRouter ou inferência sob demanda *pay-as-you-go*), alcançando custo quase nulo por clipe sem mensalidades fixas.

---

## 3. Especificação dos 3 Nichos / Contas

A arquitetura dos scripts deve ser modular e parametrizada por configurações específicas (`config/{conta}.json`):

1. **Conta 1: Época de Ouro do YouTube BR (2010–2020)**
   * **Conteúdo:** Momentos clássicos, zoeira, desafios e quadros icônicos (ex: Júlio Cocielo, Canal Canalha, Bate ou Regaça, Pânico).
   * **Tratamento Visual:** Resoluções menores e proporção 4:3 tratadas com fundo borrado (*blurred background*) para preencher 9:16 sem achatar o vídeo.
   * **Critério de Corte:** Piadas espontâneas, momentos nostálgicos e impacto cômico.

2. **Conta 2: Conteúdos Diversos / Curiosidades / Histórias**
   * **Conteúdo:** Trechos de podcasts, documentários, curiosidades científicas/históricas.
   * **Tratamento Visual:** Legendas dinâmicas palavra por palavra no centro da tela.
   * **Critério de Corte:** Ganchos imediatos nos primeiros 3 segundos, resolução da curiosidade em até 60 segundos.

3. **Conta 3: GTA 6 e Hype de Games**
   * **Conteúdo:** Trailers, novidades, vazamentos confirmados, análises e, no lançamento, gameplays e momentos inusitados.
   * **Tratamento Visual:** Layout adaptado para gameplay (ex: split screen com câmera no topo e jogo embaixo, ou corte central focado).
   * **Critério de Corte:** Termos de gatilho rápido ("Rockstar", "vazamento", "detalhe", "segredo", "física", "mapa").

---

## 4. Regras de Negócio e Diretrizes de Monetização
* **Conteúdo Transformativo Obrigatório:** Para evitar recusa por "conteúdo reutilizado" (TikTok Creativity Program e YouTube Shorts AdSense), os clipes devem conter edições ativas: zoom dinâmico, ganchos visuais, legendagem estilizada e corte focado.
* **Validação do Buffer:** A geração ocorre em lote para um diretório de saída (`saida/{conta}/`), permitindo inspeção rápida antes de qualquer automação de postagem direta.

---

## 5. Estrutura de Diretórios Alvo

```
gerador_clipes/
├── config/
│   ├── conta_antigos.json
│   ├── conta_diversos.json
│   └── conta_gta6.json
├── entrada/
├── saida/
│   ├── antigos/
│   ├── diversos/
│   └── gta6/
├── scripts/
│   ├── downloader.py       # Baixa vídeo e extrai áudio via yt-dlp
│   ├── transcritor.py      # Transcreve áudio com timestamps via faster-whisper
│   ├── inteligencia.py     # Envia transcrição para o Gemini e obtém cortes em JSON
│   └── editor_ffmpeg.py    # Aplica cortes e filtros 9:16 com ffmpeg
├── .env                    # GEMINI_API_KEY e OPENROUTER_API_KEY
├── CONTEXT.md              # Este arquivo de alinhamento
├── testar_ias.py           # Script de teste de conectividade com APIs
└── main.py                 # Orquestrador CLI (--conta, --link)
```

---

## 6. Estado Atual e Próximas Tarefas (Backlog para a IDE)

### Estado Concluído:
* [x] Ambiente base Ubuntu atualizado com Python 3.12, FFmpeg, Git.
* [x] Ambiente virtual `venv` criado e dependências instaladas (`google-genai`, `openai`, `faster-whisper`, `yt-dlp`, `python-dotenv`).
* [x] Arquivo `.env` configurado com `GEMINI_API_KEY`.
* [x] Validação da API do Gemini testada e aprovada com sucesso via `testar_ias.py`.

### Tarefas Imediatas para o Agente da IDE:
1. **Criar a estrutura de diretórios:** Criar as pastas `config/`, `entrada/`, `saida/` e `scripts/`.
2. **Implementar `scripts/downloader.py`:**
   * Receber uma URL do YouTube.
   * Baixar o vídeo em formato MP4 (qualidade máxima até 1080p).
   * Extrair a faixa de áudio em formato WAV/MP3 leve para alimentar o Whisper.
3. **Implementar `scripts/transcritor.py`:**
   * Carregar o modelo leve do `faster-whisper` (ex: `base` ou `small`) na CPU.
   * Gerar lista de segmentos com `start`, `end` e `text`.
4. **Implementar `scripts/inteligencia.py`:**
   * Enviar os segmentos de texto para o Gemini (via `google-genai`).
   * Usar JSON Schema estrito para forçar o retorno no formato:
     ```json
     {
       "inicio_segundos": 125.0,
       "fim_segundos": 178.0,
       "titulo": "Momento Épico Cocielo",
       "legenda_post": "...",
       "hashtags": ["#nostalgia", "#youtubebr"]
     }
     ```
5. **Implementar `scripts/editor_ffmpeg.py`:**
   * Executar corte preciso com `-ss` e `-to`.
   * Aplicar filtro de reenquadramento vertical 9:16 (com fundo desfocado para vídeos 4:3/antigos).
