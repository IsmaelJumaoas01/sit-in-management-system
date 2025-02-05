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
    if request.method == 'POST':
        form_data = {key: request.form[key] for key in ['idno', 'lastname', 'firstname', 'middlename', 'course', 'year', 'email', 'password']}

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE IDNO = %s", (form_data['idno'],))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('IDNO already exists. Please choose a different IDNO.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('register'))

        cursor.execute("SELECT * FROM students WHERE EMAIL = %s", (form_data['email'],))
        existing_email = cursor.fetchone()

        if existing_email:
            flash('Email address already registered. Please choose a different email.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('register'))

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

    return render_template('register.html')


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
