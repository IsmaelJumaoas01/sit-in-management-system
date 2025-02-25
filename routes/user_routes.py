from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db import get_db_connection

user_bp = Blueprint('user', __name__)

@user_bp.route('/edit_info', methods=['GET', 'POST'])
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
            return redirect(url_for('user.dashboard'))

        return render_template('edit_info.html', user_idno=user_idno, firstname=firstname, lastname=lastname,
                               middlename=middlename, course=course, year=year, email=email)
    else:
        flash('You must be logged in to edit your information.', 'error')
        return redirect(url_for('auth.login'))

@user_bp.route('/home')
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
                return render_template('staff_dashboard.html', 
                                       staff_firstname=firstname, 
                                       staff_lastname=lastname,
                                       staff_email=email)
            elif session['USER_TYPE'] == 'STUDENT':
                return render_template('dashboard.html', 
                                       user_idno=user_idno,
                                       firstname=firstname,
                                       middlename=middlename,
                                       lastname=lastname,
                                       course=course,
                                       year=year,
                                       email=email)
            elif session['USER_TYPE'] == 'ADMIN':
                return render_template('admin_dashboard.html', 
                                       user_idno=user_idno,
                                       firstname=firstname,
                                       middlename=middlename,
                                       lastname=lastname,
                                       course=course,
                                       year=year,
                                       email=email)
                                       
        return render_template('dashboard.html', user_idno=user_idno, firstname=firstname, lastname=lastname, middlename=middlename, course=course, year=year, email=email)
    else:
        flash('You must be logged in to view the dashboard.', 'error')
        return redirect(url_for('auth.login'))
