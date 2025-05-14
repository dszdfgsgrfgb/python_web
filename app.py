from flask import Flask, request, render_template, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import sys
import tempfile
import os
import json
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

def stream_output(process, sid):
    for line in iter(process.stdout.readline, b''):
        socketio.emit('output', {'data': line.decode()}, room=sid)
    process.stdout.close()

def stream_error(process, sid):
    for line in iter(process.stderr.readline, b''):
        socketio.emit('error', {'data': line.decode()}, room=sid)
    process.stderr.close()

@socketio.on('install_package')
def handle_package_install(data):
    package = data.get('package')
    if not package:
        emit('error', {'data': 'No package specified'})
        return

    try:
        process = subprocess.Popen(
            [sys.executable, '-m', 'pip', 'install', package],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True
        )

        # Create threads to stream output and error in real-time
        thread_out = threading.Thread(target=stream_output, args=(process, request.sid))
        thread_err = threading.Thread(target=stream_error, args=(process, request.sid))
        
        thread_out.start()
        thread_err.start()
        
        # Wait for the process to complete
        process.wait()
        
        thread_out.join()
        thread_err.join()

        if process.returncode == 0:
            emit('complete', {'status': 'success'})
        else:
            emit('complete', {'status': 'error'})

    except Exception as e:
        emit('error', {'data': str(e)})

@socketio.on('execute_code')
def handle_code_execution(data):
    code = data.get('code')
    if not code:
        emit('error', {'data': 'No code provided'})
        return

    try:
        # Create a temporary file to store the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file_name = f.name

        process = subprocess.Popen(
            [sys.executable, temp_file_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True
        )

        # Create threads to stream output and error in real-time
        thread_out = threading.Thread(target=stream_output, args=(process, request.sid))
        thread_err = threading.Thread(target=stream_error, args=(process, request.sid))
        
        thread_out.start()
        thread_err.start()
        
        # Wait for the process to complete
        process.wait()
        
        thread_out.join()
        thread_err.join()

        # Clean up the temporary file
        os.unlink(temp_file_name)

        if process.returncode == 0:
            emit('complete', {'status': 'success'})
        else:
            emit('complete', {'status': 'error'})

    except Exception as e:
        emit('error', {'data': str(e)})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
