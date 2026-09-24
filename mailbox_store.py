import os
import json
import time
import uuid

MAILBOX_DIR = "mailboxes"
USERS_FILE = "users.json"

# Default accounts for local testing
DEFAULT_USERS = {
    "alice@local": "password123",
    "bob@local": "password123"
}

def init_store():
    if not os.path.exists(MAILBOX_DIR):
        os.makedirs(MAILBOX_DIR, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump(DEFAULT_USERS, f, indent=2)
            
    for user in load_users().keys():
        user_dir = os.path.join(MAILBOX_DIR, user)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir, exist_ok=True)

def load_users():
    if not os.path.exists(USERS_FILE):
        return DEFAULT_USERS
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def user_exists(email):
    return email in load_users()

def authenticate_user(username_or_email, password):
    users = load_users()
    for email, pwd in users.items():
        user_part = email.split("@")[0]
        if (username_or_email == email or username_or_email == user_part) and pwd == password:
            return email
    return None

def save_message(recipient_email, sender_email, subject, body):
    user_dir = os.path.join(MAILBOX_DIR, recipient_email)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
        
    filename = f"{int(time.time() * 1000)}-{uuid.uuid4().hex}.eml"
    filepath = os.path.join(user_dir, filename)
    
    content = f"From: {sender_email}\nTo: {recipient_email}\nSubject: {subject}\n\n{body}"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filename

def list_messages(user_email):
    user_dir = os.path.join(MAILBOX_DIR, user_email)
    if not os.path.exists(user_dir):
        return []
    files = [f for f in os.listdir(user_dir) if f.endswith(".eml")]
    files.sort()
    
    messages = []
    for idx, fname in enumerate(files, 1):
        fpath = os.path.join(user_dir, fname)
        size = os.path.getsize(fpath)
        messages.append((idx, fname, size))
    return messages

def read_message(user_email, index):
    messages = list_messages(user_email)
    if index < 1 or index > len(messages):
        return None
    fname = messages[index - 1][1]
    fpath = os.path.join(MAILBOX_DIR, user_email, fname)
    with open(fpath, "r", encoding="utf-8") as f:
        return f.read()

def delete_message(user_email, index):
    messages = list_messages(user_email)
    if index < 1 or index > len(messages):
        return False
    fname = messages[index - 1][1]
    fpath = os.path.join(MAILBOX_DIR, user_email, fname)
    if os.path.exists(fpath):
        os.remove(fpath)
        return True
    return False

if __name__ == "__main__":
    init_store()
    print("Mailbox store initialized.")