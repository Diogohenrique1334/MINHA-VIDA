import uvicorn
import requests
import json
import datetime
from fastapi import FastAPI, Request, HTTPException
from sqlalchemy import func, cast, Date
import traceback
from dotenv import load_dotenv
import os
import pytz  # Adicione esta importação

load_dotenv()

API_VERSION = os.getenv("API_VERSION")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

from models import Minha_vida
from dependencies import pegar_sessao

app = FastAPI()

# Configuração do fuso horário do Brasil
FUSO_BRASIL = pytz.timezone('America/Sao_Paulo')

# --- FUNÇÕES AUXILIARES ---
def agora_brasil():
    """Retorna o datetime atual no fuso horário do Brasil"""
    return datetime.datetime.now(FUSO_BRASIL)

def data_hoje_brasil():
    """Retorna a data atual no fuso horário do Brasil"""
    return agora_brasil().date()

# --- FUNÇÕES DE ENVIO DE MENSAGEM ---
def send_whatsapp_message(recipient_id, message_text):
    print(f"Tentando enviar '{message_text}' para {recipient_id}")
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": recipient_id, "type": "text", "text": {"body": message_text}}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"--- ERRO AO ENVIAR MENSAGEM: {e.response.text if e.response else e} ---")

def send_button_message(recipient_id, question_text, buttons):
    print(f"Tentando enviar pergunta com botões para {recipient_id}")
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    action_buttons = [{"type": "reply", "reply": {"id": b["payload"], "title": b["title"]}} for b in buttons]
    data = { "messaging_product": "whatsapp", "to": recipient_id, "type": "interactive", "interactive": {"type": "button", "body": {"text": question_text}, "action": {"buttons": action_buttons}}}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"--- ERRO AO ENVIAR BOTÕES: {e.response.text if e.response else e} ---")

def send_list_message(recipient_id, header_text, body_text, button_text, sections):
    print(f"Tentando enviar lista para {recipient_id}")
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": header_text[:60]
            },
            "body": {
                "text": body_text[:1024]
            },
            "action": {
                "button": button_text[:20],
                "sections": sections
            }
        }
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(f"Status: {response.status_code}, Resposta: {response.text}")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"--- ERRO AO ENVIAR LISTA: {e.response.text if e.response else e} ---")

# --- LÓGICA DA CONVERSA ---

TOPICOS_SIM_NAO = {
    'academia': {'coluna': 'Academia', 'texto': 'Você foi à academia hoje?'},
    'leitura': {'coluna': 'Leitura', 'texto': 'E sobre leitura, você praticou hoje?'},
    'estudar': {'coluna': 'Estudar', 'texto': 'Reservou um tempo para os estudos?'},
    'alimentacao_saudavel': {'coluna': 'Alimentação_saudavel', 'texto': 'Sua alimentação foi saudável?'},
    'consumo_de_agua': {'coluna': 'Consumo_de_agua', 'texto': 'Bebeu água o suficiente hoje?'},
    'secreto': {'coluna': 'secreto', 'texto': 'Fumou hoje?'},
    'exercicio_aerobico': {'coluna': 'Exercício_aerobico', 'texto': 'Praticou atividade física hoje?'},
    'atividade_sexual': {'coluna': 'Atividade_sexual', 'texto': 'Fez sexo hoje?'}
}

TOPICOS_TEXTO = {
    'nota_humor_inicio': {'coluna': 'nota_humor', 'texto': 'Qual sua nota de humor ao acordar? (de 0 a 10)', 'tipo': 'nota'},
    'hora_acordei': {'coluna': 'data_hora_acordei', 'texto': 'Beleza. E que horas você acordou hoje? (ex: 07:30)', 'tipo': 'hora'},
    'hora_dormir': {'coluna': 'data_hora_dormi', 'texto': 'Entendido. E que horas você foi dormir na noite anterior? (ex: 23:30)', 'tipo': 'hora_anterior'},
    'nota_humor_fim': {'coluna': 'Nota_humor_fim_dia', 'texto': 'Para finalizar, qual sua nota de humor ao ir dormir? (de 0 a 10)', 'tipo': 'nota'}
}

def send_top_level_menu(sender_phone):
    texto = "Olá! Bem-vindo(a) ao seu diário. 😄\n\nO que você gostaria de registrar agora?"
    botoes = [
        {"title": "💪 Registrar Hábitos", "payload": "show_menu_habitos"},
        {"title": "📊 Registrar Métricas", "payload": "show_menu_metricas"}
    ]
    send_button_message(sender_phone, texto, botoes)

