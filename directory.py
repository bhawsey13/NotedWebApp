from flask import Flask, redirect, url_for, request, render_template, session, make_response
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from flask_moment import Moment
from bson.objectid import ObjectId
import os
import bcrypt
import pdfkit
import re
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
import nltk
nltk.data.path.append('nltk_data')
from elevenlabs.client import ElevenLabs
from elevenlabs import save


#Flask app object
app = Flask(__name__)


#secret key
app.secret_key = os.getenv('SECRET_KEY')


#Configure session
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_SECURE'] = True      #Only send cookies over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True    #Protect against XSS


#Configure DB connection
uri = os.getenv('MONGODB_URI')
dbclient = MongoClient(uri, server_api=ServerApi('1'))
db = dbclient.NotedWebApp
notes = db.notes
users = db.users


#configure Moment for capturing timezone accurate DateTime
moment = Moment(app)


#configure ElevenLabs api
elclient = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))


#function for detecting special characters
def containsSpecialChars(text):
    return "$" in text or "@" in text or ";" in text or "%" in text or "=" in text or "?" in text or "#" in text or "(" in text or ")" in text or "<" in text or ">" in text or "{" in text or "}" in text




#Start of directory:

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/createNote", methods=['GET', 'POST'])
def createNote():
    if session.get('username', None) == None:
        return redirect(url_for('login'))

    errorMessage = None
    if request.method == 'POST':
        noteName = request.form['name']
        if noteName == "" :
            errorMessage = "Name field cannot be empty.  Please enter a valid name."
        elif noteName[0] == " ":
            errorMessage = "Name field cannot start with a space.  Please enter a valid name."
        elif containsSpecialChars(noteName):
            errorMessage = "Name field cannot contain special characters such as $, @, ;, %, =, ?, #, (), <> or {}.  Please enter a valid name."
        elif len(noteName)  > 60:
            errorMessage = "Name field too long.  Please enter a name less than 60 characters."
        else:
            noteID = ObjectId()
            creatorID = users.find_one({'username': session.get('username', None)}, {'_id': 1})['_id']
            creatorName = session.get('username', None)
            creationDateTime = str(datetime.utcnow())
            lastSavedEditDateTime = str(datetime.utcnow())
            name = noteName
            area = request.form['area']
            template = request.form['template']
            privacy = request.form['privacy']

            if template == 'Cornell':
                content = """<table style="width: 100%;"><tbody><tr><td style="width: 35%; text-align: center;"><p><strong>Cues</strong></p><p style="text-align: left;">After class: Main ideas, prompts, and questions</p>
                            </td><td style="width: 65%; text-align: center;"><p><strong>Notes</strong></p><p style="text-align: left;">During class: Main points and details</p></td></tr><tr>
                            <td style="text-align: center;" colspan="2"><p><strong>Summary</strong></p><p style="text-align: left;">After class: Summary of the lesson and highlighting key points</p>
                            </td></tr></tbody></table>"""
            elif template == 'Mapping':
                content = """<p style="text-align:center;"><strong>Main Topic</strong></p><table style="width: 100%;"><tbody>
                            <tr><th style="width: 33.3333%;">Subtopic 1</th><th style="width: 33.3333%;">Subtopic 2</th><th style="width: 33.3333%;">Subtopic 3</th></tr>
                            <tr><td style="width: 33.3333%; text-align:center;">Key Details</td><td style="width: 33.3333%; text-align:center;">Key Details</td><td style="width: 33.3333%; text-align:center;">Key Details</td></tr>
                            <tr><td style="width: 33.3333%;"><ol><li>Point 1</li><li>Point 2</li><li>Point 3</li></ol></td><td style="width: 33.3333%;"><ol><li>Point 1</li><li>Point 2</li>
                            <li>Point 3</li></ol></td><td style="width: 33.3333%;"><ol><li>Point 1</li><li>Point 2</li><li>Point 3</li></ol></td></tr></tbody></table>"""
            elif template == 'Outlining':
                content = """<p><strong>Main Topic</strong></p><ul><li>Subtopic 1<ul><li>Key point 1</li><li>Key point 2</li><li>Key point 3</li></ul></li></ul><ul><li>Subtopic 2<ul><li>Key point 1</li>
                            <li>Key point 2</li><li>Key point 3</li></ul></li></ul><ul><li>Subtopic 3<ul><li>Key point 1</li><li>Key point 2</li><li>Key point 3</li></ul></li></ul>"""
            elif template == 'Charting':
                content = """<p><strong>Main Topic</strong></p><table style="width: 100%;"><tbody><tr><th style="width: 33.3333%;">Topic 1</th><th style="width: 33.3333%;">Topic 2</th><th style="width: 33.3333%;">Topic 3</th></tr>
                            <tr><td style="width: 33.3333%;"><ol><li>Point 1 Details</li><li>Point 2 Details</li><li>Point 3 Details</li></ol></td><td style="width: 33.3333%;"><ol><li>Point 1 Details</li><li>Point 2 Details</li>
                            <li>Point 3 Details</li></ol></td><td style="width: 33.3333%;"><ol><li>Point 1 Details</li><li>Point 2 Details</li><li>Point 3 Details</li></ol></td></tr></tbody></table>"""
            elif template == 'Sentence':
                content = """<p><strong> Main Topic </strong></p><ol><li>Sentence covering key details of the topic</li><li>Sentence covering key details of the topic</li><li>Sentence covering key details of the topic</li></ol>"""

            notes.insert_one({'_id':  noteID, 'name': name, 'creatorName': creatorName, 'creatorID': creatorID, 'creationDateTime': creationDateTime, 'lastSavedEditDateTime': lastSavedEditDateTime, 'area': area, 'template': template, 'privacy': privacy, 'content': content})
            users.update_one({'_id': creatorID}, {'$push': {'createdNotes': noteID}})
            return redirect(url_for('editNote', noteID=noteID))
    
    return render_template("createNote.html", errorMessage=errorMessage)


