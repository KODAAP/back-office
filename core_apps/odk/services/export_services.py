import io
import os
import re
import tempfile
import zipfile
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pyxform.xls2json

from .base_service import BaseODKService


class ODKExportService(BaseODKService):

    def _get_labels_and_choices(
        self,
        project_id: int,
        form_id: str,
        language: Optional[str] = None,
    ) -> Tuple[Dict[str, str], Dict[str, Dict[str, str]], Dict[str, str]]:
        """
        Parse le XLSForm pour extraire:
        - labels: field name -> label
        - choices: list_name -> {choice_name -> choice_label}
        - field_to_list: field name -> list_name (for reliable choice lookup)
        """
        xlsx_bytes = self._get_form_xlsx(project_id, form_id)
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(xlsx_bytes)
            tmp_path = tmp.name
        try:
            survey = pyxform.xls2json.parse_file_to_json(tmp_path)
        finally:
            os.unlink(tmp_path)

        labels: Dict[str, str] = {}
        choices: Dict[str, Dict[str, str]] = {}
        field_to_list: Dict[str, str] = {}

        def _extract_label(node_label, name: str) -> str:
            """Helper to extract a label string from a node's label field."""
            if not node_label:
                return name
            if isinstance(node_label, list) and node_label:
                if language:
                    for lang_item in node_label:
                        if lang_item.get("@xml:lang") == language:
                            return lang_item.get("#text", name)
                return node_label[0].get("#text", name)
            return str(node_label)

        def recurse(node: Any, path: str = "") -> None:
            node_type = node.get("type")
            name = node.get("name", "")
            full_name = f"{path}/{name}" if path and name else name

            # Extract label
            label = _extract_label(node.get("label"), name)

            # Store labels (full path and short name)
            if node_type and node_type != "survey" and name:
                labels[full_name] = label
                labels[name] = label

            # Choices for select/rank questions
            if node_type in ["select one", "select all that apply", "rank"]:
                list_name = node.get("list_name") or name

                # Map field name -> list_name for reliable lookup later
                field_to_list[name] = list_name
                field_to_list[full_name] = list_name

                choice_map: Dict[str, str] = {}
                for child in node.get("children", []):
                    ch_name = child.get("name")
                    ch_lbl = _extract_label(child.get("label"), ch_name)
                    if ch_name:
                        choice_map[ch_name] = ch_lbl
                choices[list_name] = choice_map

            # Recurse into groups/repeats
            for child in node.get("children", []):
                recurse(child, full_name)

        recurse(survey)
        return labels, choices, field_to_list

    def _safe_sheet_name(self, name: str) -> str:
        """Nettoie le nom pour onglet Excel (max 31 chars, sans chars invalides)."""
        name = re.sub(r"[\\/*?\":<>|]", "_", name)[:31].strip()
        return name or "sheet"

    def export_smart_excel(
        self,
        project_id: int,
        form_id: str,
        remove_group_prefix: bool = True,
        include_labels: bool = True,
        include_choice_labels: bool = False,
        language: Optional[str] = None,
    ) -> Tuple[bytes, str]:
        """Export Excel multi-onglets : main + repeats, avec options labels/nettoyage/choix."""
        # Retrieve labels, choices, and field->list_name mapping
        labels, choices, field_to_list = self._get_labels_and_choices(
            project_id, form_id, language
        )

        # Download ZIP of CSV submissions (no attachments)
        zip_content = self.zip_submissions(project_id, form_id)

        with zipfile.ZipFile(io.BytesIO(zip_content)) as zin:
            csv_files = [f for f in zin.namelist() if f.endswith(".csv")]

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                for csv_file in csv_files:
                    csv_bytes = zin.read(csv_file)
                    df = pd.read_csv(io.StringIO(csv_bytes.decode("utf-8-sig")))

                    # Strip group path prefixes from column names
                    new_columns = []
                    for col in list(df.columns):
                        if remove_group_prefix and "/" in col:
                            col = col.rsplit("/", 1)[-1]
                        new_columns.append(col)
                    df.columns = new_columns

                    # Replace choice codes with labels.
                    # For select_multiple, values are space-separated codes — map each token individually.
                    # Note: if choice labels contain spaces, results for select_multiple will be ambiguous.
                    if include_choice_labels:
                        for col in df.columns:
                            list_name = field_to_list.get(col)
                            if list_name and list_name in choices:
                                cmap = choices[list_name]

                                def map_value(val, cmap=cmap):
                                    if pd.isna(val):
                                        return val
                                    tokens = str(val).split(" ")
                                    return " ".join(cmap.get(t, t) for t in tokens)

                                df[col] = df[col].apply(map_value)

                    # Determine sheet name from CSV filename
                    sheet_name = csv_file.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                    sheet_name = self._safe_sheet_name(sheet_name)

                    if include_labels:
                        label_row = [labels.get(col, col) for col in df.columns]
                        df_label = pd.DataFrame([label_row], columns=df.columns)
                        df_final = pd.concat([df_label, df], ignore_index=True)
                        df_final.to_excel(
                            writer, sheet_name=sheet_name, index=False, header=False
                        )

                        # Apply formatting: blue for label row, grey for variable name row
                        worksheet = writer.sheets[sheet_name]
                        blue_fmt = writer.book.add_format(
                            {"bold": True, "bg_color": "#ADD8E6", "font_color": "white"}
                        )
                        grey_fmt = writer.book.add_format(
                            {"bold": True, "bg_color": "#D3D3D3"}
                        )
                        for i, lbl in enumerate(label_row):
                            worksheet.write(0, i, lbl, blue_fmt)
                            worksheet.write(1, i, df.columns[i], grey_fmt)
                    else:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

            output.seek(0)
            filename = f"{form_id}_smart_excel.xlsx"
            return output.getvalue(), filename

    # ─────────────────────────────────────────────────────────────────────────
    # US 10 — Organisation Avancée de l'Export ZIP (médias uniquement, structuré)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_submissions_zip_with_attachments(
        self, project_id: int, form_id: str
    ) -> bytes:
        """
        Télécharge le ZIP ODK Central incluant les pièces jointes.
        L'URL sans ?attachments=false retourne les médias dans le ZIP.
        """
        return self._make_request(
            "GET",
            f"projects/{project_id}/forms/{form_id}/submissions.csv.zip",
            return_json=False,
        )

    def export_zip_structured_media_only(
        self,
        project_id: int,
        form_id: str,
    ) -> Tuple[bytes, str]:
        """
        US 10 — Export ZIP structuré contenant UNIQUEMENT les pièces jointes (sans CSV).

        Structure produite :
            {form_id}_structured_media.zip
            ├── {nom_feuille_principale}/
            │   ├── {nom_question_media_1}/
            │   │   ├── {nom_question_media_1}_1.jpg   ← index = numéro de ligne (1-based)
            │   │   └── {nom_question_media_1}_2.jpg
            │   └── {nom_question_media_2}/
            │       └── {nom_question_media_2}_1.png
            └── {nom_repeat}/
                └── {nom_question_media}/
                    └── {nom_question_media}_1.jpg

        Args:
            project_id: ID du projet ODK Central
            form_id: Identifiant XML du formulaire

        Returns:
            Tuple (bytes du ZIP, nom du fichier)
        """
        # 1. Télécharger le ZIP ODK avec pièces jointes
        raw_zip_bytes = self._get_submissions_zip_with_attachments(project_id, form_id)

        output = io.BytesIO()

        with zipfile.ZipFile(io.BytesIO(raw_zip_bytes)) as zin:
            all_entries = zin.namelist()

            # Index des médias disponibles dans le ZIP source :
            # { basename_du_fichier -> chemin_complet_dans_le_zip }
            # ODK Central stocke les médias dans un sous-dossier "media/" ou à la racine.
            media_index: Dict[str, str] = {}
            for entry in all_entries:
                if not entry.endswith(".csv"):
                    basename = os.path.basename(entry)
                    if basename:  # ignorer les entrées de dossier vides
                        media_index[basename] = entry

            # Identifier tous les CSV (feuille principale + répétitions)
            csv_entries = [e for e in all_entries if e.endswith(".csv")]

            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zout:
                for csv_entry in csv_entries:
                    # Nom du dossier racine dans le ZIP de sortie = nom du CSV sans extension
                    # Ex: "mon_formulaire.csv" → "mon_formulaire"
                    #     "media/mon_formulaire-batiment.csv" → "mon_formulaire-batiment"
                    csv_basename = os.path.basename(csv_entry)
                    folder_name = csv_basename.rsplit(".", 1)[0]

                    # Lire le CSV pour identifier les colonnes contenant des médias
                    try:
                        csv_content = zin.read(csv_entry).decode("utf-8-sig")
                        df = pd.read_csv(io.StringIO(csv_content))
                    except Exception:
                        # CSV illisible → on passe
                        continue

                    if df.empty:
                        continue

                    # Détecter les colonnes "média" : colonnes dont au moins une valeur
                    # correspond à un fichier présent dans le ZIP source.
                    media_columns = []
                    for col in df.columns:
                        sample_values = df[col].dropna().astype(str)
                        if sample_values.apply(lambda v: v in media_index).any():
                            media_columns.append(col)

                    # Pour chaque colonne média, renommer et placer les fichiers
                    for col in media_columns:
                        # Nom court de la colonne (suppression du préfixe de groupe)
                        # Ex: "batiment/photo_facade" → "photo_facade"
                        short_col = col.rsplit("/", 1)[-1]

                        # Sous-dossier dans le ZIP : {dossier_feuille}/{nom_court_colonne}/
                        subfolder = f"{folder_name}/{short_col}"

                        for row_idx, row in df.iterrows():
                            original_name = str(row.get(col, "")).strip()

                            # Ignorer les cellules vides ou NaN
                            if not original_name or original_name.lower() == "nan":
                                continue

                            # Vérifier que le fichier existe dans le ZIP source
                            if original_name not in media_index:
                                continue

                            # Extension du fichier original (ex: ".jpg", ".png", ".pdf")
                            _, ext = os.path.splitext(original_name)

                            # Nouveau nom : {nom_court_colonne}_{index_1based}{extension}
                            new_filename = f"{short_col}_{int(row_idx) + 1}{ext}"

                            # Chemin complet dans le ZIP de sortie
                            dest_path = f"{subfolder}/{new_filename}"

                            # Lire le fichier depuis le ZIP source et l'écrire dans le ZIP de sortie
                            file_data = zin.read(media_index[original_name])
                            zout.writestr(dest_path, file_data)

        filename = f"{form_id}_structured_media.zip"
        return output.getvalue(), filename

    # ─────────────────────────────────────────────────────────────────────────
    # US 8 — Export Shapefile (Option 3 : Table / Type de géométrie / fichiers)
    # ─────────────────────────────────────────────────────────────────────────

    # Correspondance type ODK → suffixe de dossier et de fichier
    _ODK_GEO_TYPES = {
        "geopoint": "points",
        "geotrace": "lignes",
        "geoshape": "polygones",
    }

    # Suffixe court pour le nom de fichier
    _GEOM_FILE_SUFFIX = {
        "geopoint": "point",
        "geotrace": "linestring",
        "geoshape": "polygon",
    }

    def _detect_geo_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Détecte les colonnes géographiques dans un DataFrame ODK.
        ODK stocke les géométries sous forme de chaînes :
        - geopoint  : "lat lon alt acc"
        - geotrace  : "lat1 lon1 alt1 acc1; lat2 lon2 alt2 acc2; ..."
        - geoshape  : "lat1 lon1 alt1 acc1; lat2 lon2 alt2 acc2; ... lat1 lon1 alt1 acc1"

        Retourne : { nom_colonne: "geopoint"|"geotrace"|"geoshape" }
        """
        geo_pattern = re.compile(
            r"^-?\d+\.?\d*\s+-?\d+\.?\d*(\s+-?\d+\.?\d*)?(\s+-?\d+\.?\d*)?"
        )
        result: Dict[str, str] = {}

        for col in df.columns:
            sample = df[col].dropna().astype(str).head(10)
            if sample.empty:
                continue

            # Prendre la première valeur non-vide
            first = sample.iloc[0].strip()
            if not first:
                continue

            # Séparer par ";" pour compter les points
            parts = [p.strip() for p in first.split(";") if p.strip()]
            if not parts:
                continue

            # Vérifier que le premier segment ressemble à une coordonnée ODK
            if not geo_pattern.match(parts[0]):
                continue

            if len(parts) == 1:
                result[col] = "geopoint"
            else:
                # geoshape : premier et dernier point identiques (polygone fermé)
                first_pt = parts[0].split()[:2]
                last_pt = parts[-1].split()[:2]
                if first_pt == last_pt:
                    result[col] = "geoshape"
                else:
                    result[col] = "geotrace"

        return result

    def _parse_geopoint(self, value: str):
        """'lat lon alt acc' → Point(lon, lat)"""
        from shapely.geometry import Point

        parts = str(value).strip().split()
        if len(parts) >= 2:
            return Point(float(parts[1]), float(parts[0]))
        return None

    def _parse_geotrace(self, value: str):
        """'lat1 lon1;lat2 lon2;...' → LineString"""
        from shapely.geometry import LineString

        coords = []
        for seg in str(value).strip().split(";"):
            parts = seg.strip().split()
            if len(parts) >= 2:
                coords.append((float(parts[1]), float(parts[0])))
        return LineString(coords) if len(coords) >= 2 else None

    def _parse_geoshape(self, value: str):
        """'lat1 lon1;lat2 lon2;...' → Polygon"""
        from shapely.geometry import Polygon

        coords = []
        for seg in str(value).strip().split(";"):
            parts = seg.strip().split()
            if len(parts) >= 2:
                coords.append((float(parts[1]), float(parts[0])))
        return Polygon(coords) if len(coords) >= 3 else None

    def _truncate_dbf_columns(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Tronque les noms de colonnes à 10 caractères (limite DBF).
        Retourne le DataFrame modifié + mapping {nom_tronqué: nom_original}.
        """
        mapping: Dict[str, str] = {}
        new_cols: List[str] = []
        seen: set = set()
        for col in df.columns:
            truncated = col[:10]
            counter = 1
            candidate = truncated
            while candidate in seen:
                suffix = str(counter)
                candidate = truncated[: 10 - len(suffix)] + suffix
                counter += 1
            seen.add(candidate)
            mapping[candidate] = col
            new_cols.append(candidate)
        df = df.copy()
        df.columns = new_cols
        return df, mapping

    def _build_geodataframe_for_column(
        self,
        df: pd.DataFrame,
        geo_col: str,
        geo_type: str,
        geo_cols_all: Dict[str, str],
    ):
        """
        Construit un GeoDataFrame pour une colonne géographique donnée.
        Les autres colonnes géo sont exclues des attributs (elles ont leur propre couche).
        """
        import geopandas as gpd

        parsers = {
            "geopoint": self._parse_geopoint,
            "geotrace": self._parse_geotrace,
            "geoshape": self._parse_geoshape,
        }
        parser = parsers[geo_type]

        geometries = df[geo_col].apply(
            lambda v: parser(v) if pd.notna(v) and str(v).strip() else None
        )
        valid_mask = geometries.notna()
        if not valid_mask.any():
            return None

        # Colonnes attributaires : tout sauf les colonnes géo
        attr_cols = [c for c in df.columns if c not in geo_cols_all]
        attr_df = df.loc[valid_mask, attr_cols].copy()
        attr_df, col_mapping = self._truncate_dbf_columns(attr_df)

        gdf = gpd.GeoDataFrame(
            attr_df,
            geometry=geometries[valid_mask].values,
            crs="EPSG:4326",
        )
        return gdf, col_mapping

    def _gdf_to_shp_bytes(self, gdf, layer_name: str) -> Dict[str, bytes]:
        """
        Exporte un GeoDataFrame vers les fichiers Shapefile (.shp, .dbf, .prj, .cpg, .shx)
        et retourne un dict { "layer_name.ext": bytes }.
        """
        result: Dict[str, bytes] = {}
        with tempfile.TemporaryDirectory() as tmpdir:
            shp_path = os.path.join(tmpdir, f"{layer_name}.shp")
            gdf.to_file(shp_path, driver="ESRI Shapefile", encoding="utf-8")
            for ext in [".shp", ".dbf", ".prj", ".cpg", ".shx"]:
                file_path = os.path.join(tmpdir, f"{layer_name}{ext}")
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        result[f"{layer_name}{ext}"] = f.read()
        return result

    def export_shapefile(
        self,
        project_id: int,
        form_id: str,
    ) -> Tuple[bytes, str]:
        """
        Structure produite dans le ZIP :
            {form_id}_shapefile.zip
            ├── README.txt
            ├── {table}/
            │   ├── points/
            │   │   ├── {table}__{champ}__point.shp
            │   │   ├── {table}__{champ}__point.dbf
            │   │   ├── {table}__{champ}__point.prj
            │   │   ├── {table}__{champ}__point.cpg
            │   │   └── {table}__{champ}__point.shx
            │   └── lignes/
            │       └── ...
            └── {repeat}/
                └── polygones/
                    └── ...

        Règles :
        - Un dossier par table (CSV) : table principale + répétitions
        - Dans chaque dossier de table, un sous-dossier par type de géométrie (points/lignes/polygones)
        - Nommage des fichiers : {table}__{champ}__{type_geom}.{ext}
        - Projection : WGS84 (EPSG:4326), encodage UTF-8
        - Colonnes DBF tronquées à 10 caractères (contrainte Shapefile)
        - Un README.txt documente les couches et les troncatures de colonnes
        """
        # 1. Télécharger le ZIP ODK (sans pièces jointes pour alléger)
        zip_content = self.zip_submissions(project_id, form_id)

        readme_lines: List[str] = [
            f"Export Shapefile — Formulaire : {form_id}",
            "Projection : WGS84 (EPSG:4326)",
            "Encodage : UTF-8",
            "Structure : Table / Type de géométrie / Fichiers",
            "",
            "Couches disponibles :",
        ]
        truncation_notes: List[str] = []

        output = io.BytesIO()

        with zipfile.ZipFile(io.BytesIO(zip_content)) as zin:
            csv_entries = [e for e in zin.namelist() if e.endswith(".csv")]

            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zout:
                for csv_entry in csv_entries:
                    # Nom de la table = nom du CSV sans extension
                    table_name = os.path.basename(csv_entry).rsplit(".", 1)[0]

                    try:
                        csv_content = zin.read(csv_entry).decode("utf-8-sig")
                        df = pd.read_csv(io.StringIO(csv_content))
                    except Exception:
                        continue

                    if df.empty:
                        continue

                    # Détecter les colonnes géographiques
                    geo_cols = self._detect_geo_columns(df)
                    if not geo_cols:
                        continue

                    for geo_col, geo_type in geo_cols.items():
                        result = self._build_geodataframe_for_column(
                            df, geo_col, geo_type, geo_cols
                        )
                        if result is None:
                            continue
                        gdf, col_mapping = result

                        # Nom court de la colonne (sans préfixe de groupe)
                        short_col = geo_col.rsplit("/", 1)[-1]

                        # Suffixes pour dossier et nom de fichier
                        folder_type = self._ODK_GEO_TYPES[geo_type]  # "points"
                        file_suffix = self._GEOM_FILE_SUFFIX[geo_type]  # "point"

                        # Nom de la couche : {table}__{champ}__{type}
                        layer_name = f"{table_name}__{short_col}__{file_suffix}"

                        # Chemin dans le ZIP : {table}/{type_geom}/
                        zip_folder = f"{table_name}/{folder_type}"

                        # Exporter vers bytes Shapefile
                        shp_files = self._gdf_to_shp_bytes(gdf, layer_name)

                        for filename, file_bytes in shp_files.items():
                            zout.writestr(f"{zip_folder}/{filename}", file_bytes)

                        # README
                        readme_lines.append(
                            f"  {zip_folder}/{layer_name}"
                            f'  →  Table "{table_name}", champ "{short_col}"'
                            f" ({file_suffix}), {len(gdf)} entités"
                        )

                        # Notes de troncature
                        for short, original in col_mapping.items():
                            if short != original:
                                truncation_notes.append(
                                    f"  {original} → {short}  (table: {table_name})"
                                )

                # Ajouter les notes de troncature au README
                if truncation_notes:
                    readme_lines.append("")
                    readme_lines.append(
                        "Colonnes tronquées (limite DBF 10 caractères) :"
                    )
                    readme_lines.extend(truncation_notes)

                zout.writestr("README.txt", "\n".join(readme_lines))

        filename = f"{form_id}_shapefile.zip"
        return output.getvalue(), filename
