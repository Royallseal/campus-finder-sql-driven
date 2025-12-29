/*
   CampusFinder 校园失物招寻平台
   包含：8实体、7联系、索引、视图、存储过程、触发器、测试数据
*/

-- 1. 彻底清空并重新创建数据库
DROP DATABASE IF EXISTS campus_db;
CREATE DATABASE campus_db CHARACTER SET utf8mb4;
USE campus_db;

-- 2. 创建基础表 (无外键依赖)
CREATE TABLE User (
   user_id VARCHAR(20) PRIMARY KEY COMMENT '证件号',
   user_name VARCHAR(50) NOT NULL COMMENT '姓名',
   phone CHAR(11) NOT NULL COMMENT '手机号',
   department VARCHAR(100) COMMENT '学院',
   password VARCHAR(100) DEFAULT '123456' COMMENT '登录密码'
) COMMENT='用户表';

CREATE TABLE Admin (
   admin_id VARCHAR(20) PRIMARY KEY COMMENT '工号',
   admin_level INT DEFAULT 1 COMMENT '权限等级',
   password VARCHAR(100) DEFAULT 'admin123' COMMENT '管理密码'
) COMMENT='管理员表';

CREATE TABLE Category (
   cat_id INT PRIMARY KEY COMMENT '分类ID',
   cat_name VARCHAR(50) NOT NULL COMMENT '分类名称'
) COMMENT='物品分类表';

-- 3. 创建业务表 (带外键依赖)
CREATE TABLE Item (
   item_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '物品ID',
   title VARCHAR(100) NOT NULL COMMENT '物品名称',
   description TEXT COMMENT '描述',
   location VARCHAR(200) COMMENT '地点',
   pub_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '发布时间',
   status INT DEFAULT 0 COMMENT '0:待领, 1:认领中, 2:已结束',
   cat_id INT,
   user_id VARCHAR(20),
   FOREIGN KEY (cat_id) REFERENCES Category(cat_id) ON DELETE CASCADE,
   FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
) COMMENT='物品表';

CREATE TABLE Claim (
   claim_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '认领ID',
   reason TEXT comment '认领理由',
   apply_time DATETIME DEFAULT CURRENT_TIMESTAMP comment '申请时间',
   audit_status INT DEFAULT 0 comment '0:待审核, 1:通过, 2:驳回',
   item_id INT,
   user_id VARCHAR(20),
   FOREIGN KEY (item_id) REFERENCES Item(item_id) ON DELETE CASCADE,
   FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
) COMMENT='认领记录表';

CREATE TABLE Complaint (
   comp_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '投诉ID',
   reason TEXT NOT NULL COMMENT '投诉内容',
   type VARCHAR(50) COMMENT '投诉类别',
   status INT DEFAULT 0 COMMENT '0:未处理, 1:已处理',
   result VARCHAR(255) COMMENT '处理意见',
   claim_id INT,
   admin_id VARCHAR(20),
   FOREIGN KEY (claim_id) REFERENCES Claim(claim_id) ON DELETE CASCADE,
   FOREIGN KEY (admin_id) REFERENCES Admin(admin_id)
) COMMENT='投诉表';

CREATE TABLE CreditRecord (
   cred_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
   user_id VARCHAR(20),
   violation_type VARCHAR(50) COMMENT '违规类型',
   freeze_until DATETIME COMMENT '冻结至',
   FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
) COMMENT='信用黑名单表';

CREATE TABLE Message (
   msg_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '消息ID',
   user_id VARCHAR(20),
   content TEXT NOT NULL COMMENT '内容',
   is_read BOOLEAN DEFAULT FALSE COMMENT '是否已读',
   send_time DATETIME DEFAULT CURRENT_TIMESTAMP,
   FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
) COMMENT='站内消息表';

-- 4. 高级对象定义
-- 创建索引
CREATE INDEX idx_item_title ON Item(title);

-- 创建视图：查询最新待领物品
CREATE VIEW v_recent_items AS
SELECT i.item_id, i.title, i.location, c.cat_name, i.pub_time
FROM Item i
JOIN Category c ON i.cat_id = c.cat_id
WHERE i.status = 0;

-- 创建存储过程：提交认领申请并修改物品状态
DELIMITER //
CREATE PROCEDURE sp_submit_claim(IN u_id VARCHAR(20), IN i_id INT, IN r_reason TEXT)
BEGIN
    INSERT INTO Claim(user_id, item_id, reason, apply_time) VALUES (u_id, i_id, r_reason, NOW());
    UPDATE Item SET status = 1 WHERE item_id = i_id;
END //

-- 创建触发器：驳回恶意申请时自动拉黑
CREATE TRIGGER trg_bad_claim
AFTER UPDATE ON Claim
FOR EACH ROW
BEGIN
    -- 只有状态从 非驳回 改为 驳回(2) 时触发
    IF NEW.audit_status = 2 AND OLD.audit_status != 2 THEN
        INSERT INTO CreditRecord(user_id, violation_type, freeze_until)
        VALUES (NEW.user_id, '虚假冒领', DATE_ADD(NOW(), INTERVAL 30 DAY));
    END IF;
END //
DELIMITER ;

-- 5. 初始化场景测试数据
-- 用户
INSERT INTO User VALUES ('2024001', '张三', '13800138001', '计算机学院', '123456');
INSERT INTO User VALUES ('2024002', '李四', '13900139002', '管理学院', '123456');
INSERT INTO User VALUES ('2024003', '王五', '13700137003', '艺术学院', '123456');
INSERT INTO User VALUES ('2024004', '赵六', '13600136004', '法学院', '123456');
INSERT INTO User VALUES ('2024005', '孙七', '13500135005', '医学院', '123456');
-- 管理员
INSERT INTO Admin VALUES ('ADMIN01', 1, 'admin123');
INSERT INTO Admin VALUES ('ADMIN02', 2, 'admin123');
-- 分类
INSERT INTO Category VALUES (1, '电子产品'), (2, '图书证件'), (3, '生活用品'), (4, '体育器材');
-- 物品 (包含不同状态)
INSERT INTO Item(item_id, title, description, location, cat_id, user_id, status) VALUES
(1, 'iPhone 15 Pro', '黑色，看台捡到', '西区操场', 1, '2024001', 1),
(2, '考研数学全书', '写着张宇', '图书馆4楼', 2, '2024002', 0),
(3, '蓝牙耳机', '白色华为', '二食堂', 1, '2024003', 0),
(4, '宿舍钥匙', '皮卡丘挂件', 'A栋101', 3, '2024004', 0),
(5, '斯伯丁篮球', '有点磨损', '体育馆', 4, '2024001', 2);
-- 认领记录
INSERT INTO Claim(claim_id, reason, item_id, user_id, audit_status) VALUES
(1, '我昨天跑操丢的', 1, '2024002', 0),
(2, '那是我的数学书', 2, '2024004', 1);
-- 投诉
INSERT INTO Complaint(reason, type, claim_id, status) VALUES
('这个认领人根本不是失主', '冒领投诉', 1, 0),
('处理速度太慢', '态度问题', 2, 0);
-- 现有黑名单
INSERT INTO CreditRecord(user_id, violation_type, freeze_until) VALUES
('2024005', '多次虚假认领', '2026-01-30 00:00:00');

SELECT 'Database and Massive Data Ready!' AS Status;