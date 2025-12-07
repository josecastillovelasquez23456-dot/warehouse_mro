import io
import uuid
from datetime import datetime

import pandas as pd
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
)
from flask_login import login_required
from sqlalchemy import func

from models import db
from models.inventory import InventoryItem
from models.alerts import Alert
from models.inventory_history import InventoryHistory
from utils.excel import (
    load_inventory_excel,
    load_warehouse2d_excel,
    generate_discrepancies_excel,
    sort_location_advanced,
)

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


# =====================================================================================
#                           CARGA INVENTARIO BASE (SISTEMA)
# =====================================================================================

@inventory_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_inventory():
    """
    Carga el inventario base desde Excel (sistema).
    - Sobrescribe la tabla InventoryItem
    - Guarda un snapshot en InventoryHistory para histórico
    """
    if request.method == "POST":
        file = request.files.get("file")
        snapshot_name = request.form.get("snapshot_name", "").strip()

        if not file:
            flash("Debe seleccionar un archivo de Excel.", "warning")
            return redirect(url_for("inventory.upload_inventory"))

        try:
            # Usa loader flexible de utils/excel.py
            df = load_inventory_excel(file)
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("inventory.upload_inventory"))
        except Exception:
            flash("Error al leer el archivo de inventario. Verifique el formato.", "danger")
            return redirect(url_for("inventory.upload_inventory"))

        if df.empty:
            flash("El archivo de inventario está vacío.", "warning")
            return redirect(url_for("inventory.upload_inventory"))

        # Normalizar columnas clave
        df["Código del Material"] = df["Código del Material"].astype(str).str.strip()
        df["Texto breve de material"] = df["Texto breve de material"].astype(str).str.strip()
        df["Unidad de medida base"] = df["Unidad de medida base"].astype(str).str.strip()
        df["Ubicación"] = df["Ubicación"].astype(str).str.strip()
        df["Libre utilización"] = df["Libre utilización"].fillna(0).astype(float)

        # Limpiamos inventario anterior
        InventoryItem.query.delete()
        db.session.commit()

        # Insertamos nuevo inventario actual
        for _, row in df.iterrows():
            item = InventoryItem(
                material_code=row["Código del Material"],
                material_text=row["Texto breve de material"],
                base_unit=row["Unidad de medida base"],
                location=row["Ubicación"],
                libre_utilizacion=float(row["Libre utilización"]),
            )
            db.session.add(item)

        # Guardar snapshot histórico
        snapshot_id = str(uuid.uuid4())
        if not snapshot_name:
            snapshot_name = f"Inventario base {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        for _, row in df.iterrows():
            hist = InventoryHistory(
                snapshot_id=snapshot_id,
                snapshot_name=snapshot_name,
                material_code=row["Código del Material"],
                material_text=row["Texto breve de material"],
                base_unit=row["Unidad de medida base"],
                location=row["Ubicación"],
                libre_utilizacion=float(row["Libre utilización"]),
            )
            db.session.add(hist)

        db.session.commit()
        flash("Inventario cargado y almacenado en histórico.", "success")
        return redirect(url_for("inventory.dashboard"))

    return render_template("inventory/upload.html")


# =====================================================================================
#                           CARGA INVENTARIOS ANTIGUOS (HISTÓRICO)
# =====================================================================================

