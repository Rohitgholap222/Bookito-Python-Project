import pickle
import re

import MySQLdb.cursors
import numpy as np
from flask import Flask, redirect, render_template, request, session, url_for
from flask_mysqldb import MySQL

books = [
    {"title": "Harry Potter and the Sorcerer's Stone", "author": "J.K. Rowling", "image": "url1"},
    {"title": "Half of a Yellow Sun", "author": "Chimamanda Ngozi Adichie", "image": "url2"},
    {"title": "Hamlet", "author": "William Shakespeare", "image": "url3"},
]

# Load recommendation system models and data
bookito_df = pickle.load(open('PopularBookRecommendation.pkl', 'rb'))
pt = pickle.load(open('bookito.pkl', 'rb'))
book = pickle.load(open('book.pkl', 'rb'))
similarity_scores = pickle.load(open('similarity_scores.pkl', 'rb'))

# book['Amazon-URL'] = book['Book-Title'].apply(lambda x: f"https://www.amazon.com/s?k={'+'.join(x.split())}")
book['Amazon-URL'] = book['Book-Title'].apply(lambda x: f"https://www.amazon.com/s?k={'+'.join(x.split())}&ref=book_click_callback&book_title={'+'.join(x.split())}")

# Initialize Flask app
app = Flask(__name__)

# Secret key for session management
app.secret_key = 'your_secret_key'

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'rohit172'
app.config['MYSQL_DB'] = 'users'

mysql = MySQL(app)

# Login route
@app.route('/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username and password:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(
                'SELECT * FROM USER WHERE username = %s AND password = %s', 
                (username, password)
            )
            account = cursor.fetchone()
            if account:
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                return redirect(url_for('index'))
            else:
                msg = 'Incorrect username/password!'
        else:
            msg = 'Please fill out both fields!'
    return render_template('login.html', msg=msg)

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM USER WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        else:
            cursor.execute(
                'INSERT INTO USER (username, password, email) VALUES (%s, %s, %s)',
                (username, password, email)
            )
            mysql.connection.commit()
            msg = 'You have successfully registered!'
            return redirect(url_for('login'))
    return render_template('register.html', msg=msg)

# Home page route
@app.route('/index')
def index():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    books = bookito_df.to_dict(orient='records')  # Converts DataFrame to list of dictionaries
    return render_template('index.html', books=books)

# Recommendation page route
@app.route('/recommendation')
def recommendation_ui():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    return render_template('recommendation.html')

#Generate book recommendations
@app.route('/recommend_books', methods=['POST'])
def recommendation():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    user_input = request.form.get('user_input')
    if user_input not in pt.index:
        return render_template('recommendation.html', error="Book not found!")

    index = np.where(pt.index == user_input)[0][0]
    similar_items = sorted(
        list(enumerate(similarity_scores[index])),
        key=lambda x: x[1],
        reverse=True
    )[1:9]

    data = []
    for i in similar_items:
        temp_df = book[book['Book-Title'] == pt.index[i[0]]]
        if not temp_df.empty:
        # Include Amazon-URL in the data
            item = list(temp_df.drop_duplicates('Book-Title')[['Book-Title', 'Book-Author', 'Image-URL-M']].iloc[0])
            amazon_url = f"https://www.amazon.com/s?k={'+'.join(item[0].split())}"
            item.append(amazon_url)  # Append the URL to the book data
            data.append(item)

    return render_template('recommendation.html', data=data)

@app.route('/thank_you')
def thank_you():
    book_title = request.args.get('book_title')
    return render_template('thank_you.html', book_title=book_title)


@app.route('/save_book', methods=['POST'])
def save_book():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    # Capture data sent from the recommendation page
    book_title = request.form.get('book_title')
    book_author = request.form.get('book_author')
    book_url = request.form.get('book_url')
    
    # Insert book into the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        'INSERT INTO saved_books (user_id, book_title, book_author, book_url) VALUES (%s, %s, %s, %s)',
        (session['id'], book_title, book_author, book_url)
    )
    mysql.connection.commit()
    cursor.close()

    # Redirect to the saved books page
    return redirect(url_for('my_books'))



@app.route('/my_books')
def my_books():
    if 'loggedin' not in session:  # Ensure the user is logged in
        return redirect(url_for('login'))

    try:
        # Step 1: Establish database cursor
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Step 2: Fetch books for the logged-in user
        cursor.execute('SELECT book_title, book_author, book_url FROM saved_books WHERE user_id = %s', (session['id'],))
        
        # Step 3: Fetch all results and close cursor
        books = cursor.fetchall()
        cursor.close()
        
        # Step 4: Pass the books list to the template
        return render_template('saved_books.html', books=books)

    except Exception as e:
        print("Error fetching books:", e)
        return "An error occurred while fetching your saved books."





# Contact page route
@app.route('/contact')
def contact():
    return render_template('contact.html')

# Main block
if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)
