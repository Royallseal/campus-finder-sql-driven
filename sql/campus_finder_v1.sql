/* CampusFinder 数据库脚本 */

-- 1. 彻底清空并重新创建数据库
DROP DATABASE IF EXISTS campus_db;
CREATE DATABASE campus_db CHARACTER SET utf8mb4;
USE campus_db;

-- 2. 创建基础表 (无外键依赖的先建)
CREATE TABLE User (
   user_id VARCHAR(20) PRIMARY KEY,
   user_name VARCHAR(50) NOT NULL,
   phone CHAR(11) NOT NULL,
   department VARCHAR(100)
) COMMENT='用户表';

CREATE TABLE Admin (
   admin_id VARCHAR(20) PRIMARY KEY,
   admin_level INT DEFAULT 1
) COMMENT='管理员表';

CREATE TABLE Category (
   cat_id INT PRIMARY KEY,
   cat_name VARCHAR(50) NOT NULL
) COMMENT='物品分类表';

-- 3. 创建核心业务表 (有外键依赖的后建)
CREATE TABLE Item (
   item_id INT PRIMARY KEY AUTO_INCREMENT,
   title VARCHAR(100) NOT NULL,
   description TEXT,
   location VARCHAR(200),
   pub_time DATETIME DEFAULT CURRENT_TIMESTAMP,
   status INT DEFAULT 0 COMMENT '0:待领, 1:认领中, 2:已结束',
   cat_id INT,
   user_id VARCHAR(20),
   FOREIGN KEY (cat_id) REFERENCES Category(cat_id),
   FOREIGN KEY (user_id) REFERENCES User(user_id)
) COMMENT='物品表';

CREATE TABLE Claim (
   claim_id INT PRIMARY KEY AUTO_INCREMENT,
   reason TEXT,
   apply_time DATETIME DEFAULT CURRENT_TIMESTAMP,
   audit_status INT DEFAULT 0 COMMENT '0:待审核, 1:通过, 2:驳回',
   item_id INT,
   user_id VARCHAR(20),
   FOREIGN KEY (item_id) REFERENCES Item(item_id),
   FOREIGN KEY (user_id) REFERENCES User(user_id)
) COMMENT='认领记录表';

CREATE TABLE Complaint (
   comp_id INT PRIMARY KEY AUTO_INCREMENT,
   reason TEXT NOT NULL,
   result VARCHAR(255),
   claim_id INT,
   admin_id VARCHAR(20),
   FOREIGN KEY (claim_id) REFERENCES Claim(claim_id)
) COMMENT='投诉表';

CREATE TABLE CreditRecord (
   cred_id INT PRIMARY KEY AUTO_INCREMENT,
   user_id VARCHAR(20),
   violation_type VARCHAR(50),
   freeze_until DATETIME,
   FOREIGN KEY (user_id) REFERENCES User(user_id)
) COMMENT='信用黑名单表';

CREATE TABLE Message (
   msg_id INT PRIMARY KEY AUTO_INCREMENT,
   user_id VARCHAR(20),
   content TEXT NOT NULL,
   is_read BOOLEAN DEFAULT FALSE,
   send_time DATETIME DEFAULT CURRENT_TIMESTAMP,
   FOREIGN KEY (user_id) REFERENCES User(user_id)
) COMMENT='站内消息表';

-- 4. 创建高级对象
-- 索引
CREATE INDEX idx_item_title ON Item(title);

-- 视图
CREATE VIEW v_recent_items AS
SELECT i.item_id, i.title, i.location, c.cat_name, i.pub_time
FROM Item i
JOIN Category c ON i.cat_id = c.cat_id
WHERE i.status = 0;

-- 存储过程 (使用 DELIMITER 保证在 MySQL 中正常运行)
DELIMITER //
CREATE PROCEDURE sp_submit_claim(IN u_id VARCHAR(20), IN i_id INT, IN r_reason TEXT)
BEGIN
    INSERT INTO Claim(user_id, item_id, reason, apply_time)
    VALUES (u_id, i_id, r_reason, NOW());
    UPDATE Item SET status = 1 WHERE item_id = i_id;
END //
DELIMITER ;

-- 触发器
DELIMITER //
CREATE TRIGGER trg_bad_claim
AFTER UPDATE ON Claim
FOR EACH ROW
BEGIN
    -- 如果审核状态被改为 2 (驳回)，则自动拉黑
    IF NEW.audit_status = 2 AND OLD.audit_status != 2 THEN
        INSERT INTO CreditRecord(user_id, violation_type, freeze_until)
        VALUES (NEW.user_id, '虚假冒领', DATE_ADD(NOW(), INTERVAL 30 DAY));
    END IF;
END //
DELIMITER ;

-- 5. 插入初始化测试数据
INSERT INTO User VALUES ('2024001', '张同学', '13800138001', '计算机学院');
INSERT INTO Admin VALUES ('ADMIN01', 1);
INSERT INTO Category VALUES (1, '电子产品'), (2, '图书证件'), (3, '生活用品');
INSERT INTO Item(title, description, location, cat_id, user_id)
VALUES ('iPhone 15 Pro', '黑色，在西操场捡到', '西区操场', 1, '2024001');

SELECT 'Database structure created successfully!' AS Message;