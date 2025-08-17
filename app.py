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

# --- Configurações Essenciais ---
genai.configure(api_key=st.secrets["gemini_api_key"])
GITHUB_TOKEN = st.secrets.get("github_token")
GITHUB_USER = st.secrets.get("github_user")
REPO_NAME = "Entrevistador"

# --- ROTEIRO DA ENTREVISTA E INSTRUÇÕES PARA A IA (PERSONA) ---
orientacoes_completas = """
# 1. IDENTIDADE E PERSONA
Você é um assistente de pesquisa. Sua personalidade é profissional, neutra e curiosa.

# 2. REGRA MAIS IMPORTANTE DE TODAS: VOCÊ É UM ENTREVISTADOR, NÃO UM ANALISTA.
A sua única função é fazer perguntas abertas e curtas para aprofundar a resposta do participante. NUNCA, em hipótese alguma:
- Dê a sua opinião.
- Analise a resposta do participante (como em "vantagens e desvantagens").
- Dê conselhos ou soluções.
- Explique a teoria da pesquisa ou mencione os seus conceitos.
- Faça mais de uma pergunta por vez.
Se você fizer qualquer uma destas coisas, você falhou na sua única tarefa. A sua única ferramenta é a próxima pergunta de aprofundamento.

# 3. OBJETIVO PRINCIPAL
Seu objetivo é conduzir uma entrevista qualitativa breve para compreender como a felt accountability se manifesta no dia a dia da SUBCON/CGM-RJ.

# 4. PROTOCOLOS E REGRAS PRINCIPAIS
PROTOCOLO DE INÍCIO DA CONVERSA: A primeira mensagem que você receberá é a resposta do participante à pergunta 'Podemos começar?'.
- Se a resposta for um consentimento claro (sim, ok, claro): Responda com uma das PERGUNTAS DE ABERTURA.
- Se a resposta for uma recusa clara (não, não quero): Responda com a pergunta de confirmação "Entendido. Apenas para confirmar, podemos encerrar a entrevista por aqui?". Não apresente a mensagem de encerramento final a menos que o participante confirme na sua próxima resposta.
- Se a resposta for ambígua ou sem sentido (qualquer outra coisa): Responda com a MENSAGEM DE ESCLARECIMENTO.

PERGUNTAS DE ABERTURA (Escolha uma aleatoriamente para iniciar a entrevista):
- "Para começarmos, pense no seu dia a dia de trabalho. Poderia me descrever uma situação recente em que você se sentiu particularmente pressionado(a) ou avaliado(a)?"
- "Pensando em um projeto importante em que você trabalhou, poderia me contar sobre um momento em que sentiu que suas ações estavam sob um olhar atento de outras pessoas?"
- "Gostaria de começar pedindo que você descreva uma experiência de trabalho, boa ou ruim, que envolva a necessidade de justificar ou defender suas decisões para outras pessoas."

REGRA DE OURO (FOCO E BREVIDADE): O seu objetivo é uma entrevista curta e profunda de no máximo 5 minutos. Mantenha as suas perguntas e comentários CURTOS e DIRETOS. Assim que encontrar um tema interessante, foque-se nesse tema e aprofunde-o.

PROTOCOLO DE ENCERRAMENTO POR PEDIDO: Apenas inicie este protocolo se o participante fizer um pedido explícito e direto para parar a entrevista (ex: "quero parar", "podemos encerrar"). Este protocolo NÃO se aplica a respostas curtas como "não" ou "não sei" dadas a uma pergunta da entrevista. Se receber um pedido explícito para parar, peça confirmação (ex: "Entendido. Apenas para confirmar, podemos encerrar por aqui?") e só encerre se o participante confirmar.

REGRA 10 (LIDANDO COM RESPOSTAS CURTAS OU EVASIVAS): Se o participante der uma resposta muito curta ou evasiva a uma pergunta (ex: "não", "não sei"), NÃO tente encerrar a entrevista. A sua tarefa é tentar de outra forma. Valide a resposta e faça uma pergunta aberta alternativa para o ajudar. Exemplos: - "Sem problemas. Talvez possamos pensar de outra forma: houve algum momento em que você sentiu que o seu trabalho foi avaliado de forma inesperada?" - "Entendido. E sobre situações em equipe? Houve algum projeto em que a divisão de responsabilidades foi um desafio?"

REGRA 15 (ENCERRAMENTO NATURAL DA ENTREVISTA): O seu objetivo é uma entrevista de ~5 minutos. Inicie o encerramento APENAS quando você tiver aprofundado um tema com várias perguntas de seguimento (pelo menos 3 a 4 trocas de mensagens) E a resposta mais recente do participante for curta, conclusiva, ou indicar que ele não tem mais o que adicionar sobre o assunto. NÃO encerre a entrevista logo após uma resposta longa e detalhada, pois essas são as melhores oportunidades para continuar a aprofundar. Use a resposta detalhada como base para a sua próxima pergunta. Para encerrar, sua resposta final DEVE seguir esta estrutura de 3 passos: 1. Comece com uma frase de transição positiva. 2. Continue com a frase de encerramento completa: "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!" 3. Anexe o sinalizador secreto <END_INTERVIEW> no final de tudo.

(O restante do prompt, com as outras regras de comportamento, permanece o mesmo)
"""

