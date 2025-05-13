# app/routes.py
from urllib.parse import urlsplit
from app          import app, db
from flask        import render_template, flash, redirect, url_for, request
from app.forms    import LoginForm, RegistrationForm, EditProfileForm
from app.models   import User, UVRegister, Arduino, Location, Arduino_Components, Components, Category
from datetime     import datetime, timezone, timedelta, date

from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa
from sqlalchemy import func


@app.route('/')
@app.route('/index')
@login_required
def index():
    registers = db.session.query(UVRegister, Location)\
                .join(Location, UVRegister.location_id == Location.id).all()

    hoje = datetime.now()
    inicio_semana = (hoje - timedelta(days=hoje.weekday())).strftime('%Y-%m-%d')

    # Consulta para contar assembly_arduinos por dia
    assembly_arduinos_por_dia = db.session.query(
        func.date(UVRegister.register_date),
        func.count(UVRegister.id)
    ).filter(
        UVRegister.register_date >= inicio_semana
    ).group_by(
        func.date(UVRegister.register_date)
    ).all()

    # Prepara os dados para o gráfico
    dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    dados_grafico = {d: 0 for d in dias_semana}

    for dia, total in assembly_arduinos_por_dia:
        dia = datetime.strptime(dia, "%Y-%m-%d").date()
        nome_dia = dias_semana[dia.weekday()]
        dados_grafico[nome_dia] = total

    labels = [label for label in dados_grafico.keys()]
    values = [value for value in dados_grafico.values()]

    return render_template('index.html', registers=registers, labels=labels, values=values)

@app.route('/login', methods=('GET', 'POST'))
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password (form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))

        login_user(user, remember=form.remember_me.data)

        next_page = request.args.get('next')
        if next_page:
            parsed_url = urlsplit(next_page)
            if parsed_url.netloc == '' and parsed_url.path.startswith('/'):
                return redirect(next_page) 
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username = form.username.data, email = form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form, exibir_botao_voltar=True)

@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    posts = [
        {'author': user, 'body': 'Test post #1'},
        {'author': user, 'body': 'Test post #2'}
    ]
    return render_template('user.html', user=user, posts=posts, exibir_botao_voltar=True)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)

@app.route('/assembly_arduinos', methods=['GET', 'POST'])
@login_required
def assembly_arduinos():
    categories = db.session.query(Category)\
             .join(Components, Category.id == Components.category_id)\
             .order_by(Category.name)\
             .all()
    
    categories_with_components = []
    for category in categories:
        components = Components.query.filter_by(category_id=category.id).all()
        categories_with_components.append({
            'category': category,
            'components': components
        })
    
    if request.method == 'POST':
        # Criar novo Arduino
        new_arduino = Arduino(
            user_id=current_user.id,
            register_day=datetime.now(timezone.utc)
        )
        db.session.add(new_arduino)
        db.session.flush()
        
        for category_data in categories_with_components:
            for component in category_data['components']:
                quantity = request.form.get(f'component_{component.id}', 0, type=int)
                if quantity > 0:
                    arduino_component = Arduino_Components(
                        arduino_id=new_arduino.id,
                        component_id=component.id,
                        quantity=quantity
                    )
                    db.session.add(arduino_component)
        
        db.session.commit()
        flash('Arduino cadastrado com sucesso!')
        return redirect(url_for('assembly_arduinos'))
    
    user_arduinos = Arduino.query.filter_by(user_id=current_user.id).all()
    
    return render_template('assembly_arduinos.html', 
                         categories_with_components=categories_with_components,
                         user_arduinos=user_arduinos)

@app.route('/arduino/<int:arduino_id>')
@login_required
def arduino_detalhes(arduino_id):
    # Verifica se o Arduino pertence ao usuário atual
    arduino = db.session.query(Arduino)\
             .filter(Arduino.id == arduino_id, Arduino.user_id == current_user.id)
    
    # Busca os componentes com join em Components e Category
    components = db.session.query(
        Arduino_Components,
        Components,
        Category
    ).join(
        Components, Arduino_Components.component_id == Components.id
    ).join(
        Category, Components.category_id == Category.id
    ).filter(
        Arduino_Components.arduino_id == arduino_id
    ).all()
    
    # Calcula o total
    total = sum(ac.quantity * c.price for ac, c, _ in components)
    
    return render_template('arduino_detalhes.html',
                         arduino=arduino,
                         components=components,
                         total=total)

@app.route('/editar_registro')
def editar_registro():
    return render_template('editar_registro.html', exibir_botao_voltar=True)


@app.route('/estatistica')
@login_required
def estatistica():
    return render_template('estatistica.html', title='Estatisticas', exibir_botao_voltar=True)

@app.route('/manual')
@login_required
def manual():
    return render_template('manual.html', title='Manual', exibir_botao_voltar=True)

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit() 
