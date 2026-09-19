from backend.db import get_conn

STRINGS = {
    "en": {
        "label_aviso": "DEADLINE APPROACHING",
        "label_expirado": "DEADLINE EXPIRED",
        "label_sucesso": "DELIVERED SUCCESSFULLY",
        "task_overdue": "'{title}' was already supposed to be delivered.",
        "task_warning": "'{title}' is due at {due}.",
        "task_success": "'{title}' was delivered successfully.",
        "project_overdue": "The final delivery deadline has already passed.",
        "project_warning": "Final delivery on {due}.",
        "test_message": "This is a test notification.",
    },
    "pt": {
        "label_aviso": "PRAZO A APROXIMAR-SE",
        "label_expirado": "PRAZO EXPIRADO",
        "label_sucesso": "ENTREGUE COM SUCESSO",
        "task_overdue": "'{title}' já devia ter sido entregue.",
        "task_warning": "'{title}' vence às {due}.",
        "task_success": "'{title}' foi entregue com sucesso.",
        "project_overdue": "O prazo de entrega final já passou.",
        "project_warning": "Entrega final a {due}.",
        "test_message": "Esta é uma notificação de teste.",
    },
}


def get_lang():
    try:
        conn = get_conn()
        row = conn.execute("SELECT value FROM settings WHERE key = 'lang'").fetchone()
        conn.close()
        return row["value"] if row and row["value"] in STRINGS else "en"
    except Exception:
        return "en"


def tr(key, **kwargs):
    lang = get_lang()
    text = STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))
    return text.format(**kwargs) if kwargs else text
