create database db_zhenxinhuadamaoxian_01;

use db_zhenxinhuadamaoxian_01;

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

create table truthordares(
	`id` varchar(50) not null,
	`user_id` varchar(50) not null,
	`title` varchar(600) not null,
	`content` mediumtext,
	`item_type` integer not null,
	`agree_count` integer not null,
	`message_count` integer not null,
	`created_at` real not null,
	key `idx_created_at` (`created_at`),
	key `idx_agree_count` (`agree_count`),
	key `idx_message_count` (`message_count`),
	primary key (`id`)

) engine=innodb default charset=utf8;

create table comments(
	`id` varchar(50) not null,
	`belong_id` varchar(50) not null,
	`parent_id` varchar(50) not null,
	`user_id` varchar(50) not null,
	`content` mediumtext not null,
	`created_at` real not null,
	key `idx_created_at` (`created_at`),
	key `idx_belong_id` (`belong_id`),
	key `idx_parent_id` (`parent_id`),
	key `idx_user_id` (`user_id`),
	primary key (`id`)
) engine=innodb default charset=utf8;