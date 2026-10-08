import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from .models import Entidad, TipoEntidad


ORGANISMOS_SEGURIDAD = {
    "DGCIM": {
        "canonico": "Dirección General de Contrainteligencia Militar (DGCIM)",
        "alias": ["dgcim", "contrainteligencia militar", "boleita"],
        "tipo": TipoEntidad.ORGANISMO_SEGURIDAD,
    },
    "SEBIN": {
        "canonico": "Servicio Bolivariano de Inteligencia Nacional (SEBIN)",
        "alias": ["sebin", "el helicoide", "plaza venezuela sebin"],
        "tipo": TipoEntidad.ORGANISMO_SEGURIDAD,
    },
    "PNB": {
        "canonico": "Policía Nacional Bolivariana (PNB)",
        "alias": ["pnb", "policia nacional", "policía nacional"],
        "tipo": TipoEntidad.ORGANISMO_SEGURIDAD,
    },
    "DAET": {
        "canonico": "Dirección de Acciones Estratégicas y Tácticas (DAET - PNB)",
        "alias": ["daet", "fuerzas especiales pnb"],
        "tipo": TipoEntidad.ORGANISMO_SEGURIDAD,
    },
    "FAES": {
        "canonico": "Fuerzas de Acciones Especiales (FAES - Disuelto/Transicionado)",
        "alias": ["faes"],
        "tipo": TipoEntidad.ORGANISMO_SEGURIDAD,
    },
    "GNB": {
        "canonico": "Guardia Nacional Bolivariana (GNB)",
        "alias": ["gnb", "guardia nacional", "destacamento gnb", "conas"],
        "tipo": TipoEntidad.ORGANISMO_SEGURIDAD,
    },
    "CICPC": {
        "canonico": "Cuerpo de Investigaciones Científicas, Penales y Criminalísticas (CICPC)",
        "alias": ["cicpc", "cuerpo detectivesco"],
        "tipo": TipoEntidad.ORGANISMO_SEGURIDAD,
    },
}

UBICACIONES_REFERENCIA = {
    "el valle": {"lat": 10.4681, "lon": -66.9069, "toponimo": "El Valle, Caracas"},
    "petare": {"lat": 10.4789, "lon": -66.8042, "toponimo": "Petare, Sucre, Miranda"},
    "catia": {"lat": 10.5186, "lon": -66.9389, "toponimo": "Catia, Sucre, Caracas"},
    "la candelaria": {"lat": 10.5050, "lon": -66.9050, "toponimo": "La Candelaria, Caracas"},
    "chacao": {"lat": 10.4939, "lon": -66.8572, "toponimo": "Chacao, Miranda"},
    "san agustin": {"lat": 10.4917, "lon": -66.9111, "toponimo": "San Agustín, Caracas"},
    "plaza venezuela": {"lat": 10.4961, "lon": -66.8833, "toponimo": "Plaza Venezuela, Caracas"},
    "maracaibo": {"lat": 10.6544, "lon": -71.6294, "toponimo": "Maracaibo, Zulia"},
    "san cristobal": {"lat": 7.7669, "lon": -72.2250, "toponimo": "San Cristóbal, Táchira"},
    "valencia": {"lat": 10.1620, "lon": -68.0077, "toponimo": "Valencia, Carabobo"},
    "barquisimeto": {"lat": 10.0678, "lon": -69.3467, "toponimo": "Barquisimeto, Lara"},
}

PATRONES_VEHICULOS = [
    r"(hilux\s+(?:blanca|negra|gris)?)",
    r"(camioneta\s+sin\s+placas?)",
    r"(veh[ií]culo\s+blindado|vn-?4|ballena|murci[eé]lago)",
    r"(moto\s+alta\s+cilindrada|parrilleros?)",
]

PATRONES_OFICIALES = [
    "enfrentamiento", "abatido", "resistencia a la autoridad",
    "orden y paz", "neutralizado", "acto terrorista", "golpe continuado",
    "delito flagrante", "armas incautadas"
]

PATRONES_TERRENO = [
    "detenci[oó]n arbitraria", "sin orden", "se lo llevaron", "encapuchados",
    "vestidos de negro", "dispararon", "golpearon", "allanaron", "desarmado",
    "auxilio", "sebin", "dgcim", "desaparecido"
]


class ForensicEntityExtractor:
    @staticmethod
    def extract_entities_from_text(text: str) -> List[Entidad]:
        text_lower = text.lower()
        extracted: List[Entidad] = []
        seen_names = set()

        for key, org in ORGANISMOS_SEGURIDAD.items():
            if any(re.search(rf"\b{re.escape(alias)}\b", text_lower) for alias in org["alias"]):
                if org["canonico"] not in seen_names:
                    extracted.append(
                        Entidad(
                            id=f"ent_org_{key.lower()}",
                            tipo=org["tipo"],
                            nombre_canonico=org["canonico"],
                            alias=org["alias"]
                        )
                    )
                    seen_names.add(org["canonico"])

        for pat in PATRONES_VEHICULOS:
            matches = re.findall(pat, text_lower)
            for m in matches:
                canon = m.strip().title()
                if canon not in seen_names:
                    extracted.append(
                        Entidad(
                            id=f"ent_veh_{abs(hash(canon)) % 100000}",
                            tipo=TipoEntidad.VEHICULO,
                            nombre_canonico=canon,
                            alias=[m.strip()]
                        )
                    )
                    seen_names.add(canon)

        for name, data in UBICACIONES_REFERENCIA.items():
            if re.search(rf"\b{re.escape(name)}\b", text_lower):
                if data["toponimo"] not in seen_names:
                    extracted.append(
                        Entidad(
                            id=f"ent_loc_{abs(hash(name)) % 100000}",
                            tipo=TipoEntidad.UBICACION,
                            nombre_canonico=data["toponimo"],
                            alias=[name],
                            detalles={"lat": data["lat"], "lon": data["lon"]}
                        )
                    )
                    seen_names.add(data["toponimo"])

        return extracted

    @staticmethod
    def detect_rhetoric_profile(text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        official_hits = [p for p in PATRONES_OFICIALES if re.search(rf"\b{p}\b", text_lower)]
        witness_hits = [p for p in PATRONES_TERRENO if re.search(rf"\b{p}\b", text_lower)]

        return {
            "perfil_probable": "OFICIAL" if len(official_hits) > len(witness_hits) else "TESTIGO/TERRENO",
            "coincidencias_oficiales": official_hits,
            "coincidencias_terreno": witness_hits,
            "potencial_contradiccion": bool(official_hits and witness_hits)
        }
