from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)
    # The debug=True option allows for automatic reloading and better error messages during development