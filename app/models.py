from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy import DateTime, Integer
from app import db
from hashlib import md5
from werkzeug.security import (
        generate_password_hash, 
        check_password_hash)
from flask_login import UserMixin
from app import login

class User(UserMixin, db.Model):
    """
    Classe de modelo do usuário da platforma.

    id             : Identificador único do usuário.
    name           : Nome privado do usuário. Pode ser usado para cadastro.
    username       : Nome público do usuário (apelido/alias).
    password_hash: Senha criptografada do usuário.
    email          : Email do usuário. Pode ser usado para cadastro.
    """

    id             : so.Mapped[int] = so.mapped_column(primary_key = True, autoincrement = True)
    username       : so.Mapped[str] = so.mapped_column(sa.String(100)) # Não presente na modelagem.
    password_hash: so.Mapped[str] = so.mapped_column(sa.String(256))
    email          : so.Mapped[str] = so.mapped_column(sa.String(120))

    posts          : so.WriteOnlyMapped['Post'] = so.relationship(
        back_populates='author'
    )

    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return '<User: {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

class Post(db.Model):
    id       : so.Mapped[int]      = so.mapped_column(primary_key = True, autoincrement = True)
    body     : so.Mapped[str]      = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc)
    )
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)

    author: so.Mapped[User] = so.relationship(back_populates='posts')

    def __repr__(self):
        return '<Post {}>'.format(self.body)

class Arduino(db.Model):
    """
    Classe de modelo de um arduino pertencente a um usuário.
    Usuários cadastram arduinos que realizaram coletas de frequência.

    id          : Identificador único do arduino.
    user_id     : Identificador único do usuário que cadastrou o arduino.
    register_day: Dia de cadastro do arduino na plataforma.
    """

    id          : so.Mapped[int]      = so.mapped_column(primary_key = True, autoincrement = True)
    user_id     : so.Mapped[int]      = so.mapped_column(sa.ForeignKey(User.id),
                                               index = True)
    register_day: so.Mapped[datetime] = so.mapped_column(sa.DateTime)

    def __repr__(self):
        return f"<Arduino {self.id} -> User {self.user_id}>"

class Location(db.Model):
    """
    Classe de modelo de uma localização da qual o arduino coletou uma frequência UV.
    Não é a localização de onde o registro foi enviado a plataforma.

    id       : Identificador único da localização.
    country  : País da qual o arduino realizou a coleta.
    state    : Estado da qual o arduino realizou a coleta.
    city     : Cidade da qual o arduino realizou a coleta.
    longitude: Posição longitudinal do arduino quando fez a coleta.
    latitude : Posição latitudinal do arduino quando fez a coleta.

    """

    id       : so.Mapped[int]   = so.mapped_column(primary_key = True, autoincrement = True)
    country  : so.Mapped[str]   = so.mapped_column(sa.String(40))
    state    : so.Mapped[str]   = so.mapped_column(sa.String(40))
    city     : so.Mapped[str]   = so.mapped_column(sa.String(40))
    longitude: so.Mapped[float] = so.mapped_column()
    latitude : so.Mapped[float] = so.mapped_column()

    def __repr__(self) -> str:
        return f"<Location {self.id} -> {self.country} | {self.state} | {self.city}"

class UVRegister(db.Model):
    """
    Classe de modelo dos registros de frequências UV.

    id           : Identificador único de um registro
    arduino_id   : Identificador único do arduino que realizou a coleta.
    register_date: Data de COLETA da frequência pelo arduino.
    location_id  : Identificador único da localização de onde o arduino realizou a COLETA da frequência.
    frequency    : Frequência do raio UV coletada.
    """

    id           : so.Mapped[int]          = so.mapped_column(primary_key = True, autoincrement = True)
    arduino_id   : so.Mapped[int]          = so.mapped_column(sa.ForeignKey(Arduino.id))
    register_date: so.Mapped[sa.DateTime]  = so.mapped_column(sa.DateTime(timezone = True))
    location_id  : so.Mapped[int]          = so.mapped_column(sa.ForeignKey(Location.id))
    frequency    : so.Mapped[float]        = so.mapped_column()

    def __repr__(self) -> str:
        return f"<Registro UV {self.id} -> Frequência {self.frequency}"

class Category(db.Model):
    """
    Classe de modelo das categorias possíveis para um componente.
    
    id  : Identificador único da categoria.
    name: Nome da categoria. Exemplos: Sensor; LED; LCD; Microcontrolador.
    """

    id  : so.Mapped[int] = so.mapped_column(primary_key = True, autoincrement = True)
    name: so.Mapped[str] = so.mapped_column()


class Components(db.Model):
    """
    Classe de modelo dos componentes que podem ter em um arduino.

    id         : Identificador único do component.
    name       : Nome do componente. Exemplo: (GUVA S12-UV)
    category_id: Identificador único da categoria que o componente pertence.
    price      : Preço médio ou aproximado do componente.
    especifies : Texto com as especificações do componente.
    """

    id         : so.Mapped[int]   = so.mapped_column(primary_key = True, autoincrement = True)
    name       : so.Mapped[str]   = so.mapped_column(sa.String(30))
    category_id: so.Mapped[int]   = so.mapped_column(sa.ForeignKey(Category.id))
    price      : so.Mapped[float] = so.mapped_column()
    especifies : so.Mapped[str]   = so.mapped_column(sa.String(200))

class Arduino_Components(db.Model):
    """
    Classe de modelo de um arduino e seus componentes.
    Serve para armazenar os componenetes que formam um arduino registrado.

    arduino_id  : Identificador único do arduino.
    component_id: Identificador único do componente pertence a um arduino.
    """
    __tablename__ = "arduino_components"

    arduino_id  : so.Mapped[int] = so.mapped_column(sa.ForeignKey(Arduino.id), primary_key = True)
    component_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Components.id), primary_key = True)
    quantity    : so.Mapped[int] = so.mapped_column()