@inventory_bp.route("/history/upload", methods=["GET", "POST"])
@login_required
def upload_inventory_history():
    """
    Permite subir Excel de inventarios antiguos SIN tocar el inventario actual.
    Solo se guarda en InventoryHistory como snapshot.
    """
    if request.method == "POST":
        file = request.files.get("file")
        snapshot_name = request.form.get("snapshot_name", "").strip()

        if not file:
            flash("Debe seleccionar un archivo.", "warning")
            return redirect(url_for("inventory.upload_inventory_history"))

        try:
            df = load_inventory_excel(file)
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("inventory.upload_inventory_history"))
        except Exception:
            flash("Error al leer el archivo histórico. Verifique el formato.", "danger")
            return redirect(url_for("inventory.upload_inventory_history"))

        if df.empty:
            flash("El archivo de inventario histórico está vacío.", "warning")
            return redirect(url_for("inventory.upload_inventory_history"))

        df["Código del Material"] = df["Código del Material"].astype(str).str.strip()
        df["Texto breve de material"] = df["Texto breve de material"].astype(str).str.strip()
        df["Unidad de medida base"] = df["Unidad de medida base"].astype(str).str.strip()
        df["Ubicación"] = df["Ubicación"].astype(str).str.strip()
        df["Libre utilización"] = df["Libre utilización"].fillna(0).astype(float)

        snapshot_id = str(uuid.uuid4())
        if not snapshot_name:
            snapshot_name = f"Inventario histórico {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        for _, row in df.iterrows():
            hist = InventoryHistory(
                snapshot_id=snapshot_id,
                snapshot_name=snapshot_name,
                material_code=row["Código del Material"],
                material_text=row["Texto breve de material"],
                base_unit=row["Unidad de medida base"],
                location=row["Ubicación"],
                libre_utilizacion=float(row["Libre utilización"]),
            )
            db.session.add(hist)

        db.session.commit()
        flash("Inventario histórico cargado correctamente.", "success")
        return redirect(url_for("inventory.dashboard"))

    return render_template("inventory/upload_history.html")


# =====================================================================================
#                                   LISTA INVENTARIO
# =====================================================================================

@inventory_bp.route("/list")
@login_required
def list_inventory():
    """
    Muestra el inventario actual, ordenado por ubicación usando sort_location_advanced.
    """
    items = InventoryItem.query.all()
    items_sorted = sorted(items, key=lambda x: sort_location_advanced(x.location))
    return render_template("inventory/list.html", items=items_sorted)


# =====================================================================================
#                           DISCREPANCIAS USANDO EXCEL
# =====================================================================================

@inventory_bp.route("/discrepancies", methods=["GET", "POST"])
@login_required
def discrepancies():
    """
    Genera discrepancias usando un Excel de conteo físico.
    El Excel de conteo tiene las mismas columnas que el inventario,
    donde 'Libre utilización' representa el stock contado.
    """
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Seleccione un archivo de conteo físico.", "warning")
            return redirect(url_for("inventory.discrepancies"))

        try:
            counted_df = load_inventory_excel(file)
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("inventory.discrepancies"))
        except Exception:
            flash("Error leyendo el archivo de conteo.", "danger")
            return redirect(url_for("inventory.discrepancies"))

        counted_df["Código del Material"] = counted_df["Código del Material"].astype(str).str.strip()
        counted_df["Ubicación"] = counted_df["Ubicación"].astype(str).str.strip()
        counted_df["Libre utilización"] = counted_df["Libre utilización"].fillna(0).astype(float)

        # Agrupamos conteo físico por Código + Ubicación
        counted_group = (
            counted_df.groupby(["Código del Material", "Ubicación"], as_index=False)["Libre utilización"]
            .sum()
            .rename(columns={
                "Código del Material": "Código Material",
                "Libre utilización": "Stock contado",
            })
        )

        # Inventario del sistema agrupado
        system_q = (
            db.session.query(
                InventoryItem.material_code.label("Código Material"),
                InventoryItem.material_text.label("Descripción"),
                InventoryItem.base_unit.label("Unidad"),
                InventoryItem.location.label("Ubicación"),
                func.sum(InventoryItem.libre_utilizacion).label("Stock sistema"),
            )
            .group_by(
                InventoryItem.material_code,
                InventoryItem.material_text,
                InventoryItem.base_unit,
                InventoryItem.location,
            )
        )

        system_df = pd.read_sql(system_q.statement, db.session.bind)

        # Merge sistema vs conteo
        merged = system_df.merge(
            counted_group,
            on=["Código Material", "Ubicación"],
            how="outer",
        )

        merged["Stock sistema"] = merged["Stock sistema"].fillna(0)
        merged["Stock contado"] = merged["Stock contado"].fillna(0)
        merged["Descripción"] = merged["Descripción"].fillna("SIN DESCRIPCIÓN")
        merged["Unidad"] = merged["Unidad"].fillna("")

        # Diferencia = contado - sistema
        merged["Diferencia"] = merged["Stock contado"] - merged["Stock sistema"]

        # Estado
        estados = []
        for _, r in merged.iterrows():
            diff = r["Diferencia"]
            if diff == 0:
                estado = "OK"
            elif diff < 0:
                estado = "CRÍTICO" if diff <= -10 else "FALTA"
            else:
                estado = "SOBRA"
            estados.append(estado)

        merged["Estado"] = estados

        # Orden final
        df_final = merged[
            [
                "Código Material",
                "Descripción",
                "Unidad",
                "Ubicación",
                "Stock sistema",
                "Stock contado",
                "Diferencia",
                "Estado",
            ]
        ].copy()

        # Excel profesional
        output = generate_discrepancies_excel(df_final)
        filename = f"discrepancias_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    return render_template("inventory/discrepancies.html")


