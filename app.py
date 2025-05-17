from flask import Flask, render_template, request, redirect, url_for, session, flash
from config import Config
from models import db, mapper_registry, reflect_selected_tables
from sqlalchemy.exc import DBAPIError
from sqlalchemy import func
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


class AppUser: pass
class Role: pass
class StudyRoom: pass
class Reservation: pass
class Asset: pass
class ResetReservation: pass
class Maintenance: pass
class Policy: pass
class Feedback: pass
class AdminLog: pass

with app.app_context():
    metadata = reflect_selected_tables(app)
    for cls, table_name in [
        (AppUser, 'appuser'), (Role, 'role'), (StudyRoom, 'studyroom'),
        (Reservation, 'reservation'), (Asset, 'asset'), (ResetReservation, 'resetreservation'),
        (Maintenance, 'maintenance'), (Policy, 'policy'), (Feedback, 'feedback'), (AdminLog, 'adminlog')
    ]:
        mapper_registry.map_imperatively(cls, metadata.tables[table_name])

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = db.session.query(AppUser).filter_by(
            email=request.form['email'],
            passwordhash=request.form['password']
        ).first()
        if user:
            session.update({
                'user_id': user.userid,
                'user_name': user.firstname,
                'role_id': user.roleid
            })
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    role_id = session.get('role_id')
    if role_id in (1, 4):
        return redirect(url_for('admin_page'))
    elif role_id in (2, 3, 5 ):
        return redirect(url_for('user_page'))
    else:
        return 'Access Denied'

@app.route('/admin')
@login_required
def admin_page():
    if session.get('role_id') != 1:
        return 'Access Denied'
    return render_template('admin_dashboard.html')

@app.route('/user')
@login_required
def user_page():
    if session.get('role_id') not in (2, 3):
        return 'Access Denied'
    return render_template('user_dashboard.html')

@app.route('/reserve-room', methods=['GET', 'POST'])
@login_required
def reserve_room():
    if session.get('role_id') not in (2, 3):
        flash("Only students and faculty can reserve rooms.", 'error')
        return redirect(url_for('dashboard'))

    rooms = db.session.query(StudyRoom).filter(
        StudyRoom.isavailable == True,
        StudyRoom.capacity > 0
    ).all()

    assets = db.session.query(Asset).filter(Asset.isavailable == True).all()

    if request.method == 'POST':
        try:
            room_id = int(request.form['room_id'])
            start = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
            end = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')

            
            conflict = db.session.query(Maintenance).filter(
                Maintenance.roomid == room_id,
                Maintenance.startdate <= start,
                Maintenance.enddate >= end
            ).first()

            if conflict:
                flash("Room under maintenance for selected time.", 'error')
                return render_template('reserve_room.html', rooms=rooms, assets=assets)

            
            reservation = Reservation(
                userid=session['user_id'],
                roomid=room_id,
                starttime=start,
                endtime=end,
                status='Confirmed'
            )
            db.session.add(reservation)

            
            room = db.session.get(StudyRoom, room_id)
            room.capacity -= 1
            if room.capacity == 0:
                room.isavailable = False

            
            asset_id = request.form.get('asset_id')
            if asset_id:
                asset = db.session.get(Asset, int(asset_id))
                if asset and asset.isavailable:
                    asset_res = ResetReservation(
                        userid=session['user_id'],
                        assetid=int(asset_id),
                        reserveddate=start,
                        returndate=end,
                        status='Checked Out'
                    )
                    db.session.add(asset_res)
                    asset.isavailable = False

            db.session.commit()
            flash("Reservation successful. Asset borrowed if selected.", 'success')
            return redirect(url_for('user_page'))

        except Exception as e:
            db.session.rollback()
            flash(f"Reservation error: {str(e)}", "error")

    return render_template('reserve_room.html', rooms=rooms, assets=assets)

