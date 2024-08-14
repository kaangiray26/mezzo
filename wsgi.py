import signal
from app import app
import webbrowser
from gevent.pywsgi import WSGIServer

address = "localhost"
port = 5000

# Create the server
http_server = WSGIServer((address, port), app)

def signal_handler(signal, frame):
    print("Exiting...")
    http_server.stop()
    exit(0)

# Attach signal handlers
signal.signal(signal.SIGINT, signal_handler)

# Start and open the browser
http_server.start()
webbrowser.open(f"http://{address}:{port}")

# Serve forever
http_server.serve_forever()
