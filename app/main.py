import sqlite3
import random
import os
import string
import bcrypt
from flask import Flask, render_template, request, redirect
from waitress import serve

# ņemts no mācību materiālā
def insert_sql(cmd, vals=None):
    conn = sqlite3.connect('flask.db')   # izveido saiti ar failu, kurā glabājas datu bāze
    c = conn.cursor()   # izsauc kursora funkciju, kas "apstaigā" datu bāzi
    res = c.execute(cmd, vals).fetchall()   # execute metode darbina padoto SQL vaicājumu, fetchall metodes atgrieztās vērtības tiek saglabātas mainīgajā res
    conn.commit()   # commit() metode saglabā datu bāzē veiktās izmaiņas
    conn.close()   # close() metode aizver saikni ar datu bāzes dokumentu
    return res

def select_sql(cmd):
    conn = sqlite3.connect('flask.db')
    c = conn.cursor()
    res = c.execute(cmd).fetchall()
    conn.commit()
    conn.close()
    return res

# -----------

select_sql("CREATE TABLE IF NOT EXISTS Users (\
    id INTEGER PRIMARY KEY AUTOINCREMENT, \
    name TEXT NOT NULL, \
    surname TEXT NOT NULL, \
    token TEXT NOT NULL, \
    password TEXT NOT NULL, \
    email TEXT NOT NULL, \
    phone_number TEXT NOT NULL, \
    is_seller BOOL)")

select_sql("CREATE TABLE IF NOT EXISTS Orders (\
    id INTEGER PRIMARY KEY AUTOINCREMENT, \
    user_id INTEGER, \
    product_id INTEGER)")

select_sql("CREATE TABLE IF NOT EXISTS Products (\
    id INTEGER PRIMARY KEY AUTOINCREMENT, \
    name TEXT NOT NULL, \
    description TEXT NOT NULL, \
    image_url TEXT NOT NULL, \
    cost DECIMAL NOT NULL)")

password_hash = bcrypt.hashpw(bytes("admin", encoding='utf-8'), bcrypt.gensalt())
insert_sql("INSERT OR IGNORE INTO Users(id, name, surname, token, password, email, phone_number, is_seller) VALUES (0, 'admin', 'admin', 'admin', ?, 'admin@admin', '0', 1)", (password_hash, ))


app = Flask(__name__)

def getUser():
    token = request.cookies.get("token")
    if token is not None:
        users = insert_sql("SELECT * FROM Users WHERE token = ?", (token, ))
        if users:
            return users[0]
        else:
            return None

@app.route("/")
def home():
    products = select_sql("SELECT name, cost, image_url, id FROM Products")
    
    return render_template("index.html", products = products, user = getUser())

@app.route("/profile", methods=["GET", "POST"])
def profile():
    user = getUser()
    if not user:
        return redirect("/")
    
    if request.method == "POST":
        resp = redirect("/")
        if not request.form["password"]:
            insert_sql("UPDATE Users SET name = ?, surname = ?, email = ?, phone_number = ? WHERE token = ?", (request.form["name"], request.form["surname"], request.form["email"], request.form["phone_number"], getUser()[3], ))
        else:
            token = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(128))
            password_hash = bcrypt.hashpw(bytes(request.form["password"], encoding='utf-8'), bcrypt.gensalt())
        
            insert_sql("UPDATE Users SET name = ?, surname = ?, email = ?, phone_number = ?, password = ?, token = ? WHERE token = ?", (request.form["name"], request.form["surname"], request.form["email"], request.form["phone_number"], password_hash, token, getUser()[3], ))
            resp.set_cookie("token", token)
        return resp
    else:
        return render_template("profile.html", user = getUser())

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        result = insert_sql("SELECT password, token FROM Users WHERE email = ?", (request.form["email"], ))
        if len(result) > 0:
            password_hash = result[0][0]
            if bcrypt.checkpw(bytes(request.form["password"], encoding='utf-8'), password_hash):
                resp = redirect("/")
                resp.set_cookie("token", str(result[0][1]))
                return resp
        
    return render_template("login.html", user = getUser())

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        token = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(128))
        
        password_hash = bcrypt.hashpw(bytes(request.form["password"], encoding='utf-8'), bcrypt.gensalt())
        
        insert_sql("INSERT INTO Users(name, surname, token, password, email, phone_number, is_seller) VALUES (?, ?, ?, ?, ?, ?, ?)", (request.form["name"], request.form["surname"], token, password_hash, request.form["email"], request.form["phone_number"], False, ))
        resp = redirect("/" + request.form["redirect"])
        resp.set_cookie("token", token)
        return resp
        
    if request.args.get("redirect"):
        return render_template("register.html", user = getUser(), redirect = request.args.get("redirect"))
    else:
        return render_template("register.html", user = getUser(), redirect = "")

