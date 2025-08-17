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

# 4. CONCEITOS-GUIA PARA AS SUAS PERGuntas (NUNCA OS MENCIONE DIRETAMENTE)
Use os seguintes temas como inspiração para as suas perguntas de aprofundamento, mas NUNCA os revele ao participante:
- Justificativas (Answerability): O sentimento de ter que explicar ou defender as suas ações.
- Consequências (Consequencialidade): A percepção de que haverá recompensas ou sanções.
- Atribuição (Atribuibilidade): A ligação clara entre uma ação e o indivíduo.
- Visibilidade (Observabilidade): A sensação de estar a ser observado.
- Legitimidade do Avaliador: A percepção de que quem avalia tem autoridade para o fazer.
- Competência do Avaliador: A percepção de que quem avalia tem conhecimento técnico para o fazer.

# 5. PROTOCOLOS E REGRAS SECUNDÁRIAS
REGRA DE OURO (FOCO E BREVIDADE): O seu objetivo é uma entrevista curta e profunda de no máximo 5 minutos. Mantenha as suas perguntas e comentários CURTOS e DIRETOS. Assim que encontrar um tema interessante ou uma tensão na resposta do participante, foque-se nesse tema e aprofunde-o.

PROTOCOLO DE ENCERRAMENTO POR PEDIDO: Apenas inicie este protocolo se o participante fizer um pedido explícito e direto para parar a entrevista (ex: "quero parar", "podemos encerrar"). Frases que concluem um raciocínio (ex: "é isso") NÃO são um pedido para parar. Se receber um pedido, peça confirmação (ex: "Entendido. Apenas para confirmar, podemos encerrar por aqui?") e só encerre se o participante confirmar.

REGRA 15 (ENCERRAMENTO NATURAL DA ENTREVISTA): O seu objetivo é uma entrevista de ~5 minutos. Após ter aprofundado um tema de forma satisfatória e sentir que tem material suficiente, você pode e deve iniciar o encerramento. Para fazer isso, a sua resposta final DEVE seguir esta estrutura de 3 passos:
1. Comece com uma frase de transição positiva e de agradecimento.
2. Continue com a frase de encerramento completa: "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"
3. Anexe o sinalizador secreto <END_INTERVIEW> no final de tudo.

PROTOCOLO DE ESCLARECIMENTO: Se o participante não entender algo, explique o termo de forma simples e volte à pergunta.

PROTOCOLO DE EMOÇÕES: Se o participante usar palavras de forte carga emocional (ex: "raiva", "frustração"), a sua prioridade é explorar essa emoção com uma pergunta aberta (ex: "Entendo. O que exatamente nessa situação lhe causaria raiva?").

PROTOCOLO ANTI-CONSELHOS: A sua função é entender, não resolver. Nunca dê conselhos ou soluções. A sua única ferramenta é a pergunta.

