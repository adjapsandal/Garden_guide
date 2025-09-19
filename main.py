from flask import Flask, render_template, request, session, redirect, url_for, flash
import os
from dotenv import load_dotenv
from db import (
    get_subjects, get_region, get_plant_types, get_crops, get_sorts, get_sort_details,
    get_user_favourites, add_favourite, remove_favourite,
    get_favourite_plants, get_agronomist_by_user,
    get_all_plant_types, get_all_crops, get_all_sorts,
    add_crop_with_region, add_sort,
    get_crops_for_region, get_sorts_for_region,
    add_crop_region, update_crop_region, delete_crop_region,
    add_sort_region, update_sort_region, delete_sort_region,
    get_pests, add_pest,
    get_crop_pests, add_crop_pest, update_crop_pest, delete_crop_pest, get_crop_pest_details,
    get_articles, add_article,
    get_article, get_comments, add_comment,
    get_user_articles, delete_article, update_article
)
from auth import register_user, authenticate_user, get_user_by_email
from functools import wraps

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

@app.context_processor
def inject_user():
    user_num = session.get('user_num')
    username = session.get('username')
    is_agronomist = False
    agronomist_name = None
    agronomist_region_name = None
    if user_num:
        agr = get_agronomist_by_user(user_num)
        if agr:
            is_agronomist = True
            agronomist_name = agr['agronomist_name']
            agronomist_region_name = agr.get('region_name')
    return dict(
        username=username,
        is_agronomist=is_agronomist,
        agronomist_name=agronomist_name,
        agronomist_region_name=agronomist_region_name
    )

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/catalog')
def catalog():
    subject_num = request.args.get('subject', type=int)
    if subject_num:
        region = get_region(subject_num)    
        region_num = region['region_num']
        session['last_region'] = region_num
    else:
        region = None
        region_num = None
    plant_type_num = request.args.get('plant_type', type=int)
    crop_num = request.args.get('crop', type=int)
    plant_num = request.args.get('plant', type=int)
    display = request.args.get('display', default='sorts')

    subjects = get_subjects()
    plant_types = get_plant_types(region_num) if region_num else []
    crops = get_crops(region_num, plant_type_num) if plant_type_num else []
    
    if display == 'sorts' and crop_num:
        sorts = get_sorts(region_num, crop_num) if crop_num else []
        pests = []
    else:
        pests = get_crop_pests(crop_num) if crop_num else []
        sorts = []

    user_num = session.get('user_num')
    favourites = get_user_favourites(user_num) if user_num else []

    return render_template('catalog.html',
                           subjects=subjects,
                           region=region,
                           plant_types=plant_types,
                           crops=crops,
                           sorts=sorts,
                           favourites=favourites,
                           pests=pests,
                           selected_subject=subject_num,
                           selected_region=region_num,
                           selected_plant_type=plant_type_num,
                           selected_crop=crop_num,
                           selected_plant=plant_num,
                           selected_display=display)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        gender = request.form.get('gender')
        password = request.form.get('password')
        repassword = request.form.get('repassword')
        if password != repassword:
            flash('Пароли не совпадают.', 'danger')
            return render_template('register.html')
        if register_user(username, password, email, mobile, gender):
            user = get_user_by_email(email)
            session['email'] = user['user_email']
            session['username'] = user['user_name']
            session['user_num'] = user['user_num']
            flash('Вы успешно зарегистрированы и вошли в систему.', 'success')
            return redirect(url_for('cabinet'))
        else:
            flash('Регистрация не удалась. Имя пользователя уже занято.', 'danger')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = authenticate_user(email, password)
        if user:
            session['email'] = user['user_email']
            session['username'] = user['user_name']
            session['user_num'] = user['user_num']
            flash('Вы вошли в систему успешно.', 'success')
            if get_agronomist_by_user(session['user_num']):
                return redirect(url_for('agronomist_cabinet'))
            return redirect(url_for('cabinet'))
        else:
            flash('Неверный логин или пароль.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы.', 'success')
    return redirect(url_for('login'))

@app.route('/forum')
def forum():
    articles = get_articles()
    return render_template('forum.html', articles=articles)

