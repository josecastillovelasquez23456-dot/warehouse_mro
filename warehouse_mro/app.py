from flask import Flask, redirect, url_for
from flask_login import LoginManager
from config import Config
from models import db
from models.user import User
from routes import register_blueprints
import os

# ==========================================================
# LOGIN MANAGER
# ==========================================================
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==========================================================
# CREATE_APP (FACTORÍA PRINCIPAL)
# ==========================================================
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ======================================================
    # 🔥 FIX #1: Permitir subida de archivos (Excel)
    # ======================================================
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB
    app.config["UPLOAD_EXTENSIONS"] = [".xlsx", ".xls"]

    # Carpeta de subidas segura para Render / Koyeb
    UPLOAD_ROOT = os.path.join(app.root_path, "uploads")
    REPORT_ROOT = os.path.join(app.root_path, "reports")

    os.makedirs(UPLOAD_ROOT, exist_ok=True)
    os.makedirs(REPORT_ROOT, exist_ok=True)

    # Reemplazamos rutas en Config dinámicamente
    app.config["UPLOAD_FOLDER"] = UPLOAD_ROOT
    app.config["REPORT_FOLDER"] = REPORT_ROOT

    # ======================================================
    # Inicializar extensiones
    # ======================================================
    db.init_app(app)
    login_manager.init_app(app)

    # Registrar rutas / blueprints
    register_blueprints(app)

    # ======================================================
    # Filtro de fecha
    # ======================================================
    @app.template_filter("format_fecha")
    def format_fecha(value):
        try:
            return value.strftime("%d/%m/%Y %H:%M")
        except:
            return value

    # ======================================================
    # Ruta raíz → Login
    # ======================================================
    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    # ======================================================
    # Crear tablas + usuario OWNER
    # ======================================================
    with app.app_context():
        print("\n>>> Creando tablas si no existen...")
        db.create_all()
        db.session.commit()
        print(">>> Tablas listas.\n")

        # Usuario Owner por defecto
        owner_email = "jose.castillo@sider.com.pe"
        owner_username = "JCASTI15"
        owner_password = "Admin123#"

        owner = User.query.filter_by(email=owner_email).first()

        if not owner:
            print(">>> Creando usuario OWNER...")

            new_owner = User(
                username=owner_username,
                email=owner_email,
                role="owner",
                status="active",
                email_confirmed=True,
            )
            new_owner.set_password(owner_password)

            db.session.add(new_owner)
            db.session.commit()

            print(">>> OWNER creado correctamente.")
        else:
            owner.role = "owner"
            owner.email_confirmed = True
            db.session.commit()
            print(">>> OWNER verificado.")

    return app


# ==========================================================
# EJECUTAR LOCAL
# ==========================================================
if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
