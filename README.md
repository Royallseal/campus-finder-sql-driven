# 🎓 CampusFinder: SQL 逻辑驱动型失物招领平台

**CampusFinder** 是一个基于 **Flask + MySQL** 的校园失物招领寻物系统。该项目的核心特色在于将复杂的业务逻辑（如信用黑名单、认领状态同步）下沉至数据库层，利用 **MySQL 触发器（Triggers）**、**存储过程（Stored Procedures）** 和 **视图（Views）** 实现了业务逻辑与后端代码的高效解耦。

---

## 🚀 核心技术亮点 (Engineering Highlights)

- **数据库解耦架构：**
  - **Triggers (核心业务引擎)：** 编写了 `trg_audit_claim` 触发器，在管理员审核认领申请时，自动触发物品状态变更及违规信用记录插入，保证数据强一致性。
  - **Stored Procedures：** 封装了 `sp_submit_claim`（自动锁定物品）和 `sp_clear_expired_blacklist`（自动化维护），减少后端逻辑开销。
  - **Views (信用画像)：** 通过视图实时统计用户被拒绝次数与投诉率，快速构建用户信用模型。
- **全权限系统 (RBAC)：** 实现了普通用户与分级管理员的权限隔离。
- **失信惩戒体系：** 具备物品认领审核、冒领投诉以及基于时间的动态账号冻结机制。
- **上帝视角监控：** 特色开发了 `Debug Panel`，实现数据库所有核心表的实时监控，极大提升开发与调试效率。

---

## 🛠️ 技术栈
- **后端:** Python 3.x / Flask
- **数据库:** MySQL 8.x
- **前端:** HTML5 / Bootstrap (Bootswatch Lux 主题)
- **数据库连接:** PyMySQL (CursorDict)

---

## 📂 项目结构
```text
CampusFinder/
├── app.py              # 后端核心路由与业务逻辑
├── sql/
│   └── campus_finder_v1.sql  # 包含所有表、触发器、存储过程的初始化脚本
├── templates/          # 前端渲染模板
├── DATABASE_DESIGN.md  # 详细的数据库设计文档
└── requirements.txt    # 依赖说明
```

---

## 📌 快速开始 (Quick Start)

1. **配置环境：**
   ```bash
   pip install flask pymysql
   ```

2. **数据库初始化：**
   - 在 MySQL 中执行 `sql/campus_finder_v1.sql` 脚本。

3. **配置连接：**
   - 在项目根目录新建 `config.py`，格式如下：
   ```python
   DB_CONFIG = {
       'host': 'localhost',
       'user': 'your_username',
       'password': 'your_password',
       'database': 'campus_db',
       'charset': 'utf8mb4'
   }
   ```

4. **运行：**
   ```bash
   python app.py
   ```

---

## 🚧 待优化项 (Roadmap)
本项目目前为 V1.0 版本，主要用于验证数据库逻辑设计。后续优化方向：
- [ ] **安全性加固：** 引入 `werkzeug.security` 实现密码的加盐哈希存储（当前为明文测试环境）。
- [ ] **事务管理：** 后端进一步增加 `try...except` 异常捕获以增强系统健壮性。
- [ ] **性能优化：** 引入 SQLAlchemy 或数据库连接池。
