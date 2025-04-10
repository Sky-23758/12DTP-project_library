from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__, template_folder='html')

def get_db_connection():
    conn = sqlite3.connect('database/library.db')
    conn.row_factory = sqlite3.Row 
    return conn



@app.route('/')
def home():
    return render_template('home.html', title='Home')






@app.route('/search', methods=['GET'])
def search():
    return render_template('search.html', title='Search Books')


@app.route('/search/result', methods=['POST'])
def search_result():
    search_query = request.form['query']
    conn = get_db_connection()
    if search_query.isdigit():
        book = conn.execute("SELECT B.BookID,Title,AuthorID,ISBN,Publisher,PublishDate,BorrowDate,ReturnDate FROM Books B LEFT JOIN BorrowRecords R ON B.BookID=R.BookID WHERE B.BookID = ?", (search_query,)).fetchone()
    else:
        book = conn.execute("SELECT B.BookID,Title,AuthorID,ISBN,Publisher,PublishDate,BorrowDate,ReturnDate FROM Books B LEFT JOIN BorrowRecords R ON B.BookID=R.BookID WHERE Title LIKE ?", ('%' + search_query + '%',)).fetchone()
    conn.close()
    return render_template('book_details.html', book=book, query=search_query)




if __name__ == '__main__':
    app.run(debug=True)