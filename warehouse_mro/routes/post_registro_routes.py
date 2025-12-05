from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from models.bultos import Bulto
from models.post_registro import PostRegistro
from models import db

post_bp = Blueprint("post", __name__, url_prefix="/post")

# FORMULARIO DE POST REGISTRO
@post_bp.route("/registrar/<int:bulto_id>", methods=["GET", "POST"])
@login_required
def registrar(bulto_id):
    bulto = Bulto.query.get_or_404(bulto_id)

    if request.method == "POST":
        real = int(request.form["cantidad_real"])
        diferencia = real - bulto.cantidad

        nuevo = PostRegistro(
            bulto_id=bulto.id,
            codigo_material=bulto.codigo,
            cantidad_sistema=bulto.cantidad,
            cantidad_real=real,
            diferencia=diferencia,
            registrado_por=current_user.username
        )

        db.session.add(nuevo)
        db.session.commit()

        flash("Post-registro guardado correctamente", "success")
        return redirect(url_for("post.historial"))

    return render_template("post/registrar.html", bulto=bulto)


# LISTA DE POST-REGISTROS
@post_bp.route("/historial")
@login_required
def historial():
    registros = PostRegistro.query.order_by(PostRegistro.fecha_registro.desc()).all()
    return render_template("post/historial.html", registros=registros)
