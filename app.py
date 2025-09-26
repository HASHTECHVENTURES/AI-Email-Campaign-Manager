from flask import Flask, render_template, request, jsonify, send_file
import os

app = Flask(__name__)

@app.route('/')
def index():
    return send_file('test.html')

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'message': 'AI Email System is running!'})

@app.route('/api/test')
def test():
    return jsonify({'message': 'Test endpoint working!', 'timestamp': '2024-01-01'})

if __name__ == '__main__':
    app.run(debug=True)
