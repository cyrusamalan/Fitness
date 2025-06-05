-- public.users definition

-- Drop table

-- DROP TABLE public.users;

CREATE TABLE public.users (
	user_id serial4 NOT NULL,
	first_name text NULL,
	last_name text NULL,
	email text NOT NULL,
	phone_no text NULL,
	CONSTRAINT users_email_key UNIQUE (email),
	CONSTRAINT users_phone_no_key UNIQUE (phone_no),
	CONSTRAINT users_pkey PRIMARY KEY (user_id)
);


-- public.address definition

-- Drop table

-- DROP TABLE public.address;

CREATE TABLE public.address (
	user_id int4 NOT NULL,
	street text NULL,
	city text NULL,
	state text NULL,
	zip int4 NULL,
	CONSTRAINT address_pkey PRIMARY KEY (user_id),
	CONSTRAINT address_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);


-- public.authentication definition

-- Drop table

-- DROP TABLE public.authentication;

CREATE TABLE public.authentication (
	log_id serial4 NOT NULL,
	user_id int4 NULL,
	login_time timestamp NULL,
	status bool NULL,
	passkey varchar(255) NULL,
	username text NULL,
	CONSTRAINT authentication_pkey PRIMARY KEY (log_id),
	CONSTRAINT authentication_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);


-- public.goals definition

-- Drop table

-- DROP TABLE public.goals;

CREATE TABLE public.goals (
	goal_id serial4 NOT NULL,
	user_id int4 NULL,
	daily_calories int4 NULL,
	daily_protein int4 NULL,
	daily_carbs int4 NULL,
	daily_fats int4 NULL,
	maintenance_calories int4 NULL,
	gain_weight_calories int4 NULL,
	lose_weight_calories int4 NULL,
	CONSTRAINT goals_pkey PRIMARY KEY (goal_id),
	CONSTRAINT goals_user_id_key UNIQUE (user_id),
	CONSTRAINT goals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);


-- public.macros definition

-- Drop table

-- DROP TABLE public.macros;

CREATE TABLE public.macros (
	macro_id serial4 NOT NULL,
	item text NULL,
	calories float8 NOT NULL,
	carbs float8 NULL,
	fat float8 NULL,
	user_id int4 NULL,
	date_added date NULL,
	protein int4 NULL,
	CONSTRAINT macros_pkey PRIMARY KEY (macro_id),
	CONSTRAINT macros_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);


-- public.profile definition

-- Drop table

-- DROP TABLE public.profile;

CREATE TABLE public.profile (
	user_id int4 NOT NULL,
	height_ft int4 NULL,
	height_in int4 NULL,
	weight int4 NULL,
	age int4 NULL,
	gender bpchar(1) NULL,
	goal_weight int4 NULL,
	goal_type varchar(10) DEFAULT 'maintain'::character varying NULL,
	activity_level varchar(20) DEFAULT 'moderate'::character varying NULL,
	CONSTRAINT profile_activity_level_check CHECK (((activity_level)::text = ANY ((ARRAY['sedentary'::character varying, 'light'::character varying, 'moderate'::character varying, 'very_active'::character varying, 'extra_active'::character varying])::text[]))),
	CONSTRAINT profile_gender_check CHECK ((gender = ANY (ARRAY['M'::bpchar, 'F'::bpchar]))),
	CONSTRAINT profile_goal_type_check CHECK (((goal_type)::text = ANY ((ARRAY['bulk'::character varying, 'cut'::character varying, 'maintain'::character varying])::text[]))),
	CONSTRAINT profile_pkey PRIMARY KEY (user_id),
	CONSTRAINT profile_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);


-- public.daily_logs definition

-- Drop table

-- DROP TABLE public.daily_logs;

CREATE TABLE public.daily_logs (
	log_id serial4 NOT NULL,
	user_id int4 NULL,
	macro_id int4 NULL,
	"date" date NULL,
	quantity int4 NULL,
	CONSTRAINT daily_logs_pkey PRIMARY KEY (log_id),
	CONSTRAINT daily_logs_macro_id_fkey FOREIGN KEY (macro_id) REFERENCES public.macros(macro_id),
	CONSTRAINT daily_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);