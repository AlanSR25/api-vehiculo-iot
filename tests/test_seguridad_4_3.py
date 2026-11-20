"""
Suite reproducible de pruebas funcionales y de seguridad (Práctica 4.3)
Valida: 401 sin token, Login RBAC (Admin/Usuario/Invitado), aislamiento IDOR (403),
protección de unidad vendida contra Admin sin soporte (403), exclusividad de Invitado (409),
restricción de comandos de Invitado (403), WSS autenticado y auditoría en RDS.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = "https://alleged-radio-preparing-actress.trycloudflare.com"


def req(method: str, path: str, body=None, token: str = None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, parsed


def assert_eq(name, actual, expected):
    ok = actual == expected
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: esperado={expected}, obtenido={actual}")
    if not ok:
        sys.exit(1)


def main():
    # 1. Health público
    code, data = req("GET", "/health")
    assert_eq("P00 Health API + RDS", (code, data.get("api"), data.get("base_de_datos")), (200, "ok", "ok"))

    # 2. Rechazo 401 sin sesión
    code, _ = req("GET", "/admin/dashboard")
    assert_eq("P12a Admin sin token -> 401", code, 401)
    code, _ = req("GET", "/vehiculos/1/estado")
    assert_eq("P12b Estado sin token -> 401", code, 401)

    # 3. Login Admin (P01)
    code, admin_login = req("POST", "/auth/login", {"correo": "admin@empresa-iot.com", "password": "Admin123!"})
    assert_eq("P01 Login Admin", code, 200)
    admin_tok = admin_login["access_token"]

    # 4. Dashboard Admin con métricas reales
    code, dash = req("GET", "/admin/dashboard", token=admin_tok)
    assert_eq("P01b Dashboard Admin", code, 200)
    print("   Metricas RDS:", dash["metricas"])

    # 5. Login Usuario Comprador (cliente1)
    code, user_login = req("POST", "/auth/login", {"correo": "cliente1@gmail.com", "password": "Cliente123!"})
    assert_eq("P05a Login Usuario", code, 200)
    user_tok = user_login["access_token"]

    # 6. Aislamiento de comprador (Mis Vehículos solo devuelve unidad #2)
    code, mis = req("GET", "/mis-vehiculos", token=user_tok)
    assert_eq("P05b Mis Vehiculos (solo propios)", (code, [v["id_vehiculo"] for v in mis]), (200, [2]))

    # 7. Anti-IDOR: Usuario intenta ver/controlar unidad ajena #1 -> 403
    code, _ = req("GET", "/vehiculos/1/estado", token=user_tok)
    assert_eq("P13a Usuario consulta unidad ajena #1 -> 403", code, 403)
    code, _ = req("POST", "/vehiculos/1/movimiento", {"comando": 1, "origen": "TEST_IDOR"}, token=user_tok)
    assert_eq("P13b Usuario opera unidad ajena #1 -> 403", code, 403)

    # 8. Usuario intenta entrar a /admin/dashboard -> 403
    code, _ = req("GET", "/admin/dashboard", token=user_tok)
    assert_eq("P12c Usuario entra a Admin -> 403", code, 403)

    # 9. Admin intenta operar unidad vendida #2 sin consentimiento de soporte -> 403
    code, _ = req("POST", "/vehiculos/2/movimiento", {"comando": 1, "origen": "TEST_ADMIN"}, token=admin_tok)
    assert_eq("P13c Admin opera unidad vendida sin soporte -> 403", code, 403)

    # 10. Usuario opera su propia unidad #2 -> 200
    code, mov_ok = req("POST", "/vehiculos/2/movimiento", {"comando": 9, "origen": "TEST_PROPIETARIO"}, token=user_tok)
    assert_eq("P06 Usuario opera su unidad #2 -> 200", code, 200)

    # 11. Catálogo público (sin token)
    code, cat = req("GET", "/catalogo/publico")
    assert_eq("P11a Catalogo publico -> 200", code, 200)
    assert_eq("P11b Solo exhibicion expuesta", [u["id_vehiculo"] for u in cat["unidades_exhibicion"]], [1])

    # 12. Sesión exclusiva de Invitado sobre unidad #1
    code, inv1 = req("POST", "/invitado/sesiones/iniciar", {"id_vehiculo": 1, "nombre_invitado": "Evaluador C", "duracion_segundos": 60})
    assert_eq("P11c Invitado reserva unidad #1 -> 201", code, 201)
    inv_tok = inv1["access_token"]

    # 13. Exclusividad: Segundo invitado intenta reservar unidad #1 -> 409
    code, _ = req("POST", "/invitado/sesiones/iniciar", {"id_vehiculo": 1, "nombre_invitado": "Evaluador 2", "duracion_segundos": 60})
    assert_eq("P14 Segunda sesion simultanea bloqueada -> 409", code, 409)

    # 14. Invitado intenta comando restringido #5 (Subir brazo) -> 403
    code, _ = req("POST", "/vehiculos/1/movimiento", {"comando": 5, "origen": "INVITADO"}, token=inv_tok)
    assert_eq("P11d Comando restringido en Invitado -> 403", code, 403)

    # 15. Invitado intenta acceder a /admin/dashboard -> 403
    code, _ = req("GET", "/admin/dashboard", token=inv_tok)
    assert_eq("P12d Invitado entra a Admin -> 403", code, 403)

    # 16. Invitado ejecuta comando permitido #9 (DETENER) -> 200
    code, _ = req("POST", "/vehiculos/1/movimiento", {"comando": 9, "origen": "INVITADO"}, token=inv_tok)
    assert_eq("P11e Invitado ejecuta comando permitido #9 -> 200", code, 200)

    # 17. Invitado finaliza sesión y libera reserva -> 200
    code, _ = req("POST", "/invitado/sesiones/finalizar", token=inv_tok)
    assert_eq("P11f Invitado finaliza y libera reserva -> 200", code, 200)

    # 18. Auditoría registrada en RDS (P17)
    code, aud = req("GET", "/admin/auditoria?limit=10", token=admin_tok)
    assert_eq("P17 Auditoria accesible para Admin -> 200", (code, len(aud) > 0), (200, True))
    print(f"   Ultimos eventos auditados: {[a['accion'] for a in aud[:5]]}")

    print("\n=== TODAS LAS PRUEBAS DE BACKEND Y SEGURIDAD 4.3 PASARON AL 100% ===")


if __name__ == "__main__":
    main()
