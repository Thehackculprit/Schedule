from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import datetime, os
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

app = Flask(__name__)
app.secret_key = "super_secret_key"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CLIENT_SECRETS_FILE = "credentials.json"

def get_service():
    creds = google.oauth2.credentials.Credentials(**session["credentials"])
    return googleapiclient.discovery.build("calendar", "v3", credentials=creds)

def credentials_to_dict(credentials):
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }

@app.route("/")
def index():
    if "credentials" not in session:
        return redirect("/authorize")
    return render_template("index.html")

@app.route("/authorize")
def authorize():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = url_for("oauth2callback", _external=True)
    auth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
    session["state"] = state
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=session["state"])
    flow.redirect_uri = url_for("oauth2callback", _external=True)
    flow.fetch_token(authorization_response=request.url)
    session["credentials"] = credentials_to_dict(flow.credentials)
    return redirect("/")

@app.route("/slots", methods=["GET"])
def get_slots():
    """Fetch available slots for today (9am–5pm, 30min each)."""
    service = get_service()
    now = datetime.datetime.utcnow().isoformat() + "Z"
    today = datetime.datetime.utcnow().date()
    
    start_day = datetime.datetime.combine(today, datetime.time(9, 0))
    end_day = datetime.datetime.combine(today, datetime.time(17, 0))
    
    busy = service.freebusy().query(
        body={"timeMin": start_day.isoformat()+"Z",
              "timeMax": end_day.isoformat()+"Z",
              "timeZone": "UTC",
              "items": [{"id": "primary"}]}
    ).execute()

    busy_times = [(datetime.datetime.fromisoformat(b["start"][:-1]),
                   datetime.datetime.fromisoformat(b["end"][:-1]))
                   for b in busy["calendars"]["primary"].get("busy", [])]

    slots = []
    slot_start = start_day
    while slot_start < end_day:
        slot_end = slot_start + datetime.timedelta(minutes=30)
        overlap = any(bs < slot_end and be > slot_start for bs, be in busy_times)
        if not overlap:
            slots.append({
                "start": slot_start.isoformat(),
                "end": slot_end.isoformat()
            })
        slot_start = slot_end

    return jsonify(slots)

@app.route("/book", methods=["POST"])
def book_slot():
    data = request.json
    start = datetime.datetime.fromisoformat(data["start"])
    end = datetime.datetime.fromisoformat(data["end"])

    event = {
        "summary": "Booked Slot",
        "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat(), "timeZone": "UTC"}
    }

    service = get_service()
    service.events().insert(calendarId="primary", body=event).execute()
    return jsonify({"status": "success"})
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
