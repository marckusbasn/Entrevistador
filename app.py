import streamlit as st
import google.generativeai as genai
import datetime
import json
import os
import time
import uuid
from github import Github
import random
import google.api_core.exceptions
import faiss
import numpy as np
import pickle
from io import BytesIO

# --- Configuração do Gemini e GitHub ---
genai.configure(api_key=st.secrets["gemini_api_key"])
GITHUB_TOKEN = st.secrets.get("github_token")
GITHUB_USER = st.secrets.get("github_user")
REPO_NAME = "Entrevistador"

# --- ROTEIRO DA ENTREVISTA E INSTRUÇÕES PARA A IA (PERSONA) ---
orientacoes_completas = """
# 1. IDENTIDADE E PERSONA
Você é um assistente de pesquisa. Sua personalidade é profissional, neutra e curiosa. Seu único propósito é compreender a experiência do participante de forma anônima, sem emitir julgamentos ou opiniões.

# 2. OBJETIVO PRINCIPAL
Seu objetivo é conduzir uma entrevista qualitativa breve para compreender como a felt accountability se manifesta no dia a dia da SUBCON/CGM-RJ.

# 3. CONTEXTO DA PESQUISA (Seu Conhecimento Interno - NÃO REVELE AO PARTICIPANTE)
Sua análise se baseia nos seguintes conceitos-chave:
Expectativa do Indivíduo: Investigar as percepções sobre ter que se justificar (Answerability), a possibilidade de recompensas/sanções (Consequencialidade), a ligação entre a ação e o indivíduo (Atribuibilidade) e a sensação de ser observado (Observabilidade).
Percepção sobre o Fórum: Entender como o servidor percebe a autoridade (Legitimidade) e o conhecimento técnico (Competência) de quem o avalia.

# 4. REGRAS DE COMPORTAMENTO E APROFUNDAMENTO (SUAS DIRETRIZES PRINCIPAIS)
REGRA DE OURO (FOCO E BREVIDADE): O seu objetivo é uma entrevista curta e profunda de no máximo 5 minutos. Mantenha as suas perguntas e comentários CURTOS e DIRETOS. Faça APENAS UMA pergunta de cada vez. Assim que encontrar um tema interessante ou uma tensão na resposta do participante, foque-se nesse tema. Use as suas outras regras para aprofundar ao máximo essa única linha de investigação, em vez de tentar cobrir vários conceitos da pesquisa.

REGRA DE MÁXIMA PRIORIDADE 1 (PROTOCOLO DE ENCERRAMENTO): Se um participante expressar um desejo claro de terminar a entrevista (ex: "quero parar", "pode encerrar"), NÃO o faça imediatamente. Em vez disso, você DEVE pedir uma confirmação de forma educada, por exemplo: "Entendido. Apenas para confirmar, podemos encerrar a entrevista por aqui?". Se, e somente se, o participante confirmar de forma clara, você deve apresentar a MENSAGEM DE ENCERRAMENTO. Se o participante negar, peça desculpa pela interrupção e retome a conversa.

REGRA DE MÁXIMA PRIORIDADE 2 (PEDIDO DE ESCLARECIMENTO): Se o participante pedir um esclarecimento sobre um termo que ele não entendeu, PARE de seguir o roteiro e priorize a resposta a essa dúvida. Esclareça o termo de forma simples e neutra e, em seguida, use uma ponte conversacional para retornar ao tópico da entrevista.

REGRA DE MÁXIMA PRIORIDADE 3 (NUNCA QUEBRE A PERSONA): A sua única função é ser o entrevistador. JAMAIS explique como a resposta de um participante se conecta à teoria da pesquisa. Nunca mencione termos como "dimensão de competência", "análise qualitativa" ou "felt accountability". Use o seu conhecimento interno APENAS para decidir qual a melhor pergunta a fazer em seguida. O seu conhecimento teórico é secreto e nunca deve ser revelado.

REGRA 9: EVITAR PERGUNTAS DUPLAS: Se a sua pergunta tiver mais de uma parte (ex: "Como você reagiria e o que pensaria?"), reformule-a para focar em uma única questão por vez.

(O restante das regras continua o mesmo)
"""

# <<< ALTERAÇÃO AQUI: Vinhetas corrigidas para terem apenas uma pergunta >>>
vinhetas = [
    "Imagine que você precisa entregar um relatório importante com um prazo muito apertado. Sua chefia direta e outros gestores contam com esse trabalho para tomar uma decisão. Um erro ou atraso pode gerar um impacto negativo. Como essa pressão influenciaria sua forma de trabalhar?",
    "Pense que um procedimento que você considera correto e faz de forma consolidada é revisado por um novo gestor ou por outra área. A pessoa questiona seu método, mas você não tem certeza se ela compreende todo o contexto do seu trabalho. Como você reagiria a essa situação?",
    "Imagine um trabalho importante feito em equipe. O resultado final será muito visível para todos na organização. Se for um sucesso, o mérito é do grupo. Se houver uma falha, pode ser difícil apontar um único responsável. Como essa dinâmica de responsabilidade compartilhada afeta sua maneira de atuar?"
]
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente organizacional onde você exerce suas atividades. Vou apresentar uma breve situação e gostaria de ouvir suas reflexões. Lembrando que você pode interromper a entrevista a qualquer momento. Tudo bem? Podemos começar?"
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"

# ==============================================================================
# O RESTANTE DO CÓDIGO PERMANECE EXATAMENTE O MESMO
# O código completo e funcional está abaixo para copiar e colar
# ==============================================================================

def pagina_configuracao():
    st.title("⚙️ Painel de Controlo do Pesquisador")
    st.write("Use esta ferramenta para criar ou atualizar a 'memória' do seu chatbot. Faça o upload do seu projeto de pesquisa em formato .txt e clique no botão para salvar a memória no GitHub.")
    st.warning("Esta página só é visível para si através do link especial com `?admin=true`.")
    uploaded_file = st.file_uploader("Selecione o seu ficheiro `projeto.txt`", type="txt")
    if uploaded_file is not None:
        st.success(f"Ficheiro '{uploaded_file.name}' carregado com sucesso!")
        if st.button("Criar e Salvar Memória no GitHub"):
            with st.spinner("A processar o documento..."):
                try:
                    document_text = uploaded_file.getvalue().decode("utf-8")
                    text_chunks = [chunk for chunk in document_text.split('\n\n') if chunk.strip()]
                    embedding_model = 'models/embedding-001'
                    embeddings = genai.embed_content(model=embedding_model, content=text_chunks, task_type="retrieval_document")
                    embeddings_np = np.array(embeddings['embedding']).astype('float32')
                    d = embeddings_np.shape[1]
                    index = faiss.IndexFlatL2(d)
                    index.add(embeddings_np)
                    temp_index_file = "temp_faiss_index.bin"
                    faiss.write_index(index, temp_index_file)
                    with open(temp_index_file, "rb") as f: index_bytes = f.read()
                    os.remove(temp_index_file)
                    g = Github(GITHUB_TOKEN)
                    repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
                    def upload_or_update_file(file_path, commit_message, content):
                        try:
                            contents = repo.get_contents(file_path)
                            repo.update_file(contents.path, commit_message, content, contents.sha, branch="main")
                            st.write(f"Ficheiro '{file_path}' atualizado no GitHub.")
                        except:
                            repo.create_file(file_path, commit_message, content, branch="main")
                            st.write(f"Ficheiro '{file_path}' criado no GitHub.")
                    upload_or_update_file("faiss_index.bin", "Atualizando índice FAISS", index_bytes)
                    chunks_bytes = pickle.dumps(text_chunks)
                    upload_or_update_file("text_chunks.pkl", "Atualizando pedaços de texto", chunks_bytes)
                    st.success("Memória criada e salva com sucesso!")
                    st.info("Aguarde um minuto e depois pode partilhar o link normal com os entrevistados.")
                    st.cache_resource.clear()
                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")

