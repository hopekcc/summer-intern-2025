
from flask import Flask, render_template

import firebase_admin
from firebase_admin import credentials, auth

app = Flask(__name__)
'''
# Initialize Firebase
cred = credentials.Certificate("firebase_key.json")  # or the exact name of your downloaded key
firebase_admin.initialize_app(cred)
'''
@app.route('/')
def home():
    return render_template('home.html', username='Ryan', insert_text='Wish you have a good day!!!')

if __name__ == '__main__':
    app.run(debug=True)
