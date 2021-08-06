import os

from flask import Flask
from flask import request
from flask import make_response

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


@app.route('/player', methods=['GET', 'POST'])
def player():
    response = MessagingResponse()

    if "HELP" == request.form['Body'].upper():
        response.message("Text CLUE to get another hint about where you "
                         "need to go.\nText STUCK to summon the bat signal "
                         "and get additional assistance.\nIf you have "
                         "another question, just text to connect with our "
                         "AI.\nHave fun!")
        resp = make_response(str(response))
    elif "STUCK" == request.form['Body'].upper():
        response.message("Help is on the way!")
        resp = make_response(str(response))

        client.messages.create(from_=app.config['TWILIO_CALLER_ID'],
                               to=app.config['TWILIO_GM'],
                               body="Player is indicating she is stuck.")
    elif "YES" in request.form['Body'].upper():
        response.message("Awesome! Gather up your crew and get stoked for "
                         "a rad photo scavenger hunt around lovely Livingston "
                         "Manor. A few folks you might know are going to give "
                         "you clues of locations you will need to go. To "
                         "memorialize this time with your besties, snag a "
                         "picture with your fellow Scavengers at each spot. "
                         "If you find all the locations, a special surprise "
                         "awaits!")
        response.message("If you ever need assistance on your journey, text "
                         "HELP to see all the available options. If you're "
                         "confused by a particular hint, text CLUE to get "
                         "up to 3 additional hints on where to go. If you're "
                         "still stuck after that, just text me here and "
                         "our hyper intelligent machine learning algorithm "
                         "will determine how to help.")
        response.message("Are you ladies ready to go? Text YES or NO.")

        resp = make_response(str(response))
        resp.set_cookie("Stop", "Creek")

        client.messages.create(from_=app.config['TWILIO_CALLER_ID'],
                               to=app.config['TWILIO_GM'],
                               body="Game started.")
    elif "NO" == request.form['Body'].upper():
        response.message("Ah, c'mon now. Rob spent a time on this. It'll "
                         "be fun! Text YES to get going.")
        resp = make_response(str(response))
    else:
        response.message("Text HELP for a list of the options. Text YES to "
                         "start the scavenger hunt!")
        resp = make_response(str(response))

    return resp


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    if port == 5000:
        app.debug = True
    app.run(host='0.0.0.0', port=port)
