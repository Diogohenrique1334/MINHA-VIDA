import uvicorn
import requests
import json
import datetime
from fastapi import FastAPI, Request, HTTPException
from sqlalchemy import func
import traceback
from dotenv import load_dotenv
import os
import pytz

load_dotenv()

API_VERSION = os.getenv("API_VERSION")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

from backend.models import Minha_vida
from backend.dependencies import pegar_sessao

app = FastAPI()

FUSO_BRASIL = pytz.timezone('America/Sao_Paulo')

def agora_brasil():
    return datetime.datetime.now(FUSO_BRASIL)

def data_hoje_brasil():
    return agora_brasil().date()

def data_ontem_brasil():
    return data_hoje_brasil() - datetime.timedelta(days=1)

DIAS_SEMANA_PT = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']

def resolver_data(token):
    """Resolve o token de dia que trafega nos payloads em um datetime.date.

    Aceita as datas em formato ISO (AAAA-MM-DD) e mantém compatibilidade com
    os tokens antigos 'hoje'/'ontem' para conversas iniciadas antes do deploy.
    """
    if token == 'hoje':
        return data_hoje_brasil()
    if token == 'ontem':
        return data_ontem_brasil()
    return datetime.date.fromisoformat(token)

def rotulo_dia(data):
    """Rótulo amigável para um datetime.date: 'hoje', 'ontem' ou 'em 05/06 (qua)'."""
    if data == data_hoje_brasil():
        return 'hoje'
    if data == data_ontem_brasil():
        return 'ontem'
    return f"em {data.strftime('%d/%m')} ({DIAS_SEMANA_PT[data.weekday()]})"

def parse_data_usuario(texto):
    """Converte uma data digitada pelo usuário em datetime.date, ou None se inválida.

    Aceita 05/06, 5/6, 05/06/2025, 05/06/25, 05-06. Ano omitido assume o ano atual.
    """
    texto = texto.strip()
    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%d/%m', '%d-%m-%Y', '%d-%m'):
        try:
            data = datetime.datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
        if fmt in ('%d/%m', '%d-%m'):
            data = data.replace(year=data_hoje_brasil().year)
        return data
    return None

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
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": question_text},
            "action": {"buttons": action_buttons}
        }
    }
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
            "header": {"type": "text", "text": header_text[:60]},
            "body": {"text": body_text[:1024]},
            "action": {"button": button_text[:20], "sections": sections}
        }
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(f"Status: {response.status_code}, Resposta: {response.text}")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"--- ERRO AO ENVIAR LISTA: {e.response.text if e.response else e} ---")

TOPICOS_SIM_NAO = {
    'academia': {'coluna': 'Academia', 'texto': 'Você foi à academia {dia}?', 'titulo': 'Academia'},
    'leitura': {'coluna': 'Leitura', 'texto': 'E sobre leitura, você praticou {dia}?', 'titulo': 'Leitura'},
    'estudar': {'coluna': 'Estudar', 'texto': 'Reservou um tempo para os estudos {dia}?', 'titulo': 'Estudar'},
    'alimentacao_saudavel': {'coluna': 'Alimentação_saudavel', 'texto': 'Sua alimentação foi saudável {dia}?', 'titulo': 'Alimentação'},
    'consumo_de_agua': {'coluna': 'Consumo_de_agua', 'texto': 'Bebeu água o suficiente {dia}?', 'titulo': 'Água'},
    'secreto': {'coluna': 'secreto', 'texto': 'Fumou {dia}?', 'titulo': 'Secreto'},
    'exercicio_aerobico': {'coluna': 'Exercício_aerobico', 'texto': 'Praticou atividade física {dia}?', 'titulo': 'Exercício'},
    'atividade_sexual': {'coluna': 'Atividade_sexual', 'texto': 'Fez sexo {dia}?', 'titulo': 'Sexo'}
}