# =====================================================================================
#                                   CONTEO HTML
# =====================================================================================

@inventory_bp.route("/count", methods=["GET", "POST"])
@login_required
def count_inventory():
    """
    Conteo en línea:
    - GET: muestra inventario + input para stock contado
    - POST: genera Excel de discrepancias usando lo digitado
    """
    if request.method == "GET":
        items = InventoryItem.query.all()
        items_sorted = sorted(items, key=lambda x: sort_location_advanced(x.location))
        return render_template("inventory/count.html", items=items_sorted)

    items = InventoryItem.query.all()
    filas = []

    for item in items:
        raw_val = request.form.get(f"count_{item.id}", "").strip()
        try:
            contado = float(raw_val) if raw_val != "" else 0
        except Exception:
            contado = 0

        sistema = float(item.libre_utilizacion or 0)
        diferencia = contado - sistema

        if diferencia == 0:
            estado = "OK"
        elif diferencia < 0:
            estado = "CRÍTICO" if diferencia <= -10 else "FALTA"
        else:
            estado = "SOBRA"

        filas.append({
            "Código Material": item.material_code,
            "Descripción": item.material_text,
            "Unidad": item.base_unit,
            "Ubicación": item.location,
            "Stock sistema": sistema,
            "Stock contado": contado,
            "Diferencia": diferencia,
            "Estado": estado,
        })

    df_final = pd.DataFrame(filas)
    output = generate_discrepancies_excel(df_final)
    filename = f"discrepancias_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# =====================================================================================
#                                 DASHBOARD INVENTARIO
# =====================================================================================

@inventory_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Dashboard de inventario:
    - KPIs
    - Resumen por ubicación
    - Materiales críticos
    - Últimas alertas
    - Últimos snapshots
    """
    total_items = InventoryItem.query.count()
    total_stock = db.session.query(
        func.sum(InventoryItem.libre_utilizacion)
    ).scalar() or 0
    total_ubicaciones = db.session.query(InventoryItem.location).distinct().count()
    stock_promedio = round(total_stock / total_items, 2) if total_items else 0

    resumen_anaqueles = (
        db.session.query(
            InventoryItem.location,
            func.sum(InventoryItem.libre_utilizacion).label("stock"),
            func.count(InventoryItem.id).label("items"),
        )
        .group_by(InventoryItem.location)
        .order_by(InventoryItem.location.asc())
        .all()
    )

    criticos = (
        InventoryItem.query
        .filter(InventoryItem.libre_utilizacion <= 5)
        .order_by(InventoryItem.libre_utilizacion.asc())
        .limit(20)
        .all()
    )

    alertas = Alert.query.order_by(Alert.created_at.desc()).limit(10).all()

    snapshots = (
        db.session.query(
            InventoryHistory.snapshot_id,
            InventoryHistory.snapshot_name,
            func.min(InventoryHistory.uploaded_at).label("fecha"),
        )
        .group_by(InventoryHistory.snapshot_id, InventoryHistory.snapshot_name)
        .order_by(func.min(InventoryHistory.uploaded_at).desc())
        .limit(10)
        .all()
    )

    return render_template(
        "inventory/dashboard.html",
        total_items=total_items,
        total_stock=total_stock,
        ubicaciones=total_ubicaciones,   # <- nombre que usa tu HTML
        stock_prom=stock_promedio,       # <- nombre que usa tu HTML
        resumen=resumen_anaqueles,       # <- nombre que usa tu HTML
        criticos=criticos,
        alertas=alertas,
        snapshots=snapshots,
    )
