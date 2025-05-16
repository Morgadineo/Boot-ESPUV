# app/routes.py
from urllib.parse import urlsplit
from app          import app, db
from flask        import render_template, flash, redirect, url_for, request
from app.forms    import LoginForm, RegistrationForm, EditProfileForm
from app.models   import User, UVRegister, Arduino, Location, Arduino_Components, Components, Category, Post
from datetime     import datetime, timezone, timedelta, date
from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa
from sqlalchemy import func
from flask_wtf.csrf import validate_csrf
from wtforms import ValidationError

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
    
    # Posts do usuário
    posts = db.session.scalars(
        sa.select(Post)
        .where(Post.user_id == user.id)
        .order_by(Post.timestamp.desc())
    ).all()
    
    # Consulta para Arduinos do usuário
    arduinos = db.session.scalars(
        sa.select(Arduino)
        .where(Arduino.user_id == user.id)
        .order_by(Arduino.register_day.desc())
    ).all()
    
    # Para cada Arduino, buscar seus componentes
    arduinos_componentes = []
    for arduino in arduinos:
        componentes = db.session.execute(
            sa.select(
                Arduino_Components,
                Components,
                Category
            )
            .join(Components, Arduino_Components.component_id == Components.id)
            .join(Category, Components.category_id == Category.id)
            .where(Arduino_Components.arduino_id == arduino.id)
        ).all()
        arduinos_componentes.append((arduino, componentes))
    
    return render_template('user.html',
                         user=user,
                         posts=posts,
                         arduinos_componentes=arduinos_componentes)

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
        try:
            # Valida o token CSRF
            validate_csrf(request.form.get('csrf_token'))
            
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
            flash('Arduino cadastrado com sucesso!', 'success')
            return redirect(url_for('assembly_arduinos'))
        
        except ValidationError:
            db.session.rollback()
            flash('Token CSRF inválido. Por favor, tente novamente.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao montar Arduino: {str(e)}', 'danger')
    
    user_arduinos = Arduino.query.filter_by(user_id=current_user.id).all()
    
    return render_template('assembly_arduinos.html', 
                         categories_with_components=categories_with_components,
                         user_arduinos=user_arduinos)

@app.route('/editar_registro')
def editar_registro():
    return render_template('editar_registro.html', exibir_botao_voltar=True)

@app.route('/estatistica')
@login_required
def estatistica():
    # Estatísticas básicas
    uv_registers_count = UVRegister.query.count()
    average_frequency = db.session.query(db.func.avg(UVRegister.frequency)).scalar() or 0
    active_arduinos_count = Arduino.query.count()
    
    top_locations = db.session.query(
        Location,
        db.func.count(UVRegister.id).label('records_count'),
        db.func.avg(UVRegister.frequency).label('average_frequency')
    ).join(UVRegister, Location.id == UVRegister.location_id)\
     .group_by(Location.id)\
     .order_by(db.desc('records_count'))\
     .limit(5).all()
    
    recent_registers = db.session.query(
        UVRegister,
        Location
    ).join(Location, UVRegister.location_id == Location.id)\
     .order_by(UVRegister.register_date.desc())\
     .limit(10).all()
    
    # Dados para o gráfico
    chart_data = db.session.query(
        db.func.date(UVRegister.register_date).label('day'),
        db.func.avg(UVRegister.frequency).label('avg_frequency')
    ).group_by('day')\
     .order_by('day')\
     .limit(30).all()
    
    chart_labels = [str(data.day) for data in chart_data]
    chart_values = [float(data.avg_frequency) for data in chart_data]
    
    return render_template('estatistica.html',
                         uv_registers_count=uv_registers_count,
                         average_frequency=average_frequency,
                         active_arduinos_count=active_arduinos_count,
                         top_locations=top_locations,
                         recent_registers=recent_registers,
                         chart_labels=chart_labels,
                         chart_values=chart_values)

@app.route('/manual')
@login_required
def manual():
    return render_template('manual.html', title='Manual', exibir_botao_voltar=True)

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit() 

