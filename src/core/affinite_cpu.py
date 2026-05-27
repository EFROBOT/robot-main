import os


def fixer_affinite_cpu(cpu_id: int, logs=None, nom_thread: str = "") -> bool:
    try:
        os.sched_setaffinity(0, {int(cpu_id)})
        if logs is not None:
            logs.log("RPi", f"Affinité CPU fixée: {nom_thread or 'thread'} -> CPU{cpu_id}")
        return True
    except Exception as exc:
        if logs is not None:
            logs.log("WARN", f"Affinité CPU impossible ({nom_thread or 'thread'}): {exc}")
        return False
