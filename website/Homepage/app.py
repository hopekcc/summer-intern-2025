
import os
from flask import Flask, render_template, request, send_from_directory, url_for, abort
from werkzeug.utils import secure_filename
import re #regex

app = Flask(__name__)

PDF_FOLDER = os.path.join(app.root_path, 'static', 'pdfs')
app.config['PDF_FOLDER'] = PDF_FOLDER

@app.route('/')
def home():
    return render_template('home.html', username='Mentor', insert_text='Welcome to our demo!!!')

# CHORDPRO PREVIEW
@app.route('/preview', methods=['GET', 'POST'])
def preview():
    if request.method == 'POST':
        chordpro_text = request.form.get('chordpro_text')
        return render_template('preview.html', content=chordpro_text)
    return render_template('preview.html', content=None)

# CHORDPRO PDF VIEWER
@app.route('/view/<path:filename>')
def view_pdf(filename):
    filename = secure_filename(filename)
    file_path = os.path.join(app.config['PDF_FOLDER'], filename)
    if not os.path.exists(file_path):
        abort(404)
    return render_template('view.html', filename=filename)

# SIMPLIFY FOR URL
def make_slug(title):
    # lowercase, strip out non‑alphanumerics, smash together
    return re.sub(r'[^a-z0-9]', '',
                  title.lower()) + '.pdf'

# RETRIEVE PDF METHOD
@app.route('/pdfs/<path:filename>')
def serve_pdf(filename):
    return send_from_directory(app.config['PDF_FOLDER'], filename)

# ARTIST SEARCH METHOD
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
# TITLE SEARCH METHOD
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
        for song in all_songs:
            if keyword in song.lower():
                filename = make_slug(song)
                # builds "/view/jinglebells.pdf", etc.
                pdf_url = url_for('view_pdf', filename=filename)
                results.append({
                    'title': song,
                    'pdf_url': pdf_url
                })

    return render_template('search_title.html', keyword=keyword, results=results)


# GCP Hosting
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
