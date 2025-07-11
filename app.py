import streamlit as st
import os
import pickle
import json
import io
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload

# Streamlit UI setup
st.set_page_config(page_title="Google Drive Remote Manager", layout="centered")
st.title("🔐 Google Drive Remote Manager")

# Load credentials from secrets.toml
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

CREDENTIALS_PATH = "/tmp/credentials.json"
TOKEN_PATH = "/tmp/token.pickle"
SCOPES = ["https://www.googleapis.com/auth/drive"]

with open(CREDENTIALS_PATH, "w") as f:
    json.dump(credentials_dict, f)

# Google auth flow
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

# Handle redirect
query_params = st.query_params
if "code" in query_params and "flow" in st.session_state:
    flow = st.session_state.flow
    flow.fetch_token(code=query_params["code"][0])
    creds = flow.credentials
    with open(TOKEN_PATH, "wb") as token:
        pickle.dump(creds, token)
    st.success("✅ Login successful! Reloading...")
    st.rerun()

# Main logic
try:
    creds = get_credentials()
    drive_service = build("drive", "v3", credentials=creds)

    st.subheader("📁 Your Google Drive Files (First 10 from My Drive):")
    results = drive_service.files().list(q="'root' in parents and trashed=false", pageSize=10, fields="files(id, name)").execute()
    files = results.get("files", [])
    if not files:
        st.info("Your Drive is empty or inaccessible.")
    for file in files:
        st.markdown(f"📄 **{file['name']}** — `{file['id']}`")

    def download_folder(folder_id, local_path="downloads"):
        os.makedirs(local_path, exist_ok=True)
        query = f"'{folder_id}' in parents and trashed=false"
        results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        for item in results.get("files", []):
            if item["mimeType"] == "application/vnd.google-apps.folder":
                st.write(f"📂 Entering folder: {item['name']}")
                download_folder(item["id"], os.path.join(local_path, item["name"]))
            else:
                st.write(f"⬇️ Downloading file: {item['name']}")
                request = drive_service.files().get_media(fileId=item["id"])
                with open(os.path.join(local_path, item["name"]), "wb") as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()

    st.subheader("📂 Clone a Shared Google Drive Folder")
    shared_folder_id = st.text_input("Enter Shared Folder ID:")
    if shared_folder_id and st.button("🚀 Clone Folder"):
        try:
            download_folder(shared_folder_id)
            st.success("✅ Folder cloned successfully into 'downloads/' folder.")
        except Exception as e:
            st.error(f"❌ Failed to clone folder: {e}")

except Exception as e:
    st.error(f"❌ Error: {e}")