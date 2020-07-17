from socket_server import get_web_host, connection_resolve, TIMEOUT
import socket
import traceback
import ssl
import re

CA_CERT = r'ca-certificates.crt'
# CA_CERT = '/etc/ssl/certs/ca-certificates.crt'  # Linux path

# Custom certs
KEYFILE = None
CERTFILE = None


def ssl_socket(sock, keyfile=None, certfile=None, cert_reqs=None, ca_certs=None, server_hostname=None, ssl_version=None):
    """
    Wraps the socket as an SSL object

    :param sock: Client socket
    :param keyfile: Custom private key file
    :param certfile: Custom certificate file
    :return: SSL wrapped client socket
    """
    context = ssl.SSLContext(ssl_version)
    context.verify_mode = cert_reqs
    if ca_certs:
        try:
            context.load_verify_locations(ca_certs)
        except Exception as e:
            raise ssl.SSLError(e)

    if certfile:
        context.load_cert_chain(certfile, keyfile)

    if ssl.HAS_SNI:
        # if OpenSSL has support for server name indication
        return context.wrap_socket(sock, server_hostname=server_hostname)

    return context.wrap_socket(sock)


def handle_https(conn, request_data):
    """
    Creates a client socket to handle the HTTPS and resolves it by calling connection_resolve()

    :param conn:
    :param request_data:
    """

    web_host, url = get_web_host(request_data)
    port = 443

    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((web_host, port))
        print(f'[*] Connected to {web_host}')
        ssock = ssl_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1, cert_reqs=ssl.CERT_REQUIRED, ca_certs=CA_CERT, server_hostname=web_host)

        ssock.write('GET / \n'.encode('utf-8'))

        url = re.match(r'.+\.\w+', url).group(0)
        url = url if 'www' in url else 'www.' + url
        print(f'> Requested url: {url}')

        request_data = format_data(request_data, web_host)

        connection_resolve(ssock, conn, request_data)
    except socket.error as e:
        print(e)
        traceback.print_exc()
        if sock: sock.close()
        conn.close()
    except Exception as e:
        print(e)
        traceback.print_exc()
        if sock: sock.close()
        conn.close()


def format_data(data, web_host):
    """
    Modifies request data which browser sends to the proxy into an correct format so that the web server will accept it

    :param data:  Request which browser sends to the proxy server
    :param web_host: Host of the requested web server
    :return: Modified browser request that the web sever will accept
    """

    newline = b'\n'

    lines = data.rsplit(newline)
    # Split lines and format them
    for i, line in enumerate(lines):
        lines[i] = line + newline if line else line

    get_link_line, host_line, useragent_line, other_lines = b'', b'', b'', b''  # Lines of data
    for l in lines:
        if b'CONNECT' in l:
            # First line in the request will now use GET
            get_link_line = l.replace(b'CONNECT', b'GET')
            if b':443' in get_link_line:
                # remove the port
                get_link_line = get_link_line.replace(b':443', b'')

            url = get_link_line.split(b' ')[1]
            if url == web_host.encode():
                # if the requested url is same as the host, replace it with '/'
                get_link_line = get_link_line.replace(url, b'/')
            else:
                # Remove the host part of the url(leave everything after '/')
                get_link_line = get_link_line.replace(web_host.encode, b'')
        elif b'Host' in l:
            if b':443' in l:
                host_line = l.replace(b':443', b'')
            else:
                host_line = l
        elif b'User-Agent:' in l:
            useragent_line = l
        elif b'Proxy' in l:
            # Skip lines with 'proxy' in it
            continue
        elif b'Connection:' in l:
            continue
        else:
            # Append all other lines
            other_lines += l

    proxy_request_data = get_link_line + host_line + useragent_line + other_lines
    return proxy_request_data


