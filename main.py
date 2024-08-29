from flask import Flask, make_response, request, send_file, Response, redirect
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

from garminconnect import *
from garminconnect_tools import *
from ics import Calendar, Event
import os
import shutil
import json

@app.before_request
def before_request_func():
    try:
        os.mkdir('garminconnect_auth')
    except:
        pass

@app.route('/')
def index():
    return open('index.html','r').read()

@app.route('/get-token')
def getToken():
    email = request.args.get('email')
    password = request.args.get('password')

    api = init_api(email, password, tokenstore='garminconnect_auth')

    oauth1_token = json.loads(open('garminconnect_auth/oauth1_token.json','r').read())
    oauth2_token = json.loads(open('garminconnect_auth/oauth2_token.json','r').read())
    tokens = [oauth1_token,oauth2_token]
  
    response = {'name':api.full_name, 'tokens':tokens}
    response = json.dumps(response, indent=4)
    response = make_response(response, 200)
    response.mimetype = "text/plain"
    return response

@app.route('/calendar')
def calendar():
    c = Calendar()
    tokens = request.args.get('tokens')

    # Setting up the language
    lang = request.args.get('lang')
    if lang != 'fr':
        lang = 'en'
    lang = 'fr'

    # Connection using tokens
    tokens = json.loads(tokens)
    open('garminconnect_auth/oauth1_token.json','w').write(json.dumps(tokens[0]))
    open('garminconnect_auth/oauth2_token.json','w').write(json.dumps(tokens[1]))
    api = init_api(email=email, password=password, tokenstore='./garminconnect_auth')

    # Get activities
    activities = api.get_activities_by_date(startdate.isoformat(), today.isoformat())
    
    for activity in activities:
        #print(json.dumps(activity, indent=4))
        type = activity['activityType']['typeKey']

        activitiesLabels = {
            'running':'🏃‍♂️ Running',
            'walking':'🥾 Walking',
            'cycling' : '🚴 Cycling',
            'swimming' : '🏊 Swimming',
            'strength_training':'🏋️ Strength training',
            'basketball':'🏀 Basketball',
            'hiking':'🏔️ Hiking',
            'single_gas_diving':'🤿 Diving',
            'other':'❔ Other'
        }
        activitiesLabelsFR = {
            'running':'🏃‍♂️ Course',
            'walking':'🥾 Marche',
            'cycling' : '🚴 Cyclisme',
            'swimming' : '🏊 Natation',
            'strength_training':'🏋️ Musculation',
            'basketball':'🏀 Basketball',
            'hiking':'🏔️ Randonnée',
            'single_gas_diving':'🤿 Plongée',
            'other':'❔ Autre'
        }
        if lang == 'fr':
            activitiesLabels = activitiesLabelsFR

        if type in activitiesLabels:
            label = activitiesLabels[type]
        else : 
            label = type

        # Create an event
        e = Event()
        e.begin = activity['startTimeGMT']
        e.end = str(datetime.datetime.strptime(activity['startTimeGMT'], '%Y-%m-%d %H:%M:%S') + datetime.timedelta(seconds=activity['distance']))
        e.description = ''

        if 'locationName' in activity:
            e.location = activity['locationName']

        if 'activityName' in activity:
            e.description += str(activity['activityName'])

        e.description += '\n'
        if 'maxDepth' in activity:
            e.description += '\n🌊 Maximum depth : '+str(round(activity['maxDepth']/100))+'m'

        if 'distance' in activity and activity['distance'] !=0:
            e.description += '\n🗺️ Distance : '+str(round(activity['distance']/1000,2))+'km'
        if 'duration' in activity:
            e.description += '\n⏱️ Duration : '
            str_duration = ''
            if activity['duration']/60 > 60:
                str_duration += str(round(activity['duration']/60//60))+'h'
                str_duration += str(round(activity['duration']/60 - activity['duration']/60//60*60))+'min'
            else:
                str_duration += str(round(activity['duration']/60,2))+'min'
            e.description += str_duration

        e.description += '\n'
        if 'averageSpeed' in activity and activity['averageSpeed'] != 0:
            e.description += '\n🚀 Average speed : '+str(round(activity['averageSpeed'],2))+'m/s'
        if 'maxSpeed' in activity:
            e.description += '\n🚀 Maximum speed : '+str(round(activity['maxSpeed'],2))+'m/s'

        e.description += '\n'
        if 'elevationGain' in activity:
            e.description += '\n📈 Elevation Gain : '+str(round(activity['elevationGain']))+'m'
        if 'elevationLoss' in activity:
            e.description += '\n📉 Elevation Loss : '+str(round(activity['elevationLoss']))+'m'

        e.description += '\n'
        if 'calories' in activity:
            e.description += '\n🔥 Calories : '+str(round(activity['calories']))

        e.description += '\n'
        if 'averageHR' in activity:
            e.description += '\n🫀 Average heart rate : '+str(round(activity['averageHR']))+'bpm'
        if 'maxHR' in activity:
            e.description += '\n🫀 Maximum heart rate : '+str(round(activity['maxHR']))+'bpm'

        e.description += '\n'
        if 'averageRunningCadenceInStepsPerMinute' in activity:
            e.description += '\n👣 Average cadence : '+str(round(activity['averageRunningCadenceInStepsPerMinute']))+' steps per minute'
        if 'maxRunningCadenceInStepsPerMinute' in activity:
            e.description += '\n👣 Maximum cadence : '+str(round(activity['maxRunningCadenceInStepsPerMinute']))+' steps per minute'

        e.description += '\n'
        if 'startLatitude' in activity and 'startLongitude' in activity:            
            e.description += '\n📍 Position : '+str(activity['startLatitude']) +' '+ str(activity['startLongitude'])

        # not working because iOS identifies it as a number phone
        #if 'activityId' in activity:
        #    e.description += '\n🆔 '+str(activity['activityId'])

        # Improve the name
        if type in ['running','walking','cycling','swimming','hiking']: # special cases
            e.name = label+' : '+str(round(activity['distance']/1000,2))+'km in '+str_duration
        elif 'diving' in type: # Diving
            e.name = label+' : '+str_duration+' at '+str(round(activity['maxDepth']/100))+'m'
        else:
            e.name = label+' : '+str_duration

        #print(e.name)
        #print(e.description)

        c.events.add(e)

    data = c.serialize()

    response = data
    response = make_response(response, 200)
    response.mimetype = "text/calendar"
    return response

@app.after_request
def after_request_func(response):
    try:
        shutil.rmtree('garminconnect_auth')
    except:
        pass
    return response


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=1234)