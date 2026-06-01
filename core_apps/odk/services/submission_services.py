import logging
from typing import Dict, List, Optional

from .base_service import BaseODKService
from .exceptions import ODKValidationError

logger = logging.getLogger(__name__)


class ODKSubmissionService(BaseODKService):
    """Service pour la gestion des soumissions ODK"""

    def get_form_submissions(self, project_id: int, form_id: str) -> List[Dict]:
        """Récupère les soumissions d'un formulaire spécifique, juste les metadata des soumissions"""
        try:
            return self._make_request(
                "GET",
                f"projects/{project_id}/forms/{form_id}/submissions",
                headers={"X-Extended-Metadata": "true"},
            )
        except Exception as e:
            self._log_action(
                "list_submissions",
                "submission",
                f"{project_id}/{form_id}",
                {
                    "error": str(e),
                    "odk_account": (
                        self.current_account["id"] if self.current_account else None
                    ),
                },
                success=False,
            )
            raise

    def get_submission(self, project_id: int, form_id: str, instance_id: str) -> Dict:
        """Récupère une soumission spécifique"""
        try:
            return self._make_request(
                "GET",
                f"projects/{project_id}/forms/{form_id}/submissions/{instance_id}",
                headers={"X-Extended-Metadata": "true"},
            )
        except Exception as e:
            self._log_action(
                "get_submission",
                "submission",
                f"{project_id}/{form_id}/{instance_id}",
                {
                    "error": str(e),
                    "odk_account": (
                        self.current_account["id"] if self.current_account else None
                    ),
                },
                success=False,
            )
            raise

    def export_submissions(
        self, project_id: int, form_id: str, to: str = "csv"
    ) -> bytes:
        """Exporte les soumissions d'un formulaire en CSV ou XLSX"""
        try:
            result = self._make_request(
                "POST",
                f"projects/{project_id}/forms/{form_id}/submissions.csv",
                return_json=False,
            )
            if to == "xlsx":
                from io import BytesIO, StringIO

                import pandas as pd

                df = pd.read_csv(StringIO(result.decode("utf-8")))
                output = BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name="Submissions")
                return output.getvalue()

            return result

        except ODKValidationError:
            raise
        except Exception as e:
            self._log_action(
                "export_submissions_csv",
                "submission",
                f"{project_id}/{form_id}",
                {
                    "error": str(e),
                    "odk_account": (
                        self.current_account["id"] if self.current_account else None
                    ),
                },
                success=False,
            )
            raise

    def submissions_data(self, project_id: int, form_id: str, expand: bool = False):
        try:
            headers = {"content-type": "application/json"}
            url = f"projects/{project_id}/forms/{form_id}.svc/Submissions"
            if expand:
                url += "?$expand=*"
            return self._make_request(
                "GET",
                url,
                headers=headers,
            )
        except ODKValidationError:
            raise
        except Exception as e:
            self._log_action(
                "export_submissions_data",
                "submission",
                f" project:{project_id}| form:{form_id} ",
                {
                    "error": str(e),
                    "odk_account": (
                        self.current_account["id"] if self.current_account else None
                    ),
                },
                success=False,
            )

    def submission_repeat_data(
        self, project_id: int, form_id: str, repeat_name: str, instance_id: str = None
    ):
        try:
            headers = {"content-type": "application/json"}

            if instance_id:
                # On retire le préfixe "Submissions." si présent pour la syntaxe de navigation
                clean_name = repeat_name
                if clean_name.startswith("Submissions."):
                    clean_name = clean_name[len("Submissions.") :]

                # Format: Submissions('uuid:...')/repeat_name
                url = f"projects/{project_id}/forms/{form_id}.svc/Submissions('{instance_id}')/{clean_name}"
            else:
                # Fallback standard pour la liste complète (ex: Submissions.demographic)
                endpoint = (
                    repeat_name
                    if repeat_name.startswith("Submissions")
                    else f"Submissions.{repeat_name}"
                )
                url = f"projects/{project_id}/forms/{form_id}.svc/{endpoint}"

            return self._make_request(
                "GET",
                url,
                headers=headers,
            )
        except ODKValidationError:
            raise
        except Exception as e:
            self._log_action(
                "submission_repeat_data",
                "submission",
                f"project:{project_id}| form:{form_id}|{repeat_name} | instance:{instance_id}",
                {
                    "error": str(e),
                },
                success=False,
            )

    def form_repeat_list(self, project_id: int, form_id: str):
        try:
            return self._make_request(
                "GET", f"projects/{project_id}/forms/{form_id}.svc"
            )
        except ODKValidationError:
            raise

    def get_submissions_geojson(self, project_id: int, form_id: str) -> Dict:
        """
        Étape 2 — Récupère le GeoJSON natif ODK pour la table principale.
        Endpoint : GET /v1/projects/{projectId}/forms/{xmlFormId}/submissions.geojson
        Retourne un FeatureCollection avec geometry + properties.fieldpath + id.
        """
        try:
            return self._make_request(
                "GET",
                f"projects/{project_id}/forms/{form_id}/submissions.geojson",
            )
        except ODKValidationError:
            raise
        except Exception as e:
            self._log_action(
                "get_submissions_geojson",
                "submission",
                f"project:{project_id}| form:{form_id}",
                {
                    "error": str(e),
                    "odk_account": (
                        self.current_account["id"] if self.current_account else None
                    ),
                },
                success=False,
            )
            raise

    def get_geojson_unified(self, project_id: int, form_id: str) -> Dict:
        """
        Construit un FeatureCollection GeoJSON unifié (table principale + repeats).
        Utilise le schéma du formulaire et une extraction récursive pour les groupes imbriqués.
        """
        features = []
        tables_used = []
        GEO_TYPES = {"geopoint", "geotrace", "geoshape"}

        # --- Étape 1 : Récupérer le schéma du formulaire ---
        try:
            field_info = self._get_field_info(project_id, form_id)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du schéma : {e}")
            field_info = {}

        # --- Étape 2 : Lister les tables disponibles ---
        entity_sets = []
        try:
            service_doc = self.form_repeat_list(project_id, form_id)
            if service_doc and "value" in service_doc:
                entity_sets = [e["name"] for e in service_doc["value"] if "name" in e]
        except Exception as e:
            logger.warning(f"Impossible de lister les tables OData : {e}")

        # Toujours tenter la table principale si elle n'est pas listée
        if "Submissions" not in entity_sets:
            entity_sets.insert(0, "Submissions")
        else:
            entity_sets.remove("Submissions")
            entity_sets.insert(0, "Submissions")

        # Helper récursif pour extraire les données géo des objets OData imbriqués (groupes)
        def extract_geo_from_row(data_dict, parent_path=""):
            extracted = []
            for k, v in data_dict.items():
                if v is None:
                    continue

                # Le nom dans OData pour les groupes peut varier (souvent imbriqué ou à plat avec .)
                # On tente de matcher avec le schéma
                current_path = f"{parent_path}/{k}" if parent_path else k

                # Récupérer les infos du schéma (type et label)
                info = field_info.get(current_path) or field_info.get(k) or {}
                f_type = info.get("type")
                f_label = info.get("label", k)

                is_geo = f_type in GEO_TYPES or any(gk in k.lower() for gk in GEO_TYPES)

                if isinstance(v, dict):
                    # Si c'est déjà un objet géo (OData GeoJSON)
                    if "type" in v and "coordinates" in v:
                        if is_geo:
                            extracted.append((current_path, f_label, v))
                    else:
                        # C'est un groupe (objet imbriqué), on descend
                        extracted.extend(extract_geo_from_row(v, current_path))
                elif is_geo:
                    # Valeur scalaire (geopoint ODK string "lat lon alt acc")
                    extracted.append((current_path, f_label, v))
            return extracted

        # --- Étape 3 : Parcourir chaque table ---
        for table_name in entity_sets:
            try:
                if table_name == "Submissions":
                    data = self.submissions_data(project_id, form_id)
                    source_label = "main"
                else:
                    data = self.submission_repeat_data(project_id, form_id, table_name)
                    source_label = table_name

                rows = data.get("value", []) if data else []
                if not rows:
                    continue

                table_has_geo = False
                for row in rows:
                    # Extraction récursive (gère les groupes)
                    geo_data = extract_geo_from_row(row)

                    if not geo_data:
                        continue

                    table_has_geo = True

                    # Propriétés de base communes à tous les points de cette ligne
                    base_properties = {
                        k: v for k, v in row.items() if not isinstance(v, (dict, list))
                    }
                    base_properties["source_table"] = source_label
                    base_properties["submission_id"] = row.get(
                        "__Submissions-id", row.get("__id", "")
                    )

                    for field_path, field_label, val in geo_data:
                        geometry = self._odata_geo_to_geojson(val)
                        if geometry is None:
                            continue

                        props = base_properties.copy()
                        props["fieldpath"] = field_path
                        props["fieldlabel"] = field_label

                        features.append(
                            {
                                "type": "Feature",
                                "id": f"{row.get('__id', '')}_{field_path}",
                                "geometry": geometry,
                                "properties": props,
                            }
                        )

                if table_has_geo:
                    tables_used.append(source_label)

            except Exception as e:
                logger.error(f"Erreur table {table_name} : {e}")
                continue

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "total_features": len(features),
                "tables": tables_used,
            },
        }

    def _odata_geo_to_geojson(self, value) -> Optional[Dict]:
        """
        Convertit une valeur géographique ODK (OData ou chaîne brute) en objet geometry GeoJSON.
        Formats supportés :
          - OData GeoJSON natif : {"type": "Point", "coordinates": [...]}
          - Chaîne geopoint ODK : "lat lon alt acc"
          - Chaîne geotrace/geoshape ODK : "lat1 lon1 alt1;lat2 lon2 alt2;..."
        """
        if isinstance(value, dict):
            # Déjà au format GeoJSON (OData retourne parfois un objet)
            if "type" in value and "coordinates" in value:
                return value
            return None

        if not isinstance(value, str) or not value.strip():
            return None

        raw = value.strip()

        # Chaîne multi-points (geotrace / geoshape) : contient des ";"
        if ";" in raw:
            coords = []
            for point_str in raw.split(";"):
                parts = point_str.strip().split()
                if len(parts) >= 2:
                    try:
                        coords.append([float(parts[1]), float(parts[0])])
                    except ValueError:
                        continue
            if len(coords) >= 2:
                # Fermeture du polygone si premier == dernier
                if coords[0] == coords[-1] and len(coords) >= 4:
                    return {"type": "Polygon", "coordinates": [coords]}
                return {"type": "LineString", "coordinates": coords}
            return None

        # Chaîne geopoint simple : "lat lon [alt [acc]]"
        parts = raw.split()
        if len(parts) >= 2:
            try:
                lat, lon = float(parts[0]), float(parts[1])
                alt = float(parts[2]) if len(parts) >= 3 else 0.0
                return {"type": "Point", "coordinates": [lon, lat, alt]}
            except ValueError:
                return None

        return None

    def zip_submissions(self, project_id: int, form_id: str):
        try:
            return self._make_request(
                "GET",
                f"projects/{project_id}/forms/{form_id}/submissions.csv.zip?attachments=false",
                return_json=False,
            )
        except ODKValidationError:
            raise
        except Exception as e:
            self._log_action(
                "export_submissions_zip",
                "submission",
                f" project:{project_id}| form:{form_id} ",
                {
                    "error": str(e),
                    "odk_account": (
                        self.current_account["id"] if self.current_account else None
                    ),
                },
                success=False,
            )
