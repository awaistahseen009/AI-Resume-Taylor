from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, OutreachMessage, JobDescription
from services.message_generator import MessageGenerator

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/generate', methods=['POST'])
@login_required
def generate_message():
    """Generate outreach message for a job"""
    data = request.get_json()
    job_id = data.get('job_id')
    message_type = data.get('message_type')  # email, linkedin, pitch
    tone = data.get('tone', 'professional')  # professional, casual, enthusiastic
    
    if not job_id or not message_type:
        return jsonify({'error': 'Job ID and message type are required'}), 400
    
    job = JobDescription.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    try:
        generator = MessageGenerator()
        message_content = generator.generate_message(
            job_description=job.description_text,
            company=job.company,
            job_title=job.title,
            message_type=message_type,
            tone=tone,
            user_name=f"{current_user.first_name} {current_user.last_name}".strip()
        )
        
        # Save message
        message = OutreachMessage(
            user_id=current_user.id,
            job_description_id=job_id,
            message_type=message_type,
            subject=message_content.get('subject', ''),
            content=message_content.get('content', ''),
            tone=tone
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_id': message.id,
            'subject': message_content.get('subject', ''),
            'content': message_content.get('content', ''),
            'tips': message_content.get('tips', [])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@messages_bp.route('/list')
@login_required
def list_messages():
    """List user's generated messages"""
    messages = OutreachMessage.query.filter_by(user_id=current_user.id).order_by(OutreachMessage.created_at.desc()).all()
    return render_template('messages/list.html', messages=messages)

@messages_bp.route('/view/<int:message_id>')
@login_required
def view_message(message_id):
    """View message details"""
    message = OutreachMessage.query.filter_by(id=message_id, user_id=current_user.id).first()
    if not message:
        flash('Message not found', 'error')
        return redirect(url_for('messages.list_messages'))
    
    return render_template('messages/view.html', message=message)

@messages_bp.route('/delete/<int:message_id>', methods=['POST'])
@login_required
def delete_message(message_id):
    """Delete message"""
    message = OutreachMessage.query.filter_by(id=message_id, user_id=current_user.id).first()
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    db.session.delete(message)
    db.session.commit()
    
    return jsonify({'success': True})

@messages_bp.route('/edit/<int:message_id>', methods=['GET', 'POST'])
@login_required
def edit_message(message_id):
    """Edit message content"""
    message = OutreachMessage.query.filter_by(id=message_id, user_id=current_user.id).first()
    if not message:
        flash('Message not found', 'error')
        return redirect(url_for('messages.list_messages'))
    
    if request.method == 'POST':
        message.subject = request.form.get('subject', message.subject)
        message.content = request.form.get('content', message.content)
        db.session.commit()
        flash('Message updated successfully!', 'success')
        return redirect(url_for('messages.view_message', message_id=message_id))
    
    return render_template('messages/edit.html', message=message)

@messages_bp.route('/copy/<int:message_id>')
@login_required
def copy_message(message_id):
    """Get message content for copying"""
    message = OutreachMessage.query.filter_by(id=message_id, user_id=current_user.id).first()
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    return jsonify({
        'success': True,
        'subject': message.subject,
        'content': message.content,
        'message_type': message.message_type
    })
