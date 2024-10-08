from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config['SECRET_KEY'] = 'password'
socketio = SocketIO(app)

rooms = {}

def generate_unique_code(length):
    while True:
        code = ''
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        if code not in rooms:
            break
    return code

@app.route('/', methods=['POST', 'GET'])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template('home.html', error="Please enter a name.", code=code, name=name, all_rooms=rooms)

        if join != False and not code:
            return render_template('home.html', error="Please enter a room code.", code=code, name=name, all_rooms=rooms)
        
        if code:
            code = code.strip()
            code = code.upper()
        
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template('home.html', error="Room does not exist.", code=code, name=name, all_rooms=rooms)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template('home.html', all_rooms=rooms)

@app.route("/room")
def room():
    room = session.get("room")
    if room == None or session.get("name") == None or room not in rooms:
        return redirect(url_for("home"))
    return render_template("room.html", roomCode=room, messages=rooms[room]["messages"], allRooms=rooms)

 
@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in room:
        return
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)




@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1


@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({"name": name, "message": "has left the room"}, to=room)

@socketio.on("leave")
def handle_leave(data):
    room = data.get("room")
    name = session.get("name")
    if room in rooms:
        leave_room(room)
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
        send({'name': name, "message": "has left the room"}, to=room)

if __name__ == "__main__":
    socketio.run(app, debug=True)