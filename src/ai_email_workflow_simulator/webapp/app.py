"""Minimal local Flask review UI. No auth -- local-only prototype."""

from flask import Flask, abort, redirect, render_template, request, url_for

from ..pipeline.runner import resolve_needs_review
from ..storage import audit_log, db


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return redirect(url_for("queue"))

    @app.get("/queue")
    def queue():
        items = db.list_items()
        return render_template("queue.html", items=items)

    @app.get("/items/<int:item_id>")
    def item_detail(item_id: int):
        item = db.get_item(item_id)
        if item is None:
            abort(404)
        return render_template("detail.html", item=item)

    @app.post("/items/<int:item_id>/approve")
    def approve(item_id: int):
        item = _require_pending_pursue(item_id)
        db.update_item(item_id, review_status="approved")
        audit_log.log_human_review(
            item_id=item_id, action="approve", final_draft_text=item["final_draft_text"]
        )
        return redirect(url_for("item_detail", item_id=item_id))

    @app.post("/items/<int:item_id>/edit-approve")
    def edit_approve(item_id: int):
        _require_pending_pursue(item_id)
        final_text = request.form["final_draft_text"]
        db.update_item(
            item_id,
            final_draft_text=final_text,
            edited=1,
            review_status="edited_approved",
        )
        audit_log.log_human_review(item_id=item_id, action="edit_approve", final_draft_text=final_text)
        return redirect(url_for("item_detail", item_id=item_id))

    @app.post("/items/<int:item_id>/reject")
    def reject(item_id: int):
        _require_pending_pursue(item_id)
        db.update_item(item_id, review_status="rejected")
        audit_log.log_human_review(item_id=item_id, action="reject")
        return redirect(url_for("item_detail", item_id=item_id))

    @app.post("/items/<int:item_id>/resolve")
    def resolve(item_id: int):
        item = db.get_item(item_id)
        if item is None:
            abort(404)
        if item["review_status"] != "needs_review":
            abort(400, "item is not awaiting resolution")
        resolution = request.form["resolution"]
        resolve_needs_review(item_id, resolution)
        return redirect(url_for("item_detail", item_id=item_id))

    def _require_pending_pursue(item_id: int):
        item = db.get_item(item_id)
        if item is None:
            abort(404)
        if item["decision"] != "Pursue" or item["review_status"] != "pending_review":
            abort(400, "item is not a pending Pursue draft")
        return item

    return app


def main() -> None:
    create_app().run(debug=True)


if __name__ == "__main__":
    main()
