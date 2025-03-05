from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db import get_db_connection

from datetime import datetime, timedelta


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

        # For STUDENT users, load and group announcements
        if 'USER_TYPE' in session and session['USER_TYPE'] == 'STUDENT':
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT ANNOUNCEMENT_ID, TITLE, CONTENT, DATE_POSTED, POSTED_BY 
                    FROM ANNOUNCEMENTS 
                    ORDER BY DATE_POSTED DESC
                """)
                announcements_data = cursor.fetchall()
                ann_list = []
                for ann in announcements_data:
                    ann_date = ann[3]
                    if hasattr(ann_date, 'strftime'):
                        date_str = ann_date.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        date_str = ann_date
                    ann_list.append({
                        'announcement_id': ann[0],
                        'title': ann[1],
                        'content': ann[2],
                        'date_posted': date_str,
                        'posted_by': ann[4]
                    })
            except Exception as e:
                ann_list = []
            finally:
                cursor.close()
                conn.close()

            # Group announcements by time period
            grouped_announcements = group_announcements_by_time(ann_list)
            return render_template('dashboard.html', 
                                   user_idno=user_idno,
                                   firstname=firstname,
                                   middlename=middlename,
                                   lastname=lastname,
                                   course=course,
                                   year=year,
                                   email=email,
                                   grouped_announcements=grouped_announcements)
        elif 'USER_TYPE' in session:
            # Existing branches for STAFF and ADMIN
            if session['USER_TYPE'] == 'STAFF':
                return render_template('staff_dashboard.html', 
                                       staff_firstname=firstname, 
                                       staff_lastname=lastname,
                                       staff_email=email)
            elif session['USER_TYPE'] == 'ADMIN':
                return render_template('admin_dashboard.html', 
                                       user_idno=user_idno,
                                       firstname=firstname,
                                       middlename=middlename,
                                       lastname=lastname,
                                       course=course,
                                       year=year,
                                       email=email)
        return render_template('dashboard.html', 
                               user_idno=user_idno,
                               firstname=firstname,
                               lastname=lastname,
                               middlename=middlename,
                               course=course,
                               year=year,
                               email=email)
    else:
        flash('You must be logged in to view the dashboard.', 'error')
        return redirect(url_for('auth.login'))


def group_announcements_by_time(announcements):
    """
    Group announcements into categories:
      - "This Week" (from Monday of the current week)
      - "Last Week"
      - "Last Month"
      - "Earlier"
    """
    now = datetime.now()
    # Get Monday of the current week
    this_week_start = now - timedelta(days=now.weekday())
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(seconds=1)
    # Last month: from first day of last month to last day of last month
    this_month_start = now.replace(day=1)
    last_month_end = this_month_start - timedelta(seconds=1)
    last_month_start = last_month_end.replace(day=1)
    
    grouped = {
        "This Week": [],
        "Last Week": [],
        "Last Month": [],
        "Earlier": []
    }
    for ann in announcements:
        try:
            dt = datetime.strptime(ann['date_posted'], "%Y-%m-%d %H:%M:%S")
        except Exception:
            # If parsing fails, skip grouping for this announcement.
            dt = now
        if dt >= this_week_start:
            grouped["This Week"].append(ann)
        elif last_week_start <= dt <= last_week_end:
            grouped["Last Week"].append(ann)
        elif last_month_start <= dt <= last_month_end:
            grouped["Last Month"].append(ann)
        else:
            grouped["Earlier"].append(ann)
    return grouped