@app.route("/admin")
def admin():
    user = getUser()
    if not user or not user[7]:
        return redirect("/")
    else:
        orders = select_sql("SELECT Orders.id, Users.name, Users.surname, Products.name, Users.email, Users.phone_number FROM Orders JOIN Users ON Orders.user_id = Users.id JOIN Products ON Orders.product_id = Products.id")
        products = select_sql("SELECT name, cost, id FROM Products")
        return render_template("admin.html", user = getUser(), orders = orders, products = products)
    
@app.route("/edit_product", methods=["GET", "POST"])
def editProduct():
    user = getUser()
    if not user or not user[7]:
        return redirect("/")
    else:
        if request.method == "POST":
            image_url = "static/no-image.png"
            
            if 'image' in request.files:
                file = request.files['image']
                if file.filename:
                    filename = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(64))
                    file.save(os.path.join("static", "upload", filename))
                    image_url = "/static/upload/" + filename
            if insert_sql("SELECT COUNT(*) FROM Products WHERE id = ?", (request.form["id"], ))[0][0] > 0:
                insert_sql("UPDATE Products SET name = ?, cost = ?, description = ?, image_url = ? WHERE id = ?", (request.form["name"], request.form["cost"], request.form["description"], image_url, request.form["id"], ))
            else:
                insert_sql("INSERT INTO Products (name, cost, description, image_url) VALUES (?, ?, ?, ?)", (request.form["name"], request.form["cost"], request.form["description"], image_url, ))

            return redirect("/admin")
        else:
            product = insert_sql("SELECT * FROM Products WHERE id = ?", (request.args.get("id"), ))
            if len(product) > 0:
                product = product[0]
                
            return render_template("edit_product.html", user = getUser(), product = product)

@app.route("/remove")
def remove():
    user = getUser()
    if not user or not user[7]:
        return redirect("/")
    else:
        insert_sql("DELETE FROM Products WHERE id = ?", (request.args.get("id"), ))
        return redirect("/admin")
    
@app.route("/remove_order")
def removeOrder():
    user = getUser()
    if not user or not user[7]:
        return redirect("/")
    else:
        insert_sql("DELETE FROM Orders WHERE id = ?", (request.args.get("id"), ))
        return redirect("/admin")

@app.route("/product")
def product():
    product = insert_sql("SELECT name, description, cost, image_url, id FROM Products WHERE id = ?", (request.args.get("id"), ))[0]
    return render_template("product.html", user = getUser(), product = product)

@app.route("/order")
def order():
    user = getUser()
    if not user:
        # %3F == ?
        return redirect("/register?redirect=order%3Fid=" + request.args.get("id"))
    else:
        insert_sql("INSERT INTO Orders (user_id, product_id) VALUES (?, ?)", (user[0], request.args.get("id"), ))
        return render_template("order.html", user = getUser())

@app.route("/logout")
def logout():
    resp = redirect("/")
    resp.delete_cookie("token")
    return resp

serve(app, host="0.0.0.0", port=80)