def send_dynamic_menu(sender_phone, session, registro_hoje, category):
    topicos_dict = TOPICOS_SIM_NAO if category == 'habitos' else TOPICOS_TEXTO
    header_text = "Hábitos" if category == 'habitos' else "Métricas"
    
    rows = []
    for key, value in topicos_dict.items():
        resposta = getattr(registro_hoje, value['coluna'], None)
        coluna_nome = value['coluna'].replace('_', ' ').title()
        
        if resposta is None:
            status_emoji = "⬜️"
            description = "Pendente"
        else:
            if category == 'habitos':
                status_emoji = "✅" if resposta else "❌"
                description = f"Resposta: {'Sim' if resposta else 'Não'}"
            else:
                status_emoji = "⏰" if 'hora' in key else "📊"
                if isinstance(resposta, datetime.datetime):
                    # Converta para fuso do Brasil antes de exibir
                    resposta_brasil = resposta.astimezone(FUSO_BRASIL)
                    description = f"Resposta: {resposta_brasil.strftime('%H:%M')}"
                else:
                    description = f"Resposta: {resposta}"
        
        row_title = f"{status_emoji} {coluna_nome}"[:24]
        row_description = description[:72]
        
        rows.append({
            "id": f"ask_{key}",
            "title": row_title,
            "description": row_description
        })

    rows.append({
        "id": "show_menu_principal",
        "title": "⬅️ Voltar"
    })
    
    sections = [{
        "title": "Selecione um item"[:24],
        "rows": rows
    }]
    
    send_list_message(sender_phone, "Diário Pessoal", header_text, "Opções", sections)

# --- ENDPOINTS DA API ---
@app.get("/")
def root(): return {"status": "API online"}

@app.get("/webhook")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("WEBHOOK VERIFICADO!")
        return int(challenge)
    raise HTTPException(status_code=403, detail="Token inválido")