@app.route("/view/<noteID>")
def viewNote(noteID):
    if ObjectId.is_valid(noteID) == False:
        return redirect(url_for('home'))

    selectedNote = notes.find_one({'_id': ObjectId(noteID)})
    user = users.find_one({'username': session.get('username', None)})

    if selectedNote == None:
        return redirect(url_for('home'))
    elif selectedNote['privacy'] == 'Private'  and  user == None:
        return redirect(url_for('home'))
    elif user != None:
        if ObjectId(noteID) not in user['createdNotes']  and  ObjectId(noteID) not in user['receivedNotes']  and  user['admin'] != True:         #note id not in users's created or received notes and not admin
            return redirect(url_for('home'))
    if selectedNote['creatorName'] == session.get('username', None)  or  session.get('admin', None) == True:
        return redirect(url_for('editNote', noteID=noteID))

    return render_template("viewNote.html", selectedNote=selectedNote)


@app.route("/edit/<noteID>", methods=['GET', 'POST'])
def editNote(noteID):
    if ObjectId.is_valid(noteID) == False:
        return redirect(url_for('home'))

    selectedNote = notes.find_one({'_id': ObjectId(noteID)})
    if selectedNote == None:
        return redirect(url_for('home'))
    elif session.get('username', None) != selectedNote['creatorName']  and  session.get('admin', None) != True:
        return redirect(url_for('viewNote', noteID=noteID))

    if request.method == 'POST':
        content = request.form['tinymce']
        lastSavedEditDateTime = str(datetime.utcnow())
        notes.update_one({'_id': selectedNote['_id']}, {'$set': {'content': content, 'lastSavedEditDateTime': lastSavedEditDateTime}})
        selectedNote = notes.find_one({'_id': ObjectId(noteID)})

    return render_template("editNote.html", selectedNote=selectedNote)


@app.route("/delete/<noteID>", methods=['GET', 'POST'])
def deleteNote(noteID):
    if ObjectId.is_valid(noteID) == False:
        return redirect(url_for('home'))

    selectedNote = notes.find_one({'_id': ObjectId(noteID)})
    if selectedNote == None  or  ( session.get('username', None) != selectedNote['creatorName']  and  session.get('admin', None) != True ):
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        notes.delete_one({'_id': ObjectId(noteID)})
        #delete note from user's received notes and created notes
        users.update_one({'username': selectedNote['creatorName']}, {'$pull': {'createdNotes': ObjectId(noteID)}})
        users.update_many({'receivedNotes': {'$in': [ObjectId(noteID)]}}, {'$pull': {'receivedNotes': ObjectId(noteID)}})
        if session.get('admin', None) == True:
            return redirect(url_for('adminControls'))
        else: 
            return redirect(url_for('noteList', filterBy='yourNotes'))

    return render_template("deleteNote.html", selectedNote=selectedNote)


