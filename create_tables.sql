CREATE TABLE breeds (
	breed_id SERIAL PRIMARY KEY,
	breed_name VARCHAR(100) NOT NULL UNIQUE,
	description TEXT,
	min_height_cm DECIMAL(5,2) CHECK (min_height_cm > 0),
	max_height_cm DECIMAL(5,2) CHECK (max_height_cm > 0),
	typical_color VARCHAR(200),
	CHECK (min_height_cm < max_height_cm)
);

CREATE TABLE owners (
    owner_id SERIAL PRIMARY KEY,
    last_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    phone VARCHAR(20) UNIQUE,
    email VARCHAR(100) UNIQUE,
    address TEXT
);

CREATE TABLE dogs (
    dog_id SERIAL PRIMARY KEY,
    dog_name VARCHAR(100) NOT NULL,
    breed_id INTEGER NOT NULL,
    owner_id INTEGER NOT NULL,
    birth_date DATE,
    is_alive BOOLEAN DEFAULT true,
    mental_test_score INTEGER CHECK (mental_test_score BETWEEN 1 AND 5),
    notes TEXT,
    CONSTRAINT unique_dog_name_owner 
	UNIQUE (dog_name, owner_id),
    CONSTRAINT fk_dogs_breed 
	FOREIGN KEY (breed_id) REFERENCES breeds(breed_id) 
	ON DELETE RESTRICT,
    CONSTRAINT fk_dogs_owner 
	FOREIGN KEY (owner_id) REFERENCES owners(owner_id) 
	ON DELETE RESTRICT
);

CREATE TABLE diseases (
    disease_id SERIAL PRIMARY KEY,
    disease_name VARCHAR(200) NOT NULL UNIQUE,
    treatment_method TEXT,
    is_dangerous BOOLEAN DEFAULT false,
    typical_duration_days INTEGER CHECK (typical_duration_days > 0)
);

CREATE TABLE parentage (
    dog_id INTEGER PRIMARY KEY,
    father_id INTEGER,
    mother_id INTEGER,
    CONSTRAINT fk_parentage_dog 
	FOREIGN KEY (dog_id) REFERENCES dogs(dog_id) 
	ON DELETE CASCADE,
    CONSTRAINT fk_parentage_father 
	FOREIGN KEY (father_id) REFERENCES dogs(dog_id) 
	ON DELETE SET NULL,
    CONSTRAINT fk_parentage_mother 
	FOREIGN KEY (mother_id) REFERENCES dogs(dog_id) 
	ON DELETE SET NULL,
    CONSTRAINT check_dog_not_own_parent 
	CHECK (dog_id <> father_id 
	AND dog_id <> mother_id),
    CONSTRAINT check_parents_different 
	CHECK (father_id IS NULL OR mother_id IS NULL 
	OR father_id <> mother_id)
);

CREATE TABLE medical_history (
    history_id SERIAL PRIMARY KEY,
    dog_id INTEGER NOT NULL,
    disease_id INTEGER NOT NULL,
    illness_date DATE NOT NULL,
    recovery_date DATE,
    notes TEXT,
    CONSTRAINT fk_medical_history_dog 
	FOREIGN KEY (dog_id) REFERENCES dogs(dog_id) 
	ON DELETE CASCADE,
    CONSTRAINT fk_medical_history_disease 
	FOREIGN KEY (disease_id) REFERENCES diseases(disease_id) 
	ON DELETE RESTRICT,
    CONSTRAINT check_recovery_after_illness 
	CHECK (recovery_date IS NULL 
	OR recovery_date >= illness_date)
);

CREATE TABLE exhibitions (
    exhibition_id SERIAL PRIMARY KEY,
    dog_id INTEGER NOT NULL,
    exhibition_date DATE NOT NULL,
    score INTEGER CHECK (score BETWEEN 1 AND 5),
    medal VARCHAR(20) 
	CHECK (medal IN ('gold', 'silver', 'bronze', NULL)),
    notes TEXT,
    CONSTRAINT fk_exhibitions_dog 
	FOREIGN KEY (dog_id) REFERENCES dogs(dog_id) 
	ON DELETE CASCADE,
    CONSTRAINT unique_dog_exhibition_date 
	UNIQUE (dog_id, exhibition_date)
);