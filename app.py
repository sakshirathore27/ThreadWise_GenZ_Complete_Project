from flask import Flask,render_template,request,redirect,url_for,session,flash,jsonify
from werkzeug.security import generate_password_hash,check_password_hash
import sqlite3,os,secrets
from datetime import datetime
from functools import wraps
app=Flask(__name__); app.secret_key=os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE="Lax")
DB=os.path.join(os.path.dirname(__file__),"threadwise.db")
CATS=["Tops","Bottoms","Dresses","Outerwear","Shoes","Bags","Accessories","Ethnic Wear","Activewear"]
COLORS=["Black","White","Blue","Brown","Beige","Pink","Red","Green","Yellow","Grey","Purple","Orange","Multi"]
OCC=["Everyday","College","Work","Party","Wedding","Travel","Workout"]; SEAS=["All-season","Summer","Winter","Monsoon"]
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute("PRAGMA foreign_keys=ON");return c
def init():
 with db() as c:c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password_hash TEXT,created_at TEXT);
 CREATE TABLE IF NOT EXISTS garments(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,name TEXT,category TEXT,color TEXT,season TEXT,occasion TEXT,size TEXT,price REAL,purchase_date TEXT,notes TEXT,created_at TEXT);
 CREATE TABLE IF NOT EXISTS wishlist(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,name TEXT,category TEXT,color TEXT,occasion TEXT,budget REAL,priority TEXT,created_at TEXT);
 CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,user_id INTEGER,event_type TEXT,detail TEXT,severity TEXT,created_at TEXT);
 CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY,user_id INTEGER,item_name TEXT,category TEXT,verdict TEXT,reason TEXT,created_at TEXT);""")
def audit(uid,typ,detail,sev="info"):
 with db() as c:c.execute("INSERT INTO events(user_id,event_type,detail,severity,created_at) VALUES(?,?,?,?,?)",(uid,typ,detail,sev,datetime.now().isoformat(timespec="minutes")))
def auth(f):
 @wraps(f)
 def w(*a,**k):
  if not session.get("uid"):flash("Please log in first.","warning");return redirect(url_for("login"))
  return f(*a,**k)
 return w
def items():
 with db() as c:return c.execute("SELECT * FROM garments WHERE user_id=? ORDER BY id DESC",(session["uid"],)).fetchall()
def recs(xs):
 owned={x["category"] for x in xs}
 data=[("Everyday white tee","Tops","White","Everyday","A versatile base for jeans, cargos and layered fits.","#c9f6e5","👕"),("Go-with-everything bottoms","Bottoms","Black","College","A neutral bottom can pair with lots of tops.","#f8d3e8","👖"),("Sneakers on repeat","Shoes","White","Everyday","Think comfort and cost-per-wear before buying.","#ddd6ff","👟"),("A layer for the plot","Outerwear","Beige","Travel","A light layer can make simple outfits feel styled.","#ffe8a8","🧥"),("The finishing touch","Accessories","Multi","Party","Try restyling what you own before buying accessories.","#d9f0bc","👜")]
 out=[x for x in data if x[1] not in owned]
 return out[:4] or [("Restyle your favourites","Accessories","Multi","Everyday","Your closet covers the starter categories. Try a fresh combination first.","#d9f0bc","💚")]
@app.context_processor
def ctx():
 u=None
 if session.get("uid"):
  with db() as c:u=c.execute("SELECT id,name,email FROM users WHERE id=?",(session["uid"],)).fetchone()
 return dict(user=u,categories=CATS,colors=COLORS,occasions=OCC,seasons=SEAS)
@app.route("/")
def home():return redirect(url_for("dashboard")) if session.get("uid") else render_template("home.html")
@app.route("/register",methods=["GET","POST"])
def register():
 if request.method=="POST":
  name=request.form.get("name","").strip();email=request.form.get("email","").strip().lower();pw=request.form.get("password","")
  if not name or not email or len(pw)<8:flash("Enter your name, email and password (8+ characters).","danger")
  else:
   try:
    with db() as c:uid=c.execute("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",(name,email,generate_password_hash(pw),datetime.now().isoformat(timespec="minutes"))).lastrowid
    session.clear();session["uid"]=uid;audit(uid,"ACCOUNT CREATED","Password stored as a one-way hash.");return redirect(url_for("dashboard"))
   except sqlite3.IntegrityError:flash("Email already registered. Please log in.","warning")
 return render_template("auth.html",mode="register")
@app.route("/login",methods=["GET","POST"])
def login():
 if request.method=="POST":
  with db() as c:u=c.execute("SELECT * FROM users WHERE email=?",(request.form.get("email","").strip().lower(),)).fetchone()
  if u and check_password_hash(u["password_hash"],request.form.get("password","")):
   session.clear();session["uid"]=u["id"];audit(u["id"],"LOGIN SUCCESS","Successful sign-in.");return redirect(url_for("dashboard"))
  audit(None,"LOGIN FAILURE","Invalid sign-in attempt.","warning");flash("Email or password is incorrect.","danger")
 return render_template("auth.html",mode="login")
@app.route("/logout")
def logout():
 uid=session.get("uid")
 if uid:audit(uid,"LOGOUT","User signed out.")
 session.clear();return redirect(url_for("home"))
@app.route("/dashboard")
@auth
def dashboard():
 xs=items()
 with db() as c:w=c.execute("SELECT COUNT(*) FROM wishlist WHERE user_id=?",(session["uid"],)).fetchone()[0]
 counts={cat:sum(1 for x in xs if x["category"]==cat) for cat in CATS}
 return render_template("dashboard.html",items=xs,wishes=w,counts=counts)
@app.route("/wardrobe")
@auth
def wardrobe():
 xs=items();q=request.args.get("q","").lower();cat=request.args.get("category","")
 if q:xs=[x for x in xs if q in x["name"].lower() or q in x["color"].lower()]
 if cat:xs=[x for x in xs if x["category"]==cat]
 return render_template("wardrobe.html",items=xs,q=q,selected=cat)
@app.route("/add",methods=["GET","POST"])
@auth
def add():
 if request.method=="POST":
  name=request.form.get("name","").strip();cat=request.form.get("category","");color=request.form.get("color","")
  if not name or cat not in CATS or color not in COLORS:flash("Enter item name and choose a valid category and color.","danger")
  else:
   try:price=max(0,float(request.form.get("price") or 0))
   except ValueError:price=0
   with db() as c:c.execute("INSERT INTO garments(user_id,name,category,color,season,occasion,size,price,purchase_date,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(session["uid"],name,cat,color,request.form.get("season"),request.form.get("occasion"),request.form.get("size",""),price,request.form.get("purchase_date",""),request.form.get("notes",""),datetime.now().isoformat(timespec="minutes")))
   audit(session["uid"],"WARDROBE ITEM ADDED","Added a personal wardrobe item.");flash("Added to your closet ✨","success");return redirect(url_for("wardrobe"))
 return render_template("add.html")
@app.route("/delete/<int:i>",methods=["POST"])
@auth
def delete(i):
 with db() as c:cur=c.execute("DELETE FROM garments WHERE id=? AND user_id=?",(i,session["uid"]))
 if cur.rowcount:audit(session["uid"],"ITEM DELETED","Removed a wardrobe item.","warning")
 return redirect(url_for("wardrobe"))
@app.route("/smart-picks")
@auth
def picks():
 with db() as c:w=c.execute("SELECT * FROM wishlist WHERE user_id=? ORDER BY id DESC",(session["uid"],)).fetchall()
 return render_template("picks.html",suggestions=recs(items()),wishes=w)
@app.route("/wish",methods=["POST"])
@auth
def wish():
 n=request.form.get("name","").strip();cat=request.form.get("category","")
 if n and cat in CATS:
  try:b=max(0,float(request.form.get("budget") or 0))
  except ValueError:b=0
  with db() as c:c.execute("INSERT INTO wishlist(user_id,name,category,color,occasion,budget,priority,created_at) VALUES(?,?,?,?,?,?,?,?)",(session["uid"],n,cat,request.form.get("color",""),request.form.get("occasion","Everyday"),b,request.form.get("priority","Normal"),datetime.now().isoformat(timespec="minutes")))
  audit(session["uid"],"WISHLIST ITEM ADDED","Saved a planned purchase.");flash("Saved for later 🛍️","success")
 return redirect(url_for("picks"))
@app.route("/wish-delete/<int:i>",methods=["POST"])
@auth
def wish_delete(i):
 with db() as c:c.execute("DELETE FROM wishlist WHERE id=? AND user_id=?",(i,session["uid"]))
 return redirect(url_for("picks"))
@app.route("/shopping-check",methods=["GET","POST"])
@auth
def check():
 result=None
 if request.method=="POST":
  n=request.form.get("name","").strip();cat=request.form.get("category","");color=request.form.get("color","")
  if n and cat in CATS:
   match=[x for x in items() if x["category"]==cat and (not color or x["color"].lower()==color.lower())]
   verdict="YOU MIGHT ALREADY OWN THIS" if match else "POSSIBLE WARDROBE GAP"
   reason=(f"Found {len(match)} saved item(s) in {cat}"+(f" matching {color}" if color else "")+". Review before buying.") if match else f"No saved {cat}"+(f" in {color}" if color else "")+" found. This is a suggestion, not a must-buy."
   with db() as c:c.execute("INSERT INTO checks(user_id,item_name,category,verdict,reason,created_at) VALUES(?,?,?,?,?,?)",(session["uid"],n,cat,verdict,reason,datetime.now().isoformat(timespec="minutes")))
   audit(session["uid"],"SHOPPING CHECK","Checked a planned purchase.");result={"verdict":verdict,"reason":reason,"matches":match}
 with db() as c:history=c.execute("SELECT * FROM checks WHERE user_id=? ORDER BY id DESC LIMIT 10",(session["uid"],)).fetchall()
 return render_template("check.html",result=result,history=history)
@app.route("/security")
@auth
def security():
 with db() as c:events=c.execute("SELECT * FROM events WHERE user_id=? ORDER BY id DESC LIMIT 30",(session["uid"],)).fetchall()
 return render_template("security.html",events=events)
@app.route("/api/wardrobe-summary")
@auth
def api():
 xs=items();counts={}
 for x in xs:counts[x["category"]]=counts.get(x["category"],0)+1
 return jsonify(total_items=len(xs),by_category=counts,generated_at=datetime.now().isoformat(timespec="seconds"))
init()
if __name__=="__main__":app.run(host="127.0.0.1",port=5000,debug=False)
