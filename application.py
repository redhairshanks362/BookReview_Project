import os
import json

from flask import Flask
from flask import jsonify
from flask import make_response
from flask import session
from flask import render_template
from flask import redirect
from flask import request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
import requests
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from passlib.hash import pbkdf2_sha256
import secrets

app = Flask(__name__)

app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['JWT_SECRET_KEY'] = secrets.token_urlsafe(32)

jwt = JWTManager(app)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
#Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    if session.get('username') is None:
        return redirect('/login')

    return render_template("index.html")

@app.route("/registration",methods=['GET','POST'])
def registration():
    logged_in = False
    if session.get("username") is not None:
        logged_in = True
        username = session['username']
        return render_template("error.html", logged_in=logged_in, username=username)

    if request.method == "GET":
        return render_template("registration.html")
    
    else:
        username = request.form['username']
        pass1 = request.form['password1']
        pass2 = request.form['password2']
        role = request.form.get('role', 'Regular User')
        error_username = False
        error_password = False

        # check that user doesnt already exist
        user = db.execute(f"""
            select * from users where username = '{username}';
        """)
        
        if user.rowcount > 0:
            error_username = True
            return render_template("registration.html", username = username, error_username = error_username)

        # check the passwords match
        if pass1 != pass2:
            error_password = True
            return render_template("registration.html", username = username, error_password=error_password)
        hashed_password = pbkdf2_sha256.hash(pass1)
        db.execute(f"""
            INSERT INTO users (username, password, role)
            VALUES ('{username}','{hashed_password}', '{role}')
        """)
        db.commit()
        access_token = create_access_token(identity=username)
        session["username"] = username
        return redirect("/")

@app.route("/login", methods=['GET', 'POST'])
def login():

    logged_in = False
    if session.get("username") is not None:
        logged_in = True
        username = session['username']
        return render_template("error.html", logged_in=logged_in, username=username)

    if request.method == 'GET':
        return render_template("login.html")
    
    username = request.form['username']
    password = request.form['password']
    error_no_user = False
    error_wrong_pass = False

    user = db.execute(f"""
        SELECT * FROM users
        WHERE username='{username}'
    """)

    # check if username exists in db
    if user.rowcount == 0:
        error_no_user = True
        return render_template("login.html", error_no_user = error_no_user)
    
    user = user.fetchone()

    # check if password matches password in db
    if not pbkdf2_sha256.verify(password, user['password']):
        error_wrong_pass = True
        return render_template("login.html", error_wrong_pass=error_wrong_pass, username=username)
    
    # TODO: add username to session
    access_token = create_access_token(identity=username)
    session["username"] = username
    return redirect("/")


@app.route("/logout")
def logout():
    if session.get('username') is not None:
        session.pop('username')

    return redirect('/login')

@jwt_required()
def protected_route():
    current_user = get_jwt_identity()
    return f"Hello, {current_user}!"


@app.route("/results", methods=['POST'])
def results():
    if session.get('username') is None:
        return redirect('/login')

    search = request.form['book_search']
    filter_type = request.form.get('filter_type')
    filter_value = request.form.get('filter_value')

    # Construct the SQL query based on the search and filter options
    query = f"""
        SELECT * FROM books WHERE author LIKE '%{search}%'
        OR title LIKE '%{search}%' OR isbn LIKE '%{search}%'
    """

    if filter_type == 'genre' and filter_value:
        query += f" AND genre = '{filter_value}'"

    if filter_type == 'year' and filter_value:
        query += f" AND publication_year = {filter_value}"

    if filter_type == 'rating' and filter_value:
        query += f" AND rating >= {filter_value}"

    books = db.execute(query).fetchall()

    if len(books) == 0:
        return render_template("error.html", no_result=True)
    else:
        return render_template("results.html", books=books, search=search)


@app.route("/books/<string:isbn>", methods = ['POST', 'GET'])
def bookDetail(isbn):
    if session.get('username') is None:
        return redirect('/login')

    user_id = db.execute(f"select id from users where username='{session['username']}'").fetchone().id
    book = db.execute(f"select * from books where isbn='{isbn}';").fetchone()
    
    if book is None:
        return render_template("error.html")

    goodreads_data = requests.get("https://www.goodreads.com/book/review_counts.json",
        params={"key": os.getenv("GOODREADS_KEY"), "isbns": book['isbn']})
    
    gr_review_count = None
    gr_average_rate = None

    # check if book actually exists on goodreads
    if goodreads_data.status_code == 200:
        gr_review_count = goodreads_data.json()['books'][0]['work_ratings_count']
        gr_average_rate = goodreads_data.json()['books'][0]['average_rating'] 
    
    

    reviews = db.execute(f"""
        select * from books join reviews
        on books.isbn = reviews.book
        where books.isbn='{isbn}';
    """).fetchall()

    already_reviewed = False

    for review in reviews:
        if review.reviewer == user_id:
            already_reviewed = True
            break


    if request.method == "GET":
        comments = db.execute(f"""
            SELECT c.*, u.username
            FROM comments c
            JOIN users u ON c.commenter_id = u.id
            JOIN reviews r ON c.review_id = r.id
            WHERE r.book = '{isbn}'
        """).fetchall()

        return render_template(
            "book_detail.html",
            book=book,
            reviews=reviews,
            already_reviewed=already_reviewed,
            gr_review_count=gr_review_count,
            gr_average_rate=gr_average_rate,
            comments=comments
        )

        #return render_template("book_detail.html", book=book, reviews=reviews, already_reviewed=already_reviewed, gr_review_count=gr_review_count, gr_average_rate=gr_average_rate)

    elif request.method == "POST":
        rate = request.form['rate']
        review = request.form['review']
        username = session['username']

        comments = db.execute(f"""
            SELECT c.*, u.username
            FROM comments c
            JOIN users u ON c.commenter_id = u.id
            JOIN reviews r ON c.review_id = r.id
            WHERE r.book = '{isbn}'
        """).fetchall()

        user = db.execute(f"select id from users where username='{username}';").fetchone().id

        db.execute(f"""
            INSERT INTO reviews (book, reviewer, rate, review)
            VALUES ('{isbn}', {user}, {rate}, '{review}')
        """)

        db.commit()

        reviews = db.execute(f"""
            select * from books join reviews
            on books.isbn = reviews.book
            where books.isbn='{isbn}';
        """).fetchall()

        # don't render the form after insertion so user won't leave second review
        already_reviewed = True
        #return render_template("book_detail.html", book=book, reviews=reviews, already_reviewed=already_reviewed, gr_review_count=gr_review_count, gr_average_rate=gr_average_rate)
        return render_template(
            "book_detail.html",
            book=book,
            reviews=reviews,
            already_reviewed=already_reviewed,
            gr_review_count=gr_review_count,
            gr_average_rate=gr_average_rate,
            comments=comments
        )