@app.route('/excluir_arduino/<int:arduino_id>', methods=['POST'])
@login_required
def excluir_arduino(arduino_id):
    try:
        # Verifica o token CSRF
        validate_csrf(request.form.get('csrf_token'))
    except ValidationError:
        flash('Token CSRF inválido ou expirado', 'danger')
        return redirect(url_for('user', username=current_user.username))
    
    # Restante da lógica de exclusão...
    arduino = db.session.scalar(
        sa.select(Arduino)
        .where(Arduino.id == arduino_id, Arduino.user_id == current_user.id)
    )
    
    if not arduino:
        flash('Arduino não encontrado ou você não tem permissão para excluí-lo', 'danger')
        return redirect(url_for('user', username=current_user.username))
    
    try:
        # Primeiro exclui os componentes associados
        db.session.execute(
            sa.delete(Arduino_Components)
            .where(Arduino_Components.arduino_id == arduino_id)
        )
        
        # Depois exclui o Arduino
        db.session.execute(
            sa.delete(Arduino)
            .where(Arduino.id == arduino_id)
        )
        
        db.session.commit()
        flash('Arduino excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir Arduino: {str(e)}', 'danger')
    
    return redirect(url_for('user', username=current_user.username))

@app.route('/arduino/<int:arduino_id>')
@login_required
def arduino_detalhes(arduino_id):
    # Corrigindo para usar first() ou one() em vez de filter()
    arduino = db.session.query(Arduino)\
             .filter(Arduino.id == arduino_id, Arduino.user_id == current_user.id)\
             .first()
    
    if not arduino:
        flash('Arduino não encontrado ou você não tem permissão para acessá-lo', 'danger')
        return redirect(url_for('user', username=current_user.username))
    
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
    
    total = sum(ac.quantity * c.price for ac, c, _ in components)
    
    return render_template('arduino_detalhes.html',
                         arduino=arduino,
                         components=components,
                         total=total)

@app.route('/editar_arduino/<int:arduino_id>', methods=['GET', 'POST'])
@login_required
def editar_arduino(arduino_id):
    # Verifica se o Arduino pertence ao usuário atual
    arduino = db.session.scalar(
        sa.select(Arduino)
        .where(Arduino.id == arduino_id, Arduino.user_id == current_user.id)
    )
    
    if not arduino:
        flash('Arduino não encontrado ou você não tem permissão para editá-lo', 'danger')
        return redirect(url_for('user', username=current_user.username))

    # Busca todas as categorias e componentes disponíveis
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

    # Busca os componentes já selecionados para este Arduino
    selected_components = db.session.query(
        Arduino_Components.component_id,
        Arduino_Components.quantity
    ).filter(
        Arduino_Components.arduino_id == arduino_id
    ).all()
    
    selected_components_dict = {sc.component_id: sc.quantity for sc in selected_components}

    if request.method == 'POST':
        try:
            # Atualiza a data de cadastro se fornecida
            new_date = request.form.get('register_day')
            if new_date:
                arduino.register_day = datetime.strptime(new_date, '%Y-%m-%d')

            # Processa os componentes do formulário
            for category_data in categories_with_components:
                for component in category_data['components']:
                    quantity = request.form.get(f'component_{component.id}', 0, type=int)
                    
                    # Se já existe, atualiza a quantidade
                    if component.id in selected_components_dict:
                        if quantity > 0:
                            db.session.execute(
                                sa.update(Arduino_Components)
                                .where(Arduino_Components.arduino_id == arduino_id)
                                .where(Arduino_Components.component_id == component.id)
                                .values(quantity=quantity)
                            )
                        else:
                            db.session.execute(
                                sa.delete(Arduino_Components)
                                .where(Arduino_Components.arduino_id == arduino_id)
                                .where(Arduino_Components.component_id == component.id)
                            )
                    # Se não existe e quantidade > 0, adiciona novo
                    elif quantity > 0:
                        new_component = Arduino_Components(
                            arduino_id=arduino_id,
                            component_id=component.id,
                            quantity=quantity
                        )
                        db.session.add(new_component)

            db.session.commit()
            flash('Arduino atualizado com sucesso!', 'success')
            return redirect(url_for('arduino_detalhes', arduino_id=arduino_id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar Arduino: {str(e)}', 'danger')

    return render_template('editar_arduino.html',
                         arduino=arduino,
                         categories_with_components=categories_with_components,
                         selected_components=selected_components_dict)
