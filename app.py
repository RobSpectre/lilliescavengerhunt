import os

from flask import Flask
from flask import request

from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import Hangup
from twilio.twiml.voice_response import VoiceResponse
from twilio.twiml.voice_response import Say


app = Flask(__name__, static_url_path='/static')
app.config.from_pyfile('local_settings.py')

client = Client(app.config['TWILIO_ACCOUNT_SID'],
                app.config['TWILIO_AUTH_TOKEN'])


@app.route('/voice', methods=['GET', 'POST'])
def voice():
    response = VoiceResponse()

    say = Say("You have reached Lillie's 40th birthday scavenger hunt.",
              voice="Polly.Kimberly-Neural")
    say.break_(strength="x-weak", time="100ms")
    say.append("If you need help with the next step, text the word HELP"
               " to this phone number. If you need a clue, text the word "
               "CLUE. If you are still stuck, just text "
               "your question to this number.")
    say.break_(strength="x-weak", time="100ms")
    say.append("Goodbye!")

    response.append(say)

    hangup = Hangup()
    response.append(hangup)

    return str(response)


@app.route('/sms', methods=['GET', 'POST'])
def sms():
    response = MessagingResponse()

    if request.form['From'] == app.config.get('TWILIO_GM'):
        response.redirect('/gm')
    else:
        response.redirect('/player')

    return str(response)


@app.route('/gm', methods=['GET', 'POST'])
def gm():
    response = MessagingResponse()

    if "START" in request.form['Body']:
        body = "Awwwwwwwwwww... BERFDAY TIME! Lillie - are you ready " \
               "for a fun adventure to kick off your 40th? " \
               "" \
               "Text YES or NO."
        response.message("Message sent.")
    else:
        body = request.form['Body']

    client.messages.create(from_=app.config['TWILIO_CALLER_ID'],
                           to=app.config['TWILIO_PLAYER'],
                           body=body)

    return str(response)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    if port == 5000:
        app.debug = True
    app.run(host='0.0.0.0', port=port)
