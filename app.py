from flask import Flask, render_template, request, jsonify, session
import json
import os
from twilio.rest import Client  

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Improved security with dynamic secret key

# Twilio credentials (Replace with actual values)
TWILIO_ACCOUNT_SID = "AC446c82c2f78412c299537e432b47e65a"
TWILIO_AUTH_TOKEN = "0b1147c104304d80892560a078959721"
TWILIO_PHONE_NUMBER = "+15412043554"

# Data storage (Simulating a database)
USER_PROFILE = {"name": "John Doe", "email": "johndoe@example.com", "phone": "+1234567890"}
ALERTS_FILE = "alerts.json"
CONTACTS_FILE = "contacts.json"

# Load contacts safely
def load_contacts():
    """Loads emergency contacts from a JSON file."""
    if os.path.exists(CONTACTS_FILE):
        try:
            with open(CONTACTS_FILE, "r") as file:
                contacts = json.load(file)
                if isinstance(contacts, list):
                    return contacts
        except json.JSONDecodeError:
            print("Error: Invalid JSON format in contacts file.")
    return []

# Load alerts safely
def load_alerts():
    """Loads alert history from a JSON file."""
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, "r") as file:
                alerts = json.load(file)
                if isinstance(alerts, list):
                    return alerts
        except json.JSONDecodeError:
            print("Error: Invalid JSON format in alerts file.")
    return []

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
    """Receives exact GPS location from the frontend and stores in session."""
    data = request.get_json()
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if latitude and longitude:
        session["location"] = {"latitude": latitude, "longitude": longitude}
        return jsonify({"message": "Location received!", "latitude": latitude, "longitude": longitude})

    return jsonify({"message": "Invalid location data"}), 400

@app.route('/send_alert', methods=['POST'])
def send_alert():
    """Sends an SOS alert via Twilio SMS to updated contacts."""
    location = session.get("location")

    if not location:
        return jsonify({"message": "Location not available. Please enable GPS and try again."}), 400

    latitude, longitude = location["latitude"], location["longitude"]
    message_body = f"🚨 SOS Alert! Location: {latitude}, {longitude}"

    try:
        # Validate Twilio credentials
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
            return jsonify({"message": "Twilio credentials missing"}), 500

        # Load fresh contacts dynamically
        emergency_contacts = load_contacts()
        if not emergency_contacts:
            return jsonify({"message": "No emergency contacts available."}), 400

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        for number in emergency_contacts:
            try:
                message = client.messages.create(
                    body=message_body,
                    from_=TWILIO_PHONE_NUMBER,
                    to=number
                )
                print(f"✅ Message sent to {number} - SID: {message.sid}")  # Debug log
            except Exception as sms_error:
                print(f"❌ Error sending SMS to {number}: {sms_error}")  # Debug log

        # Save the alert
        alert_data = {"latitude": latitude, "longitude": longitude, "time": "Just Now"}
        alerts = load_alerts()
        alerts.append(alert_data)

        with open(ALERTS_FILE, "w") as file:
            json.dump(alerts, file)

        return jsonify({"message": "SOS alert sent!", "location": {"latitude": latitude, "longitude": longitude}}), 200

    except Exception as e:
        print(f"🚨 Twilio Error: {e}")  # Debug log
        return jsonify({"message": "SMS sending failed", "error": str(e)}), 500

@app.route('/get_alerts', methods=['GET'])
def get_alerts():
    """Fetches all previous alerts."""
    return jsonify({"alerts": load_alerts()})

@app.route('/add_contact', methods=['POST'])
def add_contact():
    """Adds a new emergency contact and updates the stored list."""
    data = request.get_json()
    new_number = data.get("phone_number")

    if new_number and isinstance(new_number, str) and new_number not in load_contacts():
        contacts = load_contacts()
        contacts.append(new_number)

        with open(CONTACTS_FILE, "w") as file:
            json.dump(contacts, file)

        return jsonify({"message": "Contact added successfully!", "contacts": contacts})

    return jsonify({"message": "Invalid or duplicate contact"}), 400

@app.route('/get_contacts', methods=['GET'])
def get_contacts():
    """Fetches the list of emergency contacts."""
    return jsonify({"contacts": load_contacts()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