@app.route('/my-reservations', methods=['GET', 'POST'])
@login_required
def my_reservations():
    if session.get('role_id') not in (2, 3):
        return 'Access Denied'

    policy = db.session.query(Policy).first()
    now = datetime.now()

    reservations = db.session.query(Reservation).filter_by(userid=session['user_id']).all()
    asset_reservations = db.session.query(ResetReservation).filter_by(userid=session['user_id']).all()

    if request.method == 'POST':
        try:
            if 'asset_reservation_id' in request.form:
                a = db.session.get(ResetReservation, int(request.form['asset_reservation_id']))
                if request.form['action'] == 'cancel':
                    a.status = 'cancelled'
                    asset = db.session.query(Asset).get(a.assetid)
                    if asset:
                        asset.isavailable = True
                    db.session.commit()
                elif request.form['action'] == 'modify':
                    a.reserveddate = datetime.strptime(request.form['new_reserved'], '%Y-%m-%dT%H:%M')
                    a.returndate = datetime.strptime(request.form['new_return'], '%Y-%m-%dT%H:%M')
                    db.session.commit()
            else:
                r = db.session.get(Reservation, int(request.form['reservation_id']))
                diff_hours = (r.starttime - now).total_seconds() / 3600
                if request.form['action'] == 'cancel' and diff_hours < policy.maxcancellationhours:
                    flash("Too late to cancel.", 'error')
                elif request.form['action'] == 'modify' and diff_hours < policy.maxmodificationhours:
                    flash("Too late to modify.", 'error')
                elif request.form['action'] == 'cancel':
                    r.status = 'cancelled'
                    room = db.session.query(StudyRoom).get(r.roomid)
                    if room:
                        room.capacity += 1
                        if not room.isavailable:
                            room.isavailable = True
                    db.session.commit()
                elif request.form['action'] == 'modify':
                    r.starttime = datetime.strptime(request.form['new_start'], '%Y-%m-%dT%H:%M')
                    r.endtime = datetime.strptime(request.form['new_end'], '%Y-%m-%dT%H:%M')
                    db.session.commit()
            return redirect(url_for('my_reservations'))
        except DBAPIError as e:
            db.session.rollback()
            flash(f"Error: {e.orig}", 'error')

    return render_template(
        'my_reservations.html',
        reservations=reservations,
        asset_reservations=asset_reservations,
        now=now,
        policy=policy
    )



@app.route('/borrow-asset', methods=['GET', 'POST'])
@login_required
def borrow_asset():
    assets = db.session.query(Asset).filter_by(isavailable=True).all()
    if request.method == 'POST':
        try:
            new_reservation = ResetReservation(
                userid=session['user_id'],
                assetid=int(request.form['asset_id']),
                reserveddate=request.form['reserved_date'],
                returndate=request.form['return_date'],
                status='Checked Out'
            )
            db.session.add(new_reservation)
            db.session.commit()
            flash("Asset borrowed successfully!", "success")
            return redirect(url_for('user_page'))
        except DBAPIError as e:
            db.session.rollback()
            flash(f"Database error: {e.orig}", 'error')
        except Exception as e:
            flash(f"Unexpected error: {str(e)}", 'error')
    return render_template('borrow_asset.html', assets=assets)


@app.route('/submit-feedback', methods=['GET', 'POST'])
@login_required
def submit_feedback():
    rooms = db.session.query(StudyRoom).join(Reservation).filter(
        Reservation.userid == session['user_id']
    ).distinct().all()

    assets = db.session.query(Asset).join(ResetReservation).filter(
        ResetReservation.userid == session['user_id']
    ).distinct().all()

    if request.method == 'POST':
        try:
            db.session.add(Feedback(
                userid=session['user_id'],
                roomid=request.form.get('room_id') or None,
                assetid=request.form.get('asset_id') or None,
                rating=request.form['rating'],
                comment=request.form['comment'],
                submittedat=datetime.utcnow()
            ))
            db.session.commit()
            flash("Feedback submitted. Thank you!", "success")
            return redirect(url_for('user_page'))
        except DBAPIError as e:
            db.session.rollback()
            flash(f"Database error: {e.orig}", 'error')
        except Exception as e:
            flash(f"Unexpected error: {str(e)}", 'error')

    return render_template('submit_feedback.html', rooms=rooms, assets=assets)

