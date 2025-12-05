from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models.bultos import Bulto, PostRegistro
from models import db
from datetime import datetime
import pandas as pd
import io
import calendar

bultos_bp = Blueprint("bultos", __name__, url_prefix="/bultos")


# =====================================================================
#   REGISTRO DE BULTOS  (FORMULARIO)
# =====================================================================
@bultos_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_bulto():
    if request.method == "POST":
        try:
            cantidad = int(request.form.get("cantidad", "0"))
        except ValueError:
            cantidad = 0

        chofer = request.form.get("chofer", "").strip()
        placa = request.form.get("placa", "").strip()
        fecha_hora_raw = request.form.get("fecha_hora", "").strip()
        observacion = request.form.get("observacion", "").strip()

        # Si no viene fecha, se usa ahora
        if fecha_hora_raw:
            # HTML datetime-local → "YYYY-MM-DDTHH:MM"
            try:
                fecha_hora = datetime.fromisoformat(fecha_hora_raw)
            except ValueError:
                fecha_hora = datetime.utcnow()
        else:
            fecha_hora = datetime.utcnow()

        nuevo_bulto = Bulto(
            cantidad=cantidad,
            chofer=chofer,
            placa=placa,
            fecha_hora=fecha_hora,
            observacion=observacion,
            creado_en=datetime.utcnow()
        )

        db.session.add(nuevo_bulto)
        db.session.commit()

        flash("Bulto registrado correctamente.", "success")
        return redirect(url_for("bultos.new_bulto"))

    return render_template("bultos/form_bulto.html")


# =====================================================================
#   LISTA + KPIs + DATOS PARA GRÁFICAS
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
        try:
            desde_dt = datetime.strptime(desde, "%Y-%m-%d")
            query = query.filter(Bulto.fecha_hora >= desde_dt)
        except ValueError:
            pass
    if hasta:
        try:
            hasta_dt = datetime.strptime(hasta, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            query = query.filter(Bulto.fecha_hora <= hasta_dt)
        except ValueError:
            pass

    bultos = query.order_by(Bulto.fecha_hora.asc()).all()

    # ================== KPIs PRINCIPALES ==================
    total_bultos = sum(b.cantidad for b in bultos)
    hoy = datetime.today().date()
    bultos_hoy = sum(b.cantidad for b in bultos if b.fecha_hora.date() == hoy)
    total_trailers = len({b.placa for b in bultos if b.placa})

    # ================== GRÁFICO: BULTOS POR DÍA ==================
    graf_dia = {}
    for b in bultos:
        clave = b.fecha_hora.strftime("%d-%m")
        graf_dia[clave] = graf_dia.get(clave, 0) + b.cantidad

    dias = []
    bultos_dias = []
    for d, v in sorted(graf_dia.items()):
        dias.append(d)
        bultos_dias.append(v)

    # ================== GRÁFICO: BULTOS POR SEMANA ==================
    graf_sem = {}
    for b in bultos:
        week = b.fecha_hora.isocalendar().week
        graf_sem[week] = graf_sem.get(week, 0) + b.cantidad

    semanas = []
    bultos_sem = []
    for w, v in sorted(graf_sem.items()):
        semanas.append(f"Semana {w}")
        bultos_sem.append(v)

    semanas_totales = len(semanas)

    # ================== GRÁFICO: BULTOS POR MES ==================
    graf_mes = {}
    for b in bultos:
        m = b.fecha_hora.month
        graf_mes[m] = graf_mes.get(m, 0) + b.cantidad

    meses = []
    bultos_mes = []
    for m, v in sorted(graf_mes.items()):
        meses.append(calendar.month_name[m])  # "January", "February", ...
        bultos_mes.append(v)

    # ================== INCONSISTENCIAS (PLACEHOLDER POR AHORA) ==================
    inconsistencias_mes = [0] * len(meses)
    faltante_mes = [0] * len(meses)
    inconsistencias = sum(inconsistencias_mes)

    return render_template(
        "bultos/list.html",
        bultos=bultos,
        total_bultos=total_bultos,
        bultos_hoy=bultos_hoy,
        total_trailers=total_trailers,
        semanas_totales=semanas_totales,
        inconsistencias=inconsistencias,
        dias=dias,
        bultos_dias=bultos_dias,
        semanas=semanas,
        bultos_sem=bultos_sem,
        meses=meses,
        bultos_mes=bultos_mes,
        inconsistencias_mes=inconsistencias_mes,
        faltante_mes=faltante_mes,
    )


# =====================================================================
#   LISTA PARA HACER CONTEO REAL
# =====================================================================
@bultos_bp.route("/contar")
@login_required
def contar_bultos():
    bultos = Bulto.query.order_by(Bulto.fecha_hora.desc()).all()
    return render_template("bultos/contar_bultos.html", bultos=bultos)


# =====================================================================
#   FORMULARIO DE POST–REGISTRO (CONTEO REAL)
# =====================================================================
@bultos_bp.route("/post/<int:bulto_id>", methods=["GET", "POST"])
@login_required
def post_registro(bulto_id):
    bulto = Bulto.query.get_or_404(bulto_id)

    if request.method == "POST":
        try:
            real = int(request.form.get("cantidad_real", "0"))
        except ValueError:
            real = 0

        diferencia = real - bulto.cantidad

        nuevo = PostRegistro(
            bulto_id=bulto.id,
            cantidad_sistema=bulto.cantidad,
            cantidad_real=real,
            diferencia=diferencia,
            observacion=request.form.get("observacion", ""),
            registrado_por=current_user.username,
            fecha_registro=datetime.utcnow(),
        )

        db.session.add(nuevo)
        db.session.commit()

        flash("Conteo registrado correctamente.", "success")
        return redirect(url_for("bultos.historial_post"))

    return render_template("bultos/post_registro.html", bulto=bulto)


# =====================================================================
#   HISTORIAL DE POST-REGISTROS
# =====================================================================
@bultos_bp.route("/historial")
@login_required
def historial_post():
    historial = (
        PostRegistro.query.order_by(PostRegistro.fecha_registro.desc()).all()
    )
    return render_template("bultos/historial_post.html", historial=historial)
