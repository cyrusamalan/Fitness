create database Fitness

create table users(
	user_id serial primary key,
	first_name text,
	last_name text,
	email text unique not null,
	phone_no bigint unique
);
create table macros(
	macro_id serial primary key,
	item text,
	calories float not null,
	protien float not null,
	carbs float,
	fat float,
	user_id int references users(user_id)
);
create table address(
	user_id int primary key,
	street text,
	city text,
	state text,
	zip int,
	foreign key(user_id) references users(user_id)
);
create table goals(
	goal_id serial primary key,
	user_id int references users(user_id),
	daily_calories int,
	daily_protein int,
	daily_carbs int,
	daily_fats int
);
create table authentication(
	log_id serial primary key,
	user_id int references users(user_id),
	login_time timestamp,
	status boolean,
	passkey varchar(255)
);
create table daily_logs(
	log_id serial primary key,
	user_id int references users(user_id),
	macro_id int references macros(macro_id),
	"date" date,
	quantity int
);
create table profile(
	user_id int primary key,
	height_ft INT,
	height_in INT,
	weight int,
	age int,
	gender CHAR(1) CHECK (gender IN ('M', 'F')),
	goal_weight int,
	foreign key(user_id) references users(user_id)
);
