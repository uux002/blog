#create database db_zhenxinhuadamaoxian_01;
# mysql -u root -p < init_project.sql

create database db_fredshao_blog;

use db_fredshao_blog;

create table accounts(
	`id` varchar(50) not null,
	`email` varchar(50) not null,
	`passwd` varchar(50) not null,
	`admin` bool not null,
	`created_at` real not null,
	unique key `idx_email` (`email`),
	key `idx_created_at` (`created_at`),
	primary key(`id`)
) engine=innodb default charset=utf8;

create table users(
	`id` varchar(50) not null,
	`account_id` varchar(50) not null,
	`nickname` varchar(50) not null,
	`image` varchar(500),
	`created_at` real not null,
	key `idx_created_at` (`created_at`),
	primary key(`id`)

) engine=innodb default charset=utf8;

create table category(
	`id` varchar(50) not null,
	`title` varchar(50) not null,	# 分类名
	`scope` tinyint not null,		# 0 不公开，1公开
	`created_at` real not null,
	primary key(`id`)
)engine=innodb default charset=utf8;

create table article(
	`id` varchar(50) not null,
	`author` varchar(50) not null,
	`belong_category` varchar(50) not null,
	`category_name` varchar(50) not null,
	`article_title` varchar(100),
	`article_state` tinyint not null,		# 文章状态，0 草稿，1 发布
	`scope` tinyint not null,				# 作用域，0不公开，1公开
	`article_content` MEDIUMTEXT,
	`last_update` real not null,
	`created_at` real not null,
	key `idx_last_update` (`last_update`),
	key `idx_created_at` (`created_at`),
	key `idx_belong_category` (`belong_category`),
	primary key(`id`)
)engine=innodb default charset=utf8;

