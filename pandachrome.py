import os
import uuid
from PIL import Image as PImage
from datetime import datetime
from functools import wraps
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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') is not None:
            return f(*args, **kwargs)
        else:
            flash('Please log in first...', 'error')
            return redirect(url_for('login', next=request.url))
    return decorated_function

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    pwdhash = db.Column(db.String())
    email = db.Column(db.String(120), unique=True)
    activated = db.Column(db.Boolean)
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

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    added = db.Column(db.DateTime)
    title = db.Column(db.String(80))
    description = db.Column(db.String(240))
    projects = db.relationship('Project', backref='category', lazy='dynamic')
    
    def __init__(self, title, description, owner_id):
        self.title = title 
        self.description = description
        self.owner_id = owner_id
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    added = db.Column(db.DateTime)
    title = db.Column(db.String(80))
    description = db.Column(db.String(240))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    
    def __init__(self, title, description, category_id, owner_id):
        self.title = title 
        self.description = description
        self.owner_id = owner_id
        self.category_id = category_id
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    added = db.Column(db.DateTime)
    title = db.Column(db.String(80))
    filename = db.Column(db.String(80))
    description = db.Column(db.String(240))
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __init__(self, title, description, filename, owner_id):
        self.title = title 
        self.description = description
        self.filename = filename
        self.owner_id = owner_id
        db.session.add(self)
        db.session.commit()
    
###
# VIEWS
###

# require login:
@app.route('/project/<int:project_id>/<int:image_id>')
def projectimage(project_id, image_id):
    return render_template('test.html', project_id=project_id, image_id=image_id)
    
@app.route('/image/<int:image_id>')
def image(image_id):
    return render_template('test.html', image_id=image_id)
    
# no login required
#@app.route('/<username>/project/<int:project_id>/<int:image_id>')
#@app.route('/<username>/project/<int:project_id>')
#@app.route('/<username>/image/<int:image_id>')

@app.route('/category/<int:category_id>/delete', methods=['POST'])
def category_delete(category_id):
    if request.method == 'POST':
        owner = User.query.filter_by(username=session['username']).first()
        category = Category.query.filter_by(owner_id=owner.id).filter_by(id=category_id).first()
        # delete the category
        category.delete()
        # get the category list for the template:
        categories = Category.query.filter_by(owner_id=owner.id)
        return render_template('categories.html', categories=categories)

    return render_template('index.html')
            
@app.route('/project/<int:project_id>/delete', methods=['POST'])
def project_delete(project_id):
    if request.method == 'POST':
        owner = User.query.filter_by(username=session['username']).first()
        project = Project.query.filter_by(owner_id=owner.id).filter_by(id=project_id).first()
        # delete the project
        project.delete()
        # get the project list for the template:
        projects = Project.query.filter_by(owner_id=owner.id)
        categories = Category.query.filter_by(owner_id=owner.id)
        return render_template('projects.html', projects=projects, categories=categories)

    return render_template('index.html')

@app.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
def project_edit(project_id):
    owner = User.query.filter_by(username=session['username']).first()
    project = Project.query.filter_by(owner_id=owner.id).filter_by(id=project_id).first()
    categories = Category.query.filter_by(owner_id=owner.id)

    if request.method == 'POST':
        # edit the project
        project.title = request.form.get('title') 
        project.description = request.form.get('description') 
        project.category_id = request.form.get('category_id') 
        db.session.commit()

        # get the project list for the template:
        projects = Project.query.filter_by(owner_id=owner.id)

        # show the updated project list
        #return render_template('projects.html', projects=projects, categories=categories)
        return redirect(url_for('projects'))

    elif request.method == 'GET':
        return render_template('project_edit.html', project=project, categories=categories)
            
@app.route('/project/<int:project_id>')
def project(project_id):
    # show project detail page
    owner = User.query.filter_by(username=session['username']).first()
    project = Project.query.filter_by(owner_id=owner.id).filter_by(id=project_id).first()
    return render_template('project.html', project=project)
    
@app.route('/categories', methods=['GET', 'POST'])
@require_login
def categories():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
    
        if not (title):
            flash("You must give at least a title")
        else:
            if 'username' in session:
                # i.e. logged in
                owner = User.query.filter_by(username=session['username']).first()
                category = Category(title=title, description=description, owner_id=owner.id)
                flash("successfully created new category " + title)
            #return to_index()
            return redirect(url_for('categories'))

    owner = User.query.filter_by(username=session['username']).first()
    categories = Category.query.filter_by(owner_id=owner.id)
    return render_template('categories.html', categories=categories)

@app.route('/projects', methods=['GET', 'POST'])
@require_login
def projects():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category_id = request.form.get('category_id')
    
        if not (title):
            flash("You must give at least a title")
        else:
            if 'username' in session:
                # i.e. logged in
                owner = User.query.filter_by(username=session['username']).first()
                project = Project(title=title, description=description, category_id=category_id, owner_id=owner.id)
                flash("successfully created new project " + title + ", category " + category_id)
            #return to_index()
            return redirect(url_for('projects'))

    owner = User.query.filter_by(username=session['username']).first()
    projects = Project.query.filter_by(owner_id=owner.id)
    categories = Category.query.filter_by(owner_id=owner.id)
    return render_template('projects.html', projects=projects, categories=categories)
    
@app.route('/', methods=['GET', 'POST'])
def index():
    images = Image.query.all()
    return render_template('index.html', images=images)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOADED_FILES_DEST'], filename)

@app.route('/upload', methods=['GET', 'POST'])
@require_login
def upload():

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

    return render_template('upload.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'GET':
        if 'next' in request.args:
            qs = request.args['next']
            return render_template('login.html', next=qs)
        else:
            return render_template('login.html')
    elif request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if not user.check_password(request.form['password']):
            error = "Login failed"
        else:
            session['logged_in'] = True
            session['username'] = request.form['username']
            flash('You were logged in')
            if 'next' in request.form:
                return redirect(request.form["next"])
            else:
                flash('next not found in request.form')
                return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
