
import os
from werkzeug.utils import secure_filename

from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash
from .models import *
from .models import PigWeight, Vaccination, Breeding
from . import db
from flask_login import login_user, logout_user, login_required, current_user

import pandas as pd
import io
from reportlab.pdfgen import canvas

# ✅ ZAMBIAN TIME (ONLY ADDITION)
from datetime import datetime
import pytz
ZAMBIA_TZ = pytz.timezone("Africa/Lusaka")

def zambia_now():
    return datetime.now(ZAMBIA_TZ)

main = Blueprint("main", __name__)

# =========================
# LOGIN
# =========================
@main.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        from werkzeug.security import check_password_hash
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect("/dashboard")
        else:
            flash("Invalid username or password")

    return render_template("login.html")


# =========================
# DASHBOARD (Admin/Worker View with safe totals and pig counts)
# =========================
@main.route("/dashboard")
@login_required
def dashboard():
    # All pigs (needed for both admin and worker)
    pigs = Pig.query.all()

    # 👑 ADMIN sees everything
    if current_user.role == "admin":
        sales = Sale.query.all()
        expenses = Expense.query.all()
    else:
        # 👷 WORKER sees ONLY their own entries
        sales = Sale.query.filter_by(entered_by=current_user.name).all()
        expenses = Expense.query.filter_by(entered_by=current_user.name).all()

    # Pig counts always system-wide
    available = Pig.query.filter_by(status="Available").count()
    sold = Pig.query.filter_by(status="Sold").count()

    # ✅ Safe totals (no crash if empty)
    total_sales = sum(s.price for s in sales) if sales else 0
    total_expenses = sum(e.amount for e in expenses) if expenses else 0
    profit = total_sales - total_expenses

    return render_template(
        "dashboard.html",
        pigs=pigs,
        sales=sales,
        expenses=expenses,
        available=available,
        sold=sold,
        total_sales=total_sales,
        total_expenses=total_expenses,
        profit=profit
    )


# =========================
# Dedicated Dashboard Pages
# =========================
@main.route("/dashboard/pigs")
@login_required
def dashboard_pigs():
    pigs = Pig.query.all()
    return render_template("dashboard_pigs.html", pigs=pigs)

@main.route("/dashboard/sales")
@login_required
def dashboard_sales():
    sales = Sale.query.all()
    return render_template("dashboard_sales.html", sales=sales)

@main.route("/dashboard/expenses")
@login_required
def dashboard_expenses():
    expenses = Expense.query.all()
    return render_template("dashboard_expenses.html", expenses=expenses)


# =========================
# MANAGE USERS
# =========================
@main.route("/users")
@login_required
def users():
    if current_user.role != "admin":
        return redirect("/dashboard")
    all_users = User.query.all()
    return render_template("users.html", users=all_users)


# =========================
# ADD USER
# =========================
@main.route("/add_user", methods=["POST"])
@login_required
def add_user():
    if current_user.role != "admin":
        return redirect("/dashboard")

    name = request.form.get("name")
    username = request.form.get("username")
    password = request.form.get("password")
    role = request.form.get("role")

    if not (name and username and password and role):
        flash("All fields are required")
        return redirect(url_for("main.users"))

    existing = User.query.filter_by(username=username).first()
    if existing:
        flash("Username already exists")
        return redirect(url_for("main.users"))

    from werkzeug.security import generate_password_hash
    hashed_password = generate_password_hash(password)

    new_user = User(
        name=name,
        username=username,
        password=hashed_password,
        role=role
    )

    db.session.add(new_user)
    db.session.commit()
    flash("User added successfully")
    return redirect(url_for("main.users"))


# =========================
# DELETE USER
# =========================
@main.route("/delete_user/<int:user_id>")
@login_required
def delete_user(user_id):
    if current_user.role != "admin":
        return redirect("/dashboard")

    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        flash("Cannot delete admin user")
        return redirect(url_for("main.users"))

    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully")
    return redirect(url_for("main.users"))


