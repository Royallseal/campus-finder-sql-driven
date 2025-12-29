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
    
    flash("登录失败：账号或密码错误", "danger")
    return redirect(url_for('index'))

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
    search_query = request.args.get('q', '')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 检查当前用户是否被冻结
        cursor.execute("SELECT * FROM CreditRecord WHERE user_id=%s AND freeze_until > NOW()", (session['user']['user_id'],))
        is_frozen = cursor.fetchone() is not None

        # 分类获取：0-招领(别人捡到的), 1-寻物(别人丢的)
        # 使用索引 idx_item_title 进行搜索优化
        if search_query:
            cursor.execute("SELECT * FROM v_recent_items WHERE type=0 AND title LIKE %s ORDER BY pub_time DESC", (f'%{search_query}%',))
            found_items = cursor.fetchall()
            cursor.execute("SELECT * FROM v_recent_items WHERE type=1 AND title LIKE %s ORDER BY pub_time DESC", (f'%{search_query}%',))
            lost_items = cursor.fetchall()
        else:
            cursor.execute("SELECT * FROM v_recent_items WHERE type=0 ORDER BY pub_time DESC")
            found_items = cursor.fetchall()
            cursor.execute("SELECT * FROM v_recent_items WHERE type=1 ORDER BY pub_time DESC")
            lost_items = cursor.fetchall()
        
        # 我发起的认领（领别人的）
        cursor.execute("SELECT c.*, i.title FROM Claim c JOIN Item i ON c.item_id=i.item_id WHERE c.user_id=%s", (session['user']['user_id']))
        my_claims = cursor.fetchall()
        # 别人认领我的（我发布的物品被别人认领）
        cursor.execute("""
            SELECT c.*, i.title, u.user_name as claimer_name 
            FROM Claim c 
            JOIN Item i ON c.item_id=i.item_id 
            JOIN User u ON c.user_id=u.user_id 
            WHERE i.user_id=%s AND c.user_id != %s
        """, (session['user']['user_id'], session['user']['user_id']))
        others_claims = cursor.fetchall()
        
        cursor.execute("SELECT * FROM Category")
        categories = cursor.fetchall()

        # 获取未读消息 (要求：站内通知)
        cursor.execute("SELECT * FROM Message WHERE user_id=%s ORDER BY send_time DESC", (session['user']['user_id'],))
        messages = cursor.fetchall()
        # 标记为已读
        cursor.execute("UPDATE Message SET is_read=TRUE WHERE user_id=%s", (session['user']['user_id'],))
        conn.commit()

    return render_template('user_index.html', user=session['user'], 
                           found_items=found_items, lost_items=lost_items, 
                           my_claims=my_claims, others_claims=others_claims, 
                           categories=categories, is_frozen=is_frozen,
                           messages=messages)

@app.route('/publish', methods=['POST'])
def publish_item():
    if 'user' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 再次检查冻结状态，防止绕过前端
        cursor.execute("SELECT * FROM CreditRecord WHERE user_id=%s AND freeze_until > NOW()", (session['user']['user_id'],))
        if cursor.fetchone():
            return "您的账号已被冻结，无法发布信息"
            
        cursor.execute("INSERT INTO Item (title, description, location, cat_id, user_id, type) VALUES (%s, %s, %s, %s, %s, %s)",
                     (request.form['title'], request.form['description'], request.form['location'], request.form['cat_id'], session['user']['user_id'], request.form['type']))
        conn.commit()
    return redirect(url_for('user_dashboard'))

