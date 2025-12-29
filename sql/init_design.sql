/* 校园失物招寻平台 - 初始逻辑脚本 */

CREATE TABLE User (
    user_id VARCHAR(20) PRIMARY KEY COMMENT '证件号',
    user_name VARCHAR(50) NOT NULL COMMENT '姓名',
    phone CHAR(11) NOT NULL COMMENT '手机号',
    department VARCHAR(100) COMMENT '学院'
);

CREATE TABLE Category (
    cat_id INT PRIMARY KEY COMMENT '分类ID',
    cat_name VARCHAR(50) NOT NULL COMMENT '分类名称'
);

CREATE TABLE Item (
    item_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '物品ID',
    title VARCHAR(100) NOT NULL COMMENT '物品名称',
    description TEXT COMMENT '描述',
    location VARCHAR(200) COMMENT '地点',
    pub_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '发布时间',
    status INT DEFAULT 0 COMMENT '0:待领, 1:认领中, 2:已结束',
    cat_id INT,
    user_id VARCHAR(20),
    FOREIGN KEY (cat_id) REFERENCES Category(cat_id),
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);

CREATE TABLE Claim (
    claim_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '认领ID',
    reason TEXT COMMENT '认领理由',
    apply_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '申请时间',
    audit_status INT DEFAULT 0 COMMENT '0:待审核, 1:通过, 2:驳回',
    item_id INT,
    user_id VARCHAR(20),
    FOREIGN KEY (item_id) REFERENCES Item(item_id),
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);

CREATE TABLE Complaint (
    comp_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '投诉ID',
    reason TEXT NOT NULL COMMENT '投诉内容',
    result VARCHAR(255) COMMENT '处理意见',
    claim_id INT,
    admin_id VARCHAR(20),
    FOREIGN KEY (claim_id) REFERENCES Claim(claim_id)
);

CREATE TABLE Admin (
    admin_id VARCHAR(20) PRIMARY KEY COMMENT '工号',
    admin_level INT DEFAULT 1 COMMENT '权限等级'
);

CREATE TABLE CreditRecord (
    cred_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    user_id VARCHAR(20),
    violation_type VARCHAR(50) COMMENT '违规类型',
    freeze_until DATETIME COMMENT '冻结至',
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);

CREATE TABLE Message (
    msg_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '消息ID',
    user_id VARCHAR(20),
    content TEXT NOT NULL COMMENT '内容',
    is_read BOOLEAN DEFAULT FALSE COMMENT '是否已读',
    send_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);