@app.route("/reviews/<int:review_id>/edit", methods=['GET', 'POST'])
def edit_review(review_id):
    if session.get('username') is None:
        return redirect('/login')

    review = db.execute(f"SELECT * FROM reviews WHERE id = {review_id}").fetchone()

    if review is None:
        return render_template("error.html")

    if review.reviewer != session['username']:
        return "You are not authorized to edit this review."

    if request.method == 'GET':
        return render_template("edit_review.html", review=review)
    elif request.method == 'POST':
        new_rate = request.form['rate']
        new_review = request.form['review']

        db.execute(f"""
            UPDATE reviews
            SET rate = {new_rate}, review = '{new_review}'
            WHERE id = {review_id}
        """)
        db.commit()

        return render_template("book_detail.html", isbn=review.book)

@app.route("/reviews/<int:review_id>/delete", methods=['POST'])
def delete_review(review_id):
    if session.get('username') is None:
        return redirect('/login')

    review = db.execute(f"SELECT * FROM reviews WHERE id = {review_id}").fetchone()

    if review is None:
        return render_template("error.html")

    if review.reviewer != session['username']:
        return "You are not authorized to delete this review."

    db.execute(f"DELETE FROM reviews WHERE id = {review_id}")
    db.commit()

    return render_template("book_detail.html",isbn=review.book)

@app.route("/comments/<int:comment_id>/edit", methods=['GET', 'POST'])
def edit_comment(comment_id):
    if session.get('username') is None:
        return redirect('/login')

    comment = db.execute(f"SELECT * FROM comments WHERE id = {comment_id}").fetchone()

    if comment is None:
        return render_template("error.html")

    if comment.commenter_id != session['username']:
        return "You are not authorized to edit this comment."

    if request.method == 'GET':
        return render_template("edit_comment.html", comment=comment)
    elif request.method == 'POST':
        new_comment = request.form['comment']

        db.execute(f"""
            UPDATE comments
            SET comment = '{new_comment}'
            WHERE id = {comment_id}
        """)
        db.commit()

        return render_template("book_detail.html", isbn=comment.book)

@app.route("/comments/<int:comment_id>/delete", methods=['POST'])
def delete_comment(comment_id):
    if session.get('username') is None:
        return redirect('/login')

    comment = db.execute(f"SELECT * FROM comments WHERE id = {comment_id}").fetchone()

    if comment is None:
        return render_template("error.html")

    if comment.commenter_id != session['username']:
        return "You are not authorized to delete this comment."

    db.execute(f"DELETE FROM comments WHERE id = {comment_id}")
    db.commit()

    return render_template("book_detail.html",isbn=comment.book)


@app.route("/add_book", methods=['GET', 'POST'])
def add_book():
    if request.method == 'GET':
        return render_template('add_book.html')
    elif request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        genre = request.form['genre']
        publication_year = request.form['publication_year']
        rating = request.form['rating']
        isbn_number = request.form['isbn_number']

        # Insert the book into the database
        db.execute(f"""
            INSERT INTO books (title, author, genre, year, rating, isbn)
            VALUES ('{title}', '{author}', '{genre}', '{publication_year}', '{rating}', '{isbn_number}')
        """)
        db.commit()

        return redirect('/')

@app.route("/api/<string:isbn>")
def apiBook(isbn):
    book = db.execute(f"select * from books where isbn='{isbn}';").fetchone()
    
    if book is None:
        return make_response(jsonify({'errorCode' : 404, 'message' : 'Book not found on website'}), 404)

    else:
        goodreads_data = requests.get("https://www.goodreads.com/book/review_counts.json",
        params={"key": os.getenv("GOODREADS_KEY"), "isbns": book['isbn']})
    
        gr_review_count = None
        gr_average_rate = None

        # check if book actually exists on goodreads
        if goodreads_data.status_code == 200:
            gr_review_count = goodreads_data.json()['books'][0]['work_ratings_count']
            gr_average_rate = goodreads_data.json()['books'][0]['average_rating']

        book_properties = {"title": book['title'], "author": book['author'],
            "year": book['year'], "isbn": isbn, "review_count": gr_review_count,
            "average_score": gr_average_rate}

        return make_response(jsonify(book_properties), 200) 

    