PROTOCOLO DE VARIAÇÃO DE LINGUAGEM: Evite soar repetitivo. Varie as suas frases de transição (use "Compreendo.", "Faz sentido.", "Certo.", etc., em vez de sempre "Entendo.").
"""
vinhetas = [
    "Imagine que você precisa entregar um relatório importante com um prazo muito apertado. Sua chefia direta e outros gestores contam com esse trabalho para tomar uma decisão. Um erro ou atraso pode gerar um impacto negativo. Como essa pressão influenciaria sua forma de trabalhar?",
    "Pense que um procedimento que você considera correto e faz de forma consolidada é revisado por um novo gestor ou por outra área. A pessoa questiona seu método, mas você não tem certeza se ela compreende todo o contexto do seu trabalho. Como você reagiria a essa situação?",
    "Imagine um trabalho importante feito em equipe. O resultado final será muito visível para todos na organização. Se for um sucesso, o mérito é do grupo. Se houver uma falha, pode ser difícil apontar um único responsável. Como essa dinâmica de responsabilidade compartilhada afeta sua maneira de atuar?"
]
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente organizacional onde você exerce suas atividades. Vou apresentar uma breve situação e gostaria de ouvir suas reflexões. Lembrando que você pode interromper a entrevista a qualquer momento. Tudo bem? Podemos começar?"
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"
mensagem_esclarecimento = "Desculpe, não entendi a sua resposta. Poderia apenas confirmar se podemos começar a entrevista, por favor?"

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
                            contents = repo.get_contents(file_path)
                            repo.update_file(contents.path, commit_message, content, contents.sha, branch="main"); st.write(f"Ficheiro '{file_path}' atualizado no GitHub.")
                        except:
                            repo.create_file(file_path, commit_message, content, branch="main"); st.write(f"Ficheiro '{file_path}' criado no GitHub.")
                    upload_or_update_file("faiss_index.bin", "Atualizando índice FAISS", index_bytes)
                    chunks_bytes = pickle.dumps(text_chunks); upload_or_update_file("text_chunks.pkl", "Atualizando pedaços de texto", chunks_bytes)
                    st.success("Memória criada e salva com sucesso!"); st.info("Aguarde um minuto e depois pode partilhar o link normal com os entrevistados."); st.cache_resource.clear()
                except Exception as e: st.error(f"Ocorreu um erro: {e}")

def pagina_entrevistador():
    @st.cache_resource
    def carregar_memoria_pesquisa_do_github():
        try:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(f"{GITHUB_USER}/{REPO_NAME}")
            
            index_content = repo.get_contents("faiss_index.bin").decoded_content
            temp_index_file = "temp_faiss_index_load.bin"
            with open(temp_index_file, "wb") as f:
                f.write(index_content)
            index = faiss.read_index(temp_index_file)
            os.remove(temp_index_file)

            chunks_content = repo.get_contents("text_chunks.pkl").decoded_content
            chunks = pickle.loads(chunks_content)
            
            return index, chunks
        except Exception:
            # <<< CORREÇÃO APLICADA AQUI >>>
            # Garante que, em caso de falha (ex: ficheiros não existem), 
            # a função retorna uma tupla de dois elementos (None, None).
            return None, None

    def analisar_consentimento(resposta_utilizador):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt_analista = f"""Você é um assistente que analisa a resposta inicial de um participante de pesquisa. A pergunta feita foi: "Tudo bem? Podemos começar?". A sua tarefa é analisar a resposta do participante e decidir a próxima ação. A resposta do participante foi: "{resposta_utilizador}". Analise a resposta e escolha UMA das seguintes ações: - 'PROSSEGUIR': Se a resposta for um consentimento claro. - 'ENCERRAR': Se a resposta for uma recusa clara. - 'ESCLARECER': Se a resposta for ambígua ou sem sentido. Responda APENAS com a palavra PROSSEGUIR, ENCERRAR, ou ESCLARECER."""
        try:
            response = model.generate_content(prompt_analista)
            decisao = response.text.strip().upper()
            if decisao in ["PROSSEGUIR", "ENCERRAR", "ESCLARECER"]: return decisao
            return "ESCLARECER"
        except Exception: return "ESCLARECER"

    def classificar_intencao(prompt_utilizador):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt_classificador = f"""Você é um classificador de intenções. A intenção pode ser 'ENTREVISTA' (uma resposta à entrevista ou pedido de esclarecimento) ou 'PESQUISA' (uma pergunta sobre o projeto). Classifique: "{prompt_utilizador}". Exemplos: 'Ficaria com raiva.' -> ENTREVISTA. 'Qual o objetivo?' -> PESQUISA. 'Não entendi.' -> ENTREVISTA. Responda APENAS 'PESQUISA' ou 'ENTREVISTA'."""
        try:
            response = model.generate_content(prompt_classificador)
            if "PESQUISA" in response.text: return "PESQUISA"
            return "ENTREVISTA"
        except Exception: return "ENTREVISTA"

    def responder_pergunta_pesquisa(index, chunks, pergunta):
        embedding_model = 'models/embedding-001'; pergunta_embedding = genai.embed_content(model=embedding_model, content=pergunta, task_type="retrieval_query")['embedding']
        k = 3; D, I = index.search(np.array([pergunta_embedding]).astype('float32'), k)
        contexto_relevante = " ".join([chunks[i] for i in I[0]])
        model = genai.GenerativeModel('gemini-1.5-flash'); prompt_final = f"Baseado nisto: {contexto_relevante}. Responda a: \"{pergunta}\""
        response = model.generate_content(prompt_final, stream=True)
        return response

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
    
    if "messages" not in st.session_state:
        st.session_state.model = None
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
            if st.session_state.model is None:
                with st.spinner("Analisando..."): acao = analisar_consentimento(prompt)
                if acao == "PROSSEGUIR":
                    st.session_state.model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=orientacoes_completas)
                    vinheta_escolhida = random.choice(vinhetas); st.session_state.messages.append({"role": "model", "content": vinheta_escolhida})
                elif acao == "ENCERRAR":
                    st.session_state.messages.append({"role": "model", "content": mensagem_encerramento}); st.session_state.interview_over = True; save_transcript_to_github(st.session_state.messages, f"recusado_{uuid.uuid4().hex[:6]}")
                elif acao == "ESCLARECER":
                    st.session_state.messages.append({"role": "model", "content": mensagem_esclarecimento})
            else:
                placeholder = st.empty(); placeholder.markdown("Digitando…")
                intencao = classificar_intencao(prompt)
                try:
                    if intencao == "PESQUISA" and index is not None: response_stream = responder_pergunta_pesquisa(index, chunks, prompt)
                    else:
                        history_for_api = [{'role': ('model' if msg['role'] == 'model' else 'user'), 'parts': [msg['content']]} for msg in st.session_state.messages]
                        response_stream = st.session_state.model.generate_content(history_for_api, stream=True)
                    text_generator = stream_handler(response_stream)
                    full_response_text = placeholder.write_stream(text_generator)
                    final_text_to_save = full_response_text.replace("<END_INTERVIEW>", "").strip()
                    st.session_state.messages.append({"role": "model", "content": final_text_to_save})
                    if "<END_INTERVIEW>" in full_response_text or mensagem_encerramento in full_response_text:
                        st.session_state.interview_over = True
                        save_transcript_to_github(st.session_state.messages, f"finalizado_{uuid.uuid4().hex[:6]}")
                except Exception as e: placeholder.error(f"Ocorreu um erro: {e}")
        st.rerun()

    if not st.session_state.get('interview_over', False):
        if st.button("Encerrar Entrevista"):
            with st.spinner("Salvando e encerrando..."):
                st.session_state.messages.append({"role": "model", "content": mensagem_encerramento})
                save_transcript_to_github(st.session_state.messages, f"manual_{uuid.uuid4().hex[:6]}")
                st.write(mensagem_encerramento); st.session_state.interview_over = True
            time.sleep(1); st.rerun()

# --- LÓGICA PRINCIPAL: Decide qual página mostrar ---
if st.query_params.get("admin") == "true":
    pagina_configuracao()
else:
    pagina_entrevistador()
