import streamlit as st
import google.generativeai as genai
import os
import faiss
import numpy as np
import pickle
from io import BytesIO
from github import Github
from dotenv import load_dotenv

# --- INSTRUÇÕES PARA ESTA FERRAMENTA ---
st.set_page_config(layout="centered")
st.title("⚙️ Painel de Controlo do Pesquisador")
st.write("Use esta ferramenta para criar ou atualizar a 'memória' do seu chatbot entrevistador. Faça o upload do seu projeto de pesquisa em formato .txt e clique no botão para salvar a memória no GitHub.")
st.warning("Esta ferramenta é apenas para seu uso. Não partilhe o seu link.")

# --- LÓGICA DE INDEXAÇÃO E UPLOAD ---
# Tenta carregar as chaves de um ficheiro .env (para uso local)
try:
    load_dotenv()
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_USER = os.getenv("GITHUB_USER")
    REPO_NAME = os.getenv("REPO_NAME", "Entrevistador") # Usa "Entrevistador" como padrão
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except:
    st.error("Erro ao carregar as chaves do ficheiro .env. Certifique-se de que o ficheiro existe e contém as suas chaves (GITHUB_TOKEN, GITHUB_USER, GEMINI_API_KEY).")
    st.stop()


st.markdown("### Passo 1: Carregue o seu projeto de pesquisa")
uploaded_file = st.file_uploader("Selecione o seu ficheiro `projeto.txt`", type="txt")

if uploaded_file is not None:
    st.success(f"Ficheiro '{uploaded_file.name}' carregado com sucesso!")
    
    st.markdown("### Passo 2: Crie e Salve a Memória")
    if st.button("Criar e Salvar Memória no GitHub"):
        with st.spinner("A processar o documento... Isto pode demorar alguns minutos."):
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
                with open(temp_index_file, "rb") as f:
                    index_bytes = f.read()
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

                st.success("Memória criada e salva com sucesso no seu repositório GitHub!")

            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")
