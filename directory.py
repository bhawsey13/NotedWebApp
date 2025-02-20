from flask import Flask, redirect, url_for, request, render_template, session
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from flask_session import Session
from datetime import datetime
from flask_moment import Moment
from bson.objectid import ObjectId
import bcrypt


#Flask app object
app = Flask(__name__)


#Configure session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


#Configure DB connection
#client = MongoClient('localhost', 27017)
uri = "mongodb+srv://bhawsey13:SouthAfrica23@notedwebapp.o18gk.mongodb.net/?retryWrites=true&w=majority&appName=NotedWebApp"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client.NotedWebApp
notes = db.notes
users = db.users


#configure Moment for capturing timezone accurate DateTime
moment = Moment(app)





#Start of directory:

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/createNote", methods=['GET', 'POST'])
def createNote():
    if session["username"] == None:
        return redirect(url_for('login'))

    errorMessage = None
    if request.method == 'POST':
        if request.form['name'] != "" :
            noteID = ObjectId()
            creatorID = session["userID"]
            creatorName = session["username"]
            creationDateTime = str(datetime.utcnow())
            lastSavedEditDateTime = str(datetime.utcnow())
            name = request.form['name']
            area = request.form['area']
            template = request.form['template']
            privacy = request.form['privacy']

            if template == 'Cornell':
                content = " "
            elif template == 'Mapping':
                content = " "
            elif template == 'Outlining':
                content = " "
            elif template == 'Charting':
                content = " "
            elif template == 'Sentence':
                content = "<strong> Main Topic </strong> <ol> <li> Detail Sentence </li> <li> Detail Sentence </li> <li> Detail Sentence </li> </ol>"

            notes.insert_one({'_id':  noteID, 'name': name, 'creatorName': creatorName, 'creatorID': creatorID, 'creationDateTime': creationDateTime, 'lastSavedEditDateTime': lastSavedEditDateTime, 'area': area, 'template': template, 'privacy': privacy, 'content': content})
            users.update_one({'_id': creatorID}, {'$push': {'createdNotes': noteID}})
            return redirect(url_for('viewNote', noteID=noteID))
        else:
            errorMessage = "Name field cannot be empty.  Please enter a valid name."
    return render_template("createNote.html", errorMessage=errorMessage)


@app.route("/view/<noteID>")
def viewNote(noteID):
    selectedNote = notes.find_one({'_id': ObjectId(noteID)})
    if selectedNote == None:
        return redirect(url_for('home'))
    elif selectedNote['creatorName'] == session['username']:
        return redirect(url_for('editNote', noteID=noteID))

    return render_template("viewNote.html", selectedNote=selectedNote)


@app.route("/edit/<noteID>", methods=['GET', 'POST'])
def editNote(noteID):
    selectedNote = notes.find_one({'_id': ObjectId(noteID)})
    if selectedNote == None or session['username'] != selectedNote['creatorName']:
        return redirect(url_for('home'))

    if request.method == 'POST':
        content = request.form['tinymce']
        lastSavedEditDateTime = str(datetime.utcnow())
        notes.update_one({'_id': selectedNote['_id']}, {'$set': {'content': content, 'lastSavedEditDateTime': lastSavedEditDateTime}})
        selectedNote = notes.find_one({'_id': ObjectId(noteID)})

    return render_template("editNote.html", selectedNote=selectedNote)


@app.route("/delete/<noteID>", methods=['GET', 'POST'])
def deleteNote(noteID):
    selectedNote = notes.find_one({'_id': ObjectId(noteID)})
    if selectedNote == None or session['username'] != selectedNote['creatorName']:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        notes.delete_one({'_id': ObjectId(noteID)})
        #delete note from user's received notes and created notes
        users.update_one({'_id': session['userID']}, {'$pull': {'createdNotes': ObjectId(noteID)}})
        users.update_one({'receivedNotes': ObjectId(noteID)}, {'$pull': {'receivedNotes': ObjectId(noteID)}})
        return redirect(url_for('home'))

    return render_template("deleteNote.html", selectedNote=selectedNote)


@app.route("/share/<noteID>", methods=['GET', 'POST'])
def shareNote(noteID):
    errorMessage = None
    selectedNote = notes.find_one({'_id': ObjectId(noteID)})
    hasPermissionToShare = ( session['username'] == selectedNote['creatorName']  or  selectedNote['privacy'] == 'Public' )
    
    if request.method == 'POST':
        shareWith = request.form['shareWith']
        if users.find_one({'username': shareWith}) == None:
            errorMessage = "Invalid username.  Please try again."
        else:
            users.update_one({'username': shareWith}, {'$push': {'receivedNotes': ObjectId(noteID)}})
            return redirect(url_for('home'))

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
        filteredNotes = notes.find({'creatorID': session['userID']})
        receivedNotesID = users.find_one({'username': session['username']}, {'_id': 0, 'receivedNotes': 1})['receivedNotes']
        receivedNotes = notes.find({'_id': {'$in': receivedNotesID}})
    elif filterBy.startswith("search"):
        search = filterBy[7:]
        displayMessage = "Currently displaying results of search: " + search
        filteredNotes = notes.find({'name': {'$regex': search, "$options": 'i'}, 'privacy': 'Public'})
    else:
        return redirect(url_for('home'))

    return render_template("noteList.html", displayMessage=displayMessage, filteredNotes=filteredNotes, receivedNotes=receivedNotes)


@app.route("/search", methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search = request.form['search']
        return redirect(url_for('noteList', filterBy="search="+search))
    return render_template("search.html")


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
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            session["userID"] = user['_id']
            session["username"] = username
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
        elif " " in username or " " in password:
            errorMessage = "Username and password cannot contain spaces.  Please enter account details without spaces."
        else:   
            userID = ObjectId()
            session["userID"] = userID
            session["username"] = username
            hashedPassword = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            users.insert_one({'_id': userID, 'username': username, 'password': hashedPassword, 'admin': False, 'createdNotes': [], 'receivedNotes': []})
            return redirect(url_for('home'))   
                 
    return render_template("register.html", errorMessage=errorMessage)


@app.route("/logout")
def logout():
    session["userID"] = None
    session["username"] = None
    return redirect("/")


@app.route("/accountDetails")
def accountDetails():
    if session["username"] == None:
        return redirect(url_for('home'))

    errorMessage = None
    account = users.find_one({'username': session["username"]})
    return render_template("updateAccountDetails.html", errorMessage=errorMessage, account=account)





if __name__ == '__main__':
    app.run()