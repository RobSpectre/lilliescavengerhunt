import os
import json

from flask import Flask
from flask import make_response
from flask import request
from flask import render_template
from flask import url_for

from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import Hangup
from twilio.twiml.voice_response import VoiceResponse
from twilio.twiml.voice_response import Say


app = Flask(__name__, static_url_path='/static')
app.config.from_pyfile('local_settings.py')


with open('static/data/game.json') as f:
    app.config['Game'] = json.load(f)


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

    send_player_message(body)

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

        send_gm_message("Player is indicating she is stuck.")
    elif request.cookies.get('Stop', None):
        response.redirect('/player/{0}'.format(request.cookies.get('Stop')))
        resp = make_response(str(response))
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
        resp.set_cookie("Stop", "Fish")

        send_gm_message("Game started.")
    elif "NO" == request.form['Body'].upper():
        response.message("Ah, c'mon now. Rob spent a time on this. It'll "
                         "be fun! Text YES to get going.")
        resp = make_response(str(response))
    else:
        response.message("Text HELP for a list of the options. Text YES to "
                         "start the scavenger hunt!")
        resp = make_response(str(response))

    return resp


@app.route('/player/<stop>', methods=['GET', 'POST'])
def player_game(stop):
    response = MessagingResponse()

    data = app.config['Game']['Stop'][stop]

    num_media = request.form.get('NumMedia', None)

    if "YES" in request.form['Body'].upper():
        for message in data['Introduction']['Messages']:
            response = reply_message(response, message, stop)

        resp = make_response(str(response))

        send_gm_message("Video for {0} delivered.".format(stop))

    elif "CLUE" == request.form['Body'].upper():
        clue_counter = request.cookies.get('Clue', None)
        if clue_counter:
            clue_counter = int(clue_counter)
        if not clue_counter or clue_counter == "0":
            clue_counter = 0

        for message in data['Clues'][clue_counter]['Messages']:
            response = reply_message(response, message, stop)

        send_gm_message("Clue {0} for {1} requested."
                        "".format(clue_counter, stop))

        resp = make_response(str(response))

        clue_counter = clue_counter + 1

        if clue_counter > 2:
            clue_counter = 0

        resp.set_cookie("Clue", str(clue_counter))

    elif num_media and int(num_media) > 0:
        for n in range(0, int(num_media)):
            media_number = 'MediaUrl{0}'.format(str(n))
            send_gm_message("Photo received for {0}.".format(stop),
                            media_url=request.form[media_number])

        for message in data['Victory']['Messages']:
            if stop == "Brewery":
                response = reply_message(response, message, "Rob")
            else:
                response = reply_message(response, message, stop)

        resp = make_response(str(response))
        resp.set_cookie("Stop", data['Victory']['Next'])
        resp.set_cookie("Clue", "0")
    else:
        send_gm_message(request.form['Body'])

        resp = make_response(str(response))

    return resp


@app.route('/video/<location>')
def video(location):
    if location == "Fish":
        title = "Start with Sashimi"
        video = url_for('static', filename='video/kamillakowal.mp4')
        thumbnail = url_for('static', filename='images/janisjoplin.png')
    elif location == "Bridge":
        title = "Over Troubled Waters"
        video = url_for('static', filename='video/patrickmcneil.mp4')
        thumbnail = url_for('static', filename='images/joecocker.png')
    elif location == "Farm":
        title = "Camelids Have More Fun"
        video = url_for('static', filename='video/dylanplayfair.mp4')
        thumbnail = url_for('static', filename='images/jimihendrix.png')
    elif location == "Synagogue":
        title = "Brothers and Sisters"
        video = url_for('static', filename='video/ktrevorwilson.mp4')
        thumbnail = url_for('static', filename='images/arloguthrie.png')
    elif location == "Brewery":
        title = "Puppers Time"
        video = url_for('static', filename='video/nathandales.mp4')
        thumbnail = url_for('static', filename='images/bobweir.png')
    elif location == "Rob":
        title = "Happy Berfday Lillie!"
        video = url_for('static', filename='video/robspectre.mp4')
        thumbnail = url_for('static', filename='images/rogerdaltrey.png')
    else:
        title = "File Not Found"
        video = url_for('static', filename='video/sadtrombone.mp4')
        thumbnail = None
        return render_template('video.html', video=video, title=title), 404

    return render_template('video.html', video=video, title=title,
                           thumbnail=thumbnail)


def send_player_message(body, media_url=None):
    if media_url:
        msg = client.messages.create(from_=app.config['TWILIO_CALLER_ID'],
                                     to=app.config['TWILIO_PLAYER'],
                                     body=body,
                                     media_url=media_url)
    else:
        msg = client.messages.create(from_=app.config['TWILIO_CALLER_ID'],
                                     to=app.config['TWILIO_PLAYER'],
                                     body=body)

    return msg


def send_gm_message(body, media_url=None):
    if media_url:
        msg = client.messages.create(from_=app.config['TWILIO_CALLER_ID'],
                                     to=app.config['TWILIO_GM'],
                                     body=body,
                                     media_url=media_url)
    else:
        msg = client.messages.create(from_=app.config['TWILIO_CALLER_ID'],
                                     to=app.config['TWILIO_GM'],
                                     body=body)

    return msg


def reply_message(response, message, stop):
    if message.get('Path', None):
        response.message(message['Body'].format(url_for(message['Path'],
                                                        location=stop,
                                                        _external=True)))
    elif message.get('Media', None):
        msg = response.message(message['Body'])
        msg.media(message['Media'])
    else:
        response.message(message['Body'])

    return response


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    if port == 5000:
        app.debug = True
    app.run(host='0.0.0.0', port=port)
