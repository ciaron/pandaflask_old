import os
import uuid
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template, session, abort, flash, g
from flask import send_from_directory
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug import secure_filename
from werkzeug import generate_password_hash, check_password_hash

from flaskext.uploads import (UploadSet, configure_uploads, IMAGES,
                              UploadNotAllowed)

SECRET_KEY = 'development key'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
UPLOADED_PHOTOS_DEST = '/home/linstead/flask/pandachrome.flask/UPLOADS'

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOADED_FILES_DEST'] = '/home/linstead/flask/pandachrome.flask/UPLOADS'
app.config['UPLOADED_FILES_URL'] = '/files/'

uploaded_photos = UploadSet('photos', IMAGES)
configure_uploads(app, uploaded_photos)

db = SQLAlchemy(app)

def to_index():
    return redirect(url_for('index'))

def unique_id():
    return hex(uuid.uuid4().time)[2:-1]

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    pwdhash = db.Column(db.String())
    email = db.Column(db.String(120), unique=True)
    activate = db.Column(db.Boolean)
    created = db.Column(db.DateTime)
    images = db.relationship('Image', backref='owner', lazy='dynamic')

    def __init__(self, username, password, email):
        self.username = username
        self.pwdhash = generate_password_hash(password)
        self.email = email

    def __repr__(self):
        return '<User %r>' % self.username

    def check_password(self, password):
        return check_password_hash(self.pwdhash, password)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    added = db.Column(db.DateTime)
    title = db.Column(db.String(80))
    filename = db.Column(db.String(80))
    description = db.Column(db.String(240))
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)

    def __init__(self, title, description, filename, owner_id):
        self.title = title 
        self.description = description
        self.filename = filename
        self.owner_id = owner_id
        db.session.add(self)
        db.session.commit()
    
## Standard Forms
#class signup_form(Form):
#    username = TextField('Username', [validators.Required()])
#    password = PasswordField('Password', [validators.Required(), validators.EqualTo('confirm', message='Passwords must match')])
#    confirm = PasswordField('Confirm Password', [validators.Required()])
#    email = TextField('eMail', [validators.Required()])
#    accept_tos = BooleanField('I accept the TOS', [validators.Required])
#
#class login_form(Form):
#    username = TextField('Username', [validators.Required()])
#    password = TextField('Password', [validators.Required()])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    images = Image.query.all()
    return render_template('index.html', images=images)

#def upload_file():
    #if request.method == 'POST':
    #    file = request.files['file']
    #    if file and allowed_file(file.filename):
    #        filename = secure_filename(file.filename)
    #        file.save(os.path.join(app.config['UPLOADED_FILES_DEST'], filename))
    #        return redirect(url_for('uploaded_file',
    #                                filename=filename))
    #return render_template('upload.html')

# require login:
#@app.route('/project/<int:project_id>/<int:image_id>')
#@app.route('/project/<int:project_id>')
#@app.route('/image/<int:image_id>')

# no login required
#@app.route('/<username>/project/<int:project_id>/<int:image_id>')
#@app.route('/<username>/project/<int:project_id>')
#@app.route('/<username>/image/<int:image_id>')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOADED_FILES_DEST'], filename)

@app.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        photo = request.files.get('photo')
        title = request.form.get('title')
        description = request.form.get('description')
    
        if not (photo and title and description):
            flash("You must fill in all the fields")
        else:
            try:
                filename = uploaded_photos.save(photo)
            except UploadNotAllowed:
                flash("The upload was not allowed")
            else:
                if 'username' in session:
                    # i.e. logged in
                    owner = User.query.filter_by(username=session['username']).first()
                    image = Image(title=title, description=description, filename=filename, owner_id=owner.id)
                    flash("Upload successful")
                return to_index()

    return render_template('new.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if not user.check_password(request.form['password']):
            error = "Login failed"
#        if request.form['username'] != app.config['USERNAME']:
#            error = 'Invalid username'
#        elif request.form['password'] != app.config['PASSWORD']:
#            error = 'Invalid password'

        else:
            session['logged_in'] = True
            session['username'] = request.form['username']
            flash('You were logged in')
            return redirect(url_for('index'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
