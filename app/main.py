from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, Any
import sqlite3, os, hashlib, secrets, hmac, base64, json, time, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "assistant.db"
SECRET_PATH = ROOT / ".session_secret"

def get_secret():
    if SECRET_PATH.exists():
        return SECRET_PATH.read_bytes()
    secret = secrets.token_bytes(32)
    SECRET_PATH.write_bytes(secret)
    try: os.chmod(SECRET_PATH, 0o600)
    except OSError: pass
    return secret
SECRET = get_secret()
COOKIE = "pal_session"
SESSION_SECONDS = 60 * 60 * 24 * 14

def conn():
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS items(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          kind TEXT NOT NULL, title TEXT NOT NULL, details TEXT DEFAULT '',
          category TEXT DEFAULT '', amount REAL DEFAULT 0, due_date TEXT DEFAULT '',
          status TEXT DEFAULT 'open', extra TEXT DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_items_user_kind ON items(user_id,kind);
        """)

def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240000)
    return base64.b64encode(salt + digest).decode()

def password_ok(password, encoded):
    try:
        raw = base64.b64decode(encoded.encode())
        salt, expected = raw[:16], raw[16:]
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def sign(payload):
    raw = base64.urlsafe_b64encode(json.dumps(payload,separators=(",",":")).encode()).decode().rstrip("=")
    sig = hmac.new(SECRET, raw.encode(), hashlib.sha256).hexdigest()
    return raw + "." + sig

def verify(token):
    try:
        raw, sig = token.rsplit(".",1)
        expected = hmac.new(SECRET, raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected): return None
        payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw)%4)))
        if payload.get("exp",0) < time.time(): return None
        return payload
    except Exception: return None

def current_user(request: Request):
    token = request.cookies.get(COOKIE)
    data = verify(token or "")
    if not data: raise HTTPException(status_code=401, detail="Please log in again.")
    with conn() as c:
        user = c.execute("SELECT id,username FROM users WHERE id=?", (data.get("uid"),)).fetchone()
    if not user: raise HTTPException(status_code=401, detail="Account not found.")
    return dict(user)

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
class ItemIn(BaseModel):
    kind: str
    title: str = Field(min_length=1, max_length=200)
    details: str = ""
    category: str = ""
    amount: float = 0
    due_date: str = ""
    status: str = "open"
    extra: dict[str, Any] = {}
class ItemPatch(BaseModel):
    title: Optional[str] = None
    details: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    extra: Optional[dict[str, Any]] = None

app = FastAPI(title="Personal AI Life Assistant", version="1.0.0")
init_db()
app.mount("/static", StaticFiles(directory=str(ROOT/"app"/"static")), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    return (ROOT/"app"/"static"/"index.html").read_text(encoding="utf-8")

@app.get("/api/health")
def health(): return {"status":"ok","app":"Personal AI Life Assistant"}

@app.post("/api/signup")
def signup(body: Credentials, response: Response):
    username = body.username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        raise HTTPException(400, "Username: 3–32 letters, numbers, dot, dash or underscore.")
    with conn() as c:
        try:
            cur = c.execute("INSERT INTO users(username,password_hash) VALUES(?,?)",
                            (username, password_hash(body.password)))
            uid = cur.lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(409, "This username already exists.")
    response.set_cookie(COOKIE, sign({"uid":uid,"exp":time.time()+SESSION_SECONDS}),
                         httponly=True, samesite="lax", max_age=SESSION_SECONDS,
                         secure=False, path="/")
    return {"success":True,"user":{"id":uid,"username":username}}

@app.post("/api/login")
def login(body: Credentials, response: Response):
    with conn() as c:
        user = c.execute("SELECT id,username,password_hash FROM users WHERE username=?",
                         (body.username.strip(),)).fetchone()
    if not user or not password_ok(body.password,user["password_hash"]):
        raise HTTPException(401, "Username or password is incorrect.")
    response.set_cookie(COOKIE, sign({"uid":user["id"],"exp":time.time()+SESSION_SECONDS}),
                         httponly=True, samesite="lax", max_age=SESSION_SECONDS,
                         secure=False, path="/")
    return {"success":True,"user":{"id":user["id"],"username":user["username"]}}

@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"success":True}

@app.get("/api/me")
def me(request: Request): return {"user":current_user(request)}

@app.post("/api/password")
def change_password(body: PasswordChange, request: Request):
    user = current_user(request)
    with conn() as c:
        row = c.execute("SELECT password_hash FROM users WHERE id=?",(user["id"],)).fetchone()
        if not password_ok(body.current_password,row["password_hash"]):
            raise HTTPException(400,"Current password is incorrect.")
        c.execute("UPDATE users SET password_hash=? WHERE id=?",
                  (password_hash(body.new_password),user["id"]))
    return {"success":True}

@app.delete("/api/account")
def delete_account(request: Request, response: Response):
    user = current_user(request)
    with conn() as c: c.execute("DELETE FROM users WHERE id=?",(user["id"],))
    response.delete_cookie(COOKIE,path="/")
    return {"success":True}

@app.get("/api/items")
def list_items(request: Request, kind: Optional[str]=None, q: Optional[str]=None):
    user = current_user(request)
    sql = "SELECT * FROM items WHERE user_id=?"
    args = [user["id"]]
    if kind:
        sql += " AND kind=?"; args.append(kind)
    if q:
        sql += " AND (title LIKE ? OR details LIKE ? OR category LIKE ?)"
        args.extend([f"%{q}%"]*3)
    sql += " ORDER BY CASE WHEN due_date='' THEN 1 ELSE 0 END, due_date ASC, id DESC"
    with conn() as c: rows = c.execute(sql,args).fetchall()
    return {"items":[row_item(r) for r in rows]}

def row_item(r):
    d = dict(r)
    try: d["extra"] = json.loads(d.get("extra") or "{}")
    except Exception: d["extra"] = {}
    return d

@app.post("/api/items")
def create_item(body: ItemIn, request: Request):
    user = current_user(request)
    allowed = {"task","event","reminder","subject","transaction","note"}
    if body.kind not in allowed: raise HTTPException(400,"Unsupported item type.")
    if body.kind == "transaction" and body.amount < 0:
        raise HTTPException(400,"Enter a positive amount; choose Income or Expense in category.")
    with conn() as c:
        cur = c.execute("""INSERT INTO items(user_id,kind,title,details,category,amount,due_date,status,extra)
          VALUES(?,?,?,?,?,?,?,?,?)""",
          (user["id"],body.kind,body.title.strip(),body.details,body.category,
           body.amount,body.due_date,body.status,json.dumps(body.extra)))
        r = c.execute("SELECT * FROM items WHERE id=?",(cur.lastrowid,)).fetchone()
    return {"item":row_item(r)}

@app.patch("/api/items/{item_id}")
def update_item(item_id: int, body: ItemPatch, request: Request):
    user = current_user(request)
    values = body.model_dump(exclude_unset=True)
    if not values: return {"success":True}
    if "extra" in values: values["extra"] = json.dumps(values["extra"] or {})
    values["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    sets = ",".join(f"{k}=?" for k in values)
    args = list(values.values())+[item_id,user["id"]]
    with conn() as c:
        cur = c.execute(f"UPDATE items SET {sets} WHERE id=? AND user_id=?",args)
        if cur.rowcount == 0: raise HTTPException(404,"Item not found.")
        r = c.execute("SELECT * FROM items WHERE id=? AND user_id=?",(item_id,user["id"])).fetchone()
    return {"item":row_item(r)}

@app.delete("/api/items/{item_id}")
def delete_item(item_id: int, request: Request):
    user = current_user(request)
    with conn() as c:
        cur = c.execute("DELETE FROM items WHERE id=? AND user_id=?",(item_id,user["id"]))
    if not cur.rowcount: raise HTTPException(404,"Item not found.")
    return {"success":True}

@app.get("/api/dashboard")
def dashboard(request: Request):
    user = current_user(request)
    with conn() as c:
        rows = c.execute("SELECT * FROM items WHERE user_id=? ORDER BY id DESC",(user["id"],)).fetchall()
    items = [row_item(r) for r in rows]
    tasks = [x for x in items if x["kind"]=="task"]
    open_tasks = [x for x in tasks if x["status"] not in ("done","completed")]
    done_tasks = [x for x in tasks if x["status"] in ("done","completed")]
    reminders = [x for x in items if x["kind"]=="reminder" and x["status"] not in ("done","completed")]
    subjects = [x for x in items if x["kind"]=="subject"]
    tx = [x for x in items if x["kind"]=="transaction"]
    income = sum(x["amount"] for x in tx if x["category"].lower()=="income")
    expenses = sum(x["amount"] for x in tx if x["category"].lower()!="income")
    notes = [x for x in items if x["kind"]=="note"]
    return {"username":user["username"],"tasks_total":len(tasks),"tasks_open":len(open_tasks),
      "tasks_done":len(done_tasks),"reminders":len(reminders),"subjects":len(subjects),
      "study_progress":round(len(done_tasks)/len(tasks)*100) if tasks else 0,
      "income":income,"expenses":expenses,"balance":income-expenses,
      "notes":len(notes),"recent":items[:8]}

@app.get("/api/export")
def export_data(request: Request):
    user=current_user(request)
    with conn() as c:
        rows=c.execute("SELECT kind,title,details,category,amount,due_date,status,extra,created_at FROM items WHERE user_id=? ORDER BY id",(user["id"],)).fetchall()
    return {"username":user["username"],"exported_at":time.strftime("%Y-%m-%d %H:%M:%S"),"items":[row_item(r) for r in rows]}
