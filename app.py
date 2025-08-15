import streamlit as st
import google.generativeai as genai
import datetime
import json
import os
import time
import uuid
from github import Github
import random 

# --- Configuração do Gemini (CHAVE SEGURA AQUI) ---
genai.configure(api_key=st.secrets["gemini_api_key"])

# --- ROTEIRO DA ENTREVISTA E INSTRUÇÕES PARA A IA ---
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
REGRA DE MÁXIMA PRIORIDADE 1: Se o participante responder "Não" ou expressar recusa em continuar, encerre a entrevista IMEDIATAMENTE com a MENSAGEM DE ENCERRAMENTO. NÃO prossiga com a entrevista.
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
REGRA 10: LIDANDO COM RESPOSTAS DESCONEXAS: Se a resposta do participante for ambígua, irrelevante ou não se conectar com a última pergunta, não repita a vinheta ou a pergunta inicial. Em vez disso, use uma frase neutra para reconhecer a resposta e, em seguida, redirecione a conversa gentilmente. Por exemplo: "Entendi. Para continuarmos, poderia me dar um exemplo sobre..." ou "Agradeço o seu comentário. Voltando à nossa situação, como você...".
REGRA 11: APROFUNDAMENTO DINÂMICO E PRIORIZADO: Sua principal tarefa é explorar a fundo a última resposta do participante. Não passe para a próxima pergunta da vinheta ou para um novo tópico sem antes esgotar o que o participante disse. Baseie suas perguntas no conteúdo, buscando exemplos, sentimentos e razões por trás das respostas. Use frases como "Poderia me dar um exemplo de...?", "O que você sentiu exatamente quando...?", "Por que você acha que isso acontece?".
REGRA 12: SIMPLIFICAR AS PERGUNTAS: Sempre que possível, formule perguntas curtas, diretas e focadas em um único conceito por vez. Evite frases longas ou complexas que possam confundir o participante.
"""

# A mensagem de abertura e as vinhetas agora estão separadas
vinhetas = [
    "Imagine que você precisa entregar um relatório importante com um prazo muito apertado. Sua chefia direta e outros gestores contam com esse trabalho para tomar uma decisão. Um erro ou atraso pode gerar um impacto negativo. Como essa pressão influenciaria sua forma de trabalhar e o que você sentiria?",
    "Pense que um procedimento que você considera correto e faz de forma consolidada é revisado por um novo gestor ou por outra área. A pessoa questiona seu método, mas você não tem certeza se ela compreende todo o contexto do seu trabalho. Como você reagiria e o que pensaria sobre essa avaliação?",
    "Imagine um trabalho importante feito em equipe. O resultado final será muito visível para todos na organização. Se for um sucesso, o mérito é do grupo. Se houver uma falha, pode ser difícil apontar um único responsável. Como essa dinâmica de responsabilidade compartilhada afeta sua maneira de atuar?"
]
mensagem_abertura = "Olá! Agradeço sua disposição para esta etapa da pesquisa. A conversa é totalmente anônima e o objetivo é aprofundar algumas percepções sobre o ambiente organizacional onde você exerce suas atividades. Vou apresentar uma breve situação e gostaria de ouvir suas reflexões. Lembrando que você pode interromper a entrevista a qualquer momento. Tudo bem? Podemos começar?"
mensagem_encerramento = "Agradeço muito pelo seu tempo e por compartilhar suas percepções. Sua contribuição é extremamente valiosa. A entrevista está encerrada. Tenha um ótimo dia!"

# --- Funções ---
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

# --- Lógica do Streamlit ---
st.title("Chat Entrevistador de Pesquisa - UFF")

# Inicializa o chat e o histórico de mensagens na sessão
if "chat" not in st.session_state:
    st.session_state.chat = None
    st.session_state.messages = []
    
    # A primeira mensagem da IA é a mensagem de abertura
    st.session_state.messages.append({"role": "model", "content": mensagem_abertura})


# Exibe o histórico da conversa
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.write(message["content"])

# Processa a entrada do usuário
if prompt := st.chat_input("Sua resposta...", key="chat_input"):
    
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            if st.session_state.chat is None:
                # O usuário acaba de responder à mensagem de abertura. Inicia o chat.
                vinheta_escolhida = random.choice(vinhetas)
                prompt_completo = orientacoes_completas + "\n" + vinheta_escolhida
                
                st.session_state.chat = genai.GenerativeModel('gemini-1.5-flash', system_instruction=prompt_completo).start_chat()
                
                response = st.session_state.chat.send_message(prompt)
                
                st.session_state.messages.append({"role": "model", "content": response.text})
                st.write(response.text)
                
            else:
                # O chat já foi iniciado, a conversa segue normalmente
                response = st.session_state.chat.send_message(prompt)
                st.session_state.messages.append({"role": "model", "content": response.text})
                st.write(response.text)

if st.button("Encerrar Entrevista"):
    with st.spinner("Salvando e encerrando..."):
        st.session_state.messages.append({"role": "model", "content": mensagem_encerramento})
        save_transcript_to_github(st.session_state.messages)
        st.write(mensagem_encerramento)
    st.session_state.clear()
    time.sleep(2)
    st.rerun()
