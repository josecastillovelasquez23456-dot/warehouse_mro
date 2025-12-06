from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models.bultos import Bulto, PostRegistro
from models import db
from datetime import datetime
import calendar

bultos_bp = Blueprint("bultos", __name__, url_prefix="/bultos")


# =====================================================================
#   REGISTRO DE BULTOS
# =====================================================================
@bultos_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_bulto():

    if request.method == "POST":

        # ===================== CAMPOS =====================
        cantidad_raw = request.form.get("cantidad", "0")
        chofer = request.form.get("chofer", "").strip()
        placa = request.form.get("placa", "").strip()
        fecha_raw = request.form.get("fecha_hora", "").strip()
        observacion = request.form.get("observacion", "").strip()

        # ===================== CANTIDAD =====================
        try:
            cantidad = int(cantidad_raw)
        except ValueError:
            cantidad = 0

        # ===================== FECHA =====================
        # Acepta:
        #  - "2025-12-05T14:55"
        #  - "2025-12-05 14:55"
        #  - vacío → ahora mismo

        if fecha_raw:
            fecha_fixed = fecha_raw.replace("T", " ")
            try:
                fecha_hora = datetime.strptime(fecha_fixed, "%Y-%m-%d %H:%M")
            except ValueError:
                fecha_hora = datetime.utcnow()
        else:
            fecha_hora = datetime.utcnow()

        # ===================== CREAR BULTOS =====================
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
#   LISTA + KPIs + GRÁFICOS
# =====================================================================
@bultos_bp.route("/list")
@login_required
def list_bultos():

    chofer = request.args.get("chofer", "").strip()
    placa = request.args.get("placa", "").strip()
    desde = request.args.get("desde", "").strip()
    hasta = request.args.get("hasta", "").strip()

    query = Bulto.query

    # ================== FILTROS ==================
    if chofer:
        query = query.filter(Bulto.chofer.ilike(f"%{chofer}%"))
    if placa:
        query = query.filter(Bulto.placa.ilike(f"%{placa}%"))

    if desde:
        try:
            d = datetime.strptime(desde, "%Y-%m-%d")
            query = query.filter(Bulto.fecha_hora >= d)
        except ValueError:
            pass

    if hasta:
        try:
            h = datetime.strptime(hasta, "%Y-%m-%d").replace(hour=23, minute=59)
            query = query.filter(Bulto.fecha_hora <= h)
        except ValueError:
            pass

    bultos = query.order_by(Bulto.fecha_hora.asc()).all()

    # ================== KPIs ==================
    total_bultos = sum(b.cantidad for b in bultos)
    hoy = datetime.today().date()
    bultos_hoy = sum(b.cantidad for b in bultos if b.fecha_hora.date() == hoy)
    total_trailers = len({b.placa for b in bultos if b.placa})

    # ================== BULTOS POR DÍA ==================
    graf_dia = {}
    for b in bultos:
        k = b.fecha_hora.strftime("%d-%m")
        graf_dia[k] = graf_dia.get(k, 0) + b.cantidad

    dias = list(graf_dia.keys())
    bultos_dias = list(graf_dia.values())

    # ================== BULTOS POR SEMANA ==================
    graf_sem = {}
    for b in bultos:
        w = b.fecha_hora.isocalendar().week
        graf_sem[w] = graf_sem.get(w, 0) + b.cantidad

    semanas = [f"Semana {w}" for w in graf_sem.keys()]
    bultos_sem = list(graf_sem.values())
    semanas_totales = len(semanas)

    # ================== BULTOS POR MES ==================
    graf_mes = {}
    for b in bultos:
        m = b.fecha_hora.month
        graf_mes[m] = graf_mes.get(m, 0) + b.cantidad

    meses = [calendar.month_name[m] for m in graf_mes.keys()]
    bultos_mes = list(graf_mes.values())

    # Placeholder de inconsistencias
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
#   PANTALLA DE CONTEO REAL
# =====================================================================
@bultos_bp.route("/contar")
@login_required
def contar_bultos():
    bultos = Bulto.query.order_by(Bulto.fecha_hora.desc()).all()
    return render_template("bultos/contar_bultos.html", bultos=bultos)



# =====================================================================
#   FORMULARIO DE POST REGISTRO
# =====================================================================
@bultos_bp.route("/post/<int:bulto_id>", methods=["GET", "POST"])
@login_required
def post_registro(bulto_id):

    bulto = Bulto.query.get_or_404(bulto_id)

    if request.method == "POST":

        real_raw = request.form.get("cantidad_real", "0")
        try:
            real = int(real_raw)
        except ValueError:
            real = 0

        diferencia = real - bulto.cantidad

        nuevo_post = PostRegistro(
            bulto_id=bulto.id,
            cantidad_sistema=bulto.cantidad,
            cantidad_real=real,
            diferencia=diferencia,
            observacion=request.form.get("observacion", ""),
            registrado_por=current_user.username,
            fecha_registro=datetime.utcnow()
        )

        db.session.add(nuevo_post)
        db.session.commit()

        flash("Conteo registrado correctamente.", "success")
        return redirect(url_for("bultos.historial_post"))

    return render_template("bultos/post_registro.html", bulto=bulto)



# =====================================================================
#   HISTORIAL COMPLETO
# =====================================================================
@bultos_bp.route("/historial")
@login_required
def historial_post():
    historial = PostRegistro.query.order_by(PostRegistro.fecha_registro.desc()).all()
    return render_template("bultos/historial_post.html", historial=historial)
