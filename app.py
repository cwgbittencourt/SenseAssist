# -*- coding: utf-8 -*-
"""
SenseAssist - Assistente de Voz

Copyright (c) 2023 Carlos Gabriel Souza Bittencourt, Carlos Wagner Gonçalves Bittencourt, Dyego Barros
Licenciado sob a Licença MIT. Veja o arquivo LICENSE para mais informações.
"""

import sys
import speech_recognition as sr
import pyttsx3
import json
import markdown
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextBrowser, QLabel, QInputDialog
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QScreen
from dotenv import load_dotenv
import re

from langflow.load import run_flow_from_json

message = ""
load_dotenv()

# Nome do arquivo onde a palavra de ativação será armazenada
activation_word_file = 'activation_word.json'


class ChatGPTApp(QWidget):
    def __init__(self):
        super().__init__()

        # Carrega ou define a palavra de ativação
        self.activation_word = self.load_or_set_activation_word()
        

        self.init_ui()

        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'portuguese' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

        self.engine.say(f'Bem-vindo ao Assistente de Voz! Use a palavra {self.activation_word} para ativar a pesquisa do assistente.')
        self.engine.runAndWait()
        
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)

        self.stop_listening = self.recognizer.listen_in_background(
            self.microphone, self.callback)

    def load_or_set_activation_word(self):
        """Carrega a palavra de ativação de um arquivo local, ou pede ao usuário para definir uma."""
        if os.path.exists(activation_word_file):
            with open(activation_word_file, 'r') as f:
                data = json.load(f)
                return data.get('activation_word', 'sense')
        else:
            # Pede ao usuário para definir a palavra de ativação
            word, ok = QInputDialog.getText(self, 'Configurar Palavra de Ativação', 
                                            'Escolha uma palavra de ativação:')
            if ok and word:
                # Persiste a palavra de ativação em um arquivo local
                with open(activation_word_file, 'w') as f:
                    json.dump({'activation_word': word.strip().lower()}, f)
                return word.strip().lower()
            else:
                return 'sense'  # Palavra padrão caso o usuário não defina nada

    def init_ui(self):
        self.setWindowTitle(f'Assistente de Voz - Palavra de ativação: "{self.activation_word.capitalize()}"')
        
        # Obtém o tamanho da tela
        screen_geometry = QScreen.availableGeometry(QApplication.primaryScreen())
        screen_height = screen_geometry.height()

        # Define a altura da janela para 90% da altura da tela
        window_height = int(screen_height * 0.9)
        
        
        self.setGeometry(100, 100, 600, window_height)

        self.layout = QVBoxLayout()
        
        self.image_label = QLabel(self)
        pixmap = QPixmap('image/logo_SA.png')  # Substitua pelo caminho para sua imagem
        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.image_label)

        self.label = QLabel(f'Bem-vindo ao Assistente de Voz - Use "{self.activation_word.capitalize()}" para ativar')
        self.label.setFont(QFont('Arial', 16))
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)

        self.ready_label = QLabel('Aguardando comando...')
        self.ready_label.setFont(QFont('Arial', 14))
        self.ready_label.setAlignment(Qt.AlignCenter)
        self.ready_label.setStyleSheet("color: blue;")
        self.layout.addWidget(self.ready_label)

        self.text_area = QTextBrowser()
        self.text_area.setReadOnly(True)
        self.text_area.setFont(QFont('Arial', 12))
        self.layout.addWidget(self.text_area)

        self.setLayout(self.layout)

    def sinalizar_pronto_para_ouvir(self):
        self.ready_label.setText("Pronto para ouvir!")
        self.ready_label.setStyleSheet("color: green;")

    def remove_links_da_leitura(self, text: str):
        clean_text = re.sub(r'\(http.*?\)', '', text)
        return clean_text

    def callback(self, recognizer, audio):
        try:
            print('Reconhecendo...')
            #self.text_area.setStyleSheet("background-color: lightgreen;")
            self.sinalizar_pronto_para_ouvir()
            text = recognizer.recognize_google(audio, language='pt-BR')
            words = text.strip().split()

            if words and words[0].lower() == self.activation_word:
                message = ' '.join(words[1:])
                self.text_area.append(f"<b>Você:</b> {message.capitalize()}")
                self.engine.say(f'Pesquisando, {message}.')
                self.engine.runAndWait()
                response = self.get_langflow_response(message)

                markdown_response = markdown.markdown(response)
                self.text_area.append(f"<b>{self.activation_word.capitalize()}:</b> {markdown_response}")

                print(f'{self.activation_word}:', response)
                sense_diz = self.remove_links_da_leitura(text=response)
                sense_diz = sense_diz.replace('*', '').replace('#', '')
                self.engine.say(sense_diz)
                self.engine.runAndWait()

        except sr.UnknownValueError as e:
            print(f"Aguardando comando... {e}")
        except sr.RequestError as e:
            self.text_area.append(f"Erro no serviço de reconhecimento de fala: {e}\n")

    def get_langflow_response(self, message):
        print(f'Message: {message}')
        with open('SenseFlow.json', 'r') as f:
            flow_json = json.load(f)

        TWEAKS = {
            "ComposioAPI-WfTao": {
                    "action_names": [
                    "WEATHERMAP_WEATHER"
                    ],
                    "api_key": os.getenv("COMPOSIO_API_KEY"),
                    "app_names": "WEATHERMAP",
                    "auth_status_config": "WEATHERMAP CONNECTED",
                    "entity_id": "default"
                },
                "Prompt-aktgV": {
                    "template": "{context}\nQuando algo for solicitado como vídeo, notícias atuais não forneça uma resposta genérica com links que levem a outro canal de informação. \nVocê deve fornecer a informação conforme detalhado abaixo.\nSe a pergunta é relacionada ao clima de uma cidade utilize o Composio  WHEATERMAP\nOu se a pesquisa estiver relacionada ao email utilize o Composio GMAIL\nOu caso ainda não tenha uma resposta utilize o Wikipedia\nOu caso o assunto seja sobre vídeo utilize o Composio YOUTUBE\nOu  se for o caso de buscar Notícias, utilize o Comosio SERPAPI_DUCK_DUCK_GO\nCaso contrário responda você mesmo\nSempre, e em todos os casos, Informe abaixo de cada resultado qual foi a ferramenta que forneceu a resposta.",
                    "context": ""
                },
                "ToolCallingAgent-LmeiW": {
                    "handle_parsing_errors": True,
                    "input_value": "",
                    "max_iterations": 15,
                    "system_prompt": "",
                    "user_prompt": "{input}",
                    "verbose": True
                },
                "ChatInput-PUigP": {
                    "files": "",
                    "input_value": message,
                    "sender": "User",
                    "sender_name": "User",
                    "session_id": "",
                    "should_store_message": True
                },
                "ChatOutput-y42uJ": {
                    "data_template": "{text}",
                    "input_value": "",
                    "sender": "Machine",
                    "sender_name": "AI",
                    "session_id": "",
                    "should_store_message": True
                },
                "OpenAIModel-WTeze": {
                    "api_key": os.getenv("OPENAI_KEY"),
                    "input_value": "",
                    "json_mode": False,
                    "max_tokens": None,
                    "model_kwargs": {},
                    "model_name": "gpt-4o-mini",
                    "openai_api_base": "",
                    "output_schema": {},
                    "seed": 1,
                    "stream": False,
                    "system_message": "",
                    "temperature": 0.1
                },
                "WikipediaAPI-1Uq4c": {
                    "doc_content_chars_max": 4000,
                    "input_value": "",
                    "k": 4,
                    "lang": "br",
                    "load_all_available_meta": False
                },
                "ComposioAPI-M5X1s": {
                    "action_names": [
                    "YOUTUBE_LIST_CAPTION_TRACK",
                    "YOUTUBE_SEARCH_YOU_TUBE",
                    "YOUTUBE_LOAD_CAPTIONS"
                    ],
                    "api_key": os.getenv("COMPOSIO_API_KEY"),
                    "app_names": "YOUTUBE",
                    "auth_status_config": "YOUTUBE CONNECTED",
                    "entity_id": "default"
                },
                "ComposioAPI-zI5Y3": {
                    "action_names": [
                    "SERPAPI_DUCK_DUCK_GO_SEARCH"
                    ],
                    "api_key": os.getenv("COMPOSIO_API_KEY"),
                    "app_names": "SERPAPI",
                    "auth_status_config": "SERPAPI CONNECTED",
                    "entity_id": "default"
                },
                "ComposioAPI-CqcBn": {
                    "action_names": [
                    "GMAIL_ADD_LABEL_TO_EMAIL",
                    "GMAIL_FETCH_EMAILS",
                    "GMAIL_SEND_EMAIL"
                    ],
                    "api_key": os.getenv("COMPOSIO_API_KEY"),
                    "app_names": "GMAIL",
                    "auth_status_config": "GMAIL CONNECTED",
                    "entity_id": "default"
                },
                "Memory-tcSkV": {
                    "n_messages": 100,
                    "order": "Ascending",
                    "sender": "Machine and User",
                    "sender_name": "",
                    "session_id": "",
                    "template": "{sender_name}: {text}"
                }
        }

        result = run_flow_from_json(flow="SenseFlow.json",
                                    input_value=message,
                                    fallback_to_env_vars=True,
                                    tweaks=TWEAKS)

        response_text = result[0].outputs[0].results['message'].data['text']
        return response_text.strip()

    def closeEvent(self, event):
        if self.stop_listening:
            self.stop_listening(wait_for_stop=False)
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ChatGPTApp()
    ex.show()
    sys.exit(app.exec_())
