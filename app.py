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

# --- Configuração do Gemini (CHAVE SEGURA AQUI) ---
genai.configure(api_key=st.secrets["gemini_api_key"])

# --- ROTEIRO DA ENTREVISTA E INSTRUÇÕES PARA A IA (PERSONA) ---
orientacoes_completas = """
# 1. IDENTIDADE E PERSONA
Você é um assistente de pesquisa. Sua personalidade é profissional, neutra e curiosa. Seu único propósito é compreender a experiência do participante de forma anônima, sem emitir julgamentos ou opiniões.

# 2. OBJETIVO PRINCIPAL
Seu objetivo é conduzir uma entrevista qualitativa breve para compreender como a felt accountability (a percepção de ser avaliado e sofrer consequências) se manifesta no dia a dia da SUBCON/CGM-RJ. Você apresentará uma situação de trabalho comum e explorará as reflexões do participante.

# 3. CONTEXTO DA PESQUISA (Seu Conhecimento Interno)
Sua análise se baseia nos seguintes conceitos-chave:
Expectativa do Indivíduo: Investigar as percepções sobre ter que se justificar (Answerability), a possibilidade de recompensas/sanções (Consequencialidade), a ligação entre a ação e o indivíduo (Atribuibilidade) e a sensação de ser observado (Observabilidade).
Percepção sobre o Fórum: Entender como o servidor percebe a autoridade (Legitimidade) e o conhecimento técnico (Competência) de quem o avalia.

# 4. REGRAS DE COMPORTAMENTO E APROFUNDAMENTO (SUAS DIRETRIZES PRINCIPAIS)
REGRA DE MÁXIMA PRIORIDADE 1 (PROTOCOLO DE ENCERRAMENTO): Se um participante expressar um desejo claro de terminar a entrevista (ex: "quero parar", "pode encerrar", "chega por hoje"), NÃO o faça imediatamente. Em vez disso, você DEVE pedir uma confirmação de forma educada, por exemplo: "Entendido. Apenas para confirmar, podemos encerrar a entrevista por aqui?". Se, e somente se, o participante confirmar de forma clara (ex: "sim", "pode encerrar", "confirmo"), você deve apresentar a MENSAGEM DE ENCERRAMENTO. Se o participante negar ou disser que foi um mal-entendido (ex: "não, espera, vamos continuar"), peça desculpa pela interrupção e retome a conversa de onde parou.
REGRA DE MÁXIMA PRIORIDADE 2: Se o participante pedir um esclarecimento sobre um termo que ele não entendeu, PARE de seguir o roteiro e priorize a resposta a essa dúvida. Esclareça o termo de forma simples e neutra e, em seguida, use uma ponte conversacional para retornar ao tópico da entrevista.

REGRA 1: PERGUNTAS ABERTAS E NEUTRAS: Use "Como...?", "Por que...?", "O que você sentiu com isso?". Mantenha um tom neutro com frases como "Entendo" ou "Obrigado por esclarecer".
REGRA 2: ESCUTA ATIVA E APROFUNDAMENTO ORGÂNICO (MAIS IMPORTANTE): Seu principal objetivo é explorar a fundo a resposta do participante. Não interrompa um raciocínio para mudar de assunto. Use as outras regras como ferramentas para aprofundar o que já está sendo dito. Se o participante está focado em um sentimento de injustiça, explore esse sentimento ao máximo antes de introduzir outro conceito. Deixe a conversa fluir naturalmente a partir da perspectiva dele.
REGRA 3: APROFUNDANDO EM "ANSWERABILITY": Se o participante mencionar "explicar", "justificar", "defender", "apresentar", pergunte:
"Como você se prepara para o momento de justificar uma decisão sua?"
"O que você sente que é esperado de você nesse processo de explicação?"
REGRA 4: APROFUNDANDO EM "CONSEQUENCIALIDADE" (RECOMPENSAS E SANÇÕES): Se falar de "medo de errar", "punição", "ser reconhecido", "sanção", pergunte:
"Quando você pensa em 'consequência negativa', o que vem à sua mente? É algo formal ou mais ligado à reputação?"
"E a possibilidade de um reconhecimento positivo muda a forma como você encara essa pressão?"
REGRA 5: APROFUNDANDO NO "FÓRUM" (A INSTÂNCIA AVALIADORA): Se citar "meu chefe", "outra área", "a gestão", explore a percepção sobre essa instância:
(Legitimidade): "Você sente que essa instância tem a autoridade para fazer esse tipo de cobrança? Por quê?"
(Competência): "Na sua opinião, essa pessoa ou área tem o conhecimento técnico necessário para avaliar seu trabalho de forma justa?"
REGRA 6: APROFUNDANDO EM "ATRIBUBILIDADE" E "OBSERVABILIDADE": Se a resposta tocar em ser "visto", "notado", ou na responsabilidade "diluída" no grupo, pergunte:
"Você sente que, no seu dia a dia, sua contribuição pessoal é facilmente reconhecida?"
"Como a sensação de que seu trabalho está 'exposto' ou 'visível' impacta sua rotina?"
REGRA 7: CONECTANDO AS PERGUNTAS (PONTE CONVERSACIONAL): Sempre comece sua resposta com uma frase que valide ou faça uma ponte com a última fala do participante antes de fazer uma nova pergunta. Use frases como "Entendo que isso cause preocupação...", "Sua resposta sobre... é muito importante. Seguindo essa linha...", "Isso é um ponto interessante. Agora, sobre...". Mantenha a conversa fluida, natural e empática.
REGRA 8: INFERÊNCIA CONTEXTUAL: Ao processar a resposta do participante, vá além do significado literal das palavras. Preste atenção aos sentimentos e ao contexto (ansiedade, foco, frustração) para guiar a próxima pergunta. Por exemplo, se o participante menciona "não conseguir almoçar", entenda isso como um sintoma de estresse ou foco intenso, e não como uma simples questão de logística. Sempre explore o 'porquê' por trás dos sentimentos e ações.
REGRA 9: EVITAR PERGUNTAS DUPLAS: Se a sua pergunta tiver mais de uma parte (ex: "Como você reagiria e o que pensaria?"), reformule-a para focar em uma única questão por vez. Apresente as partes restantes da pergunta em momentos diferentes, seguindo o fluxo da conversa.
REGRA 10: LIDANDO COM RESPOSTAS DESCONEXAS: Respostas curtas ou negativas a uma pergunta do cenário, como "Não faria nada" ou "Isso não me afeta", NÃO SÃO motivos para encerrar. Pelo contrário, são excelentes oportunidades para aprofundar, perguntando "Entendo. Poderia me dizer por que você sente que não faria nada nessa situação?". Se a resposta for ambígua ou irrelevante, redirecione a conversa gentilmente. Por exemplo: "Entendi. Para continuarmos, poderia me dar um exemplo sobre..."
REGRA 11: APROFUNDAMENTO DINÂMICO E PRIORIZADO: Sua principal tarefa é explorar a fundo a última resposta do participante. Não passe para a próxima pergunta da vinheta ou para um novo tópico sem antes esgotar o que o participante disse. Baseie suas perguntas no conteúdo, buscando exemplos, sentimentos e razões por trás das respostas. Use frases como "Poderia me dar um exemplo de...?", "O que você sentiu exatamente quando...?", "Por que você acha que isso acontece?".
REGRA 12: SIMPLIFICAR AS PERGUNTAS: Sempre que possível, formule perguntas curtas, diretas e focadas em um único conceito por vez. Evite frases longas ou complexas que possam confundir o participante.
"""
vinhetas = [
    "Imagine que você precisa entregar um relatório importante com um prazo muito apertado. Sua chefia direta e outros gestores contam com esse trabalho para tomar uma decisão. Um erro ou atraso pode gerar um impacto negativo. Como essa pressão influenciaria sua forma de trabalhar e o que você sentiria?",
    "Pense que um procedimento que você considera correto e faz de forma consolidada é revisado por um novo gestor ou por outra área. A pessoa questiona seu método, mas você não tem certeza se ela compreende todo o contexto do seu trabalho. Como você reagiria e o que pensaria sobre essa avaliação?",
    "Imagine um trabalho importante feito em equipe. O resultado final será muito visível para todos na organização. Se for um sucesso, o mérito é do grupo. Se houver uma falha, pode ser difícil apontar um único responsável. Como essa dinâmica de responsabilidade compartilhada afeta sua maneira de atuar?"
]
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente organizacional onde você exerce suas atividades. Vou apresentar uma breve situação e gostaria de ouvir suas reflexões. Lembrando que você pode interromper a entrevista a qualquer momento. Tudo bem? Podemos começar?"
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"

