from datetime import datetime, timezone
from app.models import User, Arduino, Location, UVRegister, Category, Components, Arduino_Components
from app import db


def data_example():
    # --- Criar um Usuário ---
    user = User(
        username = "Morgado",
        email    = "arthurmorgadoteixeira@exemplo.com",
        about_me = "Usuário de teste."
    )
    user.set_password("cripto_senha_hehe")  # Senha criptografada
    db.session.add(user)
    db.session.commit()  # Persiste o usuário para gerar o ID

    # --- Criar um Arduino ---
    arduino = Arduino(
        user_id      = user.id,
        register_day = datetime.now(timezone.utc)
    )
    db.session.add(arduino)
    db.session.commit()

    # --- Criar Localização ---
    location = Location(
        country   = "Brasil",
        state     = "ES",
        city      = "Vila Velha",
        latitude  = -20.3305,
        longitude = -40.2922
    )
    db.session.add(location)
    db.session.commit()

    # --- Criar Registro UV ---
    uv_register = UVRegister(
        arduino_id    = arduino.id,
        register_date = datetime.now(timezone.utc),
        location_id   = location.id,
        frequency     = 12.0  # Valor de exemplo
    )
    db.session.add(uv_register)

    # --- Criar Componentes (opcional) ---
    component = Components(
        name        = "GUVA-S12D",
        category_id = 1,
        price       =120.0,
        especifies  = "Sensor UV de 240-370nm"
    )
    db.session.add(component)
    db.session.commit()  # Persiste tudo de uma vez

    arduino_component = Arduino_Components(
        arduino_id   = arduino.id,
        component_id = component.id 
    )

    db.session.add(arduino_component)
    db.session.commit()

    print("Dados inseridos com sucesso!")