TOPICOS_TEXTO = {
    'nota_humor_inicio': {'coluna': 'nota_humor', 'texto': 'Qual sua nota de humor ao acordar {dia}? (de 0 a 10)', 'tipo': 'nota', 'titulo': 'Humor Início'},
    'hora_acordei': {'coluna': 'data_hora_acordei', 'texto': 'Beleza. E que horas você acordou {dia}? (ex: 07:30)', 'tipo': 'hora', 'titulo': 'Hora Acordar'},
    'hora_dormir': {'coluna': 'data_hora_dormi', 'texto': 'Entendido. E que horas você foi dormir na noite anterior? (ex: 23:30)', 'tipo': 'hora_anterior', 'titulo': 'Hora Dormir'},
    'nota_humor_fim': {'coluna': 'Nota_humor_fim_dia', 'texto': 'Para finalizar, qual sua nota de humor ao ir dormir {dia}? (de 0 a 10)', 'tipo': 'nota', 'titulo': 'Humor Fim'}
}

# Colunas que o bot efetivamente registra — base para saber se um dia tem algo anotado.
COLUNAS_RASTREADAS = [v['coluna'] for v in {**TOPICOS_SIM_NAO, **TOPICOS_TEXTO}.values()]

def dia_tem_registro(registro):
    """True se o dia tem ao menos um hábito ou métrica preenchido."""
    return registro is not None and any(
        getattr(registro, coluna) is not None for coluna in COLUNAS_RASTREADAS
    )

def send_seletor_de_dia(sender_phone, session, qtd_dias=8):
    """Lista os últimos dias com status (✅ tem algo / ⬜️ vazio) + opção de digitar outra data."""
    hoje = data_hoje_brasil()
    rows = []
    for i in range(qtd_dias):
        dia = hoje - datetime.timedelta(days=i)
        registro = buscar_registro(session, dia, sender_phone)
        emoji = "✅" if dia_tem_registro(registro) else "⬜️"
        title = f"{emoji} {dia.strftime('%d/%m')} ({DIAS_SEMANA_PT[dia.weekday()]})"
        if i == 0:
            description = "hoje"
        elif i == 1:
            description = "ontem"
        else:
            description = "registrado" if dia_tem_registro(registro) else "vazio"
        rows.append({"id": f"escolher_dia_{dia.isoformat()}", "title": title[:24], "description": description[:72]})
    rows.append({"id": "escolher_outra_data", "title": "📅 Outra data"})
    sections = [{"title": "Últimos dias", "rows": rows}]
    send_list_message(sender_phone, "Diário", "Para qual dia você gostaria de registrar?", "Escolher dia", sections)

def send_dynamic_menu(sender_phone, session, registro, category, dia="hoje"):
    topicos_dict = TOPICOS_SIM_NAO if category == 'habitos' else TOPICOS_TEXTO
    header_text = "Hábitos" if category == 'habitos' else "Métricas"
    dia_texto = rotulo_dia(resolver_data(dia))
    rows = []
    for key, value in topicos_dict.items():
        resposta = getattr(registro, value['coluna'], None)
        coluna_nome = value['titulo']
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
                    resposta_brasil = resposta.astimezone(FUSO_BRASIL)
                    description = f"Resposta: {resposta_brasil.strftime('%H:%M')}"
                else:
                    description = f"Resposta: {resposta}"
        row_title = f"{status_emoji} {coluna_nome}"
        if len(row_title) > 24:
            row_title = row_title[:21] + "..."
        row_description = description
        if len(row_description) > 72:
            row_description = row_description[:69] + "..."
        rows.append({"id": f"ask_{key}_{dia}", "title": row_title, "description": row_description})

    rows.append({"id": f"show_menu_principal_{dia}", "title": "⬅️ Voltar"})
    section_title = f"{dia_texto.capitalize()}"[:24]
    sections = [{"title": section_title, "rows": rows}]
    send_list_message(sender_phone, f"Diário - {dia_texto.capitalize()}", header_text, "Opções", sections)

def limpar_status_conversa(session, sender_phone):
    """Zera o status_conversa de todos os registros do usuário.

    Garante uma única conversa ativa por vez: como o status é guardado por dia,
    sem isso vários dias podem ficar pendentes e o handler de texto (que busca por
    data desc) acabaria gravando a resposta no dia errado.
    """
    pendentes = session.query(Minha_vida).filter(
        Minha_vida.user_phone_number == sender_phone,
        Minha_vida.status_conversa.isnot(None)
    ).all()
    for registro in pendentes:
        registro.status_conversa = None

