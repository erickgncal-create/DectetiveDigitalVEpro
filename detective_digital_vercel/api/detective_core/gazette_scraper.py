"""
Módulo de Procesamiento y Análisis Forense de Gacetas Oficiales y Boletines Judiciales.
Especializado en extracción de nombramientos de mando, resoluciones y delegaciones operativas
para establecer pruebas de vinculación (Protocolo de Berkeley §60).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
import re
import uuid

import pypdf

from .models import FuenteDigital, TipoMaterial, Entidad, TipoEntidad, CoincidenciaDialogo
from .extractor import ORGANISMOS_SEGURIDAD, UBICACIONES_REFERENCIA


@dataclass
class NombramientoMando:
    id: str
    numero_gaceta: str
    fecha_gaceta: Optional[str]
    numero_resolucion: str
    organo_emisor: str
    funcionario_nombre: str
    rango_militar_policial: Optional[str]
    cargo_asignado: str
    competencia_territorial: Optional[str]
    texto_contexto: str


class GazetteScraperProcessor:
    """
    Procesa documentos PDF de Gacetas Oficiales y boletines estatales,
    extrayendo texto, identificando resoluciones de mando y vinculándolas
    con incidentes en el grafo relacional.
    """

    def __init__(self, engine):
        self.engine = engine
        self.nombramientos_registrados: List[NombramientoMando] = []

    @staticmethod
    def extraer_texto_pdf(pdf_path_or_bytes) -> str:
        """Extrae el contenido textual de un archivo o stream PDF utilizando pypdf."""
        texto_completo = []
        try:
            if isinstance(pdf_path_or_bytes, (str, Path)):
                reader = pypdf.PdfReader(str(pdf_path_or_bytes))
            else:
                import io
                reader = pypdf.PdfReader(io.BytesIO(pdf_path_or_bytes))

            for page_idx, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                texto_completo.append(txt)
        except Exception as e:
            return f"[Error al parsear PDF: {str(e)}]"

        return "\n".join(texto_completo)

    @staticmethod
    def extraer_nombramientos(texto: str) -> List[NombramientoMando]:
        """
        Analiza patrones jurídicos y lingüísticos típicos de Gacetas Oficiales venezolanas
        para identificar actos administrativos de asignación de mando.
        """
        nombramientos = []
        texto_normalizado = " ".join(texto.split())

        # 1. Detectar Número de Gaceta
        patron_gaceta = r"GACETA\s+OFICIAL\s+DE\s+LA\s+REP[UÚ]BLICA\s+BOLIVARIANA\s+DE\s+VENEZUELA\s*(?:N[º°]\s*|N[uú]mero\s*)?([0-9\.\,]+|Extraordinaria\s*N[º°]\s*[0-9\.\,]+)"
        match_gaceta = re.search(patron_gaceta, texto_normalizado, re.IGNORECASE)
        num_gaceta = match_gaceta.group(1).strip() if match_gaceta else "Gaceta Oficial No Identificada"

        # 2. Detectar Fecha de Gaceta
        patron_fecha = r"(Caracas,\s+[0-9]{1,2}\s+de\s+[a-zA-Z]+\s+de\s+[0-9]{4}|[0-9]{2}/[0-9]{2}/[0-9]{4})"
        match_fecha = re.search(patron_fecha, texto_normalizado, re.IGNORECASE)
        fecha_gaceta = match_fecha.group(1).strip() if match_fecha else None

        # 3. Detectar Resoluciones o Decretos de designación
        patron_designacion = re.compile(
            r"(?:Resoluci[oó]n|Decreto)\s+(?:N[º°]\s*([0-9\.\-]+))?.*?"
            r"(?:se\s+designa|se\s+nombra|des[ií]gnese)\s+al\s+ciudadano\s+"
            r"((?:Coronel|General(?:\s+de\s+Brigada|\s+de\s+Divisi[oó]n)?|Mayor|Capit[aá]n|Teniente(?:\s+Coronel)?|Comisionado(?:\s+Mayor|\s+Jefe)?|Inspector(?:\s+Jefe)?)\s+)?"
            r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)"
            r".*?(?:como|en\s+el\s+cargo\s+de)\s+"
            r"([^,;.]+)",
            re.IGNORECASE
        )

        matches = patron_designacion.finditer(texto_normalizado)
        for m in matches:
            res_num = m.group(1) or "S/N"
            rango = m.group(2).strip() if m.group(2) else None
            nombre_funcionario = m.group(3).strip()
            cargo = m.group(4).strip()

            # Detectar competencia territorial en el entorno del texto
            contexto = texto_normalizado[max(0, m.start() - 100): min(len(texto_normalizado), m.end() + 250)]
            territorio = None
            for top, data in UBICACIONES_REFERENCIA.items():
                if re.search(rf"\b{re.escape(top)}\b", contexto, re.IGNORECASE):
                    territorio = data["toponimo"]
                    break

            # Detectar órgano emisor
            organo = "Órgano de Seguridad del Estado"
            for k, org in ORGANISMOS_SEGURIDAD.items():
                if any(re.search(rf"\b{re.escape(alias)}\b", contexto, re.IGNORECASE) for alias in org["alias"]):
                    organo = org["canonico"]
                    break

            nombre_completo = f"{rango + ' ' if rango else ''}{nombre_funcionario}"
            nombramiento = NombramientoMando(
                id=f"nom_{uuid.uuid4().hex[:8]}",
                numero_gaceta=num_gaceta,
                fecha_gaceta=fecha_gaceta,
                numero_resolucion=res_num,
                organo_emisor=organo,
                funcionario_nombre=nombre_completo,
                rango_militar_policial=rango,
                cargo_asignado=cargo,
                competencia_territorial=territorio,
                texto_contexto=contexto.strip()
            )
            nombramientos.append(nombramiento)

        return nombramientos

    def procesar_archivo_gaceta_pdf(
        self,
        pdf_path_or_bytes,
        filename: str,
        url_origen: str,
        investigador_id: str = "Investigador-Gacetas-01",
        ip_recoleccion: str = "127.0.0.1",
        identidad_virtual: Optional[str] = "Scraper_Gacetas_Bot"
    ) -> Tuple[FuenteDigital, List[NombramientoMando], List[CoincidenciaDialogo]]:
        """
        Ingesta una gaceta en PDF, preserva la copia probatoria inmutable en la bóveda,
        extrae los nombramientos y dispara el motor de diálogo para vincular la cadena de mando.
        """
        if isinstance(pdf_path_or_bytes, (str, Path)):
            with open(pdf_path_or_bytes, "rb") as f:
                content_bytes = f.read()
        else:
            content_bytes = pdf_path_or_bytes

        # 1. Extraer texto del documento PDF
        texto = self.extraer_texto_pdf(content_bytes)

        # 2. Ingesta formal con cadena de custodia en el engine
        fuente, dialogos = self.engine.ingresar_evidencia(
            filename=filename,
            content_bytes=content_bytes,
            url_origen=url_origen,
            tipo_material=TipoMaterial.DOCUMENTO_PDF,
            plataforma="Gaceta Oficial Digital",
            autor_perfil="Imprenta Nacional / MPPRIJP",
            investigador_id=investigador_id,
            ip_recoleccion=ip_recoleccion,
            identidad_virtual=identidad_virtual,
            texto_contenido=texto,
            fecha_publicacion_original=datetime.now(timezone.utc)
        )

        # 3. Extraer nombramientos estructurados
        nombramientos = self.extraer_nombramientos(texto)
        self.nombramientos_registrados.extend(nombramientos)

        return fuente, nombramientos, dialogos
