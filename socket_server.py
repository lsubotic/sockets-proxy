from _thread import start_new_thread
import socket
import traceback
import sys

# Constants
LOCALHOST = ''
SERVER_PORT = 8080  # default port value
BUFFER_SIZE = 4096
MAX_CONNS = 100
TIMEOUT = 10


def server_start():
    """
    Creates an server socket that is visible to all devices on the network
    :return: Server socket
    """

    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((LOCALHOST, SERVER_PORT))
        server.listen(MAX_CONNS)
        print('>> Server started successfully... [CTRL-C to exit]')
        print('Listening for connections...')
        print(f'Port used: {SERVER_PORT}')

    except KeyboardInterrupt:
        print('[CTRL-C] Server shutting down...')
        sys.exit(0)
    except Exception as e:
        print(f'[!] Server initialization error: {e}')
        sys.exit(1)

    return server


def server_run():
    """
    Accepts upcoming requests from the client and starts an thread for each connection
    """
    server = server_start()
    while True:
        try:
            # Create a new client socket and receive the data
            conn, address = server.accept()
            request_data = conn.recv(BUFFER_SIZE)

            if not request_data:
                conn.close()
            else:
                # Start new thread
                start_new_thread(protocol_thread, (conn, request_data))

        except KeyboardInterrupt:
            server.close()
            print('[CTRL-C] Server shutting down...')
            sys.exit(0)


def protocol_thread(conn, request_data):
    """
    This function is called in a new thread, checks if the protocol is http or https and calls the according functions to handle them
    """
    first_line = request_data.split(b'\n')[0]

    if b'CONNECT' in first_line:
        # HTTPS (not implemented yet)
        pass
    elif b'GET' in first_line:
        # HTTP
        handle_http(conn, request_data)
    else:
        print('Unexpected error, please reload')
        return None


def get_web_host(request_data):
    """
     Gets the web server host and the requested url
    :param request_data: Request that the browser sent
    :return: web host of the requested url, requested url
    """
    first_line = request_data.decode().split('\n')[0]
    url = first_line.split(' ')[1]

    http_pos = url.find('://')
    # If 'http' is not in url, temp = url, if it is in url remove the 'http://'
    if http_pos == -1:
        temp = url
    else:
        temp = url[(http_pos + 3):]

    # Checks if the port is in the url
    port_pos = temp.find(":")

    web_server_pos = temp.find('/')
    if web_server_pos == -1:
        # Checks if there's '/' at end of the url
        web_server_pos = len(temp)

    if port_pos == -1 or web_server_pos < port_pos:
        # If the port is not in the data, slice temp in case '/' is at the end
        web_host = temp[:web_server_pos]
    else:
        # If the port is in the data, remove it
        web_host = temp[:port_pos]

    return web_host, url


def handle_http(conn, request_data):
    """
    Creates an client socket to handle the HTTP connection
    """
    web_host, url = get_web_host(request_data)
    port = 80

    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        s.connect((web_host, port))
        print(f'[*] Connected to {web_host}')
        print(f'>>>Requested url: {url}')
        connection_resolve(s, conn, request_data)
    except socket.error as e:
        print(e)
        traceback.print_exc()
        if s: s.close()
        conn.close()
    except Exception as e:
        if s: s.close()
        conn.close()
        print(e)


def connection_resolve(sock, conn, request_data):
    """
    Sends the request to the web server and forwards the web server's response back to the client
    """
    try:
        sock.send(request_data)

        while True:
            # Receives the reply from the server
            reply = sock.recv(BUFFER_SIZE)
            if len(reply) > 0:
                # Forwards the reply back to the client
                conn.send(reply)
            else:
                break
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        conn.close()
    except socket.error as e:
        print(e)
        traceback.print_exc()
        sock.close()
        conn.close()
    except Exception as e:
        print('[!] Unexpected error: ', e)
        sock.close()
        conn.close()


def custom_port(command):
    """
    Returns the custom port if the command and port are valid
    """
    try:
        if '--' in command:
            port = int(command.replace('--', ''))
            if port < 1 or port > 65535:
                print('Please enter port in valid range [1 - 65535]')
                sys.exit(0)

            return port
        else:
            print('[!] Invalid command, please try again')
            sys.exit(1)
    except Exception as e:
        print(f'[!]Invalid command, please try again {e}')
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        SERVER_PORT = custom_port(cmd)

    try:
        server_run()
    except KeyboardInterrupt:
        print('[CTRL-C] Server shutting down...')
        sys.exit(0)
    except Exception as e:
        print("[!] An error ocurred, server has been stopped: ", e)
