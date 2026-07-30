from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash

load_dotenv()

from promo import db
from promo.categorize import get_all_categories, categorize_product
from promo.textgen import generate_text
from promo.csv_import import parse_csv
from promo.shopee_sync import run_sync

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
    liked_only = request.args.get("liked") == "1"
    rows = db.list_products(category=category, status=status, liked_only=liked_only)

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
        liked_only=liked_only,
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
            "brand": request.form["brand"].strip(),
            "image_url": request.form.get("image_url", "").strip() or None,
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


@app.route("/sync-shopee", methods=["POST"])
def sync_shopee():
    try:
        summary = run_sync()
    except Exception as exc:  # falha inesperada não pode derrubar o app
        flash(f"Não foi possível buscar ofertas da Shopee agora: {exc}", "error")
        return redirect(request.referrer or url_for("index"))

    if summary["erros"]:
        flash(
            f"Busca na Shopee concluída com erros: {summary['novos']} novo(s), "
            f"{summary['atualizados']} atualizado(s). Erros: {'; '.join(summary['erros'])}",
            "error",
        )
    else:
        flash(
            f"Busca na Shopee concluída: {summary['novos']} produto(s) novo(s), "
            f"{summary['atualizados']} atualizado(s).",
            "success",
        )
    return redirect(request.referrer or url_for("index"))


@app.route("/product/<int:product_id>/status", methods=["POST"])
def set_status(product_id):
    new_status = request.form["status"]
    db.update_status(product_id, new_status)
    return redirect(request.referrer or url_for("index"))


@app.route("/product/<int:product_id>/liked", methods=["POST"])
def toggle_liked(product_id):
    db.toggle_liked(product_id)
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
