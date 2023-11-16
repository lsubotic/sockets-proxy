# sockets-proxy
Python proxy server that handles HTTP/HTTPS requests


## Setup:
Install the **sockets** module if you don't have it:
```bash
$ pip install sockets
```
Then simply run the server:
```bash
$ python socket_server.py
```
## Details
Proxy server written in python, using the `[socket](https://docs.python.org/3/library/socket.html)` module, capable of handling HTTP and HTTPS. 
*Note that Ports in range **1-1023** are not recommended as they are privileged 

## How it works
- Creates a server socket that is ready to accept incoming connections from clients (ex. Mozilla)
- Determines whether connections are HTTP or HTTPS
- `HTTP` connections get immediately resolved, `HTTPS` connections are *persistent* and stay open until closed

*NOTE for HTTPS: This is NOT a 'Man in the middle' proxy that enables the user to see the tunneled HTTPS data, as the data sent between the browser and the remote webserver is encrypted, a man in the middle proxy would require the proxy server to have its own certificates that would decrypt the browser data, read it, and then encrypt them again and send to the remote web server. The browser and the remote web server would also need to trust the ProxyServer's certificates. This proxy ONLY proxies the data, it DOES NOT read it.*
*However, for HTTP connections, as they don't have encryption, the data passing through the proxy over a HTTP connection can be easily seen* 


</br>

To configure the proxy with Mozilla check out [this guide](https://support.mozilla.org/en-US/kb/connection-settings-firefox).<br/>
For other browsers please check out their documentation.<br/>

## Examples:
- Server is waiting for the browser to connect to it


- Connection is accepted


- A request is made, to [Python docs](https://docs.python.org/3/), for example, and each further connection is handled



