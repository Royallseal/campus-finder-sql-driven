# CampusFinder 数据库设计文档

本项目使用 MySQL 数据库，字符集统一为 `utf8mb4`。

## 1. 逻辑结构设计 (E-R 关系)
系统包含 8 张核心业务表，涵盖了用户管理、物品发布、认领审核、投诉处理及信用体系。

---

## 2. 数据表详细设计

### 2.1 用户表 (`User`)
存储平台普通用户的基本信息。

| 字段名 | 类型 | 约束 | 备注 |
| :--- | :--- | :--- | :--- |
| user_id | VARCHAR(20) | PRIMARY KEY | 证件号 (学号/工号) |
| user_name | VARCHAR(50) | NOT NULL | 姓名 |
| phone | CHAR(11) | NOT NULL | 手机号 |
| department | VARCHAR(100) | - | 所属学院/部门 |
| password | VARCHAR(100) | DEFAULT '123456' | 登录密码 |

### 2.2 管理员表 (`Admin`)
存储系统管理员信息。

| 字段名 | 类型 | 约束 | 备注 |
| :--- | :--- | :--- | :--- |
| admin_id | VARCHAR(20) | PRIMARY KEY | 管理员工号 |
| admin_level | INT | DEFAULT 1 | 权限等级 |
| password | VARCHAR(100) | DEFAULT 'admin123' | 管理密码 |

### 2.3 物品分类表 (`Category`)
| 字段名 | 类型 | 约束 | 备注 |
| :--- | :--- | :--- | :--- |
| cat_id | INT | PRIMARY KEY | 分类ID |
| cat_name | VARCHAR(50) | NOT NULL | 分类名称 (如：电子产品) |

### 2.4 物品表 (`Item`)
存储丢失或拾取的物品信息。

| 字段名 | 类型 | 约束 | 备注 |
| :--- | :--- | :--- | :--- |
| item_id | INT | PRIMARY KEY, AUTO_INCREMENT | 物品唯一标识 |
| title | VARCHAR(100) | NOT NULL | 物品名称 |
| description | TEXT | - | 详细描述 (特征、颜色等) |
| location | VARCHAR(200) | - | 拾取/丢失地点 |
| pub_time | DATETIME | DEFAULT CURRENT_TIMESTAMP | 发布时间 |
| status | INT | DEFAULT 0 | 状态 (0:发布中, 1:认领中, 2:已结束) |
| type | INT | DEFAULT 0 | 类型 (0:招领-捡到, 1:寻物-丢了) |
| cat_id | INT | FOREIGN KEY | 关联分类表 |
| user_id | VARCHAR(20) | FOREIGN KEY | 发布者ID |

### 2.5 认领记录表 (`Claim`)
记录用户发起的认领申请。

| 字段名 | 类型 | 约束 | 备注 |
| :--- | :--- | :--- | :--- |
| claim_id | INT | PRIMARY KEY, AUTO_INCREMENT | 认领ID |
| reason | TEXT | - | 认领理由/线索描述 |
| apply_time | DATETIME | DEFAULT CURRENT_TIMESTAMP | 申请时间 |
| audit_status | INT | DEFAULT 0 | 审核状态 (0:待审核, 1:通过, 2:拒绝) |
| item_id | INT | FOREIGN KEY | 关联物品 |
| user_id | VARCHAR(20) | FOREIGN KEY | 申请人ID |

### 2.6 投诉表 (`Complaint`)
| 字段名 | 类型 | 约束 | 备注 |
| :--- | :--- | :--- | :--- |
| comp_id | INT | PRIMARY KEY, AUTO_INCREMENT | 投诉ID |
| reason | TEXT | NOT NULL | 投诉原因 |
| type | VARCHAR(50) | - | 投诉类型 (如：冒领投诉) |
| status | INT | DEFAULT 0 | 处理状态 (0:未处理, 1:已处理) |
| result | VARCHAR(255) | - | 管理员处理意见 |
| claim_id | INT | FOREIGN KEY | 关联的认领记录 |
| admin_id | VARCHAR(20) | FOREIGN KEY | 处理该投诉的管理员 |

### 2.7 信用黑名单表 (`CreditRecord`)
| 字段名 | 类型 | 约束 | 备注 |
| :--- | :--- | :--- | :--- |
| cred_id | INT | PRIMARY KEY, AUTO_INCREMENT | 记录ID |
| user_id | VARCHAR(20) | FOREIGN KEY | 违规用户ID |
| violation_type | VARCHAR(50) | - | 违规类型 (如：恶意冒领) |
| freeze_until | DATETIME | - | 账号冻结截止时间 |

### 2.8 站内消息表 (`Message`)
| 字段名 | 类型 | 约束 | 备注 |
| :--- | :--- | :--- | :--- |
| msg_id | INT | PRIMARY KEY, AUTO_INCREMENT | 消息ID |
| user_id | VARCHAR(20) | FOREIGN KEY | 接收者ID |
| content | TEXT | NOT NULL | 消息内容 |
| is_read | BOOLEAN | DEFAULT FALSE | 是否已读 |
| send_time | DATETIME | DEFAULT CURRENT_TIMESTAMP | 发送时间 |

---

## 3. 高级数据库对象

### 3.1 索引 (Indexes)
*   `idx_item_title`: 在 `Item` 表的 `title` 字段上建立普通索引，用于优化用户在首页搜索物品标题时的查询速度。

### 3.2 视图 (Views)
*   `v_recent_items`: 实时查询所有处于“发布中”状态的物品，包含分类名和发布者信息。
*   `v_user_violations`: 统计每个用户的违规数据（被投诉次数、认领被拒次数），用于管理员评估信用。

### 3.3 存储过程 (Stored Procedures)
*   `sp_submit_claim`: 封装认领申请逻辑，插入记录的同时自动将物品状态改为“认领中”。
*   `sp_clear_expired_blacklist`: 自动清理已过期的冻结记录。

### 3.4 触发器 (Triggers)
*   `trg_audit_claim`: **核心业务触发器**。当管理员更新认领状态时触发：
    *   若**通过**：自动将物品状态设为“已结束”。
    *   若**拒绝**：自动将物品恢复为“发布中”，并自动将申请人加入黑名单（冻结30天）。