@app.route("/share/<noteID>", methods=['GET', 'POST'])
def shareNote(noteID):
    if ObjectId.is_valid(noteID) == False:
        return redirect(url_for('home'))

    errorMessage = None
    selectedNote = notes.find_one({'_id': ObjectId(noteID)})
    hasPermissionToShare = ( session.get('username', None) == selectedNote['creatorName']  or  selectedNote['privacy'] == 'Public' )
    
    if request.method == 'POST':
        shareWith = request.form['shareWith']
        if shareWith == "":
            errorMessage = "Username field cannot be empty.  Please enter a valid username."
        elif containsSpecialChars(shareWith):
            errorMessage = "Username field cannot contain special characters such as $, @, ;, %, =, ?, #, (), <> or {}.  Please enter a valid username."
        elif " " in shareWith:
            errorMessage = "Username field cannot contain spaces.  Please enter a valid username."
        elif users.find_one({'username': shareWith}) == None:
            errorMessage = "Invalid username.  Please try again."
        else:
            users.update_one({'username': shareWith}, {'$push': {'receivedNotes': ObjectId(noteID)}})
            return redirect(url_for('viewNote', noteID=noteID))

    return render_template("shareNote.html", selectedNote=selectedNote, errorMessage=errorMessage, hasPermissionToShare=hasPermissionToShare)


@app.route("/list/<filterBy>")
def noteList(filterBy):
    displayMessage = None
    filteredNotes = None
    receivedNotes = None
    if filterBy == "library":
        displayMessage = "Currently displaying the Public Notes Library."
        filteredNotes = notes.find({'privacy': 'Public'})
    elif filterBy == "yourNotes":
        displayMessage = "Currently displaying your notes and notes that have been shared with you."
        currentUserID = users.find_one({'username': session.get('username', None)}, {'_id': 1})['_id']
        filteredNotes = notes.find({'creatorID': currentUserID})
        receivedNotesID = users.find_one({'username': session.get('username', None)}, {'_id': 0, 'receivedNotes': 1})['receivedNotes']
        receivedNotes = notes.find({'_id': {'$in': receivedNotesID}})
    elif filterBy.startswith("search"):
        search = filterBy[7:]
        displayMessage = "Currently displaying results of search: " + search
        filteredNotes = notes.find({'name': {'$regex': search, "$options": 'i'}, 'privacy': 'Public'})
    elif filterBy.startswith("creator"):
        creator = filterBy[8:]
        displayMessage = "Currently displaying all public notes for user: " + creator
        filteredNotes = notes.find({'creatorName': creator, 'privacy': 'Public'})
    else:
        return redirect(url_for('home'))

    return render_template("noteList.html", displayMessage=displayMessage, filteredNotes=filteredNotes, receivedNotes=receivedNotes)


@app.route("/search", methods=['GET', 'POST'])
def search():
    errorMessage = None
    if request.method == 'POST':
        search = request.form['search']
        if search == "":
            errorMessage = "Search field cannot be empty.  Please enter a valid search."
        elif containsSpecialChars(search):
            errorMessage = "Search field cannot contain special characters such as $, @, ;, %, =, ?, #, (), <> or {}.  Please enter a valid search."
        elif search[0] == " ":
            errorMessage = "Search field cannot start with a space.  Please enter a valid search."
        else: 
            return redirect(url_for('noteList', filterBy="search="+search))
    return render_template("search.html", errorMessage=errorMessage)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    errorMessage = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.find_one({'username': username})
        if username == "" or password == "":
            errorMessage = "Input fields cannot be empty.  Please enter valid account details."
        elif containsSpecialChars(username):
            errorMessage = "Username field cannot contain spaces or special characters such as $, @, ;, %, =, ?, #, (), <> or {}.  Please enter a valid username."
        elif containsSpecialChars(password):
            errorMessage = "Password field cannot contain spaces or special characters such as $, @, ;, %, =, ?, #, (), <> or {}.  Please enter a valid password."
        elif user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            session['username'] = username
            if user['admin']:
                session['admin'] = True
            return redirect(url_for('home'))
        else:
            errorMessage = "Invalid account details.  Please try again."
    return render_template("login.html", errorMessage=errorMessage)


@app.route("/register", methods=['GET', 'POST'])
def register():
    errorMessage = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        checkUsernameAvailabilty = users.find_one({'username': username})
        if checkUsernameAvailabilty != None:
            errorMessage = "Username already in use.  Please choose a different one or navigate to log in page if you already have an account."
        elif len(password) < 10 :
            errorMessage = "Password not secure enough.  Please choose a longer password."
        elif containsSpecialChars(username):
            errorMessage = "Username cannot contain spaces or special characters such as $, @, ;, %, =, ?, #, (), <> or {}.  Please enter valid account details."
        elif containsSpecialChars(password):
            errorMessage = "Password cannot contain spaces or special characters such as $, @, ;, %, =, ?, #, (), <> or {}.  Please enter valid account details."
        else:   
            userID = ObjectId()
            session['username'] = username
            hashedPassword = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            users.insert_one({'_id': userID, 'username': username, 'password': hashedPassword, 'admin': False, 'createdNotes': [], 'receivedNotes': []})
            return redirect(url_for('home'))   

    return render_template("register.html", errorMessage=errorMessage)


