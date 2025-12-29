# -*- coding: utf-8 -*-
"""
CampusFinder 校园失物招领寻物平台 - 后端核心逻辑
功能涵盖：用户/管理员认证、物品发布与搜索、认领审核流转、投诉处理、信用体系维护及站内通知系统。
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
from config import DB_CONFIG

app = Flask(__name__)
app.secret_key = 'campus_finder_final_secret'

def get_db_connection():
    """建立数据库连接，使用 DictCursor 以便通过键名访问数据"""
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

# --- 1. 认证模块 (登录、注册、注销) ---
@app.route('/')
def index():
    """入口页面：根据 Session 状态自动跳转或显示登录页"""
    if 'user' in session: return redirect(url_for('user_dashboard'))
    if 'admin' in session: return redirect(url_for('admin_dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    """统一登录接口：支持普通用户与管理员角色切换"""
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
    """用户注册：默认密码 123456"""
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
    """注销登录：清空所有 Session 状态"""
    session.clear()
    return redirect(url_for('index'))

# --- 2. 用户端模块 (核心业务逻辑) ---
@app.route('/user_dashboard')
def user_dashboard():
    """用户主页：包含物品浏览、搜索、消息通知及个人认领状态"""
    if 'user' not in session: return redirect(url_for('index'))
    search_query = request.args.get('q', '')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 检查当前用户是否被冻结 (信用体系集成)
        cursor.execute("SELECT * FROM CreditRecord WHERE user_id=%s AND freeze_until > NOW()", (session['user']['user_id'],))
        is_frozen = cursor.fetchone() is not None

        # 分类获取物品：利用视图 v_recent_items 并配合索引 idx_item_title 进行搜索优化
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
        
        # 获取认领记录：包含“我发起的”和“别人领我的”
        cursor.execute("SELECT c.*, i.title FROM Claim c JOIN Item i ON c.item_id=i.item_id WHERE c.user_id=%s", (session['user']['user_id']))
        my_claims = cursor.fetchall()
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

        # 获取站内消息：进入页面即自动标记为已读
        cursor.execute("SELECT * FROM Message WHERE user_id=%s ORDER BY send_time DESC", (session['user']['user_id'],))
        messages = cursor.fetchall()
        cursor.execute("UPDATE Message SET is_read=TRUE WHERE user_id=%s", (session['user']['user_id'],))
        conn.commit()

    return render_template('user_index.html', user=session['user'], 
                           found_items=found_items, lost_items=lost_items, 
                           my_claims=my_claims, others_claims=others_claims, 
                           categories=categories, is_frozen=is_frozen,
                           messages=messages)

@app.route('/publish', methods=['POST'])
def publish_item():
    """发布物品：包含后端冻结状态二次校验"""
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
    """发起认领：调用存储过程 sp_submit_claim 并发送系统通知"""
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
    """提交投诉：关联具体的认领记录"""
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("INSERT INTO Complaint (reason, type, claim_id) VALUES (%s, %s, %s)",
                     (request.form['reason'], request.form['type'], claim_id))
        conn.commit()
    return redirect(url_for('user_dashboard'))

# --- 3. 管理端模块 (管理与审计) ---
@app.route('/admin_dashboard')
def admin_dashboard():
    """管理员后台：包含用户 CRUD、认领审核、投诉处理及黑名单维护"""
    if 'admin' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 自动维护：调用存储过程清理过期黑名单
        cursor.callproc('sp_clear_expired_blacklist')
        
        # 获取用户列表：关联视图 v_user_violations 展示信用画像
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
    """更新用户信息 (CRUD - Update)"""
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE User SET user_name=%s, phone=%s WHERE user_id=%s",
                     (request.form['name'], request.form['phone'], request.form['uid']))
        conn.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<uid>')
def delete_user(uid):
    """删除用户 (CRUD - Delete)：由于设置了级联删除，相关物品和消息将同步清理"""
    if 'admin' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM User WHERE user_id=%s", (uid,))
        conn.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/audit/<int:claim_id>/<int:status>')
def audit(claim_id, status):
    """认领审核：更新状态后将触发数据库触发器 trg_audit_claim 自动处理后续逻辑"""
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
    """投诉处理：支持“确认违规”并自动冻结用户 15 天"""
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
    """手动冻结：管理员强制冻结用户 7 天"""
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 手动冻结 7 天 (要求7)
        cursor.execute("INSERT INTO CreditRecord (user_id, violation_type, freeze_until) VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL 7 DAY))",
                     (uid, '管理员手动冻结'))
        conn.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/unfreeze/<uid>')
def unfreeze_user(uid):
    """手动解冻：将用户所有未到期的冻结记录设为立即过期"""
    if 'admin' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # 将该用户的所有未到期的冻结记录设为过期
        cursor.execute("UPDATE CreditRecord SET freeze_until = NOW() WHERE user_id=%s AND freeze_until > NOW()", (uid,))
        conn.commit()
    return redirect(url_for('admin_dashboard'))


# --- 4. 调试模块：上帝视角 ---
@app.route('/debug')
def debug_view():
    """调试页面：实时监控数据库中所有表（含视图）的原始数据"""
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