@app.route('/feedback-summary')
@login_required
def feedback_summary():
    if session.get('role_id') != 1:
        return "Access Denied"

    room_feedback = db.session.query(
        StudyRoom.roomnumber,
        func.avg(Feedback.rating)
    ).join(Feedback, Feedback.roomid == StudyRoom.roomid)\
     .group_by(StudyRoom.roomnumber).all()

    asset_feedback = db.session.query(
        Asset.name,
        func.avg(Feedback.rating)
    ).join(Feedback, Feedback.assetid == Asset.assetid)\
     .group_by(Asset.name).all()

    room_labels = [r[0] for r in room_feedback]
    room_data = [float(f"{r[1]:.2f}") if r[1] else 0 for r in room_feedback]

    asset_labels = [a[0] for a in asset_feedback]
    asset_data = [float(f"{a[1]:.2f}") if a[1] else 0 for a in asset_feedback]


    return render_template(
    'feedback_summary.html',
    room_labels=room_labels,
    room_data=room_data,
    asset_labels=asset_labels,
    asset_data=asset_data
)

@app.route('/view-policy')
@login_required
def view_policy():
    policy = db.session.query(Policy).first()
    return render_template('view_policy.html', policy=policy)

@app.route('/maintenance')
@login_required
def view_maintenance():
    logs = db.session.query(Maintenance).all()
    return render_template('maintenance.html', logs=logs)

@app.route('/request-maintenance', methods=['GET', 'POST'])
@login_required
def request_maintenance():
    if session.get('role_id') not in (2, 3):
        return 'Access Denied'
    rooms = db.session.query(StudyRoom).join(Reservation).filter(
    Reservation.userid == session['user_id']
).distinct().all()

    if request.method == 'POST':
        try:
            new_maintenance = Maintenance(
                roomid=int(request.form['room_id']),
                startdate=datetime.strptime(request.form['start_date'], '%Y-%m-%dT%H:%M'),
                enddate=datetime.strptime(request.form['end_date'], '%Y-%m-%dT%H:%M'),
                reason=request.form['reason']
            )
            db.session.add(new_maintenance)
            db.session.commit()
            flash("Maintenance request submitted.", "success")
            return redirect(url_for('user_page'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "error")
    return render_template('request_maintenance.html', rooms=rooms)


@app.route('/admin-logs')
@login_required
def admin_logs():
    if session.get('role_id') != 1:
        return 'Access Denied'
    logs = db.session.query(AdminLog).all()
    return render_template('admin_logs.html', logs=logs)

@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if session.get('role_id') != 1:
        return 'Access Denied'
    user_count = db.session.query(AppUser).count()
    this_month = datetime.now().replace(day=1)
    reservation_count = db.session.query(Reservation).filter(Reservation.starttime >= this_month).count()
    popular = db.session.query(StudyRoom.roomnumber, func.count(Reservation.reservationid))\
        .join(Reservation).group_by(StudyRoom.roomnumber).order_by(func.count(Reservation.reservationid).desc()).limit(5).all()
    return render_template('admin_dashboard.html', user_count=user_count, recent_reservations=reservation_count, popular_rooms=popular)

@app.route('/check-overdue')
@login_required
def check_overdue():
    updated = db.session.query(ResetReservation).filter(
        ResetReservation.status == 'Checked Out',
        ResetReservation.returndate < date.today()
    ).update({ResetReservation.status: 'Overdue'}, synchronize_session=False)

    db.session.commit()
    flash(f"{updated} reservation(s) marked as overdue.", "success")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
