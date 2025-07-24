from flask import Flask, render_template, request, g, abort
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)

# database
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('library.db')
        db.row_factory = sqlite3.Row
        c = db.cursor()
        
        # Books table
        c.execute('''CREATE TABLE IF NOT EXISTS Books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT UNIQUE,
            book_title TEXT,
            category TEXT
        )''')
        # Borrowers table
        c.execute('''CREATE TABLE IF NOT EXISTS Borrowers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            borrower_id TEXT UNIQUE,
            borrower_email TEXT
        )''')
        # Borrows table
        c.execute('''CREATE TABLE IF NOT EXISTS Borrows (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT,
            borrower_id TEXT,
            borrow_date TEXT,
            return_date TEXT,
            instructions TEXT,
            update_time TEXT,
            FOREIGN KEY (book_id) REFERENCES Books(book_id),
            FOREIGN KEY (borrower_id) REFERENCES Borrowers(borrower_id)
        )''')
        
        db.commit()
    return db

# Close the database connection after each request
@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Home page route
@app.route('/')
def home():
    return render_template('home.html', title='HOME')

# About page route
@app.route('/about')
def about():
    return render_template('about.html', title='ABOUT')


# borrow and submission
@app.route('/borrow', methods=['GET', 'POST'])
def borrow():
    if request.method == 'POST':
        book_id = request.form['book_id']
        book_title = request.form['book_title']
        category = request.form['category']
        borrower_id = request.form['borrower_id']
        borrower_email = request.form['borrower_email']
        instructions = request.form.get('instructions', '')

        if len(book_id) < 3 or len(borrower_id) < 3 or not borrower_email:
            abort(404)

        db = get_db()
        c = db.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO Books (book_id, book_title, category) VALUES (?, ?, ?)',
                      (book_id, book_title, category))
            c.execute('INSERT OR IGNORE INTO Borrowers (borrower_id, borrower_email) VALUES (?, ?)',
                      (borrower_id, borrower_email))
            borrow_date = datetime.now().strftime("%Y-%m-%d")
            return_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
            update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute('INSERT INTO Borrows (book_id, borrower_id, borrow_date, return_date, instructions, update_time) VALUES (?, ?, ?, ?, ?, ?)',
                      (book_id, borrower_id, borrow_date, return_date, instructions, update_time))
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            abort(400)

        return render_template('confirmation.html', title='Borrow Confirmed', borrower_id=borrower_id)

    return render_template('borrow_form.html', title='Borrow')


# borrow list and search
@app.route('/borrowList')
def borrowList():
    search_query = request.args.get('search', '')
    db = get_db()
    if search_query:
        cursor = db.execute("""
            SELECT b.*, 
                   (SELECT book_title FROM Books WHERE book_id = b.book_id) as book_title,
                   (SELECT category FROM Books WHERE book_id = b.book_id) as category,
                   (SELECT borrower_email FROM Borrowers WHERE borrower_id = b.borrower_id) as borrower_email
            FROM Borrows b
            WHERE b.book_id LIKE ? OR b.borrower_id LIKE ?
            ORDER BY b.id ASC
        """, ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        cursor = db.execute("""
            SELECT b.*, 
                   (SELECT book_title FROM Books WHERE book_id = b.book_id) as book_title,
                   (SELECT category FROM Books WHERE book_id = b.book_id) as category,
                   (SELECT borrower_email FROM Borrowers WHERE borrower_id = b.borrower_id) as borrower_email
            FROM Borrows b
            ORDER BY b.id ASC
        """)
    borrows = cursor.fetchall()
    db.close()
    message = "No matching borrows found" if search_query and not borrows else ""
    return render_template('borrow_list.html', borrows=borrows, search_query=search_query, message=message)


# edit
@app.route('/edit_borrow/<int:id>')
def edit_borrow(id):
    db = get_db()
    cursor = db.execute("""
        SELECT b.*, 
               (SELECT book_title FROM Books WHERE book_id = b.book_id) as book_title,
               (SELECT category FROM Books WHERE book_id = b.book_id) as category,
               (SELECT borrower_email FROM Borrowers WHERE borrower_id = b.borrower_id) as borrower_email
        FROM Borrows b
        WHERE b.id = ?
    """, (id,))
    borrow = cursor.fetchone()
    db.close()
    if borrow is None:
        abort(404)
    return render_template('borrow_edit.html', borrow=borrow)

# update
@app.route('/update_borrow/<int:id>', methods=['POST'])
def update_borrow(id):
    db = get_db()
    c = db.cursor()
    book_id = request.form['book_id']
    book_title = request.form['book_title']
    category = request.form['category']
    borrower_id = request.form['borrower_id']
    borrower_email = request.form['borrower_email']
    borrow_date = request.form['borrow_date']
    return_date = request.form['return_date']
    instructions = request.form['instructions']
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if len(book_id) < 3 or len(borrower_id) < 3 or not borrower_email:
        abort(404)

    try:
        c.execute('UPDATE Books SET book_title = ?, category = ? WHERE book_id = ?', (book_title, category, book_id))
        c.execute('UPDATE Borrowers SET borrower_email = ? WHERE borrower_id = ?', (borrower_email, borrower_id))
        c.execute("""
            UPDATE Borrows 
            SET book_id = ?, borrower_id = ?, borrow_date = ?, return_date = ?, instructions = ?, update_time = ?
            WHERE id = ?
        """, (book_id, borrower_id, borrow_date, return_date, instructions, update_time, id))
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        abort(400)

    cursor = db.execute("""
        SELECT b.*, 
               (SELECT book_title FROM Books WHERE book_id = b.book_id) as book_title,
               (SELECT category FROM Books WHERE book_id = b.book_id) as category,
               (SELECT borrower_email FROM Borrowers WHERE borrower_id = b.borrower_id) as borrower_email
        FROM Borrows b
        ORDER BY b.id ASC
    """)
    borrows = cursor.fetchall()
    db.close()
    return render_template('borrow_list.html', borrows=borrows)

# delete
@app.route('/delete_borrow/<int:id>', methods=['POST'])
def delete_borrow(id):
    db = get_db()
    db.execute("DELETE FROM Borrows WHERE id = ?", (id,))
    cursor = db.execute("""
        SELECT b.*, 
               (SELECT book_title FROM Books WHERE book_id = b.book_id) as book_title,
               (SELECT category FROM Books WHERE book_id = b.book_id) as category,
               (SELECT borrower_email FROM Borrowers WHERE borrower_id = b.borrower_id) as borrower_email
        FROM Borrows b
        ORDER BY b.id ASC
    """)
    borrows = cursor.fetchall()
    db.commit()
    db.close()
    return render_template('borrow_list.html', borrows=borrows)

# 404
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    with app.app_context():
        # 初始化数据库，无需迁移，直接创建新表
        get_db()
    app.run(debug=True)