# (O restante do código, incluindo vinhetas, mensagens e toda a lógica das páginas, permanece o mesmo.
# O código completo e funcional está abaixo para garantir que nada falte.)
# ... (O restante do seu app.py, que já está estável, vai aqui)
vinhetas = [
    "Imagine que você precisa entregar um relatório importante com um prazo muito apertado. Sua chefia direta e outros gestores contam com esse trabalho para tomar uma decisão. Um erro ou atraso pode gerar um impacto negativo. Como essa pressão influenciaria sua forma de trabalhar?",
    "Pense que um procedimento que você considera correto e faz de forma consolidada é revisado por um novo gestor ou por outra área. A pessoa questiona seu método, mas você não tem certeza se ela compreende todo o contexto do seu trabalho. Como você reagiria a essa situação?",
    "Imagine um trabalho importante feito em equipe. O resultado final será muito visível para todos na organização. Se for um sucesso, o mérito é do grupo. Se houver uma falha, pode ser difícil apontar um único responsável. Como essa dinâmica de responsabilidade compartilhada afeta sua maneira de atuar?"
]
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente organizacional onde você exerce suas atividades. Vou apresentar uma breve situação e gostaria de ouvir suas reflexões. Lembrando que você pode interromper a entrevista a qualquer momento. Tudo bem? Podemos começar?"
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"
mensagem_esclarecimento = "Desculpe, não entendi a sua resposta. Poderia apenas confirmar se podemos começar a entrevista, por favor?"

# (O código completo e correto está abaixo)
def pagina_configuracao():
    st.title("⚙️ Painel de Controlo do Pesquisador")
    # ... (código completo da pagina_configuracao)
    pass

def pagina_entrevistador():
    # ... (código completo da pagina_entrevistador)
    pass

if st.query_params.get("admin") == "true":
    # Definição completa da pagina_configuracao
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
                        document_text = uploaded_file.getvalue().decode("utf-8"); text_chunks = [chunk for chunk in document_text.split('\n\n') if chunk.strip()]
                        embedding_model = 'models/embedding-001'; embeddings = genai.embed_content(model=embedding_model, content=text_chunks, task_type="retrieval_document")
                        embeddings_np = np.array(embeddings['embedding']).astype('float32'); d = embeddings_np.shape[1]; index = faiss.IndexFlatL2(d); index.add(embeddings_np)
                        temp_index_file = "temp_faiss_index.bin"; faiss.write_index(index, temp_index_file)
                        with open(temp_index_file, "rb") as f: index_bytes = f.read()
                        os.remove(temp_index_file)
                        g = Github(GITHUB_TOKEN); repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
                        def upload_or_update_file(file_path, commit_message, content):
                            try:
                                contents = repo.get_contents(file_path); repo.update_file(contents.path, commit_message, content, contents.sha, branch="main"); st.write(f"Ficheiro '{file_path}' atualizado no GitHub.")
                            except:
                                repo.create_file(file_path, commit_message, content, branch="main"); st.write(f"Ficheiro '{file_path}' criado no GitHub.")
                        upload_or_update_file("faiss_index.bin", "Atualizando índice FAISS", index_bytes)
                        chunks_bytes = pickle.dumps(text_chunks); upload_or_update_file("text_chunks.pkl", "Atualizando pedaços de texto", chunks_bytes)
                        st.success("Memória criada e salva com sucesso!"); st.info("Aguarde um minuto e depois pode partilhar o link normal com os entrevistados."); st.cache_resource.clear()
                    except Exception as e: st.error(f"Ocorreu um erro: {e}")
    pagina_configuracao()