@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    print(f"\n--- Webhook Recebido ---\n{json.dumps(data, indent=2)}\n-----------------------\n")

    try:
        value = data["entry"][0]["changes"][0]["value"]
        if "messages" in value:
            message_info = value["messages"][0]
            sender_phone = message_info["from"]
            
            # Usar data do Brasil
            hoje_brasil = data_hoje_brasil()
            
            with pegar_sessao() as session:
                # Buscar registros com base no fuso horário do Brasil
                registro_hoje = session.query(Minha_vida).filter(
                    func.date(Minha_vida.data.astimezone(FUSO_BRASIL)) == hoje_brasil,
                    Minha_vida.user_phone_number == sender_phone
                ).first()

                # 1. Iniciar a conversa
                if message_info["type"] == "text" and message_info["text"]["body"].lower().strip() in ["iniciar", "oi", "diario", "menu"]:
                    if not registro_hoje:
                        # Usar datetime atual no fuso do Brasil
                        novo_registro = Minha_vida(
                            data=agora_brasil(),
                            user_phone_number=sender_phone
                        )
                        session.add(novo_registro)
                        session.commit()
                        registro_hoje = session.query(Minha_vida).filter(
                            func.date(Minha_vida.data.astimezone(FUSO_BRASIL)) == hoje_brasil,
                            Minha_vida.user_phone_number == sender_phone
                        ).first()
                    send_top_level_menu(sender_phone)
                    return {"status": "ok"}
                
                # 2. Processar respostas de texto (para Métricas)
                if message_info["type"] == "text" and registro_hoje and registro_hoje.status_conversa:
                    texto_usuario = message_info["text"]["body"]
                    topic_key = registro_hoje.status_conversa.replace('aguardando_', '')
                    
                    if topic_key in TOPICOS_TEXTO:
                        topic_info = TOPICOS_TEXTO[topic_key]
                        coluna = topic_info['coluna']
                        try:
                            if topic_info['tipo'] == 'nota':
                                nota = float(texto_usuario.replace(',', '.'))
                                if not (0 <= nota <= 10): raise ValueError("Nota fora do intervalo")
                                setattr(registro_hoje, coluna, nota)
                            
                            elif topic_info['tipo'] == 'hora':
                                hora_obj = datetime.datetime.strptime(texto_usuario, '%H:%M').time()
                                # Combinar com a data atual no Brasil
                                data_completa = datetime.datetime.combine(hoje_brasil, hora_obj)
                                # Adicionar fuso horário e converter para UTC
                                data_completa_brasil = FUSO_BRASIL.localize(data_completa)
                                setattr(registro_hoje, coluna, data_completa_brasil)

                            elif topic_info['tipo'] == 'hora_anterior':
                                hora_obj = datetime.datetime.strptime(texto_usuario, '%H:%M').time()
                                # Usar a data de ontem no Brasil
                                ontem_brasil = hoje_brasil - datetime.timedelta(days=1)
                                data_completa = datetime.datetime.combine(ontem_brasil, hora_obj)
                                # Adicionar fuso horário e converter para UTC
                                data_completa_brasil = FUSO_BRASIL.localize(data_completa)
                                setattr(registro_hoje, coluna, data_completa_brasil)

                            registro_hoje.status_conversa = None
                            session.commit()
                            send_whatsapp_message(sender_phone, "Anotado! ✅")
                            send_dynamic_menu(sender_phone, session, registro_hoje, 'metricas')
                        except ValueError:
                            send_whatsapp_message(sender_phone, "Resposta inválida. Por favor, tente novamente.")
                            send_whatsapp_message(sender_phone, topic_info['texto'])

                # 3. Processar respostas interativas (Menus, Listas e Botões)
                elif message_info["type"] == "interactive":
                    if not registro_hoje:
                        send_whatsapp_message(sender_phone, "Ops, não encontrei seu registro de hoje. Tente mandar 'iniciar' primeiro.")
                        return {"status": "ok"}

                    interactive_type = message_info["interactive"]["type"]
                    payload = message_info["interactive"][interactive_type]["id"]

                    # Navegação entre menus
                    if payload.startswith('show_menu_'):
                        category = payload.replace('show_menu_', '')
                        if category == 'principal': send_top_level_menu(sender_phone)
                        else: send_dynamic_menu(sender_phone, session, registro_hoje, category)
                        return {"status": "ok"}

                    # Seleção de um item na lista para responder
                    if payload.startswith('ask_'):
                        topic_key = payload.replace('ask_', '')
                        if topic_key in TOPICOS_SIM_NAO:
                            topic_info = TOPICOS_SIM_NAO[topic_key]
                            botoes = [{"title": "✅ Sim", "payload": f"ans_{topic_key}_sim"}, {"title": "❌ Não", "payload": f"ans_{topic_key}_nao"}]
                            send_button_message(sender_phone, topic_info['texto'], botoes)
                        elif topic_key in TOPICOS_TEXTO:
                            topic_info = TOPICOS_TEXTO[topic_key]
                            registro_hoje.status_conversa = f"aguardando_{topic_key}"
                            session.commit()
                            send_whatsapp_message(sender_phone, topic_info['texto'])

                    # Resposta a um botão de Sim/Não
                    elif payload.startswith('ans_'):
                        print(f"Processando payload: {payload}")
                        
                        # Encontra a posição do último underscore
                        last_underscore_index = payload.rfind('_')
                        
                        # Extrai a resposta (última parte após o último underscore)
                        resposta = payload[last_underscore_index + 1:]
                        
                        # Extrai o tópico (tudo entre 'ans_' e o último underscore)
                        topic_key = payload[4:last_underscore_index]
                        
                        print(f"Tópico extraído: {topic_key}, Resposta: {resposta}")
                        
                        resposta_bool = (resposta == 'sim')
                        
                        if topic_key in TOPICOS_SIM_NAO:
                            print(f"Tópico reconhecido: {topic_key}")
                            coluna = TOPICOS_SIM_NAO[topic_key]['coluna']
                            setattr(registro_hoje, coluna, resposta_bool)
                            session.commit()
                            send_whatsapp_message(sender_phone, "Anotado! ✅")
                            send_dynamic_menu(sender_phone, session, registro_hoje, 'habitos')
                        else:
                            print(f"Tópico não reconhecido: {topic_key}")
                            print(f"Tópicos disponíveis: {list(TOPICOS_SIM_NAO.keys())}")
                        
    except Exception as e:
        print(f"!!!!!!!!!! ERRO CRÍTICO NO WEBHOOK !!!!!!!!!!!")
        print(f"Erro: {e}")
        traceback.print_exc()
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    return {"status": "ok"}

# --- Bloco para iniciar o servidor ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)