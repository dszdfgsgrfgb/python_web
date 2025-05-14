from flask import Flask, request, render_template, jsonify
import subprocess
import sys
import tempfile
import os
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/install_package', methods=['POST'])
def install_package():
    package = request.json.get('package')
    if not package:
        return jsonify({'error': 'No package specified'}), 400
    
    try:
        # Run pip install in a subprocess with timeout
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', package],
                              capture_output=True,
                              text=True,
                              timeout=60)
        
        return jsonify({
            'output': result.stdout,
            'error': result.stderr,
            'returncode': result.returncode
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Installation timed out (60 seconds limit)'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/execute', methods=['POST'])
def execute_code():
    code = request.json.get('code')
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    
    try:
        # Create a temporary file to store the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file_name = f.name

        # Execute the code in a subprocess with timeout
        result = subprocess.run([sys.executable, temp_file_name],
                              capture_output=True,
                              text=True,
                              timeout=30)
        
        # Clean up the temporary file
        os.unlink(temp_file_name)

        return jsonify({
            'output': result.stdout,
            'error': result.stderr,
            'returncode': result.returncode
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Execution timed out (30 seconds limit)'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
