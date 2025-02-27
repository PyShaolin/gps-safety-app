from flask import Flask, render_template, request, jsonify, session
import json
import os
import logging
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load Twilio credentials from environment variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Data storage (Simulating a database)
USER_PROFILE = {"name": "John Doe", "email": "johndoe@example.com", "phone": "+1234567890"}
ALERTS_FILE = "alerts.json"
CONTACTS_FILE = "contacts.json"

# Load contacts safely
def load_contacts():
    if os.path.exists(CONTACTS_FILE):
        try:
            with open(CONTACTS_FILE, "r") as file:
                contacts = json.load(file)
                if isinstance(contacts, list):
                    return contacts
        except json.JSONDecodeError:
            logger.error("Invalid JSON format in contacts file.")
    return []

# Save contacts
def save_contacts(contacts):
    with open(CONTACTS_FILE, "w") as file:
        json.dump(contacts, file)

# Load alerts safely
def load_alerts():
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, "r") as file:
                alerts = json.load(file)
                if isinstance(alerts, list):
                    return alerts
        except json.JSONDecodeError:
            logger.error("Invalid JSON format in alerts file.")
    return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/contacts')
def contacts():
    return render_template('contacts.html')

@app.route('/alerts')
def alerts():
    return render_template('alerts.html')

@app.route('/send_location', methods=['POST'])
def receive_location():
    """Receives and stores GPS location in session."""
    data = request.get_json()
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if latitude and longitude:
        session["location"] = {"latitude": latitude, "longitude": longitude}
        logger.info(f"Location stored: {session['location']}")
        return jsonify({"message": "Location received!", "latitude": latitude, "longitude": longitude})
    
    logger.error("Invalid location data received")
    return jsonify({"message": "Invalid location data"}), 400

@app.route('/send_alert', methods=['POST'])
def send_alert():
    location = session.get("location")
    logger.info(f"Retrieved session location: {location}")
    
    if not location:
        return jsonify({"message": "Location not available. Please enable GPS and try again."}), 400

    latitude, longitude = location["latitude"], location["longitude"]
    maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
    message_body = f"\U0001F6A8 SOS Alert! Location: {latitude}, {longitude}\nLive Location: {maps_link}"

    try:
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
            logger.error("Twilio credentials are missing.")
            return jsonify({"message": "Twilio credentials missing"}), 500

        emergency_contacts = load_contacts()
        if not emergency_contacts:
            return jsonify({"message": "No emergency contacts available."}), 400

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        sent_messages = []
        failed_messages = []
        
        for number in emergency_contacts:
            try:
                message = client.messages.create(
                    body=message_body.encode("utf-8").decode("utf-8"),
                    from_=TWILIO_PHONE_NUMBER,
                    to=number
                )
                sent_messages.append({"number": number, "sid": message.sid, "status": message.status})
                logger.info(f"✅ SMS sent to {number} - SID: {message.sid}, Status: {message.status}")
            except Exception as sms_error:
                failed_messages.append({"number": number, "error": str(sms_error)})
                logger.error(f"❌ Error sending SMS to {number}: {sms_error}")

        alert_data = {"latitude": latitude, "longitude": longitude, "time": "Just Now"}
        alerts = load_alerts()
        alerts.append(alert_data)

        with open(ALERTS_FILE, "w") as file:
            json.dump(alerts, file)

        return jsonify({
            "message": "SOS alert processed!", 
            "sent_messages": sent_messages,
            "failed_messages": failed_messages,
            "location": {"latitude": latitude, "longitude": longitude}
        }), 200

    except Exception as e:
        logger.error(f"\U0001F6A8 Twilio Error: {e}")
        return jsonify({"message": "SMS sending failed", "error": str(e)}), 500

@app.route('/get_contacts', methods=['GET'])
def get_contacts():
    """Fetches emergency contacts."""
    return jsonify({"contacts": load_contacts()})

@app.route('/add_contact', methods=['POST'])
def add_contact():
    """Adds a new emergency contact."""
    data = request.get_json()
    new_number = data.get("phone_number")

    if new_number and isinstance(new_number, str):
        contacts = load_contacts()
        if new_number not in contacts:
            contacts.append(new_number)
            save_contacts(contacts)
            return jsonify({"message": "Contact added successfully!", "contacts": contacts})
        else:
            return jsonify({"message": "Contact already exists"}), 400

    return jsonify({"message": "Invalid phone number"}), 400

@app.route('/delete_contact', methods=['POST'])
def delete_contact():
    """Deletes an emergency contact."""
    data = request.get_json()
    delete_number = data.get("phone_number")

    if delete_number and isinstance(delete_number, str):
        contacts = load_contacts()
        if delete_number in contacts:
            contacts.remove(delete_number)
            save_contacts(contacts)
            return jsonify({"message": "Contact deleted successfully!", "contacts": contacts})
        else:
            return jsonify({"message": "Contact not found"}), 400

    return jsonify({"message": "Invalid phone number"}), 400

@app.route('/get_alerts', methods=['GET'])
def get_alerts():
    """Fetches all previous alerts."""
    return jsonify({"alerts": load_alerts()})

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