def buscar_registro(session, data, sender_phone):
    """Busca (sem criar) o registro de um dia para um usuário. Retorna None se não existir."""
    return session.query(Minha_vida).filter(
        func.date(func.timezone('America/Sao_Paulo', Minha_vida.data)) == data,
        Minha_vida.user_phone_number == sender_phone
    ).first()

def get_registro_por_data(session, data, sender_phone):
    """Busca o registro do dia; cria uma linha vazia se ainda não existir."""
    registro = buscar_registro(session, data, sender_phone)
    if not registro:
        data_inicio = FUSO_BRASIL.localize(datetime.datetime.combine(data, datetime.time(0, 0)))
        novo_registro = Minha_vida(data=data_inicio, user_phone_number=sender_phone)
        session.add(novo_registro)
        session.commit()
        registro = buscar_registro(session, data, sender_phone)
    return registro

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
            with pegar_sessao() as session:
                if message_info["type"] == "text" and message_info["text"]["body"].lower().strip() in ["iniciar", "oi", "diario", "menu"]:
                    send_seletor_de_dia(sender_phone, session)
                    return {"status": "ok"}

                elif message_info["type"] == "interactive":
                    interactive_type = message_info["interactive"]["type"]
                    payload = message_info["interactive"][interactive_type]["id"]

                    if payload == 'escolher_outra_data':
                        registro = get_registro_por_data(session, data_hoje_brasil(), sender_phone)
                        limpar_status_conversa(session, sender_phone)
                        registro.status_conversa = "aguardando_data_livre"
                        session.commit()
                        send_whatsapp_message(sender_phone, "Digite a data que você quer registrar (ex: 05/06 ou 05/06/2025):")
                        return {"status": "ok"}

                    if payload.startswith('escolher_dia_'):
                        dia_escolhido = payload.replace('escolher_dia_', '')
                        data_referencia = resolver_data(dia_escolhido)
                        registro = get_registro_por_data(session, data_referencia, sender_phone)
                        texto = f"Você selecionou {rotulo_dia(data_referencia)}. O que você gostaria de registrar?"
                        botoes = [
                            {"title": "💪 Registrar Hábitos", "payload": f"show_menu_habitos_{dia_escolhido}"},
                            {"title": "📊 Registrar Métricas", "payload": f"show_menu_metricas_{dia_escolhido}"}
                        ]
                        send_button_message(sender_phone, texto, botoes)
                        return {"status": "ok"}

                    if payload.startswith('show_menu_'):
                        parts = payload.split('_')
                        category = parts[2] if len(parts) > 2 else 'principal'
                        dia_escolhido = parts[3] if len(parts) > 3 else 'hoje'
                        data_referencia = resolver_data(dia_escolhido)
                        registro = get_registro_por_data(session, data_referencia, sender_phone)
                        if category == 'principal':
                            send_seletor_de_dia(sender_phone, session)
                        else:
                            send_dynamic_menu(sender_phone, session, registro, category, dia_escolhido)
                        return {"status": "ok"}

                    if payload.startswith('ask_'):
                        rest = payload[len('ask_'):]
                        try:
                            topic_key, dia_escolhido = rest.rsplit('_', 1)
                        except ValueError:
                            topic_key = rest
                            dia_escolhido = 'hoje'
                        data_referencia = resolver_data(dia_escolhido)
                        registro = get_registro_por_data(session, data_referencia, sender_phone)
                        if topic_key in TOPICOS_SIM_NAO:
                            topic_info = TOPICOS_SIM_NAO[topic_key]
                            coluna = topic_info['coluna']
                            estado_atual = getattr(registro, coluna)
                            novo_estado = not estado_atual if estado_atual is not None else True
                            setattr(registro, coluna, novo_estado)
                            session.commit()
                            acao = "marcada como feita" if novo_estado else "marcada como não feita"
                            send_whatsapp_message(sender_phone, f"✅ Hábito {acao}!")
                            send_dynamic_menu(sender_phone, session, registro, 'habitos', dia_escolhido)
                        elif topic_key in TOPICOS_TEXTO:
                            topic_info = TOPICOS_TEXTO[topic_key]
                            texto_pergunta = topic_info['texto'].format(dia=rotulo_dia(data_referencia))
                            limpar_status_conversa(session, sender_phone)
                            registro.status_conversa = f"aguardando_{topic_key}_{dia_escolhido}"
                            session.commit()
                            send_whatsapp_message(sender_phone, texto_pergunta)
                        return {"status": "ok"}

                elif message_info["type"] == "text":
                    registro = session.query(Minha_vida).filter(
                        Minha_vida.user_phone_number == sender_phone,
                        Minha_vida.status_conversa.isnot(None)
                    ).order_by(Minha_vida.data.desc()).first()
                    if registro and registro.status_conversa:
                        texto_usuario = message_info["text"]["body"]
                        status = registro.status_conversa
                        if status == "aguardando_data_livre":
                            registro.status_conversa = None
                            session.commit()
                            data_alvo = parse_data_usuario(texto_usuario)
                            if data_alvo is None:
                                send_whatsapp_message(sender_phone, "Não entendi a data. Tente no formato 05/06 ou 05/06/2025.")
                                return {"status": "ok"}
                            if data_alvo > data_hoje_brasil():
                                send_whatsapp_message(sender_phone, "Essa data ainda não chegou. 😅 Escolha hoje ou um dia passado.")
                                return {"status": "ok"}
                            get_registro_por_data(session, data_alvo, sender_phone)
                            dia_iso = data_alvo.isoformat()
                            texto = f"Você selecionou {rotulo_dia(data_alvo)}. O que você gostaria de registrar?"
                            botoes = [
                                {"title": "💪 Registrar Hábitos", "payload": f"show_menu_habitos_{dia_iso}"},
                                {"title": "📊 Registrar Métricas", "payload": f"show_menu_metricas_{dia_iso}"}
                            ]
                            send_button_message(sender_phone, texto, botoes)
                            return {"status": "ok"}
                        if status.startswith("aguardando_"):
                            rest = status[len("aguardando_"):]
                            try:
                                topic_key, dia_escolhido = rest.rsplit('_', 1)
                            except ValueError:
                                topic_key = rest
                                dia_escolhido = 'hoje'
                        else:
                            topic_key = None
                            dia_escolhido = 'hoje'
                        data_referencia = resolver_data(dia_escolhido)
                        registro = get_registro_por_data(session, data_referencia, sender_phone)
                        if topic_key in TOPICOS_TEXTO:
                            topic_info = TOPICOS_TEXTO[topic_key]
                            coluna = topic_info['coluna']
                            try:
                                if topic_info['tipo'] == 'nota':
                                    nota = float(texto_usuario.replace(',', '.'))
                                    if not (0 <= nota <= 10):
                                        raise ValueError("Nota fora do intervalo")
                                    setattr(registro, coluna, nota)
                                elif topic_info['tipo'] == 'hora':
                                    hora_obj = datetime.datetime.strptime(texto_usuario, '%H:%M').time()
                                    data_completa = datetime.datetime.combine(data_referencia, hora_obj)
                                    data_completa_brasil = FUSO_BRASIL.localize(data_completa)
                                    setattr(registro, coluna, data_completa_brasil)
                                elif topic_info['tipo'] == 'hora_anterior':
                                    hora_obj = datetime.datetime.strptime(texto_usuario, '%H:%M').time()
                                    data_anterior = data_referencia - datetime.timedelta(days=1)
                                    data_completa = datetime.datetime.combine(data_anterior, hora_obj)
                                    data_completa_brasil = FUSO_BRASIL.localize(data_completa)
                                    setattr(registro, coluna, data_completa_brasil)
                                registro.status_conversa = None
                                session.commit()
                                send_whatsapp_message(sender_phone, "Anotado! ✅")
                                send_dynamic_menu(sender_phone, session, registro, 'metricas', dia_escolhido)
                            except ValueError:
                                send_whatsapp_message(sender_phone, "Resposta inválida. Por favor, tente novamente.")
                                send_whatsapp_message(sender_phone, topic_info['texto'].format(dia=rotulo_dia(data_referencia)))
                        return {"status": "ok"}
    except Exception as e:
        print(f"!!!!!!!!!! ERRO CRÍTICO NO WEBHOOK !!!!!!!!!!!")
        print(f"Erro: {e}")
        traceback.print_exc()
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
