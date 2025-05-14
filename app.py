from flask import Flask, request, render_template, jsonify
import subprocess
import sys
import tempfile
import os
import requests
import pkg_resources
import threading
import time
from datetime import datetime

app = Flask(__name__)

GEMINI_API_KEY = 'AIzaSyA3SlVaUvDgS6FW7DUdVHuFduByaIOeDmM'
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'
RENDER_URL = 'https://python-web-25i2.onrender.com/'

def ping_render():
    while True:
        try:
            response = requests.get(RENDER_URL)
            if response.status_code == 200:
                print(f"[{datetime.now()}] Ping successful - Status: {response.status_code}")
            else:
                print(f"[{datetime.now()}] Ping failed - Status: {response.status_code}")
        except Exception as e:
            print(f"[{datetime.now()}] Ping error: {str(e)}")
        time.sleep(30)  # Wait for 30 seconds

# Start the ping thread
ping_thread = threading.Thread(target=ping_render, daemon=True)
ping_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

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

@app.route('/get_fix', methods=['POST'])
def get_fix():
    code = request.json.get('code')
    error = request.json.get('error')
    
    if not code or not error:
        return jsonify({'error': 'Code and error message are required'}), 400
    
    try:
        prompt = f"""As a Python expert, analyze this code and error message, then provide:\n1. A brief explanation of the error\n2. The corrected code\n\nCode:\n{code}\n\nError:\n{error}\n\nPlease format your response as:\nEXPLANATION:\n[Your explanation here]\n\nFIXED_CODE:\n[Your corrected code here]"""

        headers = {
            'Content-Type': 'application/json',
        }
        
        data = {
            'contents': [{
                'parts': [{
                    'text': prompt
                }]
            }]
        }
        
        response = requests.post(
            f'{GEMINI_API_URL}?key={GEMINI_API_KEY}',
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            return jsonify({'error': f'API request failed: {response.text}'}), 500
            
        response_data = response.json()
        response_text = response_data['candidates'][0]['content']['parts'][0]['text']
        
        # Parse the response to separate explanation and fixed code
        parts = response_text.split('FIXED_CODE:')
        explanation = parts[0].replace('EXPLANATION:', '').strip()
        fixed_code = parts[1].strip() if len(parts) > 1 else ''
        
        return jsonify({
            'explanation': explanation,
            'fixed_code': fixed_code
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ai_chat', methods=['POST'])
def ai_chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    try:
        headers = {
            'Content-Type': 'application/json',
        }
        data = {
            'contents': [{
                'parts': [{
                    'text': user_message
                }]
            }]
        }
        response = requests.post(
            f'{GEMINI_API_URL}?key={GEMINI_API_KEY}',
            headers=headers,
            json=data
        )
        if response.status_code != 200:
            return jsonify({'error': f'API request failed: {response.text}'}), 500
        response_data = response.json()
        ai_reply = response_data['candidates'][0]['content']['parts'][0]['text']
        return jsonify({'reply': ai_reply})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/install_package', methods=['POST'])
def install_package():
    package = request.json.get('package')
    if not package:
        return jsonify({'error': 'No package name provided'}), 400
    
    try:
        # Install the package using pip
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return jsonify({'error': result.stderr}), 500
            
        return jsonify({'message': f'Successfully installed {package}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uninstall_package', methods=['POST'])
def uninstall_package():
    package = request.json.get('package')
    if not package:
        return jsonify({'error': 'No package name provided'}), 400
    
    try:
        # Uninstall the package using pip
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'uninstall', '-y', package],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return jsonify({'error': result.stderr}), 500
            
        return jsonify({'message': f'Successfully uninstalled {package}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/list_packages', methods=['GET'])
def list_packages():
    try:
        # Get list of installed packages
        installed_packages = [pkg.key for pkg in pkg_resources.working_set]
        return jsonify({'packages': installed_packages})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))