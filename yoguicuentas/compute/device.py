"""Descubrimiento explícito. No crea un contexto gráfico ni elige GL por índice."""

def devices():
    try:
        import pyopencl as cl
        return [d for p in cl.get_platforms() for d in p.get_devices()]
    except ImportError as exc:
        raise RuntimeError("Instalar la dependencia opcional: pip install -e '.[opencl]'") from exc
    except Exception as exc:
        raise RuntimeError(f"No se pudieron enumerar dispositivos OpenCL: {exc}") from exc


def select_device(index=0):
    available = devices()
    if type(index) is not int or not 0 <= index < len(available):
        raise ValueError(f"Dispositivo {index} inválido; disponibles: {len(available)}")
    return available[index]


def device_report(device):
    import pyopencl as cl
    return {"name": device.name.strip(), "platform": device.platform.name.strip(),
            "driver": device.driver_version, "version": device.version,
            "opencl_c": device.opencl_c_version, "pyopencl": cl.VERSION_TEXT,
            "have_gl": cl.have_gl(),
            "cl_khr_gl_sharing": "cl_khr_gl_sharing" in device.extensions.split()}