# =========================
# ADD PIG
# =========================
@main.route("/add_pig", methods=["POST"])
@login_required
def add_pig():
    tag = request.form["tag"]
    breed = request.form["breed"]
    weight = request.form["weight"]
    age = request.form["age"]

    photo_file = request.files.get("photo")
    filename = None

    if photo_file and photo_file.filename != "":
        filename = secure_filename(photo_file.filename)
        upload_folder = os.path.join(
            os.path.dirname(__file__), "static", "pig_images"
        )
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        photo_file.save(filepath)

    existing = Pig.query.filter_by(tag=tag).first()
    if existing:
        flash("Pig tag already exists!")
        return redirect("/dashboard")

    pig = Pig(
        tag=tag,
        breed=breed,
        weight=weight,
        age=age,
        photo=filename,
        entered_by=current_user.name
    )

    db.session.add(pig)
    db.session.commit()
    flash("Pig added successfully")
    return redirect("/dashboard")


# =========================
# ADD SALE
# =========================
@main.route("/add_sale", methods=["POST"])
@login_required
def add_sale():
    pig_id = request.form["pig_id"]
    price = float(request.form["price"])
    pig = Pig.query.get(pig_id)

    if pig.status == "Sold":
        flash("This pig has already been sold!")
        return redirect("/dashboard")

    pig.status = "Sold"
    sale = Sale(
        pig_id=pig_id,
        price=price,
        entered_by=current_user.name
    )

    db.session.add(sale)
    db.session.commit()
    flash("Sale recorded successfully")
    return redirect("/dashboard")


# =========================
# ADD EXPENSE
# =========================
@main.route("/add_expense", methods=["POST"])
@login_required
def add_expense():
    description = request.form["description"]
    amount = float(request.form["amount"])

    expense = Expense(
        description=description,
        amount=amount,
        entered_by=current_user.name
    )

    db.session.add(expense)
    db.session.commit()
    flash("Expense recorded successfully")
    return redirect("/dashboard")


# =========================
# DELETE PIG
# =========================
@main.route("/delete_pig/<int:id>")
@login_required
def delete_pig(id):
    if current_user.role != "admin":
        return redirect("/dashboard")
    pig = Pig.query.get_or_404(id)
    db.session.delete(pig)
    db.session.commit()
    flash("Pig deleted successfully")
    return redirect("/dashboard")


# =========================
# Pig Weight Tracking
# =========================
@main.route('/pig/<pig_id>/weight', methods=['GET','POST'])
@login_required
def pig_weight(pig_id):
    pig = Pig.query.filter_by(tag=pig_id).first_or_404()

    if request.method == 'POST':
        weight = float(request.form['weight'])
        entry = PigWeight(
            pig_id=pig.tag,
            weight=weight
        )
        db.session.add(entry)
        db.session.commit()
        flash("Weight recorded successfully")
        return redirect(url_for('main.pig_weight', pig_id=pig.tag))

    weights = PigWeight.query.filter_by(pig_id=pig.tag).all()
    return render_template(
        "pig_weight.html",
        pig=pig,
        weights=weights
    )


# =========================
# Vaccination Tracking
# =========================
@main.route('/pig/<pig_id>/vaccination', methods=['GET','POST'])
@login_required
def pig_vaccination(pig_id):
    pig = Pig.query.filter_by(tag=pig_id).first_or_404()

    if request.method == 'POST':
        from datetime import datetime, date

        vaccine = request.form['vaccine']
        date_given_str = request.form['date']
        next_due_str = request.form['next_due']

        try:
            date_given = datetime.strptime(date_given_str, "%Y-%m-%d").date()
            next_due = datetime.strptime(next_due_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format! Use YYYY-MM-DD")
            return redirect(url_for('main.pig_vaccination', pig_id=pig.tag))

        entry = Vaccination(
            pig_id=pig.tag,
            vaccine=vaccine,
            date=date_given,
            next_due=next_due
        )

        db.session.add(entry)
        db.session.commit()
        flash("Vaccination recorded successfully")
        return redirect(url_for('main.pig_vaccination', pig_id=pig.tag))

    vaccinations = Vaccination.query.filter_by(pig_id=pig.tag).all()
    return render_template(
        "pig_vaccination.html",
        pig=pig,
        vaccinations=vaccinations
    )


# =========================
# Breeding Tracking
# =========================
@main.route('/breeding', methods=['GET','POST'])
@login_required
def breeding():
    pigs = Pig.query.filter_by(status="Available").all()

    if request.method == 'POST':
        sow_id = request.form['sow_id']
        boar_id = request.form['boar_id']
        from datetime import datetime
        mating_date = datetime.strptime(request.form['mating_date'], "%Y-%m-%d").date()
        expected_birth = datetime.strptime(request.form['expected_birth'], "%Y-%m-%d").date()

        entry = Breeding(
            sow_id=sow_id,
            boar_id=boar_id,
            mating_date=mating_date,
            expected_birth=expected_birth
        )

        db.session.add(entry)
        db.session.commit()
        flash("Breeding recorded successfully")
        return redirect(url_for("main.breeding"))

    breedings = Breeding.query.all()
    return render_template(
        "breeding.html",
        breedings=breedings,
        pigs=pigs
    )


# =========================
# PDF REPORT
# =========================
@main.route("/pdf_report")
@login_required
def pdf_report():
    if current_user.role != "admin":
        return redirect("/dashboard")

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "Pig People PDF Report")

    # 📌 Always get all pigs, regardless of entered_by
    pigs = Pig.query.all()
    y = 750
    for pig in pigs:
        p.drawString(50, y, f"{pig.tag} - {pig.breed} - {pig.status}")
        y -= 20
        if y < 50:
            p.showPage()
            y = 800
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="pig_report.pdf", mimetype="application/pdf")


