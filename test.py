from pandachrome import db
from pandachrome import User

# from http://packages.python.org/Flask-SQLAlchemy/quickstart.html#a-minimal-application

db.create_all()

c = User('ciaron', 'default', 'ciaron@ciaron.net')
db.session.add(c)
db.session.commit()

users = User.query.all()