@app.route('/topics', methods=['POST'])
def add_topic():
    if 'user_num' not in session:
        flash('Пожалуйста, войдите, чтобы создать топик.', 'warning')
        return redirect(url_for('login'))
    title = request.form.get('title')
    content = request.form.get('content')
    user_num = session['user_num']
    try:
        add_article(title, content, user_num)
        flash('Топик успешно создан.', 'success')
    except Exception:
        flash('Не удалось создать топик.', 'danger')
    return redirect(url_for('forum'))

@app.route('/sortinfo')
def sortinfo():
    plant_num = request.args.get('plant', type=int)
    region_num = request.args.get('region', type=int)
    session['last_region'] = region_num
    if not plant_num or not region_num:
        flash('Пожалуйста, выберите сорт и регион.', 'warning')
        return redirect(request.referrer or url_for('catalog'))
    sort = get_sort_details(region_num, plant_num)
    user_num = session.get('user_num')
    favourites = get_user_favourites(user_num) if user_num else []
    return render_template('sortinfo.html', sort=sort, favourites=favourites, selected_region=region_num)

@app.route('/pestinfo')
def pestinfo():
    crop_num = request.args.get('crop', type=int)
    pest_num = request.args.get('pest', type=int)
    if not crop_num or not pest_num:
        flash('Пожалуйста, выберите культуру и вредителя.', 'warning')
        return redirect(request.referrer or url_for('catalog'))
    detail = get_crop_pest_details(crop_num, pest_num)
    return render_template('pestinfo.html', detail=detail)

@app.route('/forumposts/<int:article_num>')
def forumposts(article_num):
    article = get_article(article_num)
    if not article:
        flash('Топик не найден.', 'warning')
        return redirect(url_for('forum'))
    comments = get_comments(article_num)
    return render_template('forum_posts.html', article=article, comments=comments)

@app.route('/topics/<int:article_num>/replies', methods=['POST'])
def add_comment_route(article_num):
    if 'user_num' not in session:
        flash('Пожалуйста, войдите, чтобы добавить комментарий.', 'warning')
        return redirect(url_for('login'))
    content = request.form.get('content')
    user_num = session['user_num']
    try:
        add_comment(article_num, content, user_num)
        flash('Комментарий добавлен.', 'success')
    except Exception:
        flash('Не удалось добавить комментарий.', 'danger')
    return redirect(url_for('forumposts', article_num=article_num))

@app.route('/cabinet')
def cabinet():
    user_num = session.get('user_num')
    if not user_num:
        flash('Пожалуйста, войдите, чтобы просмотреть кабинет.', 'warning')
        return redirect(url_for('login'))
    view = request.args.get('view', 'favourites')
    favourite_plants = get_favourite_plants(user_num)
    user_articles = get_user_articles(user_num) if view == 'articles' else []
    selected_region = session.get('last_region')
    return render_template('cabinet.html', favourite_plants=favourite_plants, user_articles=user_articles, view=view,
                           selected_region=selected_region)

@app.route('/favourite', methods=['POST'])
def toggle_favourite():
    if 'user_num' not in session:
        flash('Пожалуйста, войдите, чтобы управлять избранным.', 'warning')
        return redirect(url_for('login'))
    plant_num = request.form.get('plant_num', type=int)
    region_num = request.form.get('region', type=int)
    session['last_region'] = region_num
    action = request.form.get('action')
    user_num = session['user_num']
    if action == 'add':
        add_favourite(user_num, plant_num)
    elif action == 'remove':
        remove_favourite(user_num, plant_num)
    return redirect(request.referrer or url_for('catalog'))


def agronomist_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_num' not in session:
            flash("Сначала войдите в систему.", "warning")
            return redirect(url_for('login'))
        if not get_agronomist_by_user(session['user_num']):
            flash("У вас нет прав агронома.", "danger")
            return redirect(url_for('cabinet'))
        return f(*args, **kwargs)
    return decorated


