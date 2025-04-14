# Sit-in Management System

A comprehensive web-based system for managing computer laboratory sit-in sessions with role-based access for Students, Staff, and Admin users.

## 🌟 Features

### Student Features
- Profile management with picture upload
- Track remaining sit-in sessions
- View active sessions and history
- Submit feedback for completed sessions

### Staff Features
- Manage student sit-in sessions
- Monitor laboratory usage
- Generate reports
- Handle student requests

### Admin Features
- Complete user management
- System configuration
- Laboratory management
- Analytics and reporting

## 🎨 Design Theme

### Color Palette
- Primary: `#4A90E2` (Professional Blue)
- Secondary: `#45A049` (Success Green)
- Background: `#F5F7FA` (Light Gray)
- Text: `#2C3E50` (Dark Blue Gray)
- Error: `#E74C3C` (Soft Red)
- Success: `#2ECC71` (Emerald Green)
- Warning: `#F1C40F` (Soft Yellow)
- Card Background: `#FFFFFF`
- Border: `#E1E8ED`

## 🏗 Project Structure
```
/sit-in-management-system
├── README.md
├── requirements.txt
├── config.py
├── app.py
├── static/
│   ├── css/
│   │   ├── base.css
│   │   ├── components/
│   │   └── themes/
│   ├── js/
│   │   ├── common/
│   │   └── views/
│   └── images/
├── templates/
│   ├── base.html
│   ├── auth/
│   ├── student/
│   ├── staff/
│   └── admin/
└── routes/
    ├── auth_routes.py
    ├── student_routes.py
    ├── staff_routes.py
    ├── admin_routes.py
    └── common_routes.py
```

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE USERS (
    IDNO VARCHAR(20) PRIMARY KEY,
    FIRSTNAME VARCHAR(50),
    LASTNAME VARCHAR(50),
    MIDDLENAME CHAR(1),
    EMAIL VARCHAR(100) UNIQUE,
    PASSWORD VARCHAR(255),
    COURSE VARCHAR(50),
    YEAR INT,
    USER_TYPE ENUM('STUDENT', 'STAFF', 'ADMIN'),
    PROFILE_PICTURE LONGBLOB,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Laboratories Table
```sql
CREATE TABLE LABORATORIES (
    LAB_ID INT PRIMARY KEY AUTO_INCREMENT,
    LAB_NAME VARCHAR(50),
    TOTAL_COMPUTERS INT,
    STATUS ENUM('ACTIVE', 'INACTIVE'),
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Computers Table
```sql
CREATE TABLE COMPUTERS (
    COMPUTER_ID INT PRIMARY KEY AUTO_INCREMENT,
    LAB_ID INT,
    STATUS ENUM('AVAILABLE', 'IN_USE', 'MAINTENANCE'),
    FOREIGN KEY (LAB_ID) REFERENCES LABORATORIES(LAB_ID)
);
```

### Sit-in Records Table
```sql
CREATE TABLE SIT_IN_RECORDS (
    RECORD_ID INT PRIMARY KEY AUTO_INCREMENT,
    USER_IDNO VARCHAR(20),
    LAB_ID INT,
    COMPUTER_ID INT,
    PURPOSE_ID INT,
    DATE TIMESTAMP,
    END_TIME TIMESTAMP NULL,
    STATUS ENUM('PENDING', 'APPROVED', 'DENIED'),
    SESSION ENUM('ON_GOING', 'ENDED'),
    FOREIGN KEY (USER_IDNO) REFERENCES USERS(IDNO),
    FOREIGN KEY (LAB_ID) REFERENCES LABORATORIES(LAB_ID),
    FOREIGN KEY (COMPUTER_ID) REFERENCES COMPUTERS(COMPUTER_ID),
    FOREIGN KEY (PURPOSE_ID) REFERENCES PURPOSES(PURPOSE_ID)
);
```

### Other Tables
- Purposes
- Sit-in Limits
- Feedbacks
- Announcements

## 🚀 Setup and Installation

### Prerequisites
- Python 3.8+
- MySQL 8.0+
- Modern web browser

### Installation Steps
1. Clone the repository
```bash
git clone https://github.com/yourusername/sit-in-management-system.git
cd sit-in-management-system
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your database credentials and other settings
```

5. Initialize database
```bash
python init_db.py
```

6. Run the application
```bash
python app.py
```

## 🔒 Security Features
- Session management
- Password hashing
- Role-based access control
- SQL injection prevention
- XSS protection
- CSRF protection
- Secure file uploads

## 📱 User Interfaces

### Common Elements
- Clean, minimalist navigation bar
- Responsive sidebar
- Card-based layout
- Consistent spacing and typography
- Loading states
- Error handling
- Toast notifications

### Authentication Pages
- Login
- Registration (Students)
- Password recovery

### Student Dashboard
- Profile management
- Session tracking
- Feedback system

### Staff Dashboard
- Student management
- Session monitoring
- Report generation

### Admin Dashboard
- User management
- System configuration
- Analytics

## 🛠 Development Guidelines

### Code Style
- Follow PEP 8 for Python
- Use ESLint for JavaScript
- Implement CSS BEM methodology
- Maintain consistent naming conventions

### Version Control
- Create feature branches
- Write meaningful commits
- Follow pull request template
- Conduct code reviews

### Testing
- Unit tests
- Integration tests
- UI tests
- Load testing

## 📝 Documentation

### API Documentation
- Endpoint descriptions
- Request/response formats
- Authentication details
- Error codes

### User Guides
- Student manual
- Staff manual
- Admin manual
- FAQs

## 🌐 Production Deployment

### Requirements
- Secure hosting environment
- SSL certificate
- Database backup system
- Monitoring setup

### Performance Optimization
- Code minification
- Image optimization
- Caching strategy
- Database indexing

## 👥 Contributing
Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License
This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## 🙏 Acknowledgments
- Flask framework
- Vue.js
- Bootstrap
- Other open-source libraries used in this project 