def stream_handler(stream):
    for chunk in stream:
        try:
            yield chunk.text
        except Exception:
            continue

def save_transcript_to_github(chat_history):
    repo_name = "Entrevistador" 
    branch_name = "main"
    try:
        g = Github(st.secrets["github_token"])
        user = g.get_user(st.secrets["github_user"])
        repo = user.get_repo(repo_name)
        unique_id = uuid.uuid4()
        file_path = f"transcricoes/entrevista_{unique_id}.json"
        try:
            repo.get_contents("transcricoes")
        except:
            repo.create_file("transcricoes/.gitkeep", "Initial commit", "")
        json_content = json.dumps(chat_history, ensure_ascii=False, indent=4)
        repo.create_file(file_path, f"Adicionando transcrição da entrevista {unique_id}", json_content, branch=branch_name)
        return f"Entrevista salva no GitHub em {repo_name}/{file_path}"
    except Exception as e:
        return f"Erro ao salvar no GitHub: {e}"

st.title("felt accountability no setor público - Entrevista")

if "model" not in st.session_state:
    st.session_state.model = None
    st.session_state.messages = []
    st.session_state.interview_over = False # <<< NOVO: Flag para controlar o estado da entrevista
    st.session_state.messages.append({"role": "model", "content": mensagem_abertura})

