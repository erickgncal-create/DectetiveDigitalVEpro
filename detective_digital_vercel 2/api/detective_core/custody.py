import hashlib
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from .models import FuenteDigital, TipoMaterial, RegistroCustodia


class CustodyManager:
    def __init__(self, base_storage_dir: str):
        self.base_dir = Path(base_storage_dir)
        self.probatory_dir = self.base_dir / "vault" / "probatory"
        self.working_dir = self.base_dir / "workspace" / "working"
        self.audit_log_dir = self.base_dir / "audit_logs"

        self.probatory_dir.mkdir(parents=True, exist_ok=True)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def calculate_sha256_bytes(data: bytes) -> str:
        hasher = hashlib.sha256()
        hasher.update(data)
        return hasher.hexdigest()

    def preserve_evidence(
        self,
        evidence_id: str,
        filename: str,
        content_bytes: bytes,
        url_origen: str,
        tipo_material: TipoMaterial,
        plataforma: str,
        autor_perfil: str,
        investigador_id: str,
        ip_recoleccion: str,
        identidad_virtual: Optional[str] = None,
        texto_contenido: str = "",
        metadatos_exif: Optional[Dict[str, Any]] = None,
        codigo_fuente_html: Optional[str] = None,
        archivado_externo_url: Optional[str] = None,
        fecha_publicacion_original: Optional[datetime] = None,
    ) -> FuenteDigital:
        sha256_hash = self.calculate_sha256_bytes(content_bytes)

        ext = Path(filename).suffix
        safe_name = f"{evidence_id}_{sha256_hash[:12]}{ext}"
        probatory_path = self.probatory_dir / safe_name
        working_path = self.working_dir / safe_name

        if not probatory_path.exists():
            with open(probatory_path, "wb") as f:
                f.write(content_bytes)
            os.chmod(probatory_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        with open(working_path, "wb") as f:
            f.write(content_bytes)

        sello_tiempo_utc = datetime.now(timezone.utc).isoformat()
        registro_custodia = RegistroCustodia(
            investigador_id=investigador_id,
            ip_recoleccion=ip_recoleccion,
            identidad_virtual_usada=identidad_virtual,
            sello_tiempo_utc=sello_tiempo_utc,
            herramientas_utilizadas=["DetectiveDigital-CustodyModule-v1.0", "SHA256-NIST-FIPS-180-4"],
            hash_sha256_probatorio=sha256_hash,
        )

        return FuenteDigital(
            id=evidence_id,
            url_origen=url_origen,
            tipo_material=tipo_material,
            plataforma=plataforma,
            autor_perfil=autor_perfil,
            hash_sha256=sha256_hash,
            ruta_copia_probatoria=str(probatory_path),
            ruta_copia_trabajo=str(working_path),
            registro_custodia=registro_custodia,
            fecha_publicacion_original=fecha_publicacion_original,
            texto_contenido=texto_contenido,
            metadatos_exif=metadatos_exif or {},
            codigo_fuente_html=codigo_fuente_html,
            archivado_externo_url=archivado_externo_url,
        )
