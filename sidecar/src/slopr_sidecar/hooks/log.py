"""Keeps the last 100 dictations in log.txt, one paragraph each."""

from slopr_sidecar.config import APP_DIR

LOG = APP_DIR / "log.txt"


def on_logged(u):
    old = LOG.read_text("utf-8").split("\n\n") if LOG.exists() else []
    LOG.write_text("\n\n".join([*filter(None, old), " ".join(u.text.split())][-100:]), "utf-8")
