import streamlit as st
import os
import pickle
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# ✅ Set page config
st.set_page_config(page_title="Google Drive Manager", layout="centered")
st.title("🔐 Google Drive Remote Manager")

# ✅ Setup credentials using Streamlit secrets
credentials_dict = {
    "web": {
        "client_id": st.secrets.google.client_id,
        "project_id": st.secrets.google.project_id,
        "auth_uri": st.secrets.google.auth_uri,
        "token_uri": st.secrets.google.token_uri,
        "auth_provider_x509_cert_url": st.secrets.google.auth_provider_x509_cert_url,
        "client_secret": st.secrets.google.client_secret,
        "redirect_uris": [st.secrets.google.redirect_uri]
    }
}

# ✅ Save to a temp file for Google API
CREDENTIALS_PATH = "/tmp/credentials.json"
TOKEN_PATH = "/tmp/token.pickle"

with open(CREDENTIALS_PATH, "w") as f:
    json.dump(credentials_dict, f)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# ✅ Get or create user credentials
def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES,
            redirect_uri=st.secrets.google.redirect_uri
        )
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.session_state.flow = flow
        st.markdown(f"[🔓 Click here to authorize Google Drive access]({auth_url})")
        st.stop()
    return creds

# ✅ Handle redirect
query_params = st.experimental_get_query_params()
if "code" in query_params and "flow" in st.session_state:
    flow = st.session_state.flow
    flow.fetch_token(code=query_params["code"][0])
    creds = flow.credentials
    with open(TOKEN_PATH, "wb") as token:
        pickle.dump(creds, token)
    st.success("✅ Login successful! Reloading...")
    st.experimental_rerun()

# ✅ Main app logic
try:
    creds = get_credentials()
    drive_service = build("drive", "v3", credentials=creds)

    st.subheader("📁 Your Google Drive Files (First 10):")
    results = drive_service.files().list(
        pageSize=10,
        fields="files(id, name)"
    ).execute()
    files = results.get("files", [])

    if files:
        for file in files:
            st.write(f"📄 {file['name']} (ID: {file['id']})")
    else:
        st.info("No files found.")
except Exception as e:
    st.error(f"❌ Error: {e}")
