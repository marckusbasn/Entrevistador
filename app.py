# ==============================================================================
# 1. IMPORTAÇÕES E CONFIGURAÇÕES
# ==============================================================================
import streamlit as st
import google.generativeai as genai
import datetime
import json
import os
import time
import uuid
from github import Github
import random
import re
import google.api_core.exceptions

# Configura as chaves de API a partir dos segredos do Streamlit
# Lembre-se de configurar o arquivo .streamlit/secrets.toml
try:
    genai.configure(api_key=st.secrets["gemini_api_key"])
    GITHUB_TOKEN = st.secrets["github_token"]
    GITHUB_USER = st.secrets["github_user"]
    REPO_NAME = "Entrevistador"
except (KeyError, FileNotFoundError) as e:
    st.error(f"Erro: A chave '{e.args[0]}' não foi encontrada nos segredos do Streamlit. Por favor, configure o arquivo .streamlit/secrets.toml")
    st.stop()


# ==============================================================================
# 2. PROMPT DA IA, MENSAGENS E VARIÁVEIS GLOBAIS
# ==============================================================================
orientacoes_completas = """
# 1. IDENTIDADE E PERSONA
Você é um assistente de pesquisa. Sua personalidade é profissional, neutra e curiosa.

# 2. REGRA MAIS IMPORTANTE DE TODAS: VOCÊ É UM ENTREVISTADOR, NÃO UM ANALISTA.
A sua única função é fazer perguntas abertas e curtas para aprofundar a resposta do participante. NUNCA, em hipótese alguma:
- Dê a sua opinião.
- Analise a resposta do participante.
- Dê conselhos ou soluções.
- Explique a teoria da pesquisa.
- Faça mais de uma pergunta por vez.
Sua única ferramenta é a próxima pergunta.

# 3. OBJETIVO PRINCIPAL
Seu objetivo é conduzir uma entrevista qualitativa breve para compreender como a felt accountability se manifesta no dia a dia da SUBCON/CGM-RJ.

# 4. PROTOCOLOS E REGRAS PRINCIPAIS
PROTOCOLO DE INÍCIO DA CONVERSA: A conversa sempre começará com a minha mensagem de abertura: 'Olá! ... Podemos começar?'. A sua primeira tarefa é analisar a mensagem do usuário que virá logo em seguida.
- Se a resposta do usuário for um consentimento claro (sim, ok, claro, podemos): Responda com uma das PERGUNTAS DE ABERTURA.
- Se a resposta do usuário for uma recusa clara (não, não quero): Responda com a MENSAGEM DE ENCERRAMENTO (que inclui a tag <END_INTERVIEW>).
- Se a resposta do usuário for ambígua ou sem sentido: Responda com a MENSAGEM DE ESCLARECIMENTO.

PROTOCOLO DE ENCERRAMENTO POR CONCLUSÃO: Após sentir que aprofundou suficientemente um ou dois exemplos do participante e a conversa parece estar se tornando circular ou o participante dá respostas curtas, você deve encerrar a entrevista. Para isso, responda com a MENSAGEM DE ENCERRAMENTO e, ao final da sua mensagem, inclua a tag especial <END_INTERVIEW>.

PERGUNTAS DE ABERTURA (Escolha uma aleatoriamente para iniciar a entrevista):
- "Para começarmos, pense no seu dia a dia de trabalho. Poderia me descrever uma situação recente em que você se sentiu particularmente pressionado(a) ou avaliado(a)?"
- "Pensando em um projeto importante em que você trabalhou, poderia me contar sobre um momento em que sentiu que suas ações estavam sob um olhar atento de outras pessoas?"

REGRA DE OURO (FOCO E BREVIDADE): O seu objetivo é uma entrevista curta e profunda de no máximo 5 minutos. Mantenha as suas perguntas e comentários CURTOS e DIRETOS. Assim que encontrar um tema interessante, foque-se nesse tema e aprofunde-o.

PROTOCOLO DE ENCERRAMENTO POR PEDIDO: Apenas inicie este protocolo se o participante fizer um pedido explícito e direto para parar a entrevista (ex: "quero parar", "podemos encerrar"). Se receber um pedido explícito para parar, peça confirmação (ex: "Entendido. Apenas para confirmar, podemos encerrar por aqui?") e só encerre com a MENSAGEM DE ENCERRAMENTO se o participante confirmar.

REGRA 10 (LIDANDO COM EVASIVAS OU DESCONFORTO): Se o participante claramente tenta mudar de assunto ou se recusa a responder, NÃO insista no mesmo tema. Valide a recusa ("Entendido.") e mude para um tópico diferente e mais geral.
"""
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente organizacional onde você exerce suas atividades. Vou fazer-lhe uma pergunta ampla para iniciarmos a conversa e gostaria de ouvir suas reflexões. Lembrando que você pode interromper a entrevista a qualquer momento. Tudo bem? Podemos começar?"
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia! <END_INTERVIEW>"
mensagem_esclarecimento = "Desculpe, não entendi a sua resposta. Poderia apenas confirmar se podemos começar a entrevista, por favor?"

MAP_FILENAME = "mapeamento_seguro.json"


# ==============================================================================
# 3. FUNÇÕES AUXILIARES (PSEUDONIMIZAÇÃO E GITHUB)
# ==============================================================================
def carregar_mapa_pseudonimos():
    if os.path.exists(MAP_FILENAME):
        with open(MAP_FILENAME, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"contador_geral": 0}

def salvar_mapa_pseudonimos(mapa):
    with open(MAP_FILENAME, 'w', encoding='utf-8') as f:
        json.dump(mapa, f, ensure_ascii=False, indent=4)

