import os

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
    elif "Creek" == request.cookies.get('Stop', None):
        response.redirect('/player/creek')
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


@app.route('/player/creek', methods=['GET', 'POST'])
def player_creek():
    response = MessagingResponse()

    if "YES" in request.form['Body'].upper():
        response.message("Awesome! Our first stop is nearby. To "
                         "help kick of your journey, we got a little help "
                         "from a familiar face. Click this link to receive "
                         "your clue: {0}".format(url_for('video',
                                                         location='fish',
                                                         _external=True)))

        resp = make_response(str(response))

        client.messages.create(from_=app.config['TWILIO_CALLER_ID'],
                               to=app.config['TWILIO_GM'],
                               body="Video for Creek delivered.")

    elif "CLUE" == request.form['Body'].upper():
        clue_counter = request.cookies.get('Clue', None)
        if not clue_counter or clue_counter == "0":
            clue_counter = 0

            response.message("This creek always bore the same name, but it "
                             "was spelled very differently over the years. "
                             "Weelewaughmack, Weelewaughwemack, "
                             "Willikwernock, Willerwhemack, Willowwemoc, "
                             "Williwemock... some fishermen just call it "
                             "Willow.")

            resp = make_response(str(response))
            resp.set_cookie("Clue", "1")
        elif clue_counter == "1":
            response.message("To find the creek's most famous fish, there are "
                             "some resources around you. Maybe see if someone "
                             "from the Livingston Manor Fly Fishing Club "
                             "is around or run a few minutes north on "
                             "Route 17 to the Catskill Fly Fishing Museum.")
            response.message("Nothing says \"I just turned 40\" like a "
                             "fishing museum. Awwwwwww yeah.")

            resp = make_response(str(response))
            resp.set_cookie("Clue", "2")
        elif clue_counter == "2":
            response.message("You don't have to wade hip deep to capture this "
                             "photo - a screenshot off Google will work fine. "
                             "We're just looking for the most popular fish!")

            resp = make_response(str(response))
            resp.set_cookie("Clue", "0")

        client.messages.create(from_=app.config['TWILIO_CALLER_ID'],
                               to=app.config['TWILIO_GM'],
                               body="Clue {0} for Creek requested."
                                    "".format(clue_counter))
    else:
        client.messages.create(from_=app.config['TWILIO_CALLER_ID'],
                               to=app.config['TWILIO_GM'],
                               body=request.form['Body'])

        resp = make_response(str(response))

    return resp


@app.route('/video/<location>')
def video(location):
    if location == "fish":
        title = "A Sashimi Start"
        video = url_for('static', filename='video/ktrevorwilson.mp4')

    return render_template('video.html', video=video, title=title)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    if port == 5000:
        app.debug = True
    app.run(host='0.0.0.0', port=port)