# =========================
# EXCEL REPORT
# =========================
@main.route("/excel_report")
@login_required
def excel_report():
    if current_user.role != "admin":
        return redirect("/dashboard")

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

        workbook = writer.book
        header_format = workbook.add_format({"bold": True, "text_wrap": True})

        # 📌 Fetch all records system-wide
        pigs = Pig.query.all()
        sold_pigs = Pig.query.filter_by(status="Sold").all()
        weights = PigWeight.query.all()
        vaccinations = Vaccination.query.all()
        breedings = Breeding.query.all()
        expenses = Expense.query.all()
        sales = Sale.query.all()

        # =========================
        # SUMMARY CALCULATIONS ✅
        # =========================
        total_sales = sum(s.price for s in sales) if sales else 0
        total_expenses = sum(e.amount for e in expenses) if expenses else 0
        profit = total_sales - total_expenses

        total_pigs = len(pigs)
        sold_count = len(sold_pigs)

        from collections import Counter
        worker_sales = Counter([s.entered_by for s in sales])

        best_worker = "N/A"
        best_worker_sales = 0

        if worker_sales:
            best_worker, best_worker_sales = worker_sales.most_common(1)[0]

        # =========================
        # SHEET 0: SUMMARY DASHBOARD ✅
        # =========================
        df_summary = pd.DataFrame([
            {"Metric": "Total Sales (K)", "Value": total_sales},
            {"Metric": "Total Expenses (K)", "Value": total_expenses},
            {"Metric": "Profit (K)", "Value": profit},
            {"Metric": "Total Pigs", "Value": total_pigs},
            {"Metric": "Sold Pigs", "Value": sold_count},
            {"Metric": "Best Worker", "Value": best_worker},
            {"Metric": "Top Worker Sales (K)", "Value": best_worker_sales},
        ])

        df_summary.to_excel(writer, index=False, sheet_name="Summary")

        ws = writer.sheets["Summary"]
        for col_num, col_name in enumerate(df_summary.columns):
            ws.write(0, col_num, col_name, header_format)
            ws.set_column(col_num, col_num, 25)

        # =========================
        # SHEET 1: PIGS
        # =========================
        df_pigs = pd.DataFrame([{
            "Tag": p.tag,
            "Breed": p.breed,
            "Weight": p.weight,
            "Age": p.age,
            "Status": p.status,
            "Entered By": p.entered_by,
            "Date": p.date,
            "Time": p.time
        } for p in pigs])

        df_pigs.to_excel(writer, index=False, sheet_name="Pigs")
        ws = writer.sheets["Pigs"]
        for col_num, col_name in enumerate(df_pigs.columns):
            ws.write(0, col_num, col_name, header_format)
            ws.set_column(col_num, col_num, 18)

        # =========================
        # SHEET 2: SOLD PIGS
        # =========================
        df_sold = pd.DataFrame([{
            "Tag": p.tag,
            "Breed": p.breed,
            "Weight": p.weight,
            "Age": p.age,
            "Status": p.status,
            "Entered By": p.entered_by,
            "Date": p.date,
            "Time": p.time
        } for p in sold_pigs])

        df_sold.to_excel(writer, index=False, sheet_name="Sold Pigs")
        ws = writer.sheets["Sold Pigs"]
        for col_num, col_name in enumerate(df_sold.columns):
            ws.write(0, col_num, col_name, header_format)
            ws.set_column(col_num, col_num, 18)

        # =========================
        # SHEET 3: SALES
        # =========================
        df_sales = pd.DataFrame([{
            "Pig ID": s.pig_id,
            "Price": s.price,
            "Entered By": s.entered_by,
            "Date": s.date,
            "Time": s.time
        } for s in sales])

        df_sales.to_excel(writer, index=False, sheet_name="Sales")
        ws = writer.sheets["Sales"]
        for col_num, col_name in enumerate(df_sales.columns):
            ws.write(0, col_num, col_name, header_format)
            ws.set_column(col_num, col_num, 20)

        # =========================
        # SHEET 4: WEIGHTS
        # =========================
        df_weights = pd.DataFrame([{
            "Pig ID": w.pig_id,
            "Weight": w.weight,
            "Date": w.date,
            "Time": w.time
        } for w in weights])

        df_weights.to_excel(writer, index=False, sheet_name="Weights")
        ws = writer.sheets["Weights"]
        for col_num, col_name in enumerate(df_weights.columns):
            ws.write(0, col_num, col_name, header_format)
            ws.set_column(col_num, col_num, 18)

        # =========================
        # SHEET 5: VACCINATIONS
        # =========================
        df_vacc = pd.DataFrame([{
            "Pig ID": v.pig_id,
            "Vaccine": v.vaccine,
            "Date": v.date,
            "Next Due": v.next_due
        } for v in vaccinations])

        df_vacc.to_excel(writer, index=False, sheet_name="Vaccinations")
        ws = writer.sheets["Vaccinations"]
        for col_num, col_name in enumerate(df_vacc.columns):
            ws.write(0, col_num, col_name, header_format)
            ws.set_column(col_num, col_num, 20)

        # =========================
        # SHEET 6: BREEDING
        # =========================
        df_breed = pd.DataFrame([{
            "Sow ID": b.sow_id,
            "Boar ID": b.boar_id,
            "Mating Date": b.mating_date,
            "Expected Birth": b.expected_birth
        } for b in breedings])

        df_breed.to_excel(writer, index=False, sheet_name="Breeding")
        ws = writer.sheets["Breeding"]
        for col_num, col_name in enumerate(df_breed.columns):
            ws.write(0, col_num, col_name, header_format)
            ws.set_column(col_num, col_num, 20)

        # =========================
        # SHEET 7: EXPENSES
        # =========================
        df_expenses = pd.DataFrame([{
            "Description": e.description,
            "Amount": e.amount,
            "Entered By": e.entered_by,
            "Date": e.date,
            "Time": e.time
        } for e in expenses])

        df_expenses.to_excel(writer, index=False, sheet_name="Expenses")
        ws = writer.sheets["Expenses"]
        for col_num, col_name in enumerate(df_expenses.columns):
            ws.write(0, col_num, col_name, header_format)
            ws.set_column(col_num, col_num, 20)

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="pigpeople_full_report.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# =========================
# EDIT PIG
# =========================
@main.route("/edit_pig/<int:id>", methods=["GET", "POST"])
@login_required
def edit_pig(id):
    pig = Pig.query.get_or_404(id)

    if request.method == "POST":
        pig.tag = request.form["tag"]
        pig.breed = request.form["breed"]
        pig.weight = request.form["weight"]
        pig.age = request.form["age"]
        pig.status = request.form["status"]

        db.session.commit()
        flash("Pig updated successfully")
        return redirect("/dashboard")

    return render_template("edit_pig.html", pig=pig)


# =========================
# EDIT EXPENSE
# =========================
@main.route("/edit_expense/<int:id>", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    expense = Expense.query.get_or_404(id)

    if request.method == "POST":
        expense.description = request.form["description"]
        expense.amount = float(request.form["amount"])

        db.session.commit()
        flash("Expense updated successfully")
        return redirect("/dashboard")

    return render_template("edit_expense.html", expense=expense)


# =========================
# EDIT SALE
# =========================
@main.route("/edit_sale/<int:id>", methods=["GET", "POST"])
@login_required
def edit_sale(id):
    sale = Sale.query.get_or_404(id)

    if request.method == "POST":
        sale.price = float(request.form["price"])

        db.session.commit()
        flash("Sale updated successfully")
        return redirect("/dashboard")

    return render_template("edit_sale.html", sale=sale)


# =========================
# LOGOUT
# =========================
@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")
