# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
from config import DB_CONFIG

app = Flask(__name__)
app.secret_key = 'campus_finder_final_secret'

def get_db_connection():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

# --- 1. 认证模块 ---
@app.route('/')
def index():
    if 'user' in session: return redirect(url_for('user_dashboard'))
    if 'admin' in session: return redirect(url_for('admin_dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    uid, pwd, role = request.form['uid'], request.form['pwd'], request.form['role']
    conn = get_db_connection()
    with conn.cursor() as cursor:
        table = 'User' if role == 'user' else 'Admin'
        id_col = 'user_id' if role == 'user' else 'admin_id'
        cursor.execute(f"SELECT * FROM {table} WHERE {id_col}=%s AND password=%s", (uid, pwd))
        res = cursor.fetchone()
        if res:
            session[role] = res
            return redirect(url_for('user_dashboard' if role == 'user' else 'admin_dashboard'))
    return "登录失败：账号或密码错误"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO User VALUES (%s, %s, %s, %s, %s)",
                         (request.form['uid'], request.form['name'], request.form['phone'], request.form['dept'], request.form['pwd']))
            conn.commit()
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- 2. 用户端 (要求2,3,5) ---
@app.route('/user_dashboard')
def user_dashboard():
    if 'user' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM v_recent_items ORDER BY pub_time DESC")
        items = cursor.fetchall()
        cursor.execute("SELECT c.*, i.title FROM Claim c JOIN Item i ON c.item_id=i.item_id WHERE c.user_id=%s", (session['user']['user_id']))
        my_claims = cursor.fetchall()
        cursor.execute("SELECT * FROM Category")
        categories = cursor.fetchall()
    return render_template('user_index.html', user=session['user'], items=items, my_claims=my_claims, categories=categories)

@app.route('/publish', methods=['POST'])
def publish_item():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("INSERT INTO Item (title, location, cat_id, user_id) VALUES (%s, %s, %s, %s)",
                     (request.form['title'], request.form['location'], request.form['cat_id'], session['user']['user_id']))
        conn.commit()
    return redirect(url_for('user_dashboard'))

@app.route('/claim/<int:item_id>', methods=['POST'])
def claim_item(item_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.callproc('sp_submit_claim', (session['user']['user_id'], item_id, request.form['reason']))
        conn.commit()
    return redirect(url_for('user_dashboard'))

@app.route('/complain/<int:claim_id>', methods=['POST'])
def complain(claim_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("INSERT INTO Complaint (reason, type, claim_id) VALUES (%s, %s, %s)",
                     (request.form['reason'], request.form['type'], claim_id))
        conn.commit()
    return redirect(url_for('user_dashboard'))

# --- 3. 管理端 (要求1,4,6,7) ---
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM User") # 用户CRUD展示
        users = cursor.fetchall()
        cursor.execute("SELECT c.*, i.title, u.user_name FROM Claim c JOIN Item i ON c.item_id=i.item_id JOIN User u ON c.user_id=u.user_id")
        claims = cursor.fetchall()
        cursor.execute("SELECT * FROM Complaint WHERE status=0")
        complaints = cursor.fetchall()
        cursor.execute("SELECT * FROM CreditRecord")
        blacklist = cursor.fetchall()
    return render_template('admin_index.html', users=users, claims=claims, complaints=complaints, blacklist=blacklist)

@app.route('/admin/update_user', methods=['POST'])
def update_user():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE User SET user_name=%s, phone=%s WHERE user_id=%s",
                     (request.form['name'], request.form['phone'], request.form['uid']))
        conn.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/audit/<int:claim_id>/<int:status>')
def audit(claim_id, status):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE Claim SET audit_status=%s WHERE claim_id=%s", (status, claim_id))
        conn.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/handle_comp/<int:comp_id>', methods=['POST'])
def handle_comp(comp_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE Complaint SET result=%s, status=1, admin_id=%s WHERE comp_id=%s",
                     (request.form['result'], session['admin']['admin_id'], comp_id))
        conn.commit()
    return redirect(url_for('admin_dashboard'))


# --- 调试模式：上帝视角 - 实时查看所有表数据 ---
@app.route('/debug')
def debug_view():
    conn = get_db_connection()
    all_tables_data = {}
    try:
        with conn.cursor() as cursor:
            # 1. 获取数据库中所有的表名（包含视图）
            cursor.execute("SHOW FULL TABLES")
            tables = cursor.fetchall()

            for table_info in tables:
                # table_info 的键名可能是 'Tables_in_campus_db'
                table_name = list(table_info.values())[0]

                # 2. 查询该表的所有行
                cursor.execute(f"SELECT * FROM `{table_name}`")
                rows = cursor.fetchall()

                # 3. 获取该表的列名（用于表头展示）
                columns = [desc[0] for desc in cursor.description] if cursor.description else []

                all_tables_data[table_name] = {
                    "columns": columns,
                    "rows": rows
                }

        return render_template('debug.html', db_data=all_tables_data)
    except Exception as e:
        return f"调试页面出错: {str(e)}"
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)