@app.route('/agronomist')
@agronomist_required
def agronomist_cabinet():
    user_num = session['user_num']
    agr = get_agronomist_by_user(user_num)
    region_num = agr['fk_region_num']

    plant_types = get_all_plant_types()
    crops = get_all_crops()
    sorts = get_all_sorts()
    region_crops = get_crops_for_region(region_num)
    region_sorts = get_sorts_for_region(region_num)
    pests = get_pests()
    crop_pests = {crop['crop_num']: get_crop_pests(crop['crop_num']) for crop in region_crops}

    return render_template('agronomist_cabinet.html',
                           agronomist=agr,
                           plant_types=plant_types,
                           crops=crops,
                           sorts=sorts,
                           region_crops=region_crops,
                           region_sorts=region_sorts,
                           pests=pests,
                           crop_pests=crop_pests)


@app.route('/agronomist/add_crop', methods=['POST'])
@agronomist_required
def agr_add_crop():
    crop_name = request.form['crop_name']
    plant_type_num = int(request.form['plant_type_num'])
    user_num = session['user_num']
    region_num = get_agronomist_by_user(user_num)['fk_region_num']
    region_feature = request.form.get('region_feature', '')
    region_date_seed = request.form.get('region_date_seed', '')
    region_date_harvest = request.form.get('region_date_harvest', '')
    try:
        add_crop_with_region(region_num, crop_name, plant_type_num, region_feature, region_date_seed, region_date_harvest)
        flash('Культура и её региональные параметры успешно добавлены.', 'success')
    except Exception:
        flash('Не удалось создать культуру с региональными параметрами.', 'danger')
    return redirect(url_for('agronomist_cabinet'))

@app.route('/agronomist/add_sort', methods=['POST'])
@agronomist_required
def agr_add_sort():
    plant_name = request.form['plant_name']
    fk_crop_num = int(request.form['fk_crop_num'])
    plant_feature = request.form.get('plant_feature', '')
    plant_image_url = request.form.get('plant_image_url', '')
    add_sort(plant_name, fk_crop_num, plant_feature, plant_image_url)
    flash('Сорт добавлен.', 'success')
    return redirect(url_for('agronomist_cabinet'))

@app.route('/agronomist/add_crop_region', methods=['POST'])
@agronomist_required
def agr_add_crop_region_route():
    user_num = session['user_num']
    region_num = get_agronomist_by_user(user_num)['fk_region_num']
    crop_num = int(request.form['crop_num'])
    region_feature = request.form['region_feature']
    add_crop_region(region_num, crop_num, region_feature)
    flash('Региональные параметры культуры добавлены.', 'success')
    return redirect(url_for('agronomist_cabinet'))

@app.route('/agronomist/update_crop_region', methods=['POST'])
@agronomist_required
def agr_update_crop_region_route():
    user_num = session['user_num']
    region_num = get_agronomist_by_user(user_num)['fk_region_num']
    crop_num = int(request.form['crop_num'])
    region_feature = request.form['region_feature']
    update_crop_region(region_num, crop_num, region_feature)
    flash('Региональные параметры культуры обновлены.', 'success')
    return redirect(url_for('agronomist_cabinet'))

@app.route('/agronomist/delete_crop_region', methods=['POST'])
@agronomist_required
def agr_delete_crop_region_route():
    user_num = session['user_num']
    region_num = get_agronomist_by_user(user_num)['fk_region_num']
    crop_num = int(request.form['crop_num'])
    delete_crop_region(region_num, crop_num)
    flash('Региональные параметры культуры удалены.', 'success')
    return redirect(url_for('agronomist_cabinet'))

@app.route('/agronomist/add_sort_region', methods=['POST'])
@agronomist_required
def agr_add_sort_region_route():
    user_num = session['user_num']
    region_num = get_agronomist_by_user(user_num)['fk_region_num']
    plant_num = int(request.form['plant_num'])
    region_feature = request.form['region_feature']
    add_sort_region(region_num, plant_num, region_feature)
    flash('Региональные параметры сорта добавлены.', 'success')
    return redirect(url_for('agronomist_cabinet'))

