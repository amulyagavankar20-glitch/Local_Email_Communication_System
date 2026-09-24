import socket
import threading
import mailbox_store as store

HOST = "127.0.0.1"
PORT = 1100

class Pop3Session(threading.Thread):
    def __init__(self, conn, addr):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.user = None
        self.authenticated = False
        self.deleted_indices = set()

    def run(self):
        try:
            self.conn.sendall(b"+OK POP3 server ready\r\n")
            reader = self.conn.makefile("r", encoding="utf-8", newline="")
            for raw_line in reader:
                parts = raw_line.rstrip("\r\n").split(" ", 1)
                cmd = parts[0].upper()
                arg = parts[1].strip() if len(parts) > 1 else ""
                if cmd == "USER":
                    self.user = arg
                    self.conn.sendall(b"+OK User accepted\r\n")
                elif cmd == "PASS":
                    auth_email = store.authenticate_user(self.user, arg)
                    if auth_email:
                        self.authenticated = True
                        self.user = auth_email
                        self.conn.sendall(b"+OK Mailbox locked and ready\r\n")
                    else:
                        self.conn.sendall(b"-ERR Invalid credentials\r\n")
                elif not self.authenticated:
                    self.conn.sendall(b"-ERR Please authenticate first\r\n")
                elif cmd == "STAT":
                    active = self._active_messages()
                    self.conn.sendall(f"+OK {len(active)} {sum(m[2] for m in active)}\r\n".encode())
                elif cmd == "LIST":
                    active = self._active_messages()
                    self.conn.sendall(f"+OK {len(active)} messages\r\n".encode())
                    for index, _, size in active:
                        self.conn.sendall(f"{index} {size}\r\n".encode())
                    self.conn.sendall(b".\r\n")
                elif cmd == "RETR":
                    index = self._message_index(arg)
                    content = store.read_message(self.user, index) if index else None
                    if content is None:
                        self.conn.sendall(b"-ERR No such message\r\n")
                    else:
                        self.conn.sendall(b"+OK Message follows\r\n")
                        for line in content.splitlines():
                            prefix = "." if line.startswith(".") else ""
                            self.conn.sendall((prefix + line + "\r\n").encode())
                        self.conn.sendall(b".\r\n")
                elif cmd == "DELE":
                    index = self._message_index(arg)
                    if not index:
                        self.conn.sendall(b"-ERR No such message\r\n")
                    else:
                        self.deleted_indices.add(index)
                        self.conn.sendall(f"+OK Message {index} marked for deletion\r\n".encode())
                elif cmd == "QUIT":
                    for index in sorted(self.deleted_indices, reverse=True):
                        store.delete_message(self.user, index)
                    self.conn.sendall(b"+OK POP3 server signing off\r\n")
                    return
                else:
                    self.conn.sendall(b"-ERR Unknown command\r\n")
        except (ConnectionError, OSError):
            pass
        finally:
            self.conn.close()

    def _active_messages(self):
        return [message for message in store.list_messages(self.user)
                if message[0] not in self.deleted_indices]

    def _message_index(self, value):
        try:
            index = int(value)
        except ValueError:
            return None
        return index if any(message[0] == index for message in self._active_messages()) else None

def start_pop3_server():
    store.init_store()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((HOST, PORT))
    except OSError as error:
        server.close()
        print(f"[POP3 Server] Could not bind {HOST}:{PORT}: {error}")
        return
    server.listen(5)
    print(f"[POP3 Server] Listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        session = Pop3Session(conn, addr)
        session.start()

if __name__ == "__main__":
    start_pop3_server()