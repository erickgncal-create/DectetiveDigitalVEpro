"""
Módulo de Conectores Automatizados y Monitores de Fuentes Abiertas.
Implementa el generador de operadores booleanos y estrategias combinadas
del Anexo V del Manual de Detectives Digitales (IPYS Venezuela).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple
import re
import uuid

from .models import TipoMaterial, FuenteDigital, CoincidenciaDialogo


@dataclass
class QueryBuilderAnexoV:
    """
    Constructor de consultas avanzadas basadas en el Anexo V de IPYS Venezuela.
    Soporta sintaxis de Google Dorks y operadores de redes sociales (X/Twitter).
    """

    @staticmethod
    def construir_query_x(
        palabras_clave: List[str],
        frase_exacta: Optional[str] = None,
        excluir_terminos: Optional[List[str]] = None,
        usuario_from: Optional[str] = None,
        usuario_to: Optional[str] = None,
        desde_fecha: Optional[str] = None,  # YYYY-MM-DD
        hasta_fecha: Optional[str] = None,  # YYYY-MM-DD
        solo_imagenes: bool = False,
        solo_videos: bool = False,
        cerca_de: Optional[str] = None,      # Ej: "Caracas", "Maracaibo"
    ) -> str:
        """Construye un operador booleano estricto para búsqueda y monitoreo en X."""
        partes = []

        if palabras_clave:
            partes.append(" ".join(palabras_clave))
        
        if frase_exacta:
            partes.append(f'"{frase_exacta.strip()}"')

        if excluir_terminos:
            for exc in excluir_terminos:
                partes.append(f'-"{exc.strip()}"' if " " in exc else f'-{exc.strip()}')

        if usuario_from:
            partes.append(f"from:{usuario_from.lstrip('@')}")

        if usuario_to:
            partes.append(f"to:{usuario_to.lstrip('@')}")

        if desde_fecha:
            partes.append(f"since:{desde_fecha}")

        if hasta_fecha:
            partes.append(f"until:{hasta_fecha}")

        if solo_videos:
            partes.append("filter:videos")
        elif solo_imagenes:
            partes.append("filter:media")

        if cerca_de:
            partes.append(f'near:"{cerca_de}"')

        return " ".join(partes)

    @staticmethod
    def construir_google_dork(
        terminos: List[str],
        dominio_site: Optional[str] = None,
        tipo_archivo: Optional[str] = None,  # pdf, doc, etc.
        en_titulo: Optional[str] = None,
        en_url: Optional[str] = None,
        despues_de: Optional[str] = None,    # YYYY-MM-DD
        antes_de: Optional[str] = None,      # YYYY-MM-DD
        alternativas_or: Optional[List[str]] = None,
        excluir_sitio: Optional[str] = None,
    ) -> str:
        """Construye un Google Dork avanzado para investigación documental y gacetas."""
        partes = []

        if dominio_site:
            partes.append(f"site:{dominio_site}")

        if tipo_archivo:
            partes.append(f"filetype:{tipo_archivo}")

        if en_titulo:
            partes.append(f'intitle:"{en_titulo}"')

        if en_url:
            partes.append(f'inurl:{en_url}')

        if terminos:
            partes.append(" ".join(terminos))

        if alternativas_or:
            or_expr = " OR ".join([f'"{a}"' if " " in a else a for a in alternativas_or])
            partes.append(f"({or_expr})")

        if despues_de:
            partes.append(f"after:{despues_de}")

        if antes_de:
            partes.append(f"before:{antes_de}")

        if excluir_sitio:
            partes.append(f"-site:{excluir_sitio}")

        return " ".join(partes)


@dataclass
class ReglaMonitor:
    id: str
    nombre: str
    plataforma: str
    consulta_sintactica: str
    objetivo_ddhh: str
    frecuencia_segundos: int = 300
    activo: bool = True
    ultima_ejecucion: Optional[datetime] = None


class AutomatedSourceMonitor:
    """
    Administrador de monitores automáticos que escanean fuentes abiertas en la web
    utilizando las reglas booleanas del Anexo V y envían los hallazgos a la bóveda forense.
    """

    def __init__(self, engine):
        self.engine = engine
        self.monitores: Dict[str, ReglaMonitor] = {}

    def registrar_monitor(
        self,
        nombre: str,
        plataforma: str,
        consulta_sintactica: str,
        objetivo_ddhh: str,
        frecuencia_segundos: int = 300
    ) -> ReglaMonitor:
        monitor_id = f"mon_{uuid.uuid4().hex[:8]}"
        regla = ReglaMonitor(
            id=monitor_id,
            nombre=nombre,
            plataforma=plataforma,
            consulta_sintactica=consulta_sintactica,
            objetivo_ddhh=objetivo_ddhh,
            frecuencia_segundos=frecuencia_segundos
        )
        self.monitores[monitor_id] = regla
        return regla

    def procesar_publicacion_entrante(
        self,
        monitor_id: str,
        texto: str,
        url_origen: str,
        autor_perfil: str,
        timestamp_publicacion: datetime,
        tipo_material: TipoMaterial = TipoMaterial.PUBLICACION_REDES,
        evento_id: Optional[str] = None
    ) -> Tuple[FuenteDigital, List[CoincidenciaDialogo]]:
        """
        Simula o procesa la captura automática de una publicación descubierta por un monitor,
        preservándola con hash SHA-256 e integrándola a la matriz de diálogo.
        """
        monitor = self.monitores.get(monitor_id)
        nombre_monitor = monitor.nombre if monitor else "Monitor Automático"

        content_bytes = texto.encode("utf-8")
        filename = f"capture_{uuid.uuid4().hex[:8]}.txt"

        fuente, dialogos = self.engine.ingresar_evidencia(
            filename=filename,
            content_bytes=content_bytes,
            url_origen=url_origen,
            tipo_material=tipo_material,
            plataforma=monitor.plataforma if monitor else "Web OSINT",
            autor_perfil=autor_perfil,
            investigador_id=f"MonitorRobot-{nombre_monitor}",
            ip_recoleccion="10.8.0.2 (Túnel VPN Rotativo Seguro)",
            identidad_virtual="MonitorBot_IPYS_Standard",
            texto_contenido=texto,
            fecha_publicacion_original=timestamp_publicacion,
            evento_asociado_id=evento_id
        )

        return fuente, dialogos
