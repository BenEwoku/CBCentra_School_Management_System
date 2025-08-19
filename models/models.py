# models/models.py
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_db_config():
    """Get DB configuration from environment variables"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'school_management'),
        'autocommit': False,
        'charset': 'utf8mb4',
        'collation': 'utf8mb4_unicode_ci',
        'use_unicode': True
    }


def get_db_connection():
    """Get database connection with automatic initialization"""
    try:
        # First connect without database to create it if needed
        config = get_db_config()
        db_name = config.pop('database')
        
        # Connect to MySQL server without specific database
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # Create database if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        conn.close()
        
        # Now connect to the specific database
        config['database'] = db_name
        conn = mysql.connector.connect(**config)
        
        # Initialize tables
        initialize_tables(conn)
        
        return conn
        
    except Error as e:
        print(f"Database error: {e}")
        raise


def initialize_tables(conn):
    """Initialize all tables in one place"""
    cursor = conn.cursor()
    
    try:
        print("Initializing database tables...")
        
        # Disable foreign key checks temporarily
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # === 1. Schools ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schools (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_name VARCHAR(255) NOT NULL,
                address TEXT,
                phone VARCHAR(20),
                email VARCHAR(255),
                logo_path TEXT,
                motto TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                website VARCHAR(255),
                established_year INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_school_name (school_name),
                INDEX idx_is_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 2. Users (Admins/Staff login credentials) ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                full_name VARCHAR(100),
                role ENUM('admin', 'headteacher', 'teacher', 'staff') DEFAULT 'staff',
                password_hash VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP NULL,
                password_reset_token VARCHAR(255) NULL,
                token_expiry TIMESTAMP NULL,
                school_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_username (username),
                INDEX idx_role (role),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 3. Academic Years ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS academic_years (
                id INT AUTO_INCREMENT PRIMARY KEY,
                year_name VARCHAR(50) NOT NULL UNIQUE,
                start_date DATE,
                end_date DATE,
                is_current BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_year_name (year_name),
                INDEX idx_is_current (is_current)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 4. Terms ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS terms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                term_name VARCHAR(50) NOT NULL,
                term_number INT,
                academic_year_id INT,
                start_date DATE,
                end_date DATE,
                is_current BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_term_name (term_name),
                INDEX idx_is_current (is_current),
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 5. Parents ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                first_name VARCHAR(50),
                surname VARCHAR(50),
                full_name VARCHAR(100),
                relation VARCHAR(50),
                email VARCHAR(100),
                phone VARCHAR(20),
                address1 TEXT,
                address2 TEXT,
                is_payer BOOLEAN DEFAULT FALSE,
                is_emergency_contact BOOLEAN DEFAULT FALSE,
                photo_path TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_full_name (full_name),
                INDEX idx_phone (phone),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 6. Students ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                first_name VARCHAR(50),
                surname VARCHAR(50),
                full_name VARCHAR(100),
                sex ENUM('Male', 'Female', 'Other'),
                date_of_birth DATE,
                religion VARCHAR(50),
                citizenship VARCHAR(50),
                email VARCHAR(100),
                last_school VARCHAR(100),
                grade_applied_for VARCHAR(50),
                class_year VARCHAR(20),
                enrollment_date DATE,
                parent_id INT,
                regNo VARCHAR(50) UNIQUE,
                is_active BOOLEAN DEFAULT TRUE,
                photo_path TEXT,
                medical_conditions TEXT,
                allergies TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_regNo (regNo),
                INDEX idx_full_name (full_name),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES parents(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 7. Teachers ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teachers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                teacher_id_code VARCHAR(50),
                salutation VARCHAR(10),
                first_name VARCHAR(50),
                surname VARCHAR(50),
                full_name VARCHAR(100),
                email VARCHAR(100),
                gender ENUM('Male', 'Female', 'Other'),
                phone_contact_1 VARCHAR(20),
                day_phone VARCHAR(20),
                current_address TEXT,
                home_district VARCHAR(100),
                subject_specialty VARCHAR(100),
                qualification VARCHAR(100),
                date_joined DATE,
                emergency_contact_1 VARCHAR(100),
                emergency_contact_2 VARCHAR(100),
                national_id_number VARCHAR(50),
                birth_date DATE,
                bank_account_number VARCHAR(50),
                next_of_kin VARCHAR(100),
                photo_path TEXT,
                employment_status ENUM('Full-time', 'Part-time', 'Contract', 'Probation', 'Terminated') DEFAULT 'Full-time',
                is_active BOOLEAN DEFAULT TRUE,
                staff_type VARCHAR(50),
                position VARCHAR(100),
                monthly_salary DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_teacher_id_code (teacher_id_code),
                INDEX idx_full_name (full_name),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 8. Departments ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT NOT NULL,
                department_name VARCHAR(100) NOT NULL,
                department_head_id INT,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_department_name (department_name),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (department_head_id) REFERENCES teachers(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 9. Classes ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                class_name VARCHAR(50),
                stream VARCHAR(50),
                level VARCHAR(50),
                class_teacher_id INT,
                term_id INT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_class_name (class_name),
                INDEX idx_level (level),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (class_teacher_id) REFERENCES teachers(id) ON DELETE SET NULL,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 10. Subjects ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                subject_name VARCHAR(100) NOT NULL,
                subject_code VARCHAR(20),
                teacher_id INT,
                level ENUM('O-Level', 'A-Level', 'Both') DEFAULT 'Both',
                is_compulsory BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_subject_name (subject_name),
                INDEX idx_subject_code (subject_code),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 11. Student Subjects ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_subjects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT NOT NULL,
                student_id INT NOT NULL,
                class_id INT NOT NULL,
                subject_id INT NOT NULL,
                academic_year_id INT NOT NULL,
                term_id INT NOT NULL,
                enrollment_notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_enrollment(student_id, subject_id, class_id, term_id, academic_year_id),
                INDEX idx_student_subject (student_id, subject_id),
                INDEX idx_class_subject (class_id, subject_id),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 12. Teacher Subjects ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_subjects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teacher_id INT NOT NULL,
                subject_id INT NOT NULL,
                class_id INT NOT NULL,
                term_id INT NOT NULL,
                academic_year_id INT NOT NULL,
                school_id INT NOT NULL,
                allocation_notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_teacher_subject (teacher_id, subject_id),
                INDEX idx_teacher_class (teacher_id, class_id),
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 13. Student Class Assignments ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_class_assignments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT NOT NULL,
                student_id INT NOT NULL,
                class_id INT NOT NULL,
                academic_year_id INT NOT NULL,
                term_id INT NOT NULL,
                assignment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_current BOOLEAN DEFAULT TRUE,
                status ENUM('Promoted', 'Completed', 'Repeated') DEFAULT 'Promoted',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_student_class (student_id, class_id),
                INDEX idx_is_current (is_current),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 14. Exams ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exams (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                academic_year_id INT,
                term_id INT,
                exam_name VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                start_date DATE,
                end_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_exam_name (exam_name),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 15. Activities ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                subject_id INT NOT NULL,
                class_id INT NOT NULL,
                term_id INT NOT NULL,
                academic_year_id INT NOT NULL,
                exam_id INT,
                exam_type ENUM('BOT', 'MID', 'EOT', 'Project', 'Competency'),
                max_marks INT DEFAULT 100,
                passing_marks INT DEFAULT 40,
                competency_scale_max DECIMAL(3,1) DEFAULT 3.0,
                competency_scale_min DECIMAL(3,1) DEFAULT 0.9,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_activity(name, subject_id, class_id, term_id, academic_year_id),
                INDEX idx_name (name),
                INDEX idx_exam_type (exam_type),
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
                FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 16. Marks ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS marks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_subject_id INT NOT NULL,
                student_id INT NOT NULL,
                subject_id INT NOT NULL,
                class_id INT NOT NULL,
                term_id INT NOT NULL,
                academic_year_id INT NOT NULL,
                school_id INT NOT NULL,
                exam_id INT,
                activity_id INT,
                marks DECIMAL(6,2),
                score_level DECIMAL(3,1),
                grade VARCHAR(10),
                max_marks DECIMAL(6,2) DEFAULT 100,
                teacher_id INT,
                teacher_comment TEXT,
                is_absent BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_student_marks (student_id, is_active),
                INDEX idx_subject_marks (subject_id, is_active),
                INDEX idx_class_marks (class_id, is_active),
                INDEX idx_term_marks (term_id, is_active),
                INDEX idx_marks_lookup (student_id, subject_id, class_id, term_id, academic_year_id, is_active),
                FOREIGN KEY (student_subject_id) REFERENCES student_subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
                FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL,
                CONSTRAINT chk_marks_exam_activity CHECK (
                    (exam_id IS NOT NULL AND activity_id IS NULL) OR
                    (exam_id IS NULL AND activity_id IS NOT NULL)
                ),
                CONSTRAINT chk_marks_range CHECK (marks >= 0 AND (max_marks IS NULL OR marks <= max_marks)),
                CONSTRAINT chk_score_level CHECK (score_level IS NULL OR (score_level >= 0.9 AND score_level <= 3.0))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 17. Grading System ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grading_system (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT NOT NULL,
                min_percentage DECIMAL(5,2) NOT NULL,
                max_percentage DECIMAL(5,2) NOT NULL,
                cbc_score_min DECIMAL(3,1) NOT NULL,
                cbc_score_max DECIMAL(3,1) NOT NULL,
                grade VARCHAR(10) NOT NULL,
                points DECIMAL(3,1) NOT NULL,
                descriptor TEXT,
                competency_level VARCHAR(50),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_grade (grade),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 18. Fee Categories ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fee_categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                category_name VARCHAR(100) NOT NULL,
                description TEXT,
                is_mandatory BOOLEAN DEFAULT TRUE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_category_name (category_name),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 19. Fee Structure ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fee_structure (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                grade_class VARCHAR(50) NOT NULL,
                academic_year VARCHAR(50) NOT NULL,
                fee_category_id INT,
                amount DECIMAL(10,2) NOT NULL,
                term VARCHAR(20) DEFAULT 'Annual',
                due_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_grade_class (grade_class),
                INDEX idx_academic_year (academic_year),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (fee_category_id) REFERENCES fee_categories(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 20. Competencies ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competencies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_subject_id INT NOT NULL,
                student_id INT NOT NULL,
                activity_component_id INT NOT NULL,
                subject_id INT NOT NULL,
                class_id INT NOT NULL,
                term_id INT NOT NULL,
                academic_year_id INT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                competency_score DECIMAL(3,1) CHECK(competency_score BETWEEN 0.9 AND 3.0),
                competency_level ENUM('Basic', 'Moderate', 'Outstanding', 'Exceptional'),
                teacher_comment TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_competency(student_subject_id, activity_component_id),
                INDEX idx_competency_score (competency_score),
                INDEX idx_competency_level (competency_level),
                FOREIGN KEY (student_subject_id) REFERENCES student_subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 21. Head Teacher Comments ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS head_teacher_comments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                class_id INT NOT NULL,
                term_id INT NOT NULL,
                academic_year_id INT NOT NULL,
                comment TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_head_comment(student_id, class_id, term_id, academic_year_id),
                INDEX idx_student_term (student_id, term_id),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 22. Teacher General Comments ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_general_comments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                class_id INT NOT NULL,
                term_id INT NOT NULL,
                academic_year_id INT NOT NULL,
                comment TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_teacher_comment(student_id, class_id, term_id, academic_year_id),
                INDEX idx_student_term (student_id, term_id),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 23. Student Fees ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_fees (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                fee_structure_id INT,
                amount DECIMAL(10,2) NOT NULL,
                discount_amount DECIMAL(10,2) DEFAULT 0,
                final_amount DECIMAL(10,2) NOT NULL,
                due_date DATE,
                academic_year VARCHAR(50),
                term VARCHAR(20),
                is_active BOOLEAN DEFAULT TRUE,
                status ENUM('Pending', 'Paid', 'Overdue', 'Partially Paid') DEFAULT 'Pending',
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_student_fees (student_id, status),
                INDEX idx_fee_status (status),
                INDEX idx_due_date (due_date),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (fee_structure_id) REFERENCES fee_structure(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 24. Fee Payments ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fee_payments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                student_fee_id INT,
                amount_paid DECIMAL(10,2) NOT NULL,
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payment_method ENUM('Cash', 'Mobile Money', 'Bank Transfer', 'Cheque', 'Other') DEFAULT 'Cash',
                reference_number VARCHAR(100),
                received_by VARCHAR(100),
                notes TEXT,
                academic_year VARCHAR(50),
                is_active BOOLEAN DEFAULT TRUE,
                term VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_payment_date (payment_date),
                INDEX idx_payment_method (payment_method),
                INDEX idx_reference_number (reference_number),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (student_fee_id) REFERENCES student_fees(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 25. Student Ledger ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_ledger (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                school_id INT,
                program_id INT,
                academic_year_id INT,
                subjects_count INT,
                sessions_per_month INT,
                sessions_per_week INT,
                study_weeks INT,
                rate_per_session DECIMAL(10,2),
                monthly_fees DECIMAL(10,2),
                ledger_date DATE,
                description TEXT,
                entry_subjects_count INT,
                amount DECIMAL(10,2),
                payment DECIMAL(10,2),
                is_active BOOLEAN DEFAULT TRUE,
                category ENUM('Tuition', 'Materials', 'Registration', 'Transport', 'Misc'),
                status ENUM('Pending', 'Paid', 'Overdue', 'Waived'),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_ledger_date (ledger_date),
                INDEX idx_category (category),
                INDEX idx_status (status),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 26. Item Categories ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS item_categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) UNIQUE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_name (name),
                INDEX idx_is_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 27. Inventory Items ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                name VARCHAR(100),
                category_id INT,
                description TEXT,
                cost DECIMAL(10,2),
                quantity INT,
                min_threshold INT,
                max_capacity INT,
                photo_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_name (name),
                INDEX idx_quantity (quantity),
                INDEX idx_min_threshold (min_threshold),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES item_categories(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 28. Inventory Transactions ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                item_id INT,
                transaction_type ENUM('check-in', 'check-out', 'adjustment', 'return'),
                quantity INT,
                person VARCHAR(100),
                date DATE,
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_transaction_type (transaction_type),
                INDEX idx_date (date),
                INDEX idx_person (person),
                FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 29. Purchase Orders ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                person VARCHAR(100),
                item_description TEXT,
                supplier VARCHAR(100),
                quantity INT,
                unit_price DECIMAL(10,2),
                cost DECIMAL(10,2),
                status ENUM('Pending', 'Ordered', 'Received', 'Cancelled'),
                order_date DATE,
                expected_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_status (status),
                INDEX idx_order_date (order_date),
                INDEX idx_supplier (supplier),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 30. Timetable ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timetable (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                academic_year_id INT,
                term_id INT,
                date DATE,
                day VARCHAR(10),
                subject_id INT,
                teacher_id INT,
                class_id INT,
                room VARCHAR(50),
                time_slot VARCHAR(50),
                status ENUM('Not Taught', 'Taught', 'Cancelled') DEFAULT 'Not Taught',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_date (date),
                INDEX idx_day (day),
                INDEX idx_time_slot (time_slot),
                INDEX idx_status (status),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 31. Attendance ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                school_id INT,
                class_id INT,
                academic_year_id INT,
                term_id INT,
                subject_id INT,
                teacher_id INT,
                lesson_type ENUM('Lesson', 'Assessment', 'Test', 'Practical', 'Revision', 'Remedial'),
                attendance_date DATE,
                time_in TIME,
                time_out TIME,
                status ENUM('Present', 'Absent', 'Late', 'Excused') DEFAULT 'Present',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_attendance_date (attendance_date),
                INDEX idx_status (status),
                INDEX idx_student_date (student_id, attendance_date),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 32. Exam Subjects ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_subjects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                exam_id INT,
                subject_id INT,
                school_id INT,
                teacher_id INT,
                exam_date DATE,
                start_time TIME,
                end_time TIME,
                room VARCHAR(50),
                class_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_exam_date (exam_date),
                INDEX idx_start_time (start_time),
                INDEX idx_room (room),
                FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 33. Announcements ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS announcements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                title VARCHAR(255),
                content TEXT,
                date_posted DATE,
                audience ENUM('All', 'Teachers', 'Students', 'Staff'),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_date_posted (date_posted),
                INDEX idx_audience (audience),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 34. Parent-Teacher Logs ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parent_teacher_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date DATE,
                teacher VARCHAR(100),
                parent_name VARCHAR(100),
                subject VARCHAR(100),
                summary TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_date (date),
                INDEX idx_teacher (teacher),
                INDEX idx_parent_name (parent_name),
                INDEX idx_is_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 35. Login Logs ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                logout_time TIMESTAMP NULL,
                ip_address VARCHAR(50),
                device VARCHAR(100),
                login_status VARCHAR(50),
                user_agent TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                INDEX idx_login_time (login_time),
                INDEX idx_user_login (user_id, login_time),
                INDEX idx_login_status (login_status),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 36. Backups ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                file_path TEXT,
                backup_type ENUM('Full', 'Incremental', 'Differential') DEFAULT 'Full',
                file_size BIGINT,
                status ENUM('Success', 'Failed', 'In Progress') DEFAULT 'Success',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_backup_type (backup_type),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 37. System Settings ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_id INT,
                setting_key VARCHAR(100) NOT NULL,
                setting_value TEXT,
                setting_type ENUM('string', 'integer', 'boolean', 'json') DEFAULT 'string',
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_school_setting(school_id, setting_key),
                INDEX idx_setting_key (setting_key),
                INDEX idx_is_active (is_active),
                FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # === 38. Audit Log ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                action VARCHAR(100) NOT NULL,
                table_name VARCHAR(100),
                record_id INT,
                old_values JSON,
                new_values JSON,
                ip_address VARCHAR(50),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_action (action),
                INDEX idx_table_name (table_name),
                INDEX idx_created_at (created_at),
                INDEX idx_user_action (user_id, action),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        print("Creating additional indexes for performance optimization...")
        
        # Additional performance indexes - using proper MySQL syntax
        try:
            # Check if index exists before creating
            indexes_to_create = [
                ("idx_student_class_term", "student_class_assignments", "student_id, class_id, term_id"),
                ("idx_teacher_subject_class", "teacher_subjects", "teacher_id, subject_id, class_id"),
                ("idx_marks_comprehensive", "marks", "student_id, subject_id, class_id, term_id, academic_year_id, is_active"),
                ("idx_attendance_comprehensive", "attendance", "student_id, attendance_date, status"),
                ("idx_fees_comprehensive", "student_fees", "student_id, status, due_date"),
                ("idx_inventory_low_stock", "inventory_items", "quantity, min_threshold")
            ]
            
            for index_name, table_name, columns in indexes_to_create:
                try:
                    cursor.execute(f"CREATE INDEX {index_name} ON {table_name}({columns})")
                    print(f"✅ Created index: {index_name}")
                except Error as e:
                    if "Duplicate key name" in str(e) or "already exists" in str(e):
                        print(f"ℹ️ Index {index_name} already exists")
                    else:
                        print(f"⚠️ Error creating index {index_name}: {e}")
                        
        except Exception as e:
            print(f"⚠️ Warning: Some indexes may not have been created: {e}")

        print("Database schema creation completed successfully!")

        # Insert default data
        print("Inserting default data...")
        
        # Default admin user
        cursor.execute('''
            INSERT IGNORE INTO users (username, full_name, role, password_hash, is_active)
            VALUES ('admin', 'System Administrator', 'admin', 'pbkdf2:sha256:260000$default$hash', TRUE)
        ''')
        
        # Default academic year
        cursor.execute('''
            INSERT IGNORE INTO academic_years (year_name, start_date, end_date, is_current)
            VALUES ('2024', '2024-01-01', '2024-12-31', TRUE)
        ''')

        # Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        conn.commit()
        print("✅ All tables created successfully in MySQL database")
        
    except Error as e:
        print(f"❌ Error initializing tables: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()


def initialize_database():
    """Standalone function to initialize database"""
    try:
        conn = get_db_connection()
        print("✅ Database initialization completed successfully")
        conn.close()
    except Error as e:
        print(f"❌ Database initialization failed: {e}")
        raise


# Database model classes for easier data manipulation
class DatabaseManager:
    """Database manager class for common operations"""
    
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """Establish database connection"""
        self.connection = get_db_connection()
        return self.connection
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            else:
                self.connection.commit()
                return cursor.rowcount
        except Error as e:
            print(f"Query error: {e}")
            self.connection.rollback()
            raise
        finally:
            cursor.close()
    
    def get_schools(self):
        """Get all active schools"""
        return self.execute_query("SELECT * FROM schools WHERE is_active = TRUE")
    
    def get_students_by_school(self, school_id):
        """Get all active students for a school"""
        return self.execute_query(
            "SELECT * FROM students WHERE school_id = %s AND is_active = TRUE",
            (school_id,)
        )
    
    def get_current_academic_year(self):
        """Get current academic year"""
        result = self.execute_query("SELECT * FROM academic_years WHERE is_current = TRUE LIMIT 1")
        return result[0] if result else None
    
    def get_current_term(self):
        """Get current term"""
        result = self.execute_query("SELECT * FROM terms WHERE is_current = TRUE LIMIT 1")
        return result[0] if result else None
    
    def get_student_marks(self, student_id, term_id=None, academic_year_id=None):
        """Get student marks for a specific term/year"""
        query = """
            SELECT m.*, s.subject_name, st.full_name as student_name
            FROM marks m
            JOIN subjects s ON m.subject_id = s.id
            JOIN students st ON m.student_id = st.id
            WHERE m.student_id = %s AND m.is_active = TRUE
        """
        params = [student_id]
        
        if term_id:
            query += " AND m.term_id = %s"
            params.append(term_id)
        
        if academic_year_id:
            query += " AND m.academic_year_id = %s"
            params.append(academic_year_id)
        
        query += " ORDER BY s.subject_name"
        return self.execute_query(query, params)
    
    def get_class_students(self, class_id, term_id=None):
        """Get all students in a class for a specific term"""
        query = """
            SELECT DISTINCT s.*, sca.status
            FROM students s
            JOIN student_class_assignments sca ON s.id = sca.student_id
            WHERE sca.class_id = %s AND s.is_active = TRUE
        """
        params = [class_id]
        
        if term_id:
            query += " AND sca.term_id = %s"
            params.append(term_id)
        
        query += " ORDER BY s.full_name"
        return self.execute_query(query, params)
    
    def get_teacher_subjects(self, teacher_id, term_id=None):
        """Get subjects assigned to a teacher"""
        query = """
            SELECT ts.*, s.subject_name, c.class_name
            FROM teacher_subjects ts
            JOIN subjects s ON ts.subject_id = s.id
            JOIN classes c ON ts.class_id = c.id
            WHERE ts.teacher_id = %s AND ts.is_active = TRUE
        """
        params = [teacher_id]
        
        if term_id:
            query += " AND ts.term_id = %s"
            params.append(term_id)
        
        return self.execute_query(query, params)
    
    def get_student_attendance(self, student_id, start_date=None, end_date=None):
        """Get student attendance records"""
        query = """
            SELECT a.*, s.subject_name, t.full_name as teacher_name
            FROM attendance a
            JOIN subjects s ON a.subject_id = s.id
            JOIN teachers t ON a.teacher_id = t.id
            WHERE a.student_id = %s
        """
        params = [student_id]
        
        if start_date:
            query += " AND a.attendance_date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND a.attendance_date <= %s"
            params.append(end_date)
        
        query += " ORDER BY a.attendance_date DESC"
        return self.execute_query(query, params)
    
    def get_student_fees_summary(self, student_id):
        """Get student fees summary"""
        return self.execute_query("""
            SELECT 
                sf.*,
                fc.category_name,
                COALESCE(SUM(fp.amount_paid), 0) as total_paid,
                (sf.final_amount - COALESCE(SUM(fp.amount_paid), 0)) as balance
            FROM student_fees sf
            JOIN fee_structure fs ON sf.fee_structure_id = fs.id
            JOIN fee_categories fc ON fs.fee_category_id = fc.id
            LEFT JOIN fee_payments fp ON sf.id = fp.student_fee_id AND fp.is_active = TRUE
            WHERE sf.student_id = %s AND sf.is_active = TRUE
            GROUP BY sf.id
            ORDER BY sf.due_date
        """, (student_id,))
    
    def get_inventory_low_stock(self, school_id):
        """Get items with low stock"""
        return self.execute_query("""
            SELECT ii.*, ic.name as category_name
            FROM inventory_items ii
            LEFT JOIN item_categories ic ON ii.category_id = ic.id
            WHERE ii.school_id = %s 
            AND ii.quantity <= ii.min_threshold
            ORDER BY (ii.quantity / GREATEST(ii.min_threshold, 1)) ASC
        """, (school_id,))
    
    def get_exam_schedule(self, exam_id):
        """Get exam schedule for a specific exam"""
        return self.execute_query("""
            SELECT 
                es.*,
                s.subject_name,
                c.class_name,
                t.full_name as teacher_name
            FROM exam_subjects es
            JOIN subjects s ON es.subject_id = s.id
            JOIN classes c ON es.class_id = c.id
            JOIN teachers t ON es.teacher_id = t.id
            WHERE es.exam_id = %s
            ORDER BY es.exam_date, es.start_time
        """, (exam_id,))
    
    def get_school_statistics(self, school_id):
        """Get comprehensive school statistics"""
        stats = {}
        
        # Student count
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM students WHERE school_id = %s AND is_active = TRUE",
            (school_id,)
        )
        stats['total_students'] = result[0]['count'] if result else 0
        
        # Teacher count
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM teachers WHERE school_id = %s AND is_active = TRUE",
            (school_id,)
        )
        stats['total_teachers'] = result[0]['count'] if result else 0
        
        # Class count
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM classes WHERE school_id = %s AND is_active = TRUE",
            (school_id,)
        )
        stats['total_classes'] = result[0]['count'] if result else 0
        
        # Subject count
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM subjects WHERE school_id = %s AND is_active = TRUE",
            (school_id,)
        )
        stats['total_subjects'] = result[0]['count'] if result else 0
        
        # Outstanding fees
        result = self.execute_query("""
            SELECT SUM(sf.final_amount - COALESCE(paid.total_paid, 0)) as outstanding
            FROM student_fees sf
            JOIN students s ON sf.student_id = s.id
            LEFT JOIN (
                SELECT student_fee_id, SUM(amount_paid) as total_paid
                FROM fee_payments
                WHERE is_active = TRUE
                GROUP BY student_fee_id
            ) paid ON sf.id = paid.student_fee_id
            WHERE s.school_id = %s AND sf.is_active = TRUE AND sf.status != 'Paid'
        """, (school_id,))
        stats['outstanding_fees'] = float(result[0]['outstanding']) if result and result[0]['outstanding'] else 0.0
        
        return stats


# Initialize database when module is imported
if __name__ == "__main__":
    print("🚀 Initializing database...")
    initialize_database()