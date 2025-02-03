from flask import Flask, render_template, request, redirect, url_for, flash
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
     
        form_data = {key: request.form[key] for key in ['idno', 'lastname', 'firstname', 'middlename', 'course', 'year', 'password']}

       
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO students (IDNO, LASTNAME, FIRSTNAME, MIDDLENAME, COURSE, YEAR, PASSWORD) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                       (form_data['idno'], form_data['lastname'], form_data['firstname'], form_data['middlename'], form_data['course'], form_data['year'], form_data['password']))
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

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE IDNO = %s", (idno,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and user[7] == password:  # Check if the password matches
            
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials, please try again.', 'error')  # Flash error message

    return render_template('login.html')



@app.route('/home')
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)
