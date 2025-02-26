from flask import Flask, render_template, request, jsonify, session
import json
import os
from twilio.rest import Client  

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session management

# Twilio credentials (Replace with actual values)
TWILIO_ACCOUNT_SID = "AC446c82c2f78412c299537e432b47e65a"
TWILIO_AUTH_TOKEN = "0b1147c104304d80892560a078959721"
TWILIO_PHONE_NUMBER = "+15412043554"

# Data storage (Simulating a database)
USER_PROFILE = {"name": "John Doe", "email": "johndoe@example.com", "phone": "+1234567890"}
ALERTS_FILE = "alerts.json"
CONTACTS_FILE = "contacts.json"

# Load contacts from file or initialize an empty list
if os.path.exists(CONTACTS_FILE):
    with open(CONTACTS_FILE, "r") as file:
        EMERGENCY_CONTACTS = json.load(file)
else:
    EMERGENCY_CONTACTS = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/profile', methods=['GET'])
def profile():
    return render_template('profile.html')

@app.route('/contacts', methods=['GET'])
def contacts():
    return render_template('contacts.html')

@app.route('/alerts', methods=['GET'])
def alerts():
    return render_template('alerts.html')

@app.route('/get_profile', methods=['GET'])
def get_profile():
    """Fetches user profile data."""
    return jsonify(USER_PROFILE)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    """Updates user profile details."""
    data = request.get_json()
    USER_PROFILE.update(data)
    return jsonify({"message": "Profile updated successfully!", "profile": USER_PROFILE})

@app.route('/send_location', methods=['POST'])
def receive_location():
    """Receives exact GPS location from the frontend."""
    data = request.get_json()
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if latitude and longitude:
        session["latitude"] = latitude
        session["longitude"] = longitude
        return jsonify({"message": "Location received!", "latitude": latitude, "longitude": longitude})

    return jsonify({"message": "Invalid location data"}), 400

@app.route('/send_alert', methods=['POST'])
def send_alert():
    """Sends an SOS alert via Twilio SMS to updated contacts."""
    latitude = session.get("latitude")
    longitude = session.get("longitude")

    if not latitude or not longitude:
        return jsonify({"message": "Location not available. Please enable GPS and try again."}), 400

    message_body = f"🚨 SOS Alert! Location: {latitude}, {longitude}"
    
    try:
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
            return jsonify({"message": "Twilio credentials missing"}), 500

        # Load the latest contacts from the file
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, "r") as file:
                updated_contacts = json.load(file)
        else:
            updated_contacts = EMERGENCY_CONTACTS

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        for number in updated_contacts:
            message = client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE_NUMBER,
                to=number
            )
            print(f"Message sent to {number} - SID: {message.sid}")  # Log success

        # Save the alert
        alert_data = {"latitude": latitude, "longitude": longitude, "time": "Just Now"}

        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, "r") as file:
                alerts = json.load(file)
        else:
            alerts = []

        alerts.append(alert_data)

        with open(ALERTS_FILE, "w") as file:
            json.dump(alerts, file)

        return jsonify({"message": "SOS alert sent!", "location": {"latitude": latitude, "longitude": longitude}}), 200

    except Exception as e:
        print(f"Twilio Error: {e}")  # Debug log
        return jsonify({"message": "SMS sending failed", "error": str(e)}), 500

@app.route('/get_alerts', methods=['GET'])
def get_alerts():
    """Fetches all previous alerts."""
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, "r") as file:
            alerts = json.load(file)
    else:
        alerts = []
    return jsonify({"alerts": alerts})

@app.route('/add_contact', methods=['POST'])
def add_contact():
    """Adds a new emergency contact and updates the stored list."""
    data = request.get_json()
    new_number = data.get("phone_number")

    if new_number and new_number not in EMERGENCY_CONTACTS:
        EMERGENCY_CONTACTS.append(new_number)

        with open(CONTACTS_FILE, "w") as file:
            json.dump(EMERGENCY_CONTACTS, file)

        return jsonify({"message": "Contact added successfully!", "contacts": EMERGENCY_CONTACTS})

    return jsonify({"message": "Invalid or duplicate contact"}), 400

@app.route('/get_contacts', methods=['GET'])
def get_contacts():
    """Fetches the list of emergency contacts."""
    return jsonify({"contacts": EMERGENCY_CONTACTS})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
