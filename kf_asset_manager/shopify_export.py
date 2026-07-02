"""Shopify staging export — turn the system of record into a Shopify product CSV.

The Asset Manager stays the one-directional source of truth: this *produces an artifact*
(a Shopify-format CSV) that you import via Shopify Admin → Products → Import. No live
coupling, fully reviewable, reversible.

Mapping:
  * One Shopify product per KF product (curtain pair, each sided cushion, a fabric
    pattern). Handle = the product base SKU, lower-cased (unique per product).
  * Variants become Shopify option rows: curtains/cushions on "Side" (Left/Right/Single),
    fabrics on "Colour" (01/02…). A single-variant product uses Shopify's default
    ("Title" / "Default Title").
  * Products export as **draft / unpublished** by default — staging, nothing sells.
  * Images are intentionally left blank in v1 (products-first; imagery is a second pass).

CLI:
  python -m kf_asset_manager.shopify_export --db audit.db --out shopify_products.csv \
         [--types Curtain Fabric] [--limit 27] [--vendor "Karen Fabrics"]
"""
import argparse
import csv
import sys

from . import sku as _sku

# Standard Shopify product-import columns (subset populated; rest blank-but-present).
COLUMNS = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Type", "Tags", "Published",
    "Option1 Name", "Option1 Value",
    "Variant SKU", "Variant Inventory Tracker", "Variant Inventory Qty",
    "Variant Inventory Policy", "Variant Fulfillment Service",
    "Variant Price", "Variant Requires Shipping", "Variant Taxable",
    "Image Src", "Image Position", "Image Alt Text", "Status",
]


def _option(product_type, role, side):
    """Return (option_name, option_value) for a variant, Shopify-style."""
    vi = _sku.variant_inputs(role, side)
    if product_type == "Fabric" and vi["colorway"]:
        return "Colour", f"{int(vi['colorway']):02d}"
    desc = _sku.variant_descriptor(**vi)
    if desc:
        return "Side", desc
    return "Title", "Default Title"        # single-variant product


def to_rows(db, product_types=None, limit_products=None, vendor="Karen Fabrics",
            status="draft", price=""):
    """Build Shopify CSV rows (list of dicts) from the built graph."""
    conn = db.conn
    published = "TRUE" if status == "active" else "FALSE"
    q = "SELECT product_id,design_id,product_type,source_id FROM products"
    args = []
    if product_types:
        q += " WHERE product_type IN (%s)" % ",".join("?" * len(product_types))
        args = list(product_types)
    q += " ORDER BY design_id,product_type,source_id"
    if limit_products:
        q += " LIMIT ?"
        args.append(int(limit_products))
    prods = conn.execute(q, args).fetchall()

    rows = []
    for p in prods:
        # per-source (sided cushion) base SKU carries its side; grouped originals don't
        src_side = None
        if p["source_id"]:
            s = conn.execute("SELECT side FROM artwork_sources WHERE source_id=?",
                             (p["source_id"],)).fetchone()
            src_side = s["side"] if s else None
        base_sku = _sku.sku(p["product_type"], p["design_id"], side=src_side)
        handle = base_sku.lower()
        title = db.title_for(p["product_id"])
        variants = conn.execute(
            """SELECT pv.asset_id,a.role,a.side FROM product_variants pv
               JOIN assets a ON pv.asset_id=a.asset_id
               WHERE pv.product_id=? ORDER BY pv.variant_label""", (p["product_id"],)).fetchall()
        for i, v in enumerate(variants):
            oname, oval = _option(p["product_type"], v["role"], v["side"])
            vsku = _sku.sku(p["product_type"], p["design_id"],
                            **_sku.variant_inputs(v["role"], v["side"]))
            row = {c: "" for c in COLUMNS}
            row["Handle"] = handle
            if i == 0:                       # product-level fields only on the first row
                row["Title"] = title
                row["Vendor"] = vendor
                row["Type"] = p["product_type"]
                row["Published"] = published
                row["Status"] = status
            row["Option1 Name"] = oname
            row["Option1 Value"] = oval
            row["Variant SKU"] = vsku
            row["Variant Inventory Tracker"] = "shopify"
            row["Variant Inventory Qty"] = "0"
            row["Variant Inventory Policy"] = "deny"
            row["Variant Fulfillment Service"] = "manual"
            row["Variant Price"] = price
            row["Variant Requires Shipping"] = "TRUE"
            row["Variant Taxable"] = "TRUE"
            rows.append(row)
    return rows


def write_csv(db, path, **opts):
    rows = to_rows(db, **opts)
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=COLUMNS)
        wr.writeheader()
        wr.writerows(rows)
    # count distinct products (handles) for the summary
    handles = {r["Handle"] for r in rows}
    return {"products": len(handles), "variant_rows": len(rows), "path": str(path)}


def _main(argv=None):
    ap = argparse.ArgumentParser(description="Export a Shopify product CSV from the KF Asset Manager DB.")
    ap.add_argument("--db", required=True, help="path to a built audit.db")
    ap.add_argument("--out", required=True, help="output CSV path")
    ap.add_argument("--types", nargs="*", default=None, help="filter to these product types (e.g. Curtain Fabric)")
    ap.add_argument("--limit", type=int, default=None, help="limit number of products")
    ap.add_argument("--vendor", default="Karen Fabrics")
    ap.add_argument("--status", default="draft", choices=["draft", "active", "archived"])
    ap.add_argument("--price", default="", help="placeholder variant price (blank = Shopify default)")
    a = ap.parse_args(argv)

    from . import model
    db = model.IdentityDB(a.db)
    info = write_csv(db, a.out, product_types=a.types, limit_products=a.limit,
                     vendor=a.vendor, status=a.status, price=a.price)
    print(f"Wrote {info['products']} products ({info['variant_rows']} variant rows) -> {info['path']}")
    print(f"Status: {a.status} (Published={'TRUE' if a.status=='active' else 'FALSE'}). "
          f"Import via Shopify Admin → Products → Import.")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
