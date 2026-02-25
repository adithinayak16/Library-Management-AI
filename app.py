from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = "library_secret_key"

# DATABASE
def init_db():
    conn = sqlite3.connect("library.db")
    c = conn.cursor()

    # Books table
    c.execute("""
    CREATE TABLE IF NOT EXISTS books(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        author TEXT,
        category TEXT,
        year TEXT,
        status TEXT
    )
    """)

    # Users table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# LOGIN REQUIRED DECORATOR 
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            flash("Please login first!", "error")
            return redirect("/")
        return f(*args, **kwargs)
    return decorated

#  LOGIN 
@app.route("/", methods=["GET","POST"])
def login():
    if "user" in session:
        return redirect("/dashboard")

    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("library.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username,password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")
        else:
            flash("Invalid username or password!", "error")
            return redirect("/")

    return render_template("login.html")

# SIGNUP
@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("library.db")
        c = conn.cursor()

        # Check if user exists
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        if c.fetchone():
            flash("User already exists!", "error")
            conn.close()
            return redirect("/signup")

        # Insert new user
        c.execute("INSERT INTO users(username,password) VALUES(?,?)", (username,password))
        conn.commit()
        conn.close()

        flash("Account created successfully!", "success")
        return redirect("/")

    return render_template("signup.html")

# LOGOUT 
@app.route("/logout")
@login_required
def logout():
    session.pop("user", None)
    return redirect("/")

# DASHBOARD 
@app.route("/dashboard")
@login_required
def dashboard():
    conn = sqlite3.connect("library.db")
    c = conn.cursor()

    c.execute("SELECT * FROM books")
    books = c.fetchall()

    c.execute("SELECT COUNT(*) FROM books")
    total_books = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM books WHERE status='Available'")
    available_books = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM books WHERE status='Borrowed'")
    borrowed_books = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT title FROM books ORDER BY id DESC LIMIT 1")
    latest = c.fetchone()
    latest_book = latest[0] if latest else "None"

    conn.close()

    return render_template("dashboard.html",
                           books=books,
                           total_books=total_books,
                           available_books=available_books,
                           borrowed_books=borrowed_books,
                           total_users=total_users,
                           latest_book=latest_book)

# To ADD BOOK 
@app.route("/add",methods=["GET","POST"])
@login_required
def add():
    if request.method=="POST":
        title = request.form["title"]
        author = request.form["author"]
        category = request.form["category"]
        year = request.form["year"]

        conn = sqlite3.connect("library.db")
        c = conn.cursor()
        c.execute("""
        INSERT INTO books(title,author,category,year,status)
        VALUES(?,?,?,?,?)
        """,(title,author,category,year,"Available"))
        conn.commit()
        conn.close()

        flash("Book Added","success")
        return redirect("/dashboard")

    return render_template("add_book.html")

# To DELETE BOOK 
@app.route("/delete/<int:id>")
@login_required
def delete(id):
    conn = sqlite3.connect("library.db")
    c = conn.cursor()
    c.execute("DELETE FROM books WHERE id=?",(id,))
    conn.commit()
    conn.close()
    flash("Deleted","success")
    return redirect("/dashboard")

# ---------------- EDIT BOOK ----------------
@app.route("/edit/<int:id>",methods=["GET","POST"])
@login_required
def edit(id):
    conn = sqlite3.connect("library.db")
    c = conn.cursor()

    if request.method=="POST":
        title = request.form["title"]
        author = request.form["author"]
        category = request.form["category"]
        year = request.form["year"]

        c.execute("""
        UPDATE books
        SET title=?,author=?,category=?,year=?
        WHERE id=?
        """,(title,author,category,year,id))

        conn.commit()
        conn.close()
        return redirect("/dashboard")

    c.execute("SELECT * FROM books WHERE id=?",(id,))
    book = c.fetchone()
    conn.close()
    return render_template("edit.html",book=book)

# ---------------- BORROW BOOK ----------------
@app.route("/borrow/<int:id>")
@login_required
def borrow(id):
    conn = sqlite3.connect("library.db")
    c = conn.cursor()
    c.execute("UPDATE books SET status='Borrowed' WHERE id=?",(id,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ---------------- RETURN BOOK ----------------
@app.route("/return/<int:id>")
@login_required
def return_book(id):
    conn = sqlite3.connect("library.db")
    c = conn.cursor()
    c.execute("UPDATE books SET status='Available' WHERE id=?",(id,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ---------------- SEARCH ----------------
@app.route("/search",methods=["GET","POST"])
@login_required
def search():
    books=[]
    if request.method=="POST":
        query = request.form["query"]
        conn = sqlite3.connect("library.db")
        c = conn.cursor()
        c.execute("SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR category LIKE ?",
                  ('%'+query+'%','%'+query+'%','%'+query+'%'))
        books = c.fetchall()
        conn.close()
    return render_template("search.html",books=books)

# ---------------- AI ASSISTANT ----------------
@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    response = ""
    if request.method == "POST":
        question = request.form["question"].lower()

        if "java" in question:
            response = "📘 Java is an object-oriented programming language widely used in software development."
        elif "python" in question:
            response = "🐍 Python is a popular programming language used in AI and Data Science."
        elif "beginner" in question or "suggest" in question:
            conn = sqlite3.connect("library.db")
            c = conn.cursor()
            c.execute("SELECT title FROM books ORDER BY id ASC LIMIT 5")
            books = c.fetchall()
            conn.close()
            response = "📚 Suggested Books:\n\n"
            for b in books:
                response += "• " + b[0] + "\n"
        else:
            conn = sqlite3.connect("library.db")
            c = conn.cursor()
            c.execute("""
                SELECT title,author,category FROM books
                WHERE title LIKE ? OR author LIKE ? OR category LIKE ?
            """, ('%'+question+'%','%'+question+'%','%'+question+'%'))
            results = c.fetchall()
            conn.close()
            if results:
                response = "📚 I found these books:\n\n"
                for b in results:
                    response += f"• {b[0]} by {b[1]} ({b[2]})\n"
            else:
                response = "❌ No matching books found."

    return render_template("chat.html", response=response)

# ---------------- ABOUT PAGE ----------------
@app.route("/about")
@login_required
def about():
    return render_template("about.html")

if __name__=="__main__":
    app.run(debug=True)