# sockets-proxy
Python proxy server which handles HTTP requests

## Features:
* Easily customizable
* Easy to run
* Supports IPv4/IPv6
* Can be wrapped with SSL to handle HTTPS connections
The script is written in Python 3.8



## How to use:
Install the **sockets** module if you don't have it:
```bash
$ pip install sockets
```
Then simply run the server:
```bash
$ python socket_server.py
```

The server will start listening for connections on port 8080 by default, to choose a custom port use **'--'**<br/>
**Example:** ```$ python socket_server.py --1312``` sets the server port to **1312**<br/>
*Ports in range **1-1023** are not recommended as they are privileged and usually reserved for well known services*.<br/>
</br>
Make sure to run the server with adminstrator privileges!