@app.route('/claim/<int:item_id>', methods=['POST'])
def claim_item(item_id):
    if 'user' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 获取物品发布者ID用于发消息
        cursor.execute("SELECT user_id, title FROM Item WHERE item_id=%s", (item_id,))
        item_info = cursor.fetchone()
        
        cursor.callproc('sp_submit_claim', (session['user']['user_id'], item_id, request.form['reason']))
        
        if item_info:
            msg = f"有人对您的物品 [{item_info['title']}] 发起了认领/线索提供，请及时审核。"
            cursor.execute("INSERT INTO Message (user_id, content) VALUES (%s, %s)", (item_info['user_id'], msg))
            
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
        # 自动清理过期黑名单 (调用存储过程)
        cursor.callproc('sp_clear_expired_blacklist')
        
        # 获取用户列表并标注是否冻结，同时关联视图 v_user_violations 获取违规统计
        cursor.execute("""
            SELECT u.*, v.rejected_claims, v.complaint_count,
            (SELECT COUNT(*) FROM CreditRecord WHERE user_id=u.user_id AND freeze_until > NOW()) as is_frozen
            FROM User u
            JOIN v_user_violations v ON u.user_id = v.user_id
        """)
        users = cursor.fetchall()
        cursor.execute("SELECT c.*, i.title, u.user_name FROM Claim c JOIN Item i ON c.item_id=i.item_id JOIN User u ON c.user_id=u.user_id")
        claims = cursor.fetchall()
        cursor.execute("SELECT * FROM Complaint WHERE status=0")
        complaints = cursor.fetchall()
        cursor.execute("SELECT * FROM CreditRecord ORDER BY freeze_until DESC")
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

@app.route('/admin/delete_user/<uid>')
def delete_user(uid):
    if 'admin' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM User WHERE user_id=%s", (uid,))
        conn.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/audit/<int:claim_id>/<int:status>')
def audit(claim_id, status):
    if 'admin' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 获取认领人信息用于发消息
        cursor.execute("SELECT c.user_id, i.title FROM Claim c JOIN Item i ON c.item_id=i.item_id WHERE c.claim_id=%s", (claim_id,))
        claim_info = cursor.fetchone()
        
        cursor.execute("UPDATE Claim SET audit_status=%s WHERE claim_id=%s", (status, claim_id))
        
        if claim_info:
            msg = f"您的认领申请 [{claim_info['title']}] 已被管理员{'通过' if status==1 else '拒绝'}。"
            cursor.execute("INSERT INTO Message (user_id, content) VALUES (%s, %s)", (claim_info['user_id'], msg))
            
        conn.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/handle_comp/<int:comp_id>', methods=['POST'])
def handle_comp(comp_id):
    if 'admin' not in session: return redirect(url_for('index'))
    action = request.form.get('action')
    result = request.form.get('result')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 获取被投诉人ID (即发起认领的人)
        cursor.execute("""
            SELECT c.user_id 
            FROM Complaint cp 
            JOIN Claim c ON cp.claim_id = c.claim_id 
            WHERE cp.comp_id = %s
        """, (comp_id,))
        res = cursor.fetchone()
        
        if res:
            uid = res['user_id']
            if action == 'violation':
                # 确认违规，冻结 15 天
                cursor.execute("INSERT INTO CreditRecord (user_id, violation_type, freeze_until) VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL 15 DAY))",
                             (uid, f'投诉确认违规: {result}'))
                msg = f"管理员已确认针对您的投诉：{result}。您的账号已被冻结15天。"
            else:
                msg = f"管理员已处理针对您的投诉，判定结果为：不违规。处理意见：{result}"
            
            cursor.execute("INSERT INTO Message (user_id, content) VALUES (%s, %s)", (uid, msg))
        
        cursor.execute("UPDATE Complaint SET result=%s, status=1, admin_id=%s WHERE comp_id=%s",
                     (result, session['admin']['admin_id'], comp_id))
        conn.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/freeze/<uid>')
def freeze_user(uid):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 手动冻结 7 天 (要求7)
        cursor.execute("INSERT INTO CreditRecord (user_id, violation_type, freeze_until) VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL 7 DAY))",
                     (uid, '管理员手动冻结'))
        conn.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/unfreeze/<uid>')
def unfreeze_user(uid):
    if 'admin' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 将该用户的所有未到期的冻结记录设为过期
        cursor.execute("UPDATE CreditRecord SET freeze_until = NOW() WHERE user_id=%s AND freeze_until > NOW()", (uid,))
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