def pseudonimizar_texto(texto, mapa):
    padroes = {
        'Pessoa': r'\b([A-Z][a-z]+(?: [A-Z][a-z]+)+)\b',
        'Sigla': r'\b(SUBCON|CGM-RJ|[A-Z]{3,})\b',
        'Email': r'[\w\.-]+@[\w\.-]+'
    }
    texto_processado = texto
    for tipo, padrao in padroes.items():
        for entidade in re.findall(padrao, texto_processado):
            if len(entidade) <= 2 or entidade.upper() in ['SIM', 'NAO', 'OK']: continue
            if entidade not in mapa:
                mapa['contador_geral'] += 1
                pseudonimo = f"[{tipo}_{mapa['contador_geral']}]"
                mapa[entidade] = pseudonimo
            texto_processado = texto_processado.replace(entidade, mapa[entidade])
    return texto_processado, mapa

def criar_transcricao_para_github(chat_history, participant_id):
    fuso_horario_br = datetime.timezone(datetime.timedelta(hours=-3))
    timestamp_inicio = chat_history[0]['timestamp'].astimezone(fuso_horario_br).strftime("%d-%m-%Y %H:%M") if chat_history else "N/A"
    texto_formatado = f"ID Anónimo do Participante: {participant_id}\n"
    texto_formatado += f"Transcrição da Entrevista (Pseudonimizada): {timestamp_inicio}\n\n"
    for msg in chat_history:
        role = "Participante" if msg['role'] == 'user' else 'Entrevistador'
        timestamp = msg.get('timestamp', datetime.datetime.now(datetime.timezone.utc)).astimezone(fuso_horario_br).strftime('%H:%M:%S')
        # USA APENAS O CONTEÚDO SEGURO (PSEUDONIMIZADO)
        texto_formatado += f"[{timestamp}] {role}: {msg['content']}\n"
    return texto_formatado

def save_transcript_to_github(chat_history, participant_id):
    if st.session_state.get('transcript_saved', False): return
    try:
        conteudo_formatado = criar_transcricao_para_github(chat_history, participant_id)
        file_path = f"transcricoes/entrevista_{participant_id}.txt"
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
        try:
            contents = repo.get_contents(file_path, ref="main")
            repo.update_file(contents.path, f"Atualizando transcrição para {participant_id}", conteudo_formatado, contents.sha, branch="main")
        except Exception:
            repo.create_file(file_path, f"Adicionando transcrição para {participant_id}", conteudo_formatado, branch="main")
        st.toast("Transcrição salva com sucesso no GitHub.")
        st.session_state.transcript_saved = True
    except Exception as e:
        st.error(f"ATENÇÃO: A transcrição não pôde ser salva no GitHub. Por favor, copie o histórico da conversa manualmente. Erro: {e}")

def stream_handler(stream):
    for chunk in stream:
        try: yield chunk.text
        except Exception: continue

# ==============================================================================
# 4. LÓGICA PRINCIPAL DA APLICAÇÃO STREAMLIT
# ==============================================================================
st.title("Entrevista para Pesquisa")

# Inicialização da sessão
if "messages" not in st.session_state:
    st.session_state.model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=orientacoes_completas)
    st.session_state.messages = []
    st.session_state.interview_over = False
    st.session_state.transcript_saved = False
    st.session_state.participant_id = f"anon_{uuid.uuid4().hex[:8]}"
    st.session_state.start_time = datetime.datetime.now(datetime.timezone.utc)
    st.session_state.messages.append({"role": "model", "content": mensagem_abertura, "timestamp": st.session_state.start_time})

# Exibição do histórico de mensagens
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        conteudo_para_exibir = message.get("original_content", message["content"])
        st.write(conteudo_para_exibir)

# Processamento da entrada do usuário
if prompt := st.chat_input("Sua resposta...", key="chat_input", disabled=st.session_state.get('interview_over', False)):
    mapa = carregar_mapa_pseudonimos()
    texto_pseudonimizado, mapa_atualizado = pseudonimizar_texto(prompt, mapa)
    salvar_mapa_pseudonimos(mapa_atualizado)
    
    st.session_state.messages.append({
        "role": "user", 
        "content": texto_pseudonimizado,
        "original_content": prompt,
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
    })
    
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("Digitando…")
        
        history_for_api = [{'role': ('model' if msg['role'] == 'model' else 'user'), 'parts': [msg['content']]} for msg in st.session_state.messages]
        
        try:
            response_stream = st.session_state.model.generate_content(history_for_api, stream=True)
            text_generator = stream_handler(response_stream)
            full_response_text = placeholder.write_stream(text_generator)
            
            final_text_to_save = full_response_text.replace("<END_INTERVIEW>", "").strip()
            st.session_state.messages.append({"role": "model", "content": final_text_to_save, "timestamp": datetime.datetime.now(datetime.timezone.utc)})

            if "<END_INTERVIEW>" in full_response_text:
                st.session_state.interview_over = True
                save_transcript_to_github(st.session_state.messages, st.session_state.participant_id)
        except Exception as e:
            placeholder.error(f"Ocorreu um erro: {e}")
    st.rerun()

# Botão de encerramento manual
if not st.session_state.get('interview_over', False):
    if st.button("Encerrar Entrevista Manualmente"):
        with st.spinner("Salvando e encerrando..."):
            st.session_state.messages.append({"role": "model", "content": mensagem_encerramento, "timestamp": datetime.datetime.now(datetime.timezone.utc)})
            save_transcript_to_github(st.session_state.messages, st.session_state.participant_id)
            st.session_state.interview_over = True
        st.rerun()
