import socket
import threading
import mailbox_store as store

HOST = "127.0.0.1"
PORT = 2525

class SmtpSession(threading.Thread):
    def __init__(self, conn, addr):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.state = "HELO"
        self.sender = None
        self.recipients = []

    def run(self):
        data_buffer = []
        try:
            self.conn.sendall(b"220 localhost SMTP Server Ready\r\n")
            reader = self.conn.makefile("r", encoding="utf-8", newline="")
            for raw_line in reader:
                line = raw_line.rstrip("\r\n")
                if self.state == "DATA_INPUT":
                    if line == ".":
                        self._finish_message(data_buffer)
                        data_buffer = []
                    else:
                        data_buffer.append(line[1:] if line.startswith("..") else line)
                    continue

                command, _, argument = line.partition(" ")
                command = command.upper()
                argument = argument.strip()
                if command in ("HELO", "EHLO"):
                    self.conn.sendall(b"250 Hello client.local\r\n")
                    self.state = "MAIL"
                elif command == "MAIL" and argument.upper().startswith("FROM:") and self.state == "MAIL":
                    self.sender = argument[5:].strip("<> ")
                    self.recipients = []
                    self.conn.sendall(b"250 OK\r\n")
                    self.state = "RCPT"
                elif command == "RCPT" and argument.upper().startswith("TO:") and self.state in ("RCPT", "DATA"):
                    recipient = argument[3:].strip("<> ")
                    if store.user_exists(recipient):
                        self.recipients.append(recipient)
                        self.conn.sendall(b"250 OK\r\n")
                        self.state = "DATA"
                    else:
                        self.conn.sendall(b"550 No such user here\r\n")
                elif command == "DATA" and self.state == "DATA" and self.recipients:
                    self.conn.sendall(b"354 Start mail input; end with <CRLF>.<CRLF>\r\n")
                    self.state = "DATA_INPUT"
                    data_buffer = []
                elif command == "QUIT":
                    self.conn.sendall(b"221 Service closing transmission channel\r\n")
                    return
                else:
                    self.conn.sendall(b"503 Bad sequence of commands\r\n")
        except (ConnectionError, OSError):
            pass
        finally:
            self.conn.close()

    def _finish_message(self, data_buffer):
        raw_message = "\n".join(data_buffer)
        header_text, _, body = raw_message.partition("\n\n")
        subject = "(No Subject)"
        for header in header_text.splitlines():
            if header.lower().startswith("subject:"):
                subject = header.split(":", 1)[1].strip()
                break
        for recipient in self.recipients:
            store.save_message(recipient, self.sender, subject, body)
        self.conn.sendall(b"250 Message accepted for delivery\r\n")
        self.state = "MAIL"
        self.sender = None
        self.recipients = []

def start_smtp_server():
    store.init_store()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((HOST, PORT))
    except OSError as error:
        server.close()
        print(f"[SMTP Server] Could not bind {HOST}:{PORT}: {error}")
        return
    server.listen(5)
    print(f"[SMTP Server] Listening on {HOST}:{PORT}")
    
    while True:
        conn, addr = server.accept()
        session = SmtpSession(conn, addr)
        session.start()

if __name__ == "__main__":
    start_smtp_server()