import socket

def fetch_emails(username, password, log_callback=None):
    def log(msg):
        if log_callback:
            log_callback(msg)

    sock = socket.create_connection(("127.0.0.1", 1100), timeout=5)
    reader = sock.makefile("r", encoding="utf-8", newline="")

    def send_cmd(cmd):
        log(f"C: {cmd}")
        sock.sendall((cmd + "\r\n").encode())
        
    def read_line():
        line = reader.readline().rstrip("\r\n")
        log(f"S: {line}")
        return line

    messages = []
    try:
        read_line()  # Banner
        send_cmd(f"USER {username}")
        if not read_line().startswith("+OK"):
            return False, "Username rejected", []
        send_cmd(f"PASS {password}")
        resp = read_line()
        if not resp.startswith("+OK"):
            return False, "Authentication failed", []

        send_cmd("LIST")
        read_line()
        list_lines = []
        while True:
            line = read_line()
            if line == "." or line.startswith("-ERR"):
                break
            list_lines.append(line)

        for item in list_lines:
            idx = item.split()[0]
            send_cmd(f"RETR {idx}")
            retr_resp = read_line()
            if retr_resp.startswith("+OK"):
                msg_body = []
                while True:
                    mline = read_line()
                    if mline == ".":
                        break
                    msg_body.append(mline[1:] if mline.startswith("..") else mline)
                messages.append((idx, "\n".join(msg_body)))

        send_cmd("QUIT")
        read_line()
        return True, "Fetched successfully", messages
    except Exception as e:
        return False, str(e), []
    finally:
        reader.close()
        sock.close()

def delete_email(username, password, msg_index, log_callback=None):
    def log(msg):
        if log_callback:
            log_callback(msg)

    sock = socket.create_connection(("127.0.0.1", 1100), timeout=5)
    reader = sock.makefile("r", encoding="utf-8", newline="")

    try:
        reader.readline()
        sock.sendall(f"USER {username}\r\n".encode())
        if not reader.readline().startswith("+OK"):
            return False, "Username rejected."
        sock.sendall(f"PASS {password}\r\n".encode())
        if not reader.readline().startswith("+OK"):
            return False, "Authentication failed."
        
        log(f"C: DELE {msg_index}")
        sock.sendall(f"DELE {msg_index}\r\n".encode())
        resp = reader.readline().strip()
        log(f"S: {resp}")

        log("C: QUIT")
        sock.sendall(b"QUIT\r\n")
        reader.readline()
        if not resp.startswith("+OK"):
            return False, resp
        return True, "Message deleted."
    except Exception as e:
        return False, str(e)
    finally:
        reader.close()
        sock.close()