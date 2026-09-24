import threading

import smtp_client
import pop3_client
import mailbox_store as store
import pop3_server
import smtp_server
import streamlit as st

st.set_page_config(page_title="Local Mail Lab", page_icon="✉", layout="wide")


@st.cache_resource
def start_backend_servers():
    store.init_store()
    threads = []
    for target, name in ((smtp_server.start_smtp_server, "smtp-server"),
                         (pop3_server.start_pop3_server, "pop3-server")):
        thread = threading.Thread(target=target, name=name, daemon=True)
        thread.start()
        threads.append(thread)
    return threads


def add_log(message):
    st.session_state.setdefault("protocol_log", []).append(message)


def fetch_mail():
    ok, message, emails = pop3_client.fetch_emails(
        st.session_state.user,
        st.session_state.password,
        log_callback=add_log,
    )
    if ok:
        st.session_state.emails = emails
    return ok, message


start_backend_servers()
st.title("Local Email Communication System")
st.caption("A teaching interface for SMTP delivery and POP3 retrieval")

for key, default in (("authenticated", False), ("emails", []), ("protocol_log", [])):
    st.session_state.setdefault(key, default)

with st.sidebar:
    st.header("Account")
    username = st.text_input("Username or email", value="alice@local")
    password = st.text_input("Password", value="password123", type="password")
    if st.button("Login", type="primary", use_container_width=True):
        email = store.authenticate_user(username.strip(), password)
        if email:
            st.session_state.authenticated = True
            st.session_state.user = email
            st.session_state.password = password
            add_log(f"Logged in as {email}")
            st.rerun()
        else:
            st.error("Invalid username or password")

    if st.session_state.authenticated:
        st.success(f"Active account: {st.session_state.user}")
        if st.button("Logout", use_container_width=True):
            for key in ("authenticated", "user", "password", "emails"):
                st.session_state.pop(key, None)
            st.rerun()

if not st.session_state.authenticated:
    st.info("Log in with alice@local or bob@local to use the mail system.")
    st.stop()

compose_tab, inbox_tab, log_tab = st.tabs(["Compose SMTP", "Inbox POP3", "Protocol Log"])

with compose_tab:
    st.subheader("Compose message")
    recipient = st.text_input("To", value="bob@local")
    subject = st.text_input("Subject")
    body = st.text_area("Message", height=220)
    if st.button("Send email", type="primary"):
        if not recipient.strip() or not body.strip():
            st.warning("Recipient and message body are required.")
        else:
            ok, message = smtp_client.send_mail(
                st.session_state.user,
                recipient.strip(),
                subject.strip(),
                body,
                log_callback=add_log,
            )
            (st.success if ok else st.error)(message)

with inbox_tab:
    st.subheader("Inbox")
    if st.button("Check mail"):
        ok, message = fetch_mail()
        (st.success if ok else st.error)(message)

    emails = st.session_state.emails
    if emails:
        labels = [f"Message {idx}" for idx, _ in emails]
        selected = st.selectbox("Select a message", range(len(emails)), format_func=lambda index: labels[index])
        st.code(emails[selected][1], language="text")
        if st.button("Delete selected message"):
            msg_id = emails[selected][0]
            ok, message = pop3_client.delete_email(
                st.session_state.user,
                st.session_state.password,
                msg_id,
                log_callback=add_log,
            )
            (st.success if ok else st.error)(message)
            if ok:
                fetch_mail()
                st.rerun()
    else:
        st.info("No messages loaded. Select Check mail.")

with log_tab:
    st.subheader("SMTP / POP3 exchange")
    st.code("\n".join(st.session_state.protocol_log) or "No protocol activity yet.", language="text")