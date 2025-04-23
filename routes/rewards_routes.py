from flask import Blueprint, request, jsonify, session
from db import get_db_connection
from datetime import datetime

rewards_bp = Blueprint('rewards', __name__)

@rewards_bp.route('/api/rewards/student/<string:student_id>')
def get_student_rewards(student_id):
    if 'IDNO' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get student's points and rewards
        cursor.execute("""
            SELECT 
                COALESCE(SUM(POINTS_EARNED), 0) as total_points,
                COUNT(*) as total_rewards
            FROM STUDENT_REWARDS 
            WHERE STUDENT_ID = %s
        """, (student_id,))
        
        result = cursor.fetchone()
        total_points = result[0] if result else 0
        total_rewards = result[1] if result else 0
        
        # Get detailed rewards history
        cursor.execute("""
            SELECT 
                REWARD_ID,
                REWARD_TYPE,
                POINTS_EARNED,
                DATE_EARNED,
                DESCRIPTION
            FROM STUDENT_REWARDS
            WHERE STUDENT_ID = %s
            ORDER BY DATE_EARNED DESC
        """, (student_id,))
        
        rewards = []
        for row in cursor.fetchall():
            rewards.append({
                'reward_id': row[0],
                'reward_type': row[1],
                'points_earned': row[2],
                'date_earned': row[3].strftime('%Y-%m-%d %H:%M:%S'),
                'description': row[4]
            })
            
        return jsonify({
            'total_points': total_points,
            'total_rewards': total_rewards,
            'rewards_history': rewards
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@rewards_bp.route('/api/rewards/top_participants')
def get_top_participants():
    if 'IDNO' not in session or session['USER_TYPE'] not in ['STAFF', 'ADMIN']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get top 5 students by total points
        cursor.execute("""
            SELECT 
                s.STUDENT_ID,
                u.FIRSTNAME,
                u.LASTNAME,
                u.COURSE,
                COALESCE(SUM(s.POINTS_EARNED), 0) as total_points,
                COUNT(*) as total_rewards
            FROM STUDENT_REWARDS s
            JOIN USERS u ON s.STUDENT_ID = u.IDNO
            GROUP BY s.STUDENT_ID, u.FIRSTNAME, u.LASTNAME, u.COURSE
            ORDER BY total_points DESC
            LIMIT 5
        """)
        
        top_participants = []
        for row in cursor.fetchall():
            top_participants.append({
                'student_id': row[0],
                'name': f"{row[1]} {row[2]}",
                'course': row[3],
                'total_points': row[4],
                'total_rewards': row[5]
            })
            
        return jsonify(top_participants)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@rewards_bp.route('/api/rewards/add', methods=['POST'])
def add_reward():
    if 'IDNO' not in session or session['USER_TYPE'] not in ['STAFF', 'ADMIN']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    student_id = data.get('student_id')
    reward_type = data.get('reward_type')
    points = data.get('points')
    description = data.get('description')
    
    if not all([student_id, reward_type, points]):
        return jsonify({'error': 'Missing required fields'}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO STUDENT_REWARDS 
            (STUDENT_ID, REWARD_TYPE, POINTS_EARNED, DATE_EARNED, DESCRIPTION)
            VALUES (%s, %s, %s, NOW(), %s)
        """, (student_id, reward_type, points, description))
        
        conn.commit()
        return jsonify({'message': 'Reward added successfully'}), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@rewards_bp.route('/points')
def get_student_points():
    if 'IDNO' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                p.POINTS,
                p.TOTAL_POINTS_EARNED,
                p.TOTAL_POINTS_SPENT,
                p.LAST_UPDATED
            FROM STUDENT_POINTS p
            WHERE p.USER_IDNO = %s
        """, (session['IDNO'],))
        
        points_data = cursor.fetchone()
        if not points_data:
            # If no points record exists, create one with 0 points
            cursor.execute("""
                INSERT INTO STUDENT_POINTS (USER_IDNO, POINTS, TOTAL_POINTS_EARNED, TOTAL_POINTS_SPENT)
                VALUES (%s, 0, 0, 0)
            """, (session['IDNO'],))
            conn.commit()
            points_data = {
                'POINTS': 0,
                'TOTAL_POINTS_EARNED': 0,
                'TOTAL_POINTS_SPENT': 0,
                'LAST_UPDATED': None
            }
            
        return jsonify(points_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@rewards_bp.route('/rewards')
def get_available_rewards():
    if 'IDNO' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                r.REWARD_ID,
                r.REWARD_NAME,
                r.DESCRIPTION,
                r.POINTS_REQUIRED,
                p.POINTS as STUDENT_POINTS
            FROM REWARDS r
            CROSS JOIN STUDENT_POINTS p
            WHERE r.IS_ACTIVE = TRUE
            AND p.USER_IDNO = %s
        """, (session['IDNO'],))
        
        rewards = cursor.fetchall()
        return jsonify(rewards)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@rewards_bp.route('/redeem/<int:reward_id>', methods=['POST'])
def redeem_reward(reward_id):
    if 'IDNO' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Start transaction
        conn.start_transaction()
        
        # Get reward details
        cursor.execute("""
            SELECT POINTS_REQUIRED
            FROM REWARDS
            WHERE REWARD_ID = %s AND IS_ACTIVE = TRUE
        """, (reward_id,))
        reward = cursor.fetchone()
        
        if not reward:
            return jsonify({'error': 'Reward not found or inactive'}), 404
            
        # Get student points
        cursor.execute("""
            SELECT POINTS
            FROM STUDENT_POINTS
            WHERE USER_IDNO = %s
        """, (session['IDNO'],))
        points = cursor.fetchone()
        
        if not points or points['POINTS'] < reward['POINTS_REQUIRED']:
            return jsonify({'error': 'Not enough points'}), 400
            
        # Update student points
        cursor.execute("""
            UPDATE STUDENT_POINTS
            SET POINTS = POINTS - %s,
                TOTAL_POINTS_SPENT = TOTAL_POINTS_SPENT + %s
            WHERE USER_IDNO = %s
        """, (reward['POINTS_REQUIRED'], reward['POINTS_REQUIRED'], session['IDNO']))
        
        # Record redemption
        cursor.execute("""
            INSERT INTO STUDENT_REWARDS (USER_IDNO, REWARD_ID, POINTS_SPENT)
            VALUES (%s, %s, %s)
        """, (session['IDNO'], reward_id, reward['POINTS_REQUIRED']))
        
        conn.commit()
        return jsonify({'message': 'Reward redeemed successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@rewards_bp.route('/history')
def get_reward_history():
    if 'IDNO' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                r.REWARD_NAME,
                sr.POINTS_SPENT,
                sr.REDEEMED_AT
            FROM STUDENT_REWARDS sr
            JOIN REWARDS r ON sr.REWARD_ID = r.REWARD_ID
            WHERE sr.USER_IDNO = %s
            ORDER BY sr.REDEEMED_AT DESC
        """, (session['IDNO'],))
        
        history = cursor.fetchall()
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close() 