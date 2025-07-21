
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html', username='Ryan', insert_text='Wish you have a good day!!!')

@app.route('/preview', methods=['GET', 'POST'])
def preview():
    if request.method == 'POST':
        chordpro_text = request.form.get('chordpro_text')
        return render_template('preview.html', content=chordpro_text)
    return render_template('preview.html', content=None)

@app.route('/search_artist', methods=['GET'])
def search_artist():
    # Now all of them are all fake names , will update later by connecting to the database
    #There are twenty six names here, all of them are fake, start with letter A to Z.
    artists = [
        'Andy', 'Brandon', 'Caleb', 'Drake',
        'Edward', 'Fred', 'Grayson', 'Humza',
        'Ismael', 'John', 'Kush', 'Lawson',
        'Michelle', 'Nick', 'Owen','Peter',
        'John','Ryan' ,'Sophie' ,'Trevor',
        'Uno','Vivian' , 'William','Xanthos',
        'Yerson','Zachery'

    ]

    letter = request.args.get('letter', 'A').upper()
    filtered = [artist for artist in artists if artist.upper().startswith(letter)]

    return render_template('search_artist.html', letter=letter, artists=filtered)

@app.route('/search_title', methods=['GET', 'POST'])
def search_title():
    # fake songs
    # just to show that there are some songs can be searched
    # The firstfive songs here are the one I have in my computer
    all_songs = [
        'Finger Family Song', 
        'Jingle Bells', 
        'London Bridge is Falling Down', 
        'Old McDonald Had A Farm', 
        'Thomas and Friends Theme Song', 
        'Fix You',
        'Believer', 
        'Blinding Lights', 
        'Starboy',
        'Love Story', 
        'Love Me Like You Do',
        'Neveda', 
        
        
    ]

    results = []
    keyword = ''

    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip().lower()
        results = [song for song in all_songs if keyword in song.lower()]

    return render_template('search_title.html', keyword=keyword, results=results)



if __name__ == '__main__':
    app.run(debug=True)
