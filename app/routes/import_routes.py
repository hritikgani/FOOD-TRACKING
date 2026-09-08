from pathlib import Path

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.services import importer

bp = Blueprint("import_bp", __name__, url_prefix="/import")


@bp.route("/")
def upload_form():
    return render_template("import/upload.html")


@bp.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Please choose a CSV or Excel file to upload.", "error")
        return redirect(url_for("import_bp.upload_form"))

    ext = Path(file.filename).suffix.lower()
    if ext not in {".csv", ".xlsx", ".xls"}:
        flash("Unsupported file type. Please upload a .csv or .xlsx file.", "error")
        return redirect(url_for("import_bp.upload_form"))

    try:
        headers, rows = importer.read_upload(file)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("import_bp.upload_form"))
    except Exception:
        flash("We couldn't read that file. Please check the format and try again.", "error")
        return redirect(url_for("import_bp.upload_form"))

    mapping = importer.auto_detect_mapping(headers)
    session_id = importer.create_session(file.filename, headers, rows, mapping)
    return redirect(url_for("import_bp.mapping", session_id=session_id))


@bp.route("/<session_id>/map", methods=["GET", "POST"])
def mapping(session_id):
    session = importer.load_session(session_id)
    if not session:
        flash("This import session has expired. Please upload the file again.", "error")
        return redirect(url_for("import_bp.upload_form"))

    if request.method == "POST":
        new_mapping = {}
        for target in importer.TARGET_FIELD_LABELS:
            value = request.form.get(f"map_{target}", "")
            if value:
                new_mapping[target] = value
        session["mapping"] = new_mapping
        session["fixed_platform"] = request.form.get("fixed_platform", "")
        importer.save_session(session_id, session)
        return redirect(url_for("import_bp.preview", session_id=session_id))

    return render_template(
        "import/mapping.html",
        session_id=session_id,
        headers=session["headers"],
        mapping=session.get("mapping", {}),
        target_fields=importer.TARGET_FIELD_LABELS,
        sample_rows=session["rows"][:5],
        row_count=len(session["rows"]),
        filename=session["filename"],
    )


@bp.route("/<session_id>/preview")
def preview(session_id):
    session = importer.load_session(session_id)
    if not session:
        flash("This import session has expired. Please upload the file again.", "error")
        return redirect(url_for("import_bp.upload_form"))
    if not session.get("mapping"):
        return redirect(url_for("import_bp.mapping", session_id=session_id))

    mapped = importer.apply_mapping(session["rows"], session["mapping"], session.get("fixed_platform"))
    validated = importer.validate_rows(mapped)

    valid_count = sum(1 for r in validated if r["valid"])
    error_count = sum(1 for r in validated if not r["valid"])
    duplicate_count = sum(1 for r in validated if r["valid"] and r["is_duplicate"])

    return render_template(
        "import/preview.html",
        session_id=session_id,
        filename=session["filename"],
        rows=validated[:300],
        total_rows=len(validated),
        shown_rows=min(300, len(validated)),
        valid_count=valid_count,
        error_count=error_count,
        duplicate_count=duplicate_count,
    )


@bp.route("/<session_id>/confirm", methods=["POST"])
def confirm(session_id):
    session = importer.load_session(session_id)
    if not session:
        flash("This import session has expired. Please upload the file again.", "error")
        return redirect(url_for("import_bp.upload_form"))

    mapped = importer.apply_mapping(session["rows"], session["mapping"], session.get("fixed_platform"))
    validated = importer.validate_rows(mapped)
    skip_duplicates = request.form.get("duplicate_action", "skip") == "skip"

    result = importer.import_rows(validated, skip_duplicates=skip_duplicates)
    importer.delete_session(session_id)

    flash(
        f"Imported {result['imported']} orders. "
        f"Skipped {result['skipped_invalid']} invalid and {result['skipped_duplicate']} duplicate rows.",
        "success",
    )
    return redirect(url_for("orders.index"))


@bp.route("/<session_id>/cancel", methods=["POST"])
def cancel(session_id):
    importer.delete_session(session_id)
    flash("Import cancelled.", "success")
    return redirect(url_for("import_bp.upload_form"))
