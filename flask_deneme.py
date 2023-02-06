from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

# Kullanıcı Giriş Decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayi görüntülümek icin lütfen giris yapin.","danger")
            return redirect(url_for("login"))
    return decorated_function

# Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min = 4,max = 25)])
    username = StringField("Kullanici Adi",validators=[validators.Length(min = 5,max = 35)])
    email = StringField("Email Adresi",validators=[validators.Email(message="Lütfen Geçerli Bir Email Adresi girin..")])
    password = PasswordField("Parola:", validators=[
        validators.data_required(message = "Lütfen bir parola belirleyin"),
        validators.equal_to(fieldname="confirm", message="Parolaniz uyuşmuyor..")
    ])
    confirm = PasswordField("Parola Dogrula")

class LoginForm(Form):
    username = StringField("Kullanici Adi")
    password = PasswordField("Parola")

app = Flask(__name__)
app.secret_key= "ybblog"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "ybblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    
    sorgu = "Select * from articles"
    
    result = cursor.execute(sorgu)

    if (result > 0):
        articles = cursor.fetchall()
        
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    
    sorgu = "Select * from articles where author = %s"
    
    result = cursor.execute(sorgu,(session["username"],))
    
    if (result > 0):
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")
    
    return render_template("dashboard.html")

#Kayıt Olma
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        
        cursor = mysql.connection.cursor()
        
        sorgu = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"
        
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()
        
        cursor.close()
        
        flash("Basariyla kayit oldunuz...","success")
        
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)
    
#Login Islemi
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data
    
        cursor = mysql.connection.cursor()
        
        sorgu = "Select * From users where username = %s"
        
        result = cursor.execute(sorgu, (username,))
    
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Basariyla giris yaptiniz...","success")
                
                #Session islemi
                session["logged_in"] = True
                session["username"] = username
                
                return redirect(url_for("index"))
            else:
                flash("Sifrenizi yalnis girdiniz...","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanici bulunmuyor...","danger")
            return redirect(url_for("login"))
    
    return render_template("login.html",form = form)

# Logout İşlemi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Detay Sayfası
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where id = %s"
    result = cursor.execute(sorgu,(id,))
    
    if (result>0):
        article = cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")

# Makale Ekleme
@app.route("/addarticle",methods = ["GET","POST"])
def addarticle():
    form = ArticleForm(request.form)
    
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        
        cursor = mysql.connection.cursor()
        
        sorgu = "Insert into articles (title,author,content) VALUES (%s,%s,%s)"
    
        cursor.execute(sorgu,(title,session["username"],content))
        
        mysql.connection.commit()
        cursor.close()
        
        flash("Makale Başariyla Eklendi","success")
        return redirect(url_for("dashboard"))
    
    else:
        return render_template("addarticle.html",form = form)
    
# Makale silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where author = %s and id = %s"
    result = cursor.execute(sorgu,(session["username"],id))
    
    if (result > 0):
        sorgu2 = "Delete from articles where id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
        return redirect(url_for("index"))
    
# Makale Güncelleme
@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def update(id):
    # GET REQUEST
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))
        
        if (result == 0):
            flash("Böyle bir makale yok veya bu isleme yetkiniz yok.","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form=form)
    # POST REQUEST    
    else:
        form = ArticleForm(request.form)
        
        newTitle = form.title.data
        newContent = form.content.data
        
        sorgu2  = "Update articles Set title = %s, content = %s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()
        
        flash("Makale Başariyla güncellendi","success")
        return redirect(url_for("dashboard"))
        
# Makale Form
class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.Length(min = 5, max = 100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.Length(min = 10)])
    

if __name__ == "__main__":
    app.run(debug=True)