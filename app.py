from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector

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
        form_data = {key: request.form[key] for key in ['idno', 'lastname', 'firstname', 'middlename', 'course', 'year', 'email', 'password', 'confirm_password']}

        if form_data['password'] != form_data['confirm_password']:
            flash('Passwords do not match. Please try again.', 'error')
            return render_template('register.html', form_data=form_data)

        if len(form_data['middlename']) != 1 or not form_data['middlename'].isupper():
            flash('Middle name must be a single capital letter.', 'error')
            return render_template('register.html', form_data=form_data)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE IDNO = %s", (form_data['idno'],))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('IDNO already exists. Please choose a different IDNO.', 'error')
            cursor.close()
            conn.close()
            return render_template('register.html', form_data=form_data)

        cursor.execute("SELECT * FROM students WHERE EMAIL = %s", (form_data['email'],))
        existing_email = cursor.fetchone()

        if existing_email:
            flash('Email address already registered. Please choose a different email.', 'error')
            cursor.close()
            conn.close()
            return render_template('register.html', form_data=form_data)

        cursor.execute(
            "INSERT INTO students (IDNO, LASTNAME, FIRSTNAME, MIDDLENAME, COURSE, YEAR, EMAIL, PASSWORD) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (form_data['idno'], form_data['lastname'], form_data['firstname'], form_data['middlename'],
             form_data['course'], form_data['year'], form_data['email'], form_data['password'])
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
        idno, password = request.form['idno'], request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT IDNO, LASTNAME, FIRSTNAME, MIDDLENAME, COURSE, YEAR, EMAIL, PASSWORD FROM students WHERE IDNO = %s", (idno,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and user[7] == password:
            session['idno'] = user[0]
            session['lastname'] = user[1]
            session['firstname'] = user[2]
            session['middlename'] = user[3]
            session['course'] = user[4]
            session['year'] = user[5]
            session['email'] = user[6]

            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials, please try again.', 'error')

    return render_template('login.html')

@app.route('/edit_info', methods=['GET', 'POST'])
def edit_info():
    if 'idno' in session:
        user_idno = session['idno']
        firstname = session['firstname']
        lastname = session['lastname']
        middlename = session['middlename']
        course = session['course']
        year = session['year']
        email = session['email']

        if request.method == 'POST':
            # Get the new details from the form
            new_firstname = request.form['firstname']
            new_lastname = request.form['lastname']
            new_middlename = request.form['middlename']
            new_course = request.form['course']
            new_year = request.form['year']
            new_email = request.form['email']

            # Validate and update the database
            conn = get_db_connection()
            cursor = conn.cursor()

            # SQL update query to update the user's details except IDNO
            cursor.execute("""
                UPDATE students
                SET FIRSTNAME = %s, LASTNAME = %s, MIDDLENAME = %s, COURSE = %s, YEAR = %s, EMAIL = %s
                WHERE IDNO = %s
            """, (new_firstname, new_lastname, new_middlename, new_course, new_year, new_email, user_idno))

            conn.commit()
            cursor.close()
            conn.close()

            session['firstname'] = new_firstname
            session['lastname'] = new_lastname
            session['middlename'] = new_middlename
            session['course'] = new_course
            session['year'] = new_year
            session['email'] = new_email

            flash('Your details have been updated successfully!', 'success')
            return redirect(url_for('dashboard'))

        return render_template('edit_info.html', user_idno=user_idno, firstname=firstname, lastname=lastname,
                               middlename=middlename, course=course, year=year, email=email)
    else:
        flash('You must be logged in to edit your information.', 'error')
        return redirect(url_for('login'))



@app.route('/home')
def dashboard():
    if 'idno' in session:
        user_idno = session['idno']
        firstname = session['firstname']
        lastname = session['lastname']
        middlename = session['middlename']
        course = session['course']
        year = session['year']
        email = session['email']
        
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
