from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db import get_db_connection
import re
import os

auth_bp = Blueprint('auth', __name__)

# Add path for default profile picture
DEFAULT_PROFILE_IMAGE = os.path.join('static', 'images', 'default-image.png')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form_data = None  

    if request.method == 'POST':
        required_keys = ['idno', 'lastname', 'firstname', 'middlename', 'course', 'year', 'email', 'password', 'confirm_password']
        
        if not all(key in request.form for key in required_keys):
            flash('All fields are required.', 'error')
            return render_template('register.html')

        form_data = {key: request.form[key] for key in required_keys}

        if not form_data['idno'].isdigit():
            flash('IDNO must only contain numbers. Please try again.', 'error')
            return render_template('register.html', form_data=form_data)

        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, form_data['email']):
            flash('Invalid email format. Please enter a valid email address.', 'error')
            return render_template('register.html', form_data=form_data)

        if form_data['password'] != form_data['confirm_password']:
            flash('Passwords do not match. Please try again.', 'error')
            return render_template('register.html', form_data=form_data)

        if len(form_data['middlename']) != 1 or not form_data['middlename'].isupper():
            flash('Middle name must be a single capital letter.', 'error')
            return render_template('register.html', form_data=form_data)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM USERS WHERE IDNO = %s", (form_data['idno'],))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('IDNO already exists. Please choose a different IDNO.', 'error')
            cursor.close()
            conn.close()
            return render_template('register.html', form_data=form_data)

        cursor.execute("SELECT * FROM USERS WHERE EMAIL = %s", (form_data['email'],))
        existing_email = cursor.fetchone()

        if existing_email:
            flash('Email address already registered. Please choose a different email.', 'error')
            cursor.close()
            conn.close()
            return render_template('register.html', form_data=form_data)

        user_type = 'STUDENT'

        # Read the default profile picture
        try:
            with open(DEFAULT_PROFILE_IMAGE, 'rb') as f:
                default_profile_picture = f.read()
        except Exception as e:
            default_profile_picture = None

        try:
            # Insert the new user
            cursor.execute(
                "INSERT INTO USERS (IDNO, LASTNAME, FIRSTNAME, MIDDLENAME, COURSE, YEAR, EMAIL, PASSWORD, USER_TYPE, PROFILE_PICTURE) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (form_data['idno'], form_data['lastname'], form_data['firstname'], form_data['middlename'],
                 form_data['course'], form_data['year'], form_data['email'], form_data['password'], user_type, default_profile_picture)
            )
            
            # Set initial sit-in limit based on course
            initial_limit = 30 if form_data['course'] in ['BSIT', 'BSCS'] else 15
            cursor.execute(
                "INSERT INTO SIT_IN_LIMITS (USER_IDNO, SIT_IN_COUNT) VALUES (%s, %s)",
                (form_data['idno'], initial_limit)
            )
            
            conn.commit()
            flash('Registration successful! You can now login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            conn.rollback()
            flash(f'An error occurred during registration: {str(e)}', 'error')
            return render_template('register.html', form_data=form_data)
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html', form_data=form_data)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if 'IDNO' not in request.form or 'PASSWORD' not in request.form:
            flash('IDNO and Password are required.', 'error')
            return render_template('login.html')
        
        IDNO = request.form['IDNO']
        PASSWORD = request.form['PASSWORD']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT IDNO, LASTNAME, FIRSTNAME, MIDDLENAME, COURSE, YEAR, EMAIL, PASSWORD, USER_TYPE FROM USERS WHERE IDNO = %s", (IDNO,))
        user = cursor.fetchone()

        if user and user[7] == PASSWORD:
            # Clear any existing session
            session.clear()
            
            # Make session permanent with 30 minutes lifetime
            session.permanent = True
            
            # Set all session variables
            session['USER_TYPE'] = user[8]
            session['IDNO'] = user[0]
            session['FIRSTNAME'] = user[2]
            session['LASTNAME'] = user[1]
            session['MIDDLENAME'] = user[3]
            session['COURSE'] = user[4]
            session['YEAR'] = user[5]
            session['EMAIL'] = user[6]
            
            print(f"Session variables set: {dict(session)}")  # Debug log

            # Redirect based on user type
            if user[8] == 'ADMIN':
                return redirect(url_for('admin.admin_dashboard'))
            elif user[8] == 'STAFF':
                return redirect(url_for('staff.staff_dashboard'))
            else:
                return redirect(url_for('user.dashboard'))

        flash('Invalid credentials, please try again.', 'error')
        cursor.close()
        conn.close()

    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