@app.route("/logout")
def logout():
    #session.clear()
    session.pop('username')
    if session.get('admin', None) != None:
        session.pop('admin')
    return redirect((url_for('home')))


@app.route("/accountDetails", methods=['GET', 'POST'])
def accountDetails():
    if session.get('username', None) == None:
        return redirect(url_for('login'))

    errorMessage = None
    if request.method == 'POST':
        newUsername = request.form['username']
        newPassword = request.form['password']
        if newUsername == ""  and  newPassword == "":
            errorMessage = "Both fields cannot be empty."
        elif newUsername != ""  and  newPassword != "":
            errorMessage = "Please only fill in one field at a time."
        elif newUsername != "":
            checkUsernameAvailabilty = users.find_one({'username': newUsername})
            if containsSpecialChars(newUsername):
                errorMessage = "Username cannot contain spaces or special characters such as $, @, ;, %, =, ?, #, (), <> or {}.  Please enter a valid username."
            elif checkUsernameAvailabilty != None:
                errorMessage = "Username already in use.  Please choose a different one."
            else:
                #update all notes created by user with the user's new username
                notes.update_many({'creatorName': session.get('username', None)}, {'$set': {'creatorName': newUsername}})
                #update the user object with new username
                users.update_one({'username': session.get('username', None)}, {'$set': {'username': newUsername}})
                #update session username variable 
                session['username'] = newUsername
                errorMessage = "Username successfuly updated"
        elif newPassword != "":
            if containsSpecialChars(newPassword):
                errorMessage = "Password cannot contain spaces or special characters such as $, @, ;, %, =, ?, #, (), <> or {}.  Please enter a valid password."
            elif len(newPassword) < 10:
                errorMessage = "Password not secure enough.  Please choose a longer password."
            else:
                hashedPassword = bcrypt.hashpw(newPassword.encode('utf-8'), bcrypt.gensalt())
                users.update_one({'username': session.get('username', None)}, {'$set': {'password': hashedPassword}})
                errorMessage = "Password successfuly updated."

    return render_template("updateAccountDetails.html", errorMessage=errorMessage, username=session.get('username', None))


@app.route("/deleteAccount/<username>", methods=['GET', 'POST'])
def deleteAccount(username):
    if session.get('username', None) != username  and  session.get('admin', None) != True:
        return redirect(url_for('home'))
    elif users.find_one({'username': username}) == None:
        return redirect(url_for('home'))

    filteredNotes = None
    filteredNotes = notes.find({'creatorName': username})
    
    if request.method == 'POST':
        whatToDoWithNotes = request.form['whatToDoWithNotes']
        if whatToDoWithNotes == "deleteNotes":
            #for each note, remove noteID from receivedNotes of all users that it was sent to
            #for each note, delete the note itself
            notesToDelete = users.find_one({'username': username}, {'_id': 0, 'createdNotes': 1})['createdNotes']
            for note in notesToDelete:
                users.update_many({'receivedNotes': {'$in': [ObjectId(note)]}}, {'$pull': {'receivedNotes': ObjectId(note)}})
                notes.delete_one({'_id': ObjectId(note)})
        elif whatToDoWithNotes == "keepNotes":
            #for each note, update creatorName to include 'deleted account'
            notes.update_many({'creatorName': username}, {'$set': {'creatorName': username + ' (DELETED ACCOUNT)'}})
        #lastly, delete the account itself and logout
        users.delete_one({'username': username})
        if session.get('admin', None) == True:
            return redirect(url_for('adminControls'))
        else:
            return redirect(url_for('logout'))

    return render_template("deleteAccount.html", filteredNotes=filteredNotes)


@app.route("/adminControls", methods=['GET', 'POST'])
def adminControls():
    if session.get('username', None) == None  or  session.get('admin', None) != True:
        return redirect(url_for('home'))

    allNotes = notes.find()
    allUsers = users.find()

    return render_template("adminControls.html", allNotes=allNotes, allUsers=allUsers)


