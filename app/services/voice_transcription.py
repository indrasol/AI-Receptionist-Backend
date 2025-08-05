import audioop
import base64
import json
import os
from flask import Flask, request
from flask_sock import Sock, ConnectionClosed
from twilio.twiml.voice_response import VoiceResponse, Start
from twilio.rest import Client
import vosk

voice_service = Flask(__name__)
sock = Sock(voice_service)
twilio_client = Client()
model = vosk.Model('models/vosk-model-small-en-us-0.15')

CL = '\x1b[0K'
BS = '\x08'


@voice_service.route('/call', methods=['POST'])
def call(request=None):
    """Accept a phone call."""
    print("\n\n\n call received")
    # TODO


@sock.route('/stream')
def stream(ws):
    """Receive and transcribe audio stream."""
    # TODO


# Flask app is now integrated into FastAPI
# The main function has been removed since this will be part of the FastAPI server 