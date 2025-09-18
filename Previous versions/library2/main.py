from flask import Flask, render_template, request, g, abort
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('library.db')
        c = db.cursor()
        db.row_factory = sqlite3.Row 
        c = db.cursor()
        
        # Orders table
        c.execute('''CREATE TABLE IF NOT EXISTS Borrows (
                  id             INTEGER PRIMARY KEY,
                  book_id        TEXT,
                  book_title     TEXT,
                  category       TEXT,
                  borrower_id    TEXT,
                  borrower_email TEXT,
                  borrow_date  TEXT,
                  return_date    TEXT,
                  Instructions   TEXT,
                  update_time    TEXT

                )''')
        
        db.commit()
    return db

# Close the database
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


# Test page route
@app.route('/test')
def test():
    return render_template('test.html', title='TEST')

# Borrow form and submission 
@app.route('/borrow', methods=['GET', 'POST'])
def borrow():
    if request.method == 'POST':
        book_id = request.form['book_id']
        book_title = request.form.get('book_title')  
        category = request.form['category']
        borrower_id = request.form['borrower_id'] 
        borrower_email = request.form['borrower_email']
        instructions = request.form.get('instructions', '')
        borrow_date = datetime.now().strftime("%Y-%m-%d")
        return_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        #404
        if len(book_id) < 3 or len(borrower_id) < 3 or not borrower_email:
            abort(404)

        db = get_db()
        c = db.cursor()
        c.execute('''
            INSERT INTO Borrows (book_id, book_title, category, borrower_id, borrower_email, borrow_date, return_date, instructions, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (book_id, book_title, category, borrower_id, borrower_email, borrow_date, return_date, instructions, update_time))
        db.commit()

        return render_template('confirmation.html', title="Borrow Confirmed", borrower_id=borrower_id)
    
    return render_template('borrow_form.html', title="Borrow")

# Borrow list with search
@app.route('/borrowList')
def borrowList():
    search_query = request.args.get('search', '')
    db = get_db()
    message = ""

    if search_query:
        cursor = db.execute("SELECT * FROM Borrows WHERE book_id LIKE ? OR borrower_id LIKE ? ORDER BY id ASC", ('%' + search_query + '%','%' + search_query + '%'))
        borrows = cursor.fetchall()
        if not borrows:
            message = "The order you are looking for does not exist"
    else:
        cursor = db.execute("SELECT * FROM Borrows ORDER BY id ASC")
        borrows = cursor.fetchall()

    db.close()

    return render_template('borrow_list.html', borrows=borrows, search_query=search_query, message=message)


# Edit borrow list
@app.route('/edit_borrow/<int:id>')
def edit_borrow(id):
    db = get_db()
    cursor = db.execute("SELECT * FROM Borrows WHERE id = ?", (id,))
    borrow = cursor.fetchone()
    db.close()
    if borrow is None:
        abort(404)
    return render_template('borrow_edit.html', borrow=borrow)


# Update borrow list
@app.route('/update_borrow/<int:id>', methods=['POST'])
def update_borrow(id):
    book_id = request.form['book_id']
    book_title = request.form['book_title']
    category = request.form['category']
    borrower_id = request.form['borrower_id']
    
    borrower_email = request.form['borrower_email']
    borrow_date = request.form['borrow_date']
    return_date = request.form['return_date']
    instructions = request.form['instructions']
    
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db = get_db()
    db.execute("""
        UPDATE Borrows 
        SET 
            book_id = ?, 
            book_title = ?, 
            category = ?, 
            borrower_id = ?, 
            
            borrower_email = ?, 
            borrow_date = ?, 
            return_date = ?, 
            instructions = ?, 
            update_time = ?
        WHERE id = ?
    """, (book_id, book_title, category, borrower_id, borrower_email, borrow_date, return_date, instructions, update_time, id))
    cursor = db.execute("SELECT * FROM Borrows ORDER BY id ASC")
    borrows = cursor.fetchall()
    db.commit()
    db.close()
    return render_template('borrow_list.html', borrows=borrows)


# Delete borrow list 
@app.route('/delete_borrow/<int:id>', methods=['POST'])
def delete_borrow(id):
    db = get_db()
    db.execute("DELETE FROM Borrows WHERE id = ?", (id,))
    cursor = db.execute("SELECT * FROM Borrows ORDER BY id ASC")
    borrows = cursor.fetchall()
    db.commit()
    db.close()
    return render_template('borrow_list.html', borrows=borrows)


if __name__ == '__main__':
    app.run(debug=True)