@app.route("/accountDetailsAdminControl/<username>", methods=['GET', 'POST'])
def accountDetailsAdminControl(username):
    validUsername = users.find_one({'username': username})
    if validUsername == None  or  session.get('admin', None) != True:
        return redirect(url_for('home'))

    errorMessage = None
    if request.method == 'POST':
        newUsername = request.form['username']
        if newUsername == "":
            errorMessage = "Username field cannot be empty."
        else:
            checkUsernameAvailabilty = users.find_one({'username': newUsername})
            if containsSpecialChars(newUsername):
                errorMessage = "Username cannot contain spaces or special characters such as $, @, ;, %, =, ?, #, (), <> or {}.  Please enter a valid username."
            elif checkUsernameAvailabilty != None:
                errorMessage = "Username already in use.  Please choose a different one."
            else:
                #update all notes created by user with the user's new username
                notes.update_many({'creatorName': username}, {'$set': {'creatorName': newUsername}})
                #update the user object with new username
                users.update_one({'username': username}, {'$set': {'username': newUsername}})
                return redirect(url_for('adminControls'))

    return render_template("accountDetailsAdminControl.html", username=username, errorMessage=errorMessage)


@app.route("/downloadNote/<noteID>", methods=['GET', 'POST'])
def downloadNote(noteID):
    if ObjectId.is_valid(noteID) == False:
        return redirect(url_for('home'))

    note = notes.find_one({'_id': ObjectId(noteID)})
    user = users.find_one({'username': session.get('username', None)})
    if note == None:
        return redirect(url_for('home'))
    elif note['privacy'] == 'Private'  and  user == None:
        return redirect(url_for('home'))
    elif user != None:
        if ObjectId(noteID) not in user['createdNotes']  and  ObjectId(noteID) not in user['receivedNotes']  and  user['admin'] != True:         #note id not in users's created or received notes and not admin
            return redirect(url_for('home'))

    noteName = note['name']
    content = '<style> th, td, tr, table {border: 1px solid #333;} </style>  <span style="width:100%; text-align:center;"><h1>' + noteName + '</h1></span>' + note['content']
    options = {
        "orientation": "landscape",
        "page-size": "A4",
        "margin-top": "1.0cm",
        "margin-right": "1.0cm",
        "margin-bottom": "1.0cm",
        "margin-left": "1.0cm",
        "encoding": "UTF-8",
    }

    config = pdfkit.configuration(wkhtmltopdf = '/usr/bin/wkhtmltopdf')         #for hosting on pythonanywhere, but will not work locally
    pdf = pdfkit.from_string(content, options=options, configuration=config)
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename="+noteName+".pdf"
    return response



@app.route("/summarizeNote/<noteID>", methods=['GET', 'POST'])
def summarizeNote(noteID):
    if ObjectId.is_valid(noteID) == False:
        return redirect(url_for('home'))

    note = notes.find_one({'_id': ObjectId(noteID)})
    user = users.find_one({'username': session.get('username', None)})
    if note == None:
        return redirect(url_for('home'))
    elif note['privacy'] == 'Private'  and  user == None:
        return redirect(url_for('home'))
    elif user != None:
        if ObjectId(noteID) not in user['createdNotes']  and  ObjectId(noteID) not in user['receivedNotes']  and  user['admin'] != True:         #note id not in users's created or received notes and not admin
            return redirect(url_for('home'))

    name = note['name']
    content = re.sub(re.compile('<.*?>'), '', note['content'])      #removes all html tags from note content so that plaintext parser can understand

    parser = PlaintextParser.from_string(content, Tokenizer("english"))
    summarizer = LsaSummarizer(Stemmer("english"))
    summarizer.stop_words = get_stop_words("english")
    summary = summarizer(parser.document, sentences_count=4)  # You can adjust the number of sentences in the summary

    return render_template("viewSummary.html", summary=summary, name=name)


@app.route("/ttsNote/<noteID>", methods=['GET', 'POST'])
def ttsNote(noteID):
    if ObjectId.is_valid(noteID) == False:
        return redirect(url_for('home'))

    note = notes.find_one({'_id': ObjectId(noteID)})
    user = users.find_one({'username': session.get('username', None)})
    if note == None:
        return redirect(url_for('home'))
    elif note['privacy'] == 'Private'  and  user == None:
        return redirect(url_for('home'))
    elif user != None:
        if ObjectId(noteID) not in user['createdNotes']  and  ObjectId(noteID) not in user['receivedNotes']  and  user['admin'] != True:         #note id not in users's created or received notes and not admin
            return redirect(url_for('home'))

    noteURL = 'static/audio/'+noteID+'.mp3'
    name = note['name']

    audio = elclient.text_to_speech.convert(
        text=note['content'],
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_turbo_v2",
        output_format="mp3_44100_128",
    )
    save(audio, noteURL)

    return render_template("playtts.html", noteURL='/'+noteURL, name=name)





if __name__ == '__main__':
    app.run()