# sockets-proxy
Python proxy server which handles HTTP requests

## How to use:
Install the **sockets** module if you don't have it:
```bash
$ pip install sockets
```
Then simply run the server:
```bash
$ python socket_server.py
```

The server will start listening for connections on port 8080 by default, to choose a custom port type in **--'value'**
**Example:** ```bash $ python socket_server.py --1312``` sets the server port to **1312**.