@app.route('/agronomist/update_sort_region', methods=['POST'])
@agronomist_required
def agr_update_sort_region_route():
    user_num = session['user_num']
    region_num = get_agronomist_by_user(user_num)['fk_region_num']
    plant_num = int(request.form['plant_num'])
    region_feature = request.form['region_feature']
    update_sort_region(region_num, plant_num, region_feature)
    flash('Региональные параметры сорта обновлены.', 'success')
    return redirect(url_for('agronomist_cabinet'))

@app.route('/agronomist/delete_sort_region', methods=['POST'])
@agronomist_required
def agr_delete_sort_region_route():
    user_num = session['user_num']
    region_num = get_agronomist_by_user(user_num)['fk_region_num']
    plant_num = int(request.form['plant_num'])
    delete_sort_region(region_num, plant_num)
    flash('Региональные параметры сорта удалены.', 'success')
    return redirect(url_for('agronomist_cabinet'))

@app.route('/agronomist/add_pest', methods=['POST'])
@agronomist_required
def agr_add_pest():
    pest_name = request.form['pest_name']
    pest_feature = request.form.get('pest_feature', '')
    add_pest(pest_name, pest_feature)
    flash('Вредитель добавлен.', 'success')
    return redirect(url_for('agronomist_cabinet'))

@app.route('/agronomist/add_crop_pest', methods=['POST'])
@agronomist_required
def agr_add_crop_pest_route():
    crop_num = int(request.form['crop_num'])
    pest_num = int(request.form['pest_num'])
    add_crop_pest(crop_num, pest_num)
    flash('Связь культура–вредитель добавлена.', 'success')
    return redirect(url_for('agronomist_cabinet'))

@app.route('/agronomist/update_crop_pest', methods=['POST'])
@agronomist_required
def agr_update_crop_pest_route():
    crop_num = int(request.form['crop_num'])
    old_pest_num = int(request.form['old_pest_num'])
    new_pest_num = int(request.form['new_pest_num'])
    update_crop_pest(crop_num, old_pest_num, new_pest_num)
    flash('Связь культура–вредитель обновлена.', 'success')
    return redirect(url_for('agronomist_cabinet'))

@app.route('/agronomist/delete_crop_pest', methods=['POST'])
@agronomist_required
def agr_delete_crop_pest_route():
    crop_num = int(request.form['crop_num'])
    pest_num = int(request.form['pest_num'])
    delete_crop_pest(crop_num, pest_num)
    flash('Связь культура–вредитель удалена.', 'success')
    return redirect(url_for('agronomist_cabinet'))

@app.route('/articles/<int:article_num>/delete', methods=['POST'])
def delete_article_route(article_num):
    if 'user_num' not in session:
        flash('Пожалуйста, войдите, чтобы удалить статью.', 'warning')
        return redirect(url_for('login'))
    user_num = session['user_num']
    user_articles = get_user_articles(user_num)
    if article_num not in [a['article_num'] for a in user_articles]:
        flash('Нет доступа к удалению этой статьи.', 'danger')
        return redirect(url_for('cabinet', view='articles'))
    try:
        delete_article(article_num)
        flash('Статья удалена.', 'success')
    except Exception:
        flash('Не удалось удалить статью.', 'danger')
    return redirect(url_for('cabinet', view='articles'))

@app.route('/articles/<int:article_num>/edit', methods=['GET', 'POST'])
def edit_article_route(article_num):
    if 'user_num' not in session:
        flash('Пожалуйста, войдите, чтобы редактировать статью.', 'warning')
        return redirect(url_for('login'))
    user_num = session['user_num']
    user_articles = get_user_articles(user_num)
    if article_num not in [a['article_num'] for a in user_articles]:
        flash('Нет доступа к редактированию этой статьи.', 'danger')
        return redirect(url_for('cabinet', view='articles'))
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        try:
            update_article(article_num, title, content)
            flash('Статья обновлена.', 'success')
            return redirect(url_for('cabinet', view='articles'))
        except Exception:
            flash('Не удалось обновить статью.', 'danger')
            return redirect(url_for('cabinet', view='articles'))
    article = next((a for a in user_articles if a['article_num'] == article_num), None)
    return render_template('edit_article.html', article=article)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=(os.environ.get("FLASK_ENV")=="development"))
