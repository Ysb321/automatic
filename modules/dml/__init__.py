from platform import system
import torch
from typing import NamedTuple, Callable, Optional

from modules.sd_hijack_utils import CondFunc

memory_providers = ["None", "atiadlxx (AMD only)"]
default_memory_provider = "None"
if system() == "Windows":
    memory_providers.append("Performance Counter")
    default_memory_provider = "Performance Counter"
do_nothing = lambda: None

def _set_memory_provider():
    from modules.shared import opts, cmd_opts, log

    if opts.directml_memory_provider == "Performance Counter":
        from .backend import pdh_mem_get_info
        from .memory import MemoryProvider
        torch.dml.mem_get_info = pdh_mem_get_info
        if torch.dml.memory_provider is not None:
            del torch.dml.memory_provider
        torch.dml.memory_provider = MemoryProvider()
    elif opts.directml_memory_provider == "atiadlxx (AMD only)":
        device_name = torch.dml.get_device_name(cmd_opts.device_id)
        if "AMD" not in device_name and "Radeon" not in device_name:
            log.warning(f"Memory stats provider is changed to None because the current device is not AMDGPU. Current Device: {device_name}")
            opts.directml_memory_provider = "None"
            _set_memory_provider()
            return
        from .backend import amd_mem_get_info
        torch.dml.mem_get_info = amd_mem_get_info
    else:
        from .backend import mem_get_info
        torch.dml.mem_get_info = mem_get_info
    torch.cuda.mem_get_info = torch.dml.mem_get_info

def directml_init():
    from modules.dml.backend import DirectML # pylint: disable=ungrouped-imports
    # Alternative of torch.cuda for DirectML.
    torch.dml = DirectML

    torch.cuda.is_available = lambda: False
    torch.cuda.device = torch.dml.device
    torch.cuda.device_count = torch.dml.device_count
    torch.cuda.current_device = torch.dml.current_device
    torch.cuda.get_device_name = torch.dml.get_device_name
    torch.cuda.get_device_properties = torch.dml.get_device_properties

    torch.cuda.empty_cache = do_nothing
    torch.cuda.ipc_collect = do_nothing
    torch.cuda.memory_stats = torch.dml.memory_stats
    torch.cuda.mem_get_info = torch.dml.mem_get_info
    torch.cuda.memory_allocated = torch.dml.memory_allocated
    torch.cuda.max_memory_allocated = torch.dml.max_memory_allocated
    torch.cuda.reset_peak_memory_stats = torch.dml.reset_peak_memory_stats
    torch.cuda.utilization = lambda: 0

    torch.Tensor.directml = lambda self: self.to(torch.dml.current_device())

def directml_do_hijack():
    import modules.dml.hijack
    from modules.devices import device

    if not torch.dml.has_float64_support(device):
        CondFunc('torch.from_numpy',
            lambda orig_func, *args, **kwargs: orig_func(args[0].astype('float32')),
            lambda *args, **kwargs: args[1].dtype == float)

    _set_memory_provider()

class OverrideItem(NamedTuple):
    value: str
    condition: Optional[Callable]
    message: Optional[str]

opts_override_table = {
    "diffusers_generator_device": OverrideItem("cpu", None, "DirectML does not support torch Generator API."),
    "diffusers_model_cpu_offload": OverrideItem(False, None, "Diffusers' model CPU offloading does not support DirectML devices."),
    "diffusers_seq_cpu_offload": OverrideItem(False, lambda opts: opts.diffusers_pipeline != "Stable Diffusion XL", "Diffusers' sequential CPU offloading is available only on StableDiffusionXLPipeline with DirectML devices."),
}

def directml_override_opts():
    from modules import shared

    if shared.cmd_opts.experimental:
        return

    count = 0
    for key in opts_override_table:
        item = opts_override_table[key]
        if getattr(shared.opts, key) != item.value and (item.condition is None or item.condition(shared.opts)):
            count += 1
            setattr(shared.opts, key, item.value)
            if item.message is not None:
                shared.log.warning(item.message)
            shared.log.warning(f'{key} is automatically overriden to {item.value}.')
    
    if count > 0:
        shared.log.info(f'{count} options are automatically overriden. If you want to keep them from overriding, run with --experimental argument.')

    _set_memory_provider()
