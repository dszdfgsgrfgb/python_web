from flask import Flask, request, render_template, jsonify
import subprocess
import sys
import tempfile
import os
import requests

app = Flask(__name__)

GEMINI_API_KEY = 'AIzaSyA3SlVaUvDgS6FW7DUdVHuFduByaIOeDmM'
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))