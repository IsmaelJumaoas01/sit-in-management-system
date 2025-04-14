-- Lab Resources Table
CREATE TABLE lab_resources (
    resource_id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    resource_type ENUM('FILE', 'LINK', 'TEXT') NOT NULL,
    content_url VARCHAR(512),  -- For files and links
    content_text TEXT,         -- For plain text content
    created_by VARCHAR(50) NOT NULL,   -- References USERS.IDNO
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_enabled BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (created_by) REFERENCES USERS(IDNO)
);

-- Resource Course Mapping Table
CREATE TABLE resource_course_mapping (
    resource_id INT,
    course_id VARCHAR(100),  -- Changed to match USERS.COURSE length
    PRIMARY KEY (resource_id, course_id),
    FOREIGN KEY (resource_id) REFERENCES lab_resources(resource_id) ON DELETE CASCADE
);

-- Resource Access Logs
CREATE TABLE resource_access_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    resource_id INT,
    user_id VARCHAR(50),  -- Changed to match USERS.IDNO
    user_type ENUM('STUDENT', 'STAFF', 'ADMIN') NOT NULL,  -- Match USERS.USER_TYPE
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES lab_resources(resource_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES USERS(IDNO)
); 