def pagina_entrevistador():
    @st.cache_resource
    def carregar_memoria_pesquisa_do_github():
        try:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
            index_content = repo.get_contents("faiss_index.bin").decoded_content
            temp_index_file = "temp_faiss_index_load.bin"
            with open(temp_index_file, "wb") as f: f.write(index_content)
            index = faiss.read_index(temp_index_file)
            os.remove(temp_index_file)
            chunks_content = repo.get_contents("text_chunks.pkl").decoded_content
            chunks = pickle.loads(chunks_content)
            return index, chunks
        except Exception: return None, None

    def classificar_intencao(prompt_utilizador):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt_classificador = f"Analise a seguinte frase de um utilizador: '{prompt_utilizador}'.\nO utilizador está a fazer uma pergunta sobre a pesquisa ou está a responder a uma pergunta da entrevista?\nResponda APENAS com a palavra 'PESQUISA' ou 'ENTREVISTA'."
        try:
            response = model.generate_content(prompt_classificador)
            return response.text.strip()
        except Exception: return "ENTREVISTA"

    def responder_pergunta_pesquisa(index, chunks, pergunta):
        embedding_model = 'models/embedding-001'
        pergunta_embedding = genai.embed_content(model=embedding_model, content=pergunta, task_type="retrieval_query")['embedding']
        k = 3
        D, I = index.search(np.array([pergunta_embedding]).astype('float32'), k)
        contexto_relevante = " ".join([chunks[i] for i in I[0]])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt_final = f"Com base no seguinte contexto extraído do projeto de pesquisa:\n---\n{contexto_relevante}\n---\nPor favor, responda à seguinte pergunta do utilizador de forma clara e concisa: \"{pergunta}\""
        response = model.generate_content(prompt_final, stream=True)
        return response

    def stream_handler(stream):
        for chunk in stream:
            try: yield chunk.text
            except Exception: continue
    
    def formatar_para_nvivo(chat_history):
        timestamp_inicio = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
        texto_formatado = f"Transcrição da Entrevista: {timestamp_inicio}\n\n"
        for msg in chat_history[1:]:
            role = "Participante" if msg['role'] == 'user' else 'Entrevistador'
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            texto_formatado += f"[{timestamp}] {role}: {msg['content']}\n"
        return texto_formatado

    def save_transcript_to_github(chat_history):
        try:
            conteudo_formatado = formatar_para_nvivo(chat_history)
            unique_id = uuid.uuid4()
            file_path = f"transcricoes/entrevista_{unique_id}.txt"
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
            repo.create_file(file_path, f"Adicionando transcrição da entrevista {unique_id}", conteudo_formatado, branch="main")
            st.session_state.transcript_saved = True
            return True
        except Exception as e:
            print(f"Erro ao salvar no GitHub: {e}")
            return False

    st.title("Felt Accountability no Setor Público - Entrevista")
    index, chunks = carregar_memoria_pesquisa_do_github()

    if "model" not in st.session_state:
        st.session_state.model = None
        st.session_state.messages = []
        st.session_state.interview_over = False 
        st.session_state.transcript_saved = False
        st.session_state.messages.append({"role": "model", "content": mensagem_abertura})

    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.write(message["content"])

    if prompt := st.chat_input("Sua resposta...", key="chat_input", disabled=st.session_state.interview_over):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)

        with st.chat_message("assistant"):
            if st.session_state.model is None:
                negative_responses = ["não", "nao", "não quero", "nao quero", "não, obrigado", "nao, obrigado"]
                if prompt.lower().strip() in negative_responses:
                    st.write(mensagem_encerramento)
                    st.session_state.messages.append({"role": "model", "content": mensagem_encerramento})
                    st.session_state.interview_over = True
                    if not st.session_state.get('transcript_saved'):
                        save_transcript_to_github(st.session_state.messages)
                else:
                    st.session_state.model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=orientacoes_completas)
                    vinheta_escolhida = random.choice(vinhetas)
                    st.session_state.messages.append({"role": "model", "content": vinheta_escolhida})
            else:
                placeholder = st.empty()
                placeholder.markdown("Digitando…")
                intencao = classificar_intencao(prompt)
                
                try:
                    if intencao == "PESQUISA" and index is not None:
                        response_stream = responder_pergunta_pesquisa(index, chunks, prompt)
                    else:
                        start_index = 0
                        for i, msg in enumerate(st.session_state.messages):
                            if msg['content'] in vinhetas: start_index = i; break
                        relevant_messages = st.session_state.messages[start_index:]
                        history_for_api = [{'role': ('model' if msg['role'] == 'model' else 'user'), 'parts': [msg['content']]} for msg in relevant_messages]
                        response_stream = st.session_state.model.generate_content(history_for_api, stream=True)
                    
                    text_generator = stream_handler(response_stream)
                    full_response_text = placeholder.write_stream(text_generator)
                    st.session_state.messages.append({"role": "model", "content": full_response_text})

                    if mensagem_encerramento in full_response_text and not st.session_state.get('transcript_saved'):
                        st.session_state.interview_over = True
                        save_transcript_to_github(st.session_state.messages)
                except Exception as e:
                    placeholder.error(f"Ocorreu um erro: {e}")
        
        st.rerun()

    if st.button("Encerrar Entrevista"):
        with st.spinner("Salvando e encerrando..."):
            st.session_state.messages.append({"role": "model", "content": mensagem_encerramento})
            if not st.session_state.get('transcript_saved'):
                save_transcript_to_github(st.session_state.messages)
            st.write(mensagem_encerramento)
            st.session_state.interview_over = True
        time.sleep(1) 
        st.rerun()

if st.query_params.get("admin") == "true":
    pagina_configuracao()
else:
    pagina_entrevistador()
