import http.server
import socketserver
import cgi
import os
import shutil

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class FileUploadHandler(http.server.BaseHTTPRequestHandler):

    def _set_headers_and_status(self, status_code, content_type="application/json"):
        """Helper to set status code, CORS, and Content-Type headers correctly."""
        self.send_response(status_code)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header("Content-Type", content_type)
        self.end_headers() # All headers are sent now

    def do_OPTIONS(self):
        # Handle the CORS preflight request
        self._set_headers_and_status(200) # Sets all headers, including CORS and ends them
        # No body needed for OPTIONS

    def do_POST(self):
        
        # Use cgi.FieldStorage to parse the incoming data stream
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type'],
            }
        )

        try:
            file_item = form["file"] 
        except KeyError:
            self._set_headers_and_status(400)
            self.wfile.write(b'{"message": "Required field \'file\' is missing"}')
            return

        if file_item.filename:
            filename = os.path.basename(file_item.filename)
            filepath = os.path.join(UPLOAD_DIR, filename)

            try:
                with open(filepath, 'wb') as output_file:
                    shutil.copyfileobj(file_item.file, output_file)
                
                print(f"Uploaded and saved: {filepath}")
                self._set_headers_and_status(200) # Sets all headers and ends them
                self.wfile.write(b'{"message": "File uploaded successfully!"}')

            except IOError as e:
                print(f"Failed to save file: {e}")
                self._set_headers_and_status(500)
                self.wfile.write(b'{"message": "Failed to save file"}')
        else:
            self._set_headers_and_status(400)
            self.wfile.write(b'{"message": "No filename found in the uploaded file part"}')


def run_server(port=8000):
    with socketserver.TCPServer(("", port), FileUploadHandler) as httpd:
        print(f"Serving at port {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server(port=8000)
