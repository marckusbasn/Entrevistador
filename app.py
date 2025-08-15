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

# --- Configuração do Gemini e GitHub (CHAVE SEGURA AQUI) ---
genai.configure(api_key=st.secrets["gemini_api_key"])
GITHUB_TOKEN = st.secrets["github_token"]
GITHUB_USER = st.secrets["github_user"]
REPO_NAME = "Entrevistador" # O nome do seu repositório

# --- ROTEIRO DA ENTREVISTA E INSTRUÇÕES PARA A IA (PERSONA) ---
# (O seu texto longo de orientacoes_completas permanece aqui, omitido por brevidade)
orientacoes_completas = """
# 1. IDENTIDADE E PERSONA
Você é um assistente de pesquisa...
"""
vinhetas = [
    "Imagine que você precisa entregar um relatório importante...",
    "Pense que um procedimento que você considera correto...",
    "Imagine um trabalho importante feito em equipe..."
]
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa..."
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções..."

# ==============================================================================
# PÁGINA 2: CONFIGURAÇÃO DA MEMÓRIA (LÓGICA DE INDEXAÇÃO)
# ==============================================================================
def pagina_configuracao():
    st.title("⚙️ Configuração da Memória da Pesquisa")
    st.write("Aqui você pode 'ensinar' o chatbot sobre a sua pesquisa. Ele usará esta informação para responder a perguntas sobre o projeto durante a entrevista.")

    st.markdown("### Passo 1: Carregue o seu projeto de pesquisa")
    uploaded_file = st.file_uploader("Selecione o seu ficheiro `projeto.txt`", type="txt")

    if uploaded_file is not None:
        st.success(f"Ficheiro '{uploaded_file.name}' carregado com sucesso!")
        
        st.markdown("### Passo 2: Crie e Salve a Memória")
        if st.button("Criar e Salvar Memória no GitHub"):
            with st.spinner("A processar o documento e a criar a memória... Isto pode demorar alguns minutos."):
                try:
                    # Lê o conteúdo do ficheiro carregado
                    document_text = uploaded_file.getvalue().decode("utf-8")
                    text_chunks = [chunk for chunk in document_text.split('\n\n') if chunk.strip()]
                    
                    # Gera os embeddings
                    embedding_model = 'models/embedding-001'
                    embeddings = genai.embed_content(model=embedding_model, content=text_chunks, task_type="retrieval_document")
                    embeddings_np = np.array(embeddings['embedding']).astype('float32')
                    
                    # Cria o índice FAISS
                    d = embeddings_np.shape[1]
                    index = faiss.IndexFlatL2(d)
                    index.add(embeddings_np)
                    
                    # Conecta-se ao GitHub
                    g = Github(GITHUB_TOKEN)
                    user = g.get_user(GITHUB_USER)
                    repo = user.get_repo(REPO_NAME)
                    
                    # Salva o índice FAISS no GitHub
                    index_bytes = BytesIO()
                    faiss.write_index(index, faiss.PyCallbackIOVecWriter(index_bytes.write))
                    repo.create_file("faiss_index.bin", "Adicionando/atualizando índice FAISS", index_bytes.getvalue(), branch="main")

                    # Salva os pedaços de texto no GitHub
                    chunks_bytes = pickle.dumps(text_chunks)
                    repo.create_file("text_chunks.pkl", "Adicionando/atualizando pedaços de texto", chunks_bytes, branch="main")

                    st.success("Memória criada e salva com sucesso no seu repositório GitHub!")
                    st.info("Pode agora ir para a página 'Entrevistador'. A aplicação irá reiniciar para carregar a nova memória.")
                    time.sleep(5)
                    st.rerun()

                except Exception as e:
                    # Verifica se o erro é porque os ficheiros já existem
                    if "sha" in str(e):
                         st.warning("A memória parece já existir. Se quiser atualizá-la, por favor, apague os ficheiros 'faiss_index.bin' and 'text_chunks.pkl' do seu repositório GitHub e tente novamente.")
                    else:
                        st.error(f"Ocorreu um erro: {e}")

# ==============================================================================
# PÁGINA 1: ENTREVISTADOR (LÓGICA DO CHAT)
# ==============================================================================
def pagina_entrevistador():
    st.title("Felt Accountability no Setor Público - Entrevista")

    # --- Funções do Chat ---
    @st.cache_resource
    def carregar_memoria_pesquisa_do_github():
        try:
            g = Github(GITHUB_TOKEN)
            user = g.get_user(GITHUB_USER)
            repo = user.get_repo(REPO_NAME)
            
            index_content = repo.get_contents("faiss_index.bin").decoded_content
            index_bytes = BytesIO(index_content)
            index = faiss.read_index(faiss.PyCallbackIOVecReader(index_bytes.read, index_bytes.tell, index_bytes.seek))

            chunks_content = repo.get_contents("text_chunks.pkl").decoded_content
            chunks = pickle.loads(chunks_content)
            
            return index, chunks
        except Exception as e:
            # Se não encontrar os ficheiros, não é um erro, apenas a memória não foi criada.
            st.sidebar.warning("A memória da pesquisa ainda não foi criada. O chatbot só poderá conduzir a entrevista. Para ativar as respostas sobre a pesquisa, vá à página de 'Configuração da Memória'.")
            return None, None

    def classificar_intencao(prompt_utilizador):
        # (código sem alterações)
        pass

    def responder_pergunta_pesquisa(index, chunks, pergunta):
        # (código sem alterações)
        pass
    
    def stream_handler(stream):
        # (código sem alterações)
        pass

    def save_transcript_to_github(chat_history):
        # (código sem alterações)
        pass

    # --- Lógica Principal da Aplicação ---
    index, chunks = carregar_memoria_pesquisa_do_github()

    if "model" not in st.session_state:
        st.session_state.model = None
        st.session_state.messages = []
        st.session_state.interview_over = False 
        st.session_state.messages.append({"role": "model", "content": mensagem_abertura})

    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.write(message["content"])

    if prompt := st.chat_input("Sua resposta...", key="chat_input", disabled=st.session_state.interview_over):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            if st.session_state.model is None:
                # (Lógica de início e consentimento, sem alterações)
                pass
            else:
                placeholder = st.empty()
                placeholder.markdown("Digitando…")
                
                intencao = classificar_intencao(prompt)
                
                try:
                    if intencao == "PESQUISA" and index is not None:
                        # (lógica RAG sem alterações)
                        pass
                    else:
                        # (lógica da entrevista sem alterações)
                        pass
                except Exception as e:
                    placeholder.error(f"Ocorreu um erro: {e}")

    if st.button("Encerrar Entrevista"):
        # (código sem alterações)
        pass

# ==============================================================================
# ESTRUTURA PRINCIPAL DA APLICAÇÃO COM BARRA LATERAL
# ==============================================================================
st.sidebar.title("Navegação")
pagina_selecionada = st.sidebar.radio("Selecione uma página:", ["Entrevistador", "Configuração da Memória"])

if pagina_selecionada == "Entrevistador":
    pagina_entrevistador()
else:
    pagina_configuracao()
