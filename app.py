from flask import Flask, render_template, request, redirect, url_for, flash

from promo import db
from promo.categorize import get_all_categories, categorize_product
from promo.textgen import generate_text
from promo.csv_import import parse_csv

app = Flask(__name__)
app.secret_key = "grupo-promocoes-local"

db.init_db()

PLATFORMS = ["Shopee", "Mercado Livre", "Amazon", "Magalu", "Shein"]


@app.context_processor
def inject_globals():
    return {"all_categories": get_all_categories(), "platforms": PLATFORMS}


@app.route("/")
def index():
    category = request.args.get("category") or None
    status = request.args.get("status") or None
    rows = db.list_products(category=category, status=status)

    products = []
    for row in rows:
        product = dict(row)
        product["generated_text"] = generate_text(row)
        products.append(product)

    return render_template(
        "index.html",
        products=products,
        selected_category=category or "",
        selected_status=status or "",
    )


@app.route("/add", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form["name"].strip()
        category = request.form.get("category") or categorize_product(name)
        site = request.form.get("site", "").strip()

        original_price_raw = request.form.get("original_price", "").strip()
        promo_price_raw = request.form.get("promo_price", "").strip()

        original_price = float(original_price_raw.replace(",", ".")) if original_price_raw else None
        promo_price = float(promo_price_raw.replace(",", "."))

        product = {
            "name": name,
            "category": category,
            "platform": site,
            "store_name": None,
            "original_price": original_price,
            "promo_price": promo_price,
            "commission_rate": None,
            "commission": None,
            "link": request.form["link"].strip(),
            "coupon": request.form.get("coupon", "").strip() or None,
            "extra_details": request.form.get("extra_details", "").strip() or None,
            "status": "pendente",
        }
        db.insert_product(product)
        flash(f'Produto "{name}" cadastrado com sucesso!', "success")
        return redirect(url_for("index"))

    return render_template("add_product.html")


@app.route("/upload", methods=["GET", "POST"])
def upload_csv():
    if request.method == "POST":
        file = request.files.get("csv_file")
        platform = request.form.get("platform", "Shopee")

        if not file or file.filename == "":
            flash("Selecione um arquivo CSV para importar.", "error")
            return redirect(url_for("upload_csv"))

        products = parse_csv(file.stream, platform)
        for product in products:
            db.insert_product(product)

        fora_do_escopo = sum(1 for p in products if p["category"] == "Fora do escopo")
        flash(
            f"Importação concluída: {len(products)} produto(s) importado(s) "
            f"({fora_do_escopo} marcado(s) como 'Fora do escopo').",
            "success",
        )
        return redirect(url_for("index"))

    return render_template("upload_csv.html")


@app.route("/product/<int:product_id>/status", methods=["POST"])
def set_status(product_id):
    new_status = request.form["status"]
    db.update_status(product_id, new_status)
    return redirect(request.referrer or url_for("index"))


@app.route("/product/<int:product_id>/category", methods=["POST"])
def set_category(product_id):
    new_category = request.form["category"]
    db.update_category(product_id, new_category)
    return redirect(request.referrer or url_for("index"))


@app.route("/product/<int:product_id>/delete", methods=["POST"])
def delete_product(product_id):
    db.delete_product(product_id)
    flash("Produto removido.", "success")
    return redirect(request.referrer or url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
