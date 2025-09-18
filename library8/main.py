import sqlite3

from config import app, get_db
from flask import render_template, request, g, abort, redirect, url_for
from datetime import datetime, timedelta
from flask_login import login_user, logout_user, login_required, current_user
from auth import User, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app.jinja_env.globals['current_year'] = datetime.now().year


# Close the database
@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Return date calculation


def calculate_return_date(borrow_date, borrow_period):
    borrow_dt = datetime.strptime(borrow_date, "%Y-%m-%d")

    if borrow_period == '7days':
        return_date = borrow_dt + timedelta(days=7)
    elif borrow_period == '14days':
        return_date = borrow_dt + timedelta(days=14)
    else:
        raise ValueError("Invalid borrow period")

    return return_date.strftime("%Y-%m-%d")

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


# Login page route
@app.route('/login', methods=['GET', 'POST'])
def login():

    print("Login route hit, method:", request.method)

    if request.method == 'POST':
        username = request.form.get('username', 'Not provided')
        password = request.form.get('password', 'Not provided')

        db = get_db()
        cursor = db.execute(
            "SELECT id, username, real_name, email, password, role FROM Users WHERE username = ?", (username,))
        user_data = cursor.fetchone()

        if user_data and check_password_hash(user_data[4], password):
            user = User(user_data[0], user_data[1],
                        user_data[2], user_data[3], user_data[5])
            login_user(user)
            return redirect(url_for('borrowList'))
        return render_template('login.html', title='Login', error="Invalid credentials")
    return render_template('login.html', title='Login')

# Logout page route


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('borrowList'))


# Borrow form and submission
@app.route('/borrow', methods=['GET', 'POST'])
def borrow():
    if not current_user.is_authenticated:
        # [ADDED] Redirect to buffer page for unauthenticated users
        return render_template('borrow_unlogged.html')

    if request.method == 'POST':
        book_id = request.form['book_id']
        book_title = request.form.get('book_title')
        category = request.form['category']

        borrower_id = current_user.id
        db = get_db()
        cursor = db.execute(
            "SELECT username, email FROM Users WHERE id = ?", (borrower_id,))
        user_data = cursor.fetchone()
        print(f"User data for borrower_id {borrower_id}: {user_data}")
        if not user_data:
            abort(404, description="User data not found")
        username = user_data['username']
        email = user_data['email']

        instructions = request.form.get('instructions', '')
        borrow_date = datetime.now().strftime("%Y-%m-%d")
        borrow_period = request.form.get('return_period')
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 404
        if len(book_id) < 3 or not category or not borrow_period:
            abort(404, description="Please ensure that the Book ID, Category and Borrowing Period are all valid and selected.")

        # Calculate return date
        try:
            return_date = calculate_return_date(borrow_date, borrow_period)
        except (ValueError, TypeError):
            abort(400, description="The borrowing date or period is invalid.")

        db = get_db()
        c = db.cursor()
        try:
            c.execute('''
                      INSERT INTO Borrows (book_id, book_title, category, borrower_id, borrow_date, return_date, instructions, update_time)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                      ''', (book_id, book_title, category, borrower_id, borrow_date, return_date, instructions, update_time))
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            abort(400)

        return render_template('confirmation.html', title="Borrow Confirmed", username=username, email=email, borrow_date=borrow_date, return_date=return_date)
    return render_template('borrow_form.html', title="Borrow")


# Borrow list with search
@app.route('/borrowList')
def borrowList():
    search_query = request.args.get('search', '')
    db = get_db()
    message = ""

    if not current_user.is_authenticated:
        cursor = db.execute("""
            SELECT b.*, u.username, u.email 
            FROM Borrows b 
            LEFT JOIN Users u ON b.borrower_id = u.id 
            WHERE b.borrower_id IS NULL OR b.borrower_id = 0
        """)
        borrows = cursor.fetchall()
        return render_template('borrow_list_guest.html', borrows=borrows, search_query=search_query, message=message)

    role = getattr(current_user, 'role', 0)
    if search_query:
        if role == 1:
            cursor = db.execute("""
                SELECT b.*, u.username, u.email 
                FROM Borrows b 
                LEFT JOIN Users u ON b.borrower_id = u.id 
                WHERE b.book_title LIKE ? OR u.username LIKE ? ORDER BY b.id ASC
            """, ('%' + search_query + '%', '%' + search_query + '%'))
            borrows = cursor.fetchall()
        else:
            cursor = db.execute("""
                SELECT b.*, u.username, u.email 
                FROM Borrows b 
                LEFT JOIN Users u ON b.borrower_id = u.id 
                WHERE b.borrower_id = ? AND (b.book_title LIKE ? OR u.username LIKE ?) ORDER BY b.id ASC
            """, (current_user.id, '%' + search_query + '%', '%' + search_query + '%'))
            borrows = cursor.fetchall()
        if not borrows:
            message = "The order you are looking for does not exist"
    else:
        if role == 1:
            cursor = db.execute("""
                SELECT b.*, u.username, u.email 
                FROM Borrows b 
                LEFT JOIN Users u ON b.borrower_id = u.id 
                ORDER BY b.id ASC
            """)
            borrows = cursor.fetchall()
        else:
            cursor = db.execute("""
                SELECT b.*, u.username, u.email 
                FROM Borrows b 
                LEFT JOIN Users u ON b.borrower_id = u.id 
                WHERE b.borrower_id = ? ORDER BY b.id ASC
            """, (current_user.id,))
            borrows = cursor.fetchall()

    return render_template('borrow_list_admin.html' if role == 1 else 'borrow_list_guest.html', borrows=borrows, search_query=search_query, message=message)


# Administrator privileges
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# Edit borrow list
@login_required
@app.route('/edit_borrow/<int:id>')
def edit_borrow(id):
    db = get_db()
    cursor = db.execute("""
        SELECT b.*, u.username, u.email 
        FROM Borrows b 
        LEFT JOIN Users u ON b.borrower_id = u.id 
        WHERE b.id = ?
    """, (id,))
    borrow = cursor.fetchone()

    if borrow is None:
        abort(404)
    from datetime import datetime
    borrow_date = datetime.strptime(
        borrow['borrow_date'], '%Y-%m-%d') if borrow['borrow_date'] else None
    return_date = datetime.strptime(
        borrow['return_date'], '%Y-%m-%d') if borrow['return_date'] else None
    return render_template('borrow_edit.html', borrow=borrow, borrow_date=borrow_date, return_date=return_date)


# Update borrow list
@login_required
@app.route('/update_borrow/<int:id>', methods=['POST'])
def update_borrow(id):
    db = get_db()

    cursor = db.execute("SELECT * FROM Borrows WHERE id = ?", (id,))

    original_borrow = cursor.fetchone()
    if original_borrow is None:
        abort(404)

    book_id = request.form['book_id']
    book_title = request.form['book_title']
    category = request.form['category']

    borrower_id = original_borrow[1]

    borrow_date = request.form.get(
        'borrow_date', datetime.now().strftime('%Y-%m-%d'))
    return_period = request.form['return_period']
    instructions = request.form['instructions']

    try:
        return_date = calculate_return_date(borrow_date, return_period)
    except (ValueError, TypeError):
        abort(400, description="The borrowing date or period is invalid.")

    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db = get_db()
    db.execute("""
        UPDATE Borrows 
        SET 
            book_id = ?, 
            book_title = ?, 
            category = ?, 
            
            
            borrow_date = ?, 
            return_date = ?, 
            instructions = ?, 
            update_time = ?
        WHERE id = ?
    """, (book_id, book_title, category, borrow_date, return_date, instructions, update_time, id))

    cursor = db.execute("""
        SELECT b.*, u.username, u.email 
        FROM Borrows b 
        LEFT JOIN Users u ON b.borrower_id = u.id 
        WHERE b.id = ?
    """, (id,))
    borrow = cursor.fetchone()
    if borrow is None:
        abort(404)

    cursor = db.execute("""
        SELECT b.*, u.username, u.email 
        FROM Borrows b 
        LEFT JOIN Users u ON b.borrower_id = u.id 
        ORDER BY b.id ASC
    """)

    borrows = cursor.fetchall()
    db.commit()
    return render_template('borrow_list_admin.html', borrows=borrows, search_query='', message='')


# Delete borrow list
@login_required
@app.route('/delete_borrow/<int:id>', methods=['POST'])
def delete_borrow(id):
    db = get_db()
    db.execute("DELETE FROM Borrows WHERE id = ?", (id,))
    cursor = db.execute("SELECT * FROM Borrows ORDER BY id ASC")
    borrows = cursor.fetchall()
    db.commit()

    return render_template('borrow_list_admin.html', borrows=borrows, search_query='', message='')


# Custom 404 error handler
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    with app.app_context():
        db = get_db()
        c = db.cursor()
        c.execute("SELECT COUNT(*) FROM Users")
        if c.fetchone()[0] == 0:
            c.execute("DELETE FROM Users")
            c.execute("INSERT INTO Users (username, password, real_name, email, role) VALUES (?, ?, ?, ?, ?)",
                      ("admin", generate_password_hash("admin123"), "Admin User", "admin@example.com", 1))
            c.execute("INSERT INTO Users (username, password, real_name, email, role) VALUES (?, ?, ?, ?, ?)",
                      ("user1", generate_password_hash("user123"), "User One", "user1@example.com", 0))
    app.run(debug=True)
