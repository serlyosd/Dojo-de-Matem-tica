# Dojo da Matemática — fase 1

Prova técnica local de um tutor de matemática com identidade de aventura ninja. Esta entrega testa **texto, leitura de foto e transcrição de áudio**. Ela ainda não implementa o núcleo pedagógico da fase 2.

## O que esta prova faz

- Mostra uma missão matemática curta.
- Recebe resposta digitada, foto (`JPG`, `PNG` ou `WebP`) ou áudio do navegador.
- Usa o Qwen3-VL no Ollama **somente** para transcrever a foto.
- Usa FFmpeg e Vosk **somente** para converter e transcrever o áudio localmente.
- Confere a resposta confirmada com regras Python locais, rápidas e determinísticas.
- Sempre mostra a leitura da foto ou a transcrição em uma caixa editável.
- Só faz a conferência local depois que a pessoa confirma essa leitura.
- Guarda no SQLite apenas a leitura automática, a correção, a análise e as versões.
- Apaga os arquivos temporários de foto e áudio depois do processamento.
- Executa somente uma leitura pesada por vez, com tempo limite e botão de cancelamento.

> **Limite desta entrega:** a análise exibida serve para avaliar a integração técnica. Ela não muda barra de habilidade, não atribui domínio e não constitui diagnóstico.

## Proteção de desempenho

- Respostas digitadas e cálculos simples não iniciam o Ollama.
- Após a confirmação, respostas de texto, foto e áudio usam a mesma conferência Python.
- Foto e áudio compartilham uma única vaga de processamento; uma segunda tentativa recebe uma mensagem para aguardar ou cancelar.
- Foto tem limite padrão de 90 segundos; áudio, 120 segundos.
- O botão **Cancelar tarefa** encerra a requisição ao Ollama ou o processo local do FFmpeg/Vosk.
- Arquivos temporários são removidos mesmo em erro, timeout ou cancelamento.
- O Vosk roda em um processo separado, com uma única thread e áudio limitado a 60 segundos.
- O modelo padrão é o português pequeno `vosk-model-small-pt-0.3`, adequado à prova em um computador com 4 GB de RAM.

## Primeiro uso no Windows

### 1. Instale os programas

Instale:

1. Python 3.12. Marque a opção que adiciona o Python ao sistema.
2. Ollama para Windows.
3. Qwen3-VL no Ollama com o nome `qwen3-vl:4b`.
4. FFmpeg para Windows.

O script de preparação instala a biblioteca Vosk e baixa automaticamente o modelo português pequeno. Nenhum transcritor ou modelo adicional é necessário.

Depois de instalar e abrir o Ollama, execute no **Prompt de Comando**:

```bat
ollama run qwen3-vl:4b
```

Espere o download terminar. Digite `/bye` para sair da conversa de teste.

Os arquivos locais ficarão organizados assim:

```text
Dojo-de-Matem-tica/
├── models/
│   └── vosk-model-small-pt-0.3/
│       ├── final.mdl
│       ├── Gr.fst
│       ├── HCLr.fst
│       ├── mfcc.conf
│       ├── phones
│       ├── word_boundary.int
│       └── ivector/
└── tools/
    └── ffmpeg/
        └── bin/
            └── ffmpeg.exe
```

Se usar outros locais ou nomes, edite somente `scripts\configurar_dojo.bat`.

Os caminhos acima já estão configurados nesse arquivo. Não é preciso alterá-lo quando as pastas forem mantidas como no exemplo.
Essa é a estrutura legada oficial do modelo português. Se a extração criar uma pasta duplicada com o mesmo nome dentro dela, os scripts a normalizam automaticamente. Um modelo válido já existente não é baixado novamente.

### 2. Prepare o aplicativo

Clique duas vezes em:

```text
scripts\preparar_windows.bat
```

Esse passo precisa de internet para baixar as bibliotecas Python. É feito uma vez.

### 3. Verifique os componentes

Abra o Ollama. Depois, clique duas vezes em:

```text
scripts\verificar_windows.bat
```

Leia os itens `PRONTO` e `FALTA`. Não use foto ou áudio pessoal nessa verificação.
Quando alguma ação manual for necessária, o Windows emitirá dois bipes e mostrará somente o próximo passo.

### 4. Inicie

Clique duas vezes em:

```text
scripts\iniciar_dojo.bat
```

O navegador deverá abrir em `http://127.0.0.1:8000`.

Para encerrar, feche a janela preta ou pressione `Ctrl+C` nela.

## Teste real no computador

Faça nesta ordem:

1. Clique em **Verificar componentes**.
2. Teste uma resposta digitada.
3. Envie uma foto fictícia de uma conta.
4. Corrija de propósito um caractere na caixa de confirmação.
5. Abra **Explicar por voz** e clique em **Verificar microfone**.
6. Quando o navegador perguntar, escolha **Permitir**.
7. Grave uma frase curta, ouça e envie.
8. Corrija a transcrição, se necessário, antes de analisar.
9. Anote tempo, erros de leitura e mensagens de falha.

Se o microfone estiver bloqueado, clique no cadeado ao lado do endereço do navegador e altere a permissão do microfone para **Permitir**.
Antes de o navegador abrir a caixa de autorização, a página toca um aviso curto e mostra uma única instrução.

## O que o Codex consegue verificar fora do Windows

O ambiente de desenvolvimento pode verificar código, JavaScript, SQLite e testes simulados. Ele não consegue instalar programas nem autorizar o microfone no seu computador Windows. Também não comprova a velocidade ou a qualidade real dos modelos sem executar no seu equipamento.

Por isso, uma saída `PRONTO` de `scripts\verificar_windows.bat` é necessária antes do teste real. Não envie fotos, áudios ou o arquivo `dojo.db`; basta informar as linhas `PRONTO` e `FALTA` mostradas pelo verificador.

## Dados locais

No Windows, o banco fica em:

```text
%LOCALAPPDATA%\DojoDaMatematica\dojo.db
```

Modelos, banco, fotos e áudios não devem ser enviados ao GitHub. As mídias desta prova são temporárias e são apagadas depois da leitura ou transcrição.

## Testes simulados para desenvolvimento

Os testes automatizados **não avaliam a qualidade real** do Qwen3-VL, do Vosk nem do microfone. Eles usam respostas simuladas para verificar:

- confirmação e correção antes da análise;
- armazenamento mínimo no SQLite;
- remoção de mídia temporária;
- aceitação do áudio WebM gravado pelo navegador;
- comando de conversão para WAV mono de 16 kHz;
- chamada isolada do Vosk com o modelo português pequeno;
- limite de duração, thread única, timeout e cancelamento;
- rejeição de formato de foto não permitido.

Para executá-los:

```bash
python -m pytest
```

## Desenvolvimento local

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Variáveis opcionais:

| Variável | Padrão |
| --- | --- |
| `OLLAMA_URL` | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | `qwen3-vl:4b` |
| `VOSK_MODEL_DIR` | pasta do modelo `vosk-model-small-pt-0.3` |
| `FFMPEG` | `ffmpeg` |
| `DOJO_DATA_DIR` | `%LOCALAPPDATA%\DojoDaMatematica` no Windows; `data/` nos demais sistemas |
| `PHOTO_TIMEOUT_SECONDS` | `90` |
| `AUDIO_TIMEOUT_SECONDS` | `120` |
| `MAX_AUDIO_SECONDS` | `60` |

## Fora do escopo

Não estão nesta fase:

- mapa completo de habilidades;
- investigação pedagógica adaptativa;
- regras de progresso e retenção;
- painel do responsável;
- conquistas e diário;
- backup e restauração;
- instalador único;
- integração com câmera do celular.

Esses itens não devem ser iniciados antes da avaliação desta prova técnica.