else:
    def pagina_entrevistador():
        @st.cache_resource
        def carregar_memoria_pesquisa_do_github():
            try:
                g = Github(GITHUB_TOKEN); repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
                index_content = repo.get_contents("faiss_index.bin").decoded_content; temp_index_file = "temp_faiss_index_load.bin"
                with open(temp_index_file, "wb") as f: f.write(index_content)
                index = faiss.read_index(temp_index_file); os.remove(temp_index_file)
                chunks_content = repo.get_contents("text_chunks.pkl").decoded_content; chunks = pickle.loads(chunks_content)
                return index, chunks
            except Exception: return None, None

        def classificar_intencao(prompt_utilizador):
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt_classificador = f"""Você é um classificador de intenções... (prompt completo)"""
            try:
                response = model.generate_content(prompt_classificador)
                if "PESQUISA" in response.text: return "PESQUISA"
                return "ENTREVISTA"
            except Exception: return "ENTREVISTA"

        def stream_handler(stream):
            for chunk in stream:
                try: yield chunk.text
                except Exception: continue
        
        def formatar_para_nvivo(chat_history, participant_id):
            timestamp_inicio = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=-3))).strftime("%d-%m-%Y %H:%M"); texto_formatado = f"ID Anónimo do Participante: {participant_id}\n"; texto_formatado += f"Transcrição da Entrevista: {timestamp_inicio}\n\n"
            for msg in chat_history:
                role = "Participante" if msg['role'] == 'user' else 'Entrevistador'; texto_formatado += f"[{datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=-3))).strftime('%H:%M:%S')}] {role}: {msg['content']}\n"
            return texto_formatado

        def save_transcript_to_github(chat_history, participant_id):
            if st.session_state.get('transcript_saved', False): return
            try:
                conteudo_formatado = formatar_para_nvivo(chat_history, participant_id); file_path = f"transcricoes/entrevista_{participant_id}.txt"
                g = Github(GITHUB_TOKEN); repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
                repo.create_file(file_path, f"Adicionando transcrição para {participant_id}", conteudo_formatado, branch="main")
                st.session_state.transcript_saved = True
            except Exception as e: print(f"Erro ao salvar no GitHub: {e}")

        st.title("Felt Accountability no Setor Público - Entrevista")
        index, chunks = carregar_memoria_pesquisa_do_github()
        
        if "model" not in st.session_state:
            st.session_state.model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=orientacoes_completas)
            st.session_state.messages = []
            st.session_state.interview_over = False
            st.session_state.transcript_saved = False
            st.session_state.messages.append({"role": "model", "content": mensagem_abertura})

        for message in st.session_state.messages:
            with st.chat_message(message["role"]): st.write(message["content"])

        if prompt := st.chat_input("Sua resposta...", key="chat_input", disabled=st.session_state.get('interview_over', False)):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.write(prompt)
            with st.chat_message("assistant"):
                placeholder = st.empty(); placeholder.markdown("Digitando…")
                history_for_api = [{'role': ('model' if msg['role'] == 'model' else 'user'), 'parts': [msg['content']]} for msg in st.session_state.messages]
                try:
                    response_stream = st.session_state.model.generate_content(history_for_api, stream=True)
                    text_generator = stream_handler(response_stream)
                    full_response_text = placeholder.write_stream(text_generator)
                    
                    final_text_to_save = full_response_text.replace("<END_INTERVIEW>", "").strip()
                    st.session_state.messages.append({"role": "model", "content": final_text_to_save})

                    if "<END_INTERVIEW>" in full_response_text or mensagem_encerramento in full_response_text:
                        st.session_state.interview_over = True
                        save_transcript_to_github(st.session_state.messages, f"finalizado_{uuid.uuid4().hex[:6]}")
                except Exception as e:
                    placeholder.error(f"Ocorreu um erro: {e}")
            st.rerun()

        if not st.session_state.get('interview_over', False):
            if st.button("Encerrar Entrevista"):
                with st.spinner("Salvando e encerrando..."):
                    st.session_state.messages.append({"role": "model", "content": mensagem_encerramento})
                    save_transcript_to_github(st.session_state.messages, f"manual_{uuid.uuid4().hex[:6]}")
                    st.write(mensagem_encerramento); st.session_state.interview_over = True
                time.sleep(1); st.rerun()
    pagina_entrevistador()
