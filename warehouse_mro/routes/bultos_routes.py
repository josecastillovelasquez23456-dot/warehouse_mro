from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash
from flask_login import login_required, current_user
from models.bultos import Bulto, PostRegistro
from models import db
from datetime import datetime
import pandas as pd
import io

bultos_bp = Blueprint("bultos", __name__, url_prefix="/bultos")


# =====================================================================
#   REGISTRO DE NUEVOS BULTOS (NECESARIO PARA EL SIDEBAR)
# =====================================================================
@bultos_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_bulto():

    if request.method == "POST":

        cantidad = int(request.form.get("cantidad"))
        chofer = request.form.get("chofer")
        placa = request.form.get("placa")
        fecha_hora = request.form.get("fecha_hora")
        observacion = request.form.get("observacion")

        nuevo_bulto = Bulto(
            cantidad=cantidad,
            chofer=chofer,
            placa=placa,
            fecha_hora=datetime.fromisoformat(fecha_hora),
            observacion=observacion,
            creado_en=datetime.now()
        )

        db.session.add(nuevo_bulto)
        db.session.commit()

        flash("Bulto registrado correctamente.", "success")
        return redirect(url_for("bultos.new_bulto"))

    return render_template("bultos/form_bulto.html")


# =====================================================================
#   LISTA + FILTROS + KPIs
# =====================================================================
@bultos_bp.route("/list")
@login_required
def list_bultos():

    chofer = request.args.get("chofer", "").strip()
    placa = request.args.get("placa", "").strip()
    desde = request.args.get("desde", "").strip()
    hasta = request.args.get("hasta", "").strip()

    query = Bulto.query

    if chofer:
        query = query.filter(Bulto.chofer.ilike(f"%{chofer}%"))
    if placa:
        query = query.filter(Bulto.placa.ilike(f"%{placa}%"))
    if desde:
        query = query.filter(Bulto.fecha_hora >= datetime.strptime(desde, "%Y-%m-%d"))
    if hasta:
        h = datetime.strptime(hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(Bulto.fecha_hora <= h)

    bultos = query.order_by(Bulto.fecha_hora.asc()).all()

    total_bultos = sum(b.cantidad for b in bultos)
    bultos_hoy = sum(b.cantidad for b in bultos if b.fecha_hora.date() == datetime.today().date())
    total_trailers = len(set(b.placa for b in bultos if b.placa))

    return render_template(
        "bultos/list.html",
        bultos=bultos,
        total_bultos=total_bultos,
        bultos_hoy=bultos_hoy,
        total_trailers=total_trailers,
    )


# =====================================================================
#   LISTA PARA HACER CONTEO REAL (POST-REGISTRO)
# =====================================================================
@bultos_bp.route("/contar")
@login_required
def contar_bultos():

    bultos = Bulto.query.order_by(Bulto.fecha_hora.desc()).all()

    return render_template(
        "bultos/contar_bultos.html",
        bultos=bultos
    )


# =====================================================================
#   FORMULARIO DE POST–REGISTRO
# =====================================================================
@bultos_bp.route("/post/<int:bulto_id>", methods=["GET", "POST"])
@login_required
def post_registro(bulto_id):

    bulto = Bulto.query.get_or_404(bulto_id)

    if request.method == "POST":

        real = int(request.form["cantidad_real"])
        diferencia = real - bulto.cantidad

        nuevo = PostRegistro(
            bulto_id=bulto.id,
            cantidad_sistema=bulto.cantidad,
            cantidad_real=real,
            diferencia=diferencia,
            observacion=request.form.get("observacion", ""),
            registrado_por=current_user.username,
            fecha_registro=datetime.utcnow()
        )

        db.session.add(nuevo)
        db.session.commit()

        flash("Conteo registrado correctamente.", "success")
        return redirect(url_for("bultos.historial_post"))

    return render_template("bultos/post_registro.html", bulto=bulto)


# =====================================================================
#   HISTORIAL DE POST–REGISTROS
# =====================================================================
@bultos_bp.route("/historial")
@login_required
def historial_post():

    historial = (
        PostRegistro
        .query
        .order_by(PostRegistro.fecha_registro.desc())
        .all()
    )

    return render_template("bultos/historial_post.html", historial=historial)