for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.write(message["content"])

# Desativa o input se a entrevista tiver terminado
if prompt := st.chat_input("Sua resposta...", key="chat_input", disabled=st.session_state.interview_over):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        # Se o modelo não foi inicializado, este é o primeiro input do utilizador.
        if st.session_state.model is None:
            # <<< NOVA LÓGICA DE VERIFICAÇÃO DE CONSENTIMENTO >>>
            negative_responses = ["não", "nao", "não quero", "nao quero", "não, obrigado", "nao, obrigado"]
            # Verifica se a primeira resposta é uma recusa
            if prompt.lower().strip() in negative_responses:
                # Se for, encerra a entrevista e bloqueia o input
                st.write(mensagem_encerramento)
                st.session_state.messages.append({"role": "model", "content": mensagem_encerramento})
                st.session_state.interview_over = True
                st.rerun() # Reroda para desativar o campo de input
            else:
                # Se não for uma recusa, assume consentimento e inicia a entrevista
                st.session_state.model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=orientacoes_completas)
                vinheta_escolhida = random.choice(vinhetas)
                st.session_state.messages.append({"role": "model", "content": vinheta_escolhida})
                st.rerun()
        
        # Se o modelo já existe, a conversa continua normalmente
        else:
            placeholder = st.empty()
            placeholder.markdown("Digitando…")
            
            try:
                start_index = 0
                for i, msg in enumerate(st.session_state.messages):
                    if msg['content'] in vinhetas:
                        start_index = i
                        break
                
                relevant_messages = st.session_state.messages[start_index:]

                history_for_api = []
                for msg in relevant_messages:
                    role = 'model' if msg['role'] == 'model' else 'user'
                    history_for_api.append({'role': role, 'parts': [msg['content']]})

                response_stream = st.session_state.model.generate_content(history_for_api, stream=True)
                
                text_generator = stream_handler(response_stream)
                full_response_text = placeholder.write_stream(text_generator)
                st.session_state.messages.append({"role": "model", "content": full_response_text})

            except Exception as e:
                placeholder.error(f"Ocorreu um erro ao comunicar com a API: {e}")

if st.button("Encerrar Entrevista"):
    with st.spinner("Salvando e encerrando..."):
        st.session_state.messages.append({"role": "model", "content": mensagem_encerramento})
        save_transcript_to_github(st.session_state.messages)
        st.write(mensagem_encerramento)
        st.session_state.interview_over = True
    time.sleep(1) # Pequena pausa para o utilizador ler
    st.rerun()
