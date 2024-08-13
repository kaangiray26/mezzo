from gevent.pywsgi import WSGIServer
from app import app
import webbrowser

address = "localhost"
port = 5000

# Start the server
try:
    print(f"Server starting at http://{address}:{port}")
    http_server = WSGIServer((address, port), app)
    http_server.start()
    webbrowser.open("http://localhost:5000")
    http_server.serve_forever()

    # http_server.serve_forever()
except KeyboardInterrupt:
    print("Server stopped.")
    exit(0)
