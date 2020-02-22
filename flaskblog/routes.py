import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from flaskblog import app, db, bcrypt, mail
from flaskblog.forms import (RegistrationForm, LoginForm, UpdateAccount,
                             PostForm, ResetPasswordForm, RequestResetForm)
from flaskblog.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message


@app.route('/')
@app.route('/home')
@login_required
def home():
    page=request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(user_id = current_user.id).order_by(Post.date_posted.desc()).paginate(page=page,per_page=5)
    return render_template('home.html', posts=posts)


@app.route('/about')
def about():
    return render_template('about.html', title = 'About')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    print('I am here')
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password
        )
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created, you will be able to login', 'success')
        print(f'Account created for {form.username.data}!')

        return redirect(url_for('login'))
    return render_template('register.html', title='Register',form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email = form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check username and password', 'danger')
    return render_template('Login.html', title='Login',form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

def upload_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_filename = f"{random_hex}{f_ext}"
    picture_path = os.path.join(app.root_path, 'static/profile_pic',picture_filename)
    output_size = (125,125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_filename




@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccount()
    if form.validate_on_submit():
        if form.picture.data:
            picture_filename = upload_picture(form.picture.data)
            current_user.image_file = picture_filename
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated','success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email

    image_file = url_for('static', filename=f'profile_pic/{current_user.image_file}')
    return render_template(
        'Account.html', title='Account', image_file=image_file, form=form
    )


@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        if form.title.data and form.content.data:
            post = Post(title=form.title.data, content=form.content.data, author=current_user)
            db.session.add(post)
            db.session.commit()
            flash('Your post has been successfully created!', 'success')
            return redirect(url_for('home'))
    return render_template(
        'create_post.html', title='New Post', form=form, legend='New Post'
    )

@app.route('/post/<int:post_id>')
def post(post_id):
    ret_post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=ret_post.title, post=ret_post)


@app.route('/post/<int:post_id>/update', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    ret_post = Post.query.get_or_404(post_id)
    if ret_post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        ret_post.title = form.title.data
        ret_post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated', 'Success')
        return redirect(url_for('post', post_id=ret_post.id))
    elif request.method == 'GET':
        form.title.data = ret_post.title
        form.content.data = ret_post.content
    return render_template(
        'create_post.html', title='Update Post', form=form, legend='Update Post'
    )


@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    ret_post = Post.query.get_or_404(post_id)
    if ret_post.author != current_user:
        abort(403)
    db.session.delete(ret_post)
    db.session.commit()
    flash('Your post has been deleted', 'success')
    return redirect(url_for('home'))


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page,per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password reset request',
                  sender='niyojanuser@gmail.com',
                  recipients=[user.email]
                  )
    msg.body = f'''To Reset your password visit following link
    {url_for('reset_token', token=token, _external=True)}
    If you did not send this request, then simply ignore this message and no changes will be made
    '''
    mail.send(msg)


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('Email has been sent with instructions to reset the password', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('This is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request.html'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        # db.session.add(user)
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated, you will be able to login', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

