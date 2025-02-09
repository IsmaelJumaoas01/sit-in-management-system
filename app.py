from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector, re

app = Flask(__name__)
app.secret_key = 'xdsxdxdxdasxdsxsaasaxasdaxda'

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="SMS"
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    form_data = None  

    if request.method == 'POST':
        # Check if all required keys are present in the form data
        required_keys = ['idno', 'lastname', 'firstname', 'middlename', 'course', 'year', 'email', 'password', 'confirm_password']
        
        # If any of the required keys is missing, return an error
        if not all(key in request.form for key in required_keys):
            flash('All fields are required.', 'error')
            return render_template('register.html')

        # Gather form data
        form_data = {key: request.form[key] for key in required_keys}

        # Validate IDNO
        if not form_data['idno'].isdigit():
            flash('IDNO must only contain numbers. Please try again.', 'error')
            return render_template('register.html', form_data=form_data)

        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, form_data['email']):
            flash('Invalid email format. Please enter a valid email address.', 'error')
            return render_template('register.html', form_data=form_data)

        # Check if passwords match
        if form_data['password'] != form_data['confirm_password']:
            flash('Passwords do not match. Please try again.', 'error')
            return render_template('register.html', form_data=form_data)

        # Validate middle name
        if len(form_data['middlename']) != 1 or not form_data['middlename'].isupper():
            flash('Middle name must be a single capital letter.', 'error')
            return render_template('register.html', form_data=form_data)

        # Check if IDNO or email already exists
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

        # Set user type as 'student' automatically
        user_type = 'student'

        cursor.execute(
            "INSERT INTO USERS (IDNO, LASTNAME, FIRSTNAME, MIDDLENAME, COURSE, YEAR, EMAIL, PASSWORD, USER_TYPE) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (form_data['idno'], form_data['lastname'], form_data['firstname'], form_data['middlename'],
             form_data['course'], form_data['year'], form_data['email'], form_data['password'], user_type)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash('Registration successful! You can now login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form_data=form_data)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Check if IDNO and PASSWORD fields are in the request form
        if 'IDNO' not in request.form or 'PASSWORD' not in request.form:
            flash('IDNO and Password are required.', 'error')
            return render_template('login.html')
        
        IDNO = request.form['IDNO']
        PASSWORD = request.form['PASSWORD']

        # Check if the user exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT IDNO, LASTNAME, FIRSTNAME, MIDDLENAME, COURSE, YEAR, EMAIL, PASSWORD, USER_TYPE FROM USERS WHERE IDNO = %s", (IDNO,))
        user = cursor.fetchone()

        if user and user[7] == PASSWORD:
            session['USER_TYPE'] = user[8]  # Set user_type from USER_TYPE column
            session['IDNO'] = user[0]
            session['FIRSTNAME'] = user[2]
            session['LASTNAME'] = user[1]
            session['MIDDLENAME'] = user[3]
            session['COURSE'] = user[4]
            session['YEAR'] = user[5]
            session['EMAIL'] = user[6]

            return redirect(url_for('dashboard'))

        flash('Invalid credentials, please try again.', 'error')

    return render_template('login.html')



@app.route('/edit_info', methods=['GET', 'POST'])
def edit_info():
    if 'IDNO' in session:
        user_idno = session['IDNO']
        firstname = session['FIRSTNAME']
        lastname = session['LASTNAME']
        middlename = session['MIDDLENAME']
        course = session['COURSE']
        year = session['YEAR']
        email = session['EMAIL']

        if request.method == 'POST':
            # Make sure the key names match exactly with the HTML form
            new_firstname = request.form['firstname']
            new_lastname = request.form['lastname']
            new_middlename = request.form['middlename']
            new_course = request.form['course']
            new_year = request.form['year']
            new_email = request.form['email']

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""UPDATE USERS SET FIRSTNAME = %s, LASTNAME = %s, MIDDLENAME = %s, COURSE = %s, YEAR = %s, EMAIL = %s WHERE IDNO = %s""",
                           (new_firstname, new_lastname, new_middlename, new_course, new_year, new_email, user_idno))

            conn.commit()
            cursor.close()
            conn.close()

            session['FIRSTNAME'] = new_firstname
            session['LASTNAME'] = new_lastname
            session['MIDDLENAME'] = new_middlename
            session['COURSE'] = new_course
            session['YEAR'] = new_year
            session['EMAIL'] = new_email

            flash('Your details have been updated successfully!', 'success')
            return redirect(url_for('dashboard'))

        return render_template('edit_info.html', user_idno=user_idno, firstname=firstname, lastname=lastname,
                               middlename=middlename, course=course, year=year, email=email)
    else:
        flash('You must be logged in to edit your information.', 'error')
        return redirect(url_for('login'))



@app.route('/home')
def dashboard():
    if 'IDNO' in session:
        user_idno = session['IDNO']
        firstname = session.get('staff_firstname', session.get('FIRSTNAME'))
        lastname = session.get('staff_lastname', session.get('LASTNAME'))
        middlename = session.get('MIDDLENAME')
        course = session.get('COURSE')
        year = session.get('YEAR')
        email = session.get('EMAIL')

        if 'USER_TYPE' in session:
            if session['USER_TYPE'] == 'STAFF':
                # Staff dashboard
                return render_template('staff_dashboard.html', 
                                       staff_firstname=firstname, 
                                       staff_lastname=lastname,
                                       staff_email=email)
            elif session['USER_TYPE'] == 'STUDENT':
                # Student dashboard
                return render_template('dashboard.html', 
                                       user_idno=user_idno,
                                       firstname=firstname,
                                       middlename=middlename,
                                       lastname=lastname,
                                       course=course,
                                       year=year,
                                       email=email)
        
        # Default dashboard if USER_TYPE is not set
        return render_template('dashboard.html', user_idno=user_idno, firstname=firstname, lastname=lastname, middlename=middlename, course=course, year=year, email=email)
    else:
        flash('You must be logged in to view the dashboard.', 'error')
        return redirect(url_for('login'))


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
