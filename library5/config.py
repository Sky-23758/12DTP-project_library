from flask import Flask, g
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()  
app.config['SESSION_COOKIE_PARTITIONED'] = False

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('library.db')
        
        db.row_factory = sqlite3.Row 
        c = db.cursor()
        
        # Borrows table
        c.execute('''CREATE TABLE IF NOT EXISTS Borrows (
                  id             INTEGER PRIMARY KEY,
                  book_id        TEXT,
                  book_title     TEXT,
                  category       TEXT,
                  borrower_id    TEXT,
                  borrower_email TEXT,
                  borrow_date    TEXT,
                  return_date    TEXT,
                  Instructions   TEXT,
                  update_time    TEXT

                )''')

        
        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS Users (
                  id             INTEGER PRIMARY KEY,
                  username       TEXT UNIQUE NOT NULL,
                  password       TEXT NOT NULL,
                  role           TEXT NOT NULL CHECK(role IN ('admin', 'guest'))
                )''')
        
        db.commit()
    return db