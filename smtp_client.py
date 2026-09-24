import socket

def send_mail(sender, recipient, subject, body, log_callback=None):
    def log(msg):
        if log_callback:
            log_callback(msg)

    sock = socket.create_connection(("127.0.0.1", 2525), timeout=5)
    reader = sock.makefile("r", encoding="utf-8", newline="")

    def read_response():
        response = reader.readline().strip()
        log(f"S: {response}")
        return response

    def send_command(command):
        log(f"C: {command}")
        sock.sendall((command + "\r\n").encode())
        return read_response()

    try:
        if not read_response().startswith("220"):
            return False, "SMTP server did not send a ready response."
        for command in ("HELO client.local", f"MAIL FROM:<{sender}>", f"RCPT TO:<{recipient}>"):
            if not send_command(command).startswith("250"):
                return False, f"SMTP command failed: {command}"
        if not send_command("DATA").startswith("354"):
            return False, "SMTP server rejected message data."

        lines = [f"Subject: {subject}", "", *body.replace("\r\n", "\n").split("\n")]
        payload = "\r\n".join(line if not line.startswith(".") else "." + line for line in lines)
        log(f"C: {payload}")
        sock.sendall((payload + "\r\n.\r\n").encode())
        if not read_response().startswith("250"):
            return False, "SMTP server rejected message delivery."
        if not send_command("QUIT").startswith("221"):
            return False, "SMTP server did not close the session cleanly."
        return True, "Email sent successfully."
    except Exception as e:
        return False, str(e)
    finally:
        reader.close()
        sock.close()