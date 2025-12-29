/*==============================================================*/
/* DBMS name:      MySQL 5.0                                    */
/* Created on:     2025/12/29 21:22:45                          */
/*==============================================================*/


drop trigger trg_bad_claim;

drop procedure if exists sp_submit_claim;

drop table if exists Admin;

drop table if exists Category;

drop table if exists Claim;

drop table if exists Complaint;

drop table if exists CreditRecord;

drop index idx_item_title on Item;

drop table if exists Item;

drop table if exists Message;

drop table if exists User;

/*==============================================================*/
/* Table: Admin                                                 */
/*==============================================================*/
create table Admin
(
   admin_id             VARCHAR(20) not null comment '工号',
   admin_level          INT default 1 comment '权限等级',
   primary key (admin_id)
);

/*==============================================================*/
/* Table: Category                                              */
/*==============================================================*/
create table Category
(
   cat_id               INT not null comment '分类ID',
   cat_name             VARCHAR(50) not null comment '分类名称',
   primary key (cat_id)
);

/*==============================================================*/
/* Table: Claim                                                 */
/*==============================================================*/
create table Claim
(
   claim_id             INT not null auto_increment comment '认领ID',
   reason               TEXT comment '认领理由',
   apply_time           DATETIME default CURRENT_TIMESTAMP comment '申请时间',
   audit_status         INT default 0 comment '0:待审核, 1:通过, 2:驳回',
   item_id              INT,
   user_id              VARCHAR(20),
   primary key (claim_id)
);

/*==============================================================*/
/* Table: Complaint                                             */
/*==============================================================*/
create table Complaint
(
   comp_id              INT not null auto_increment comment '投诉ID',
   reason               TEXT not null comment '投诉内容',
   result               VARCHAR(255) comment '处理意见',
   claim_id             INT,
   admin_id             VARCHAR(20),
   primary key (comp_id)
);

/*==============================================================*/
/* Table: CreditRecord                                          */
/*==============================================================*/
create table CreditRecord
(
   cred_id              INT not null auto_increment comment '记录ID',
   user_id              VARCHAR(20),
   violation_type       VARCHAR(50) comment '违规类型',
   freeze_until         DATETIME comment '冻结至',
   primary key (cred_id)
);

/*==============================================================*/
/* Table: Item                                                  */
/*==============================================================*/
create table Item
(
   item_id              INT not null auto_increment comment '物品ID',
   title                VARCHAR(100) not null comment '物品名称',
   description          TEXT comment '描述',
   location             VARCHAR(200) comment '地点',
   pub_time             DATETIME default CURRENT_TIMESTAMP comment '发布时间',
   status               INT default 0 comment '0:待领, 1:认领中, 2:已结束',
   cat_id               INT,
   user_id              VARCHAR(20),
   primary key (item_id)
);

/*==============================================================*/
/* Index: idx_item_title                                        */
/*==============================================================*/
create index idx_item_title on Item
(
   title
);

/*==============================================================*/
/* Table: Message                                               */
/*==============================================================*/
create table Message
(
   msg_id               INT not null auto_increment comment '消息ID',
   user_id              VARCHAR(20),
   content              TEXT not null comment '内容',
   is_read              BOOLEAN default FALSE comment '是否已读',
   send_time            DATETIME default CURRENT_TIMESTAMP,
   primary key (msg_id)
);

/*==============================================================*/
/* Table: User                                                  */
/*==============================================================*/
create table User
(
   user_id              VARCHAR(20) not null comment '证件号',
   user_name            VARCHAR(50) not null comment '姓名',
   phone                CHAR(11) not null comment '手机号',
   department           VARCHAR(100) comment '学院',
   primary key (user_id)
);

alter table Claim add constraint FK_Reference_3 foreign key (item_id)
      references Item (item_id);

alter table Claim add constraint FK_Reference_4 foreign key (user_id)
      references User (user_id);

alter table Complaint add constraint FK_Reference_5 foreign key (claim_id)
      references Claim (claim_id);

alter table CreditRecord add constraint FK_Reference_6 foreign key (user_id)
      references User (user_id);

alter table Item add constraint FK_Reference_1 foreign key (cat_id)
      references Category (cat_id);

alter table Item add constraint FK_Reference_2 foreign key (user_id)
      references User (user_id);

alter table Message add constraint FK_Reference_7 foreign key (user_id)
      references User (user_id);


CREATE PROCEDURE sp_submit_claim(IN u_id VARCHAR(20), IN i_id INT, IN r_reason TEXT)
BEGIN
    -- 插入认领记录
    INSERT INTO Claim(user_id, item_id, reason, apply_time) 
    VALUES (u_id, i_id, r_reason, NOW());
    -- 修改物品状态为认领中
    UPDATE Item SET status = 1 WHERE item_id = i_id;
END BEGIN;


-- 当认领状态被改为 2 (驳回/冒领) 时，自动插入黑名单
IF NEW.audit_status = 2 THEN
    INSERT INTO CreditRecord(user_id, violation_type, freeze_until)
    VALUES (NEW.user_id, '虚假冒领', DATE_ADD(NOW(), INTERVAL 30 DAY));
END IF;

