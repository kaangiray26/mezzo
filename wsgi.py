from gevent.pywsgi import WSGIServer
from app import app

address = "localhost"
port = 5000

# Start the server
try:
    http_server = WSGIServer((address, port), app)
    http_server.serve_forever()
except KeyboardInterrupt:
    print("Server stopped.")
    exit(0)
