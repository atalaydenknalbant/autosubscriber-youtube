from __future__ import annotations

import subprocess


def terminate_process_tree(pid: int, timeout: float = 5.0) -> None:
    try:
        import psutil

        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for process in children:
            process.terminate()
        parent.terminate()
        gone, alive = psutil.wait_procs([*children, parent], timeout=timeout)
        for process in alive:
            process.kill()
        return
    except Exception:
        pass

    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(pid)],
        capture_output=True,
        text=True,
        check=False,
    )
