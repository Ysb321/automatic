import os
import time
import shutil
import importlib
from typing import Dict
from urllib.parse import urlparse
from modules import shared
from modules.upscaler import Upscaler, UpscalerLanczos, UpscalerNearest, UpscalerNone
from modules.paths import script_path, models_path

diffuser_repos = []

def walk(top, onerror:callable=None):
    # A near-exact copy of `os.path.walk()`, trimmed slightly. Probably not nessesary for most people's collections, but makes a difference on really large datasets.
    nondirs = []
    walk_dirs = []
    try:
        scandir_it = os.scandir(top)
    except OSError as error:
        if onerror is not None:
            onerror(error, top)
        return
    with scandir_it:
        while True:
            try:
                try:
                    entry = next(scandir_it)
                except StopIteration:
                    break
            except OSError as error:
                if onerror is not None:
                    onerror(error, top)
                return
            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False
            if not is_dir:
                nondirs.append(entry.name)
            else:
                try:
                    if entry.is_symlink() and not os.path.exists(entry.path):
                        raise NotADirectoryError('Broken Symlink')
                    walk_dirs.append(entry.path)
                except OSError as error:
                    if onerror is not None:
                        onerror(error, entry.path)
    # Recurse into sub-directories
    for new_path in walk_dirs:
        if os.path.basename(new_path).startswith('models--'):
            continue
        yield from walk(new_path, onerror)
    # Yield after recursion if going bottom up
    yield top, nondirs


def download_civit_model(model_url: str, model_name: str, model_path: str, preview):
    model_file = os.path.join(shared.opts.ckpt_dir, model_path, model_name)
    res = f'CivitAI download: name={model_name} url={model_url} path={model_path}'
    if os.path.isfile(model_file):
        res += ' already exists'
        shared.log.warning(res)
        return res
    import requests
    import rich.progress as p

    req = requests.get(model_url, stream=True, timeout=30)
    total_size = int(req.headers.get('content-length', 0))
    block_size = 16384 # 16KB blocks
    written = 0
    shared.state.begin()
    shared.state.job = 'downloload model'
    try:
        with open(model_file, 'wb') as f:
            with p.Progress(p.TextColumn('[cyan]{task.description}'), p.DownloadColumn(), p.BarColumn(), p.TaskProgressColumn(), p.TimeRemainingColumn(), p.TimeElapsedColumn(), p.TransferSpeedColumn()) as progress:
                task = progress.add_task(description="Download starting", total=total_size)
                # for data in tqdm(req.iter_content(block_size), total=total_size//1024, unit='KB', unit_scale=False):
                for data in req.iter_content(block_size):
                    written = written + len(data)
                    f.write(data)
                    progress.update(task, advance=block_size, description="Downloading")
        if written < 1024 * 1024 * 1024: # min threshold
            os.remove(model_file)
            raise ValueError(f'removed invalid download: bytes={written}')
        if preview is not None:
            preview_file = os.path.splitext(model_file)[0] + '.jpg'
            preview.save(preview_file)
            res += f' preview={preview_file}'
    except Exception as e:
        shared.log.error(f'CivitAI download error: name={model_name} url={model_url} path={model_path} {e}')
    if total_size == written:
        shared.log.info(f'{res} size={total_size}')
    else:
        shared.log.error(f'{res} size={total_size} written={written}')
    shared.state.end()
    return res


def download_diffusers_model(hub_id: str, cache_dir: str = None, download_config: Dict[str, str] = None, token = None, variant = None, revision = None, mirror = None):
    from diffusers import DiffusionPipeline
    import huggingface_hub as hf
    shared.state.begin()
    shared.state.job = 'downloload model'
    if download_config is None:
        download_config = {
            "force_download": False,
            "resume_download": True,
            "cache_dir": shared.opts.diffusers_dir,
            "load_connected_pipeline": True,
        }
    if cache_dir is not None:
        download_config["cache_dir"] = cache_dir
    if variant is not None and len(variant) > 0:
        download_config["variant"] = variant
    if revision is not None and len(revision) > 0:
        download_config["revision"] = revision
    if mirror is not None and len(mirror) > 0:
        download_config["mirror"] = mirror
    shared.log.debug(f"Diffusers downloading: {hub_id} {download_config}")
    if token is not None and len(token) > 2:
        shared.log.debug(f"Diffusers authentication: {token}")
        hf.login(token)
    pipeline_dir = DiffusionPipeline.download(hub_id, **download_config)
    try:
        model_info_dict = hf.model_info(hub_id).cardData # pylint: disable=no-member # TODO Diffusers is this real error?
    except Exception:
        model_info_dict = None
    # some checkpoints need to be downloaded as "hidden" as they just serve as pre- or post-pipelines of other pipelines
    if model_info_dict is not None and "prior" in model_info_dict:
        download_dir = DiffusionPipeline.download(model_info_dict["prior"][0], **download_config)
        model_info_dict["prior"] = download_dir
        # mark prior as hidden
        with open(os.path.join(download_dir, "hidden"), "w", encoding="utf-8") as f:
            f.write("True")
    shared.writefile(model_info_dict, os.path.join(pipeline_dir, "model_info.json"))
    shared.state.end()
    return pipeline_dir


def load_diffusers_models(model_path: str, command_path: str = None):
    import huggingface_hub as hf
    places = []
    places.append(model_path)
    if command_path is not None and command_path != model_path:
        places.append(command_path)
    diffuser_repos.clear()
    output = []
    for place in places:
        if not os.path.isdir(place):
            continue
        try:
            res = hf.scan_cache_dir(cache_dir=place)
            for r in list(res.repos):
                cache_path = os.path.join(r.repo_path, "snapshots", list(r.revisions)[-1].commit_hash)
                diffuser_repos.append({ 'name': r.repo_id, 'filename': r.repo_id, 'path': cache_path, 'size': r.size_on_disk, 'mtime': r.last_modified, 'hash': list(r.revisions)[-1].commit_hash, 'model_info': str(os.path.join(cache_path, "model_info.json")) })
                if not os.path.isfile(os.path.join(cache_path, "hidden")):
                    output.append(str(r.repo_id))
        except Exception as e:
            shared.log.error(f"Error listing diffusers: {place} {e}")
    shared.log.debug(f'Scanning diffusers cache: {model_path} {command_path} {len(output)}')
    return output


def find_diffuser(name: str):
    import huggingface_hub as hf
    if name in diffuser_repos:
        return name
    if shared.cmd_opts.no_download:
        return None
    hf_api = hf.HfApi()
    hf_filter = hf.ModelFilter(
        model_name=name,
        task='text-to-image',
        library=['diffusers'],
    )
    models = list(hf_api.list_models(filter=hf_filter, full=True, limit=20, sort="downloads", direction=-1))
    shared.log.debug(f'Searching diffusers models: {name} {len(models) > 0}')
    if len(models) > 0:
        return models[0].modelId
    return None


modelloader_directories = {}
cache_last = 0
cache_time = 1


def directory_has_changed(dir:str, *, recursive:bool=True) -> bool: # pylint: disable=redefined-builtin
    try:
        dir = os.path.abspath(dir)
        if dir not in modelloader_directories:
            return True
        if cache_last > (time.time() - cache_time):
            return False
        if not (os.path.exists(dir) and os.path.isdir(dir) and os.path.getmtime(dir) == modelloader_directories[dir][0]):
            return True
        if recursive:
            for _dir in modelloader_directories:
                if _dir.startswith(dir) and _dir != dir and not (os.path.exists(_dir) and os.path.isdir(_dir) and os.path.getmtime(_dir) == modelloader_directories[_dir][0]):
                    return True
    except Exception as e:
        shared.log.error(f"Filesystem Error: {e.__class__.__name__}({e})")
        return True
    return False


def directory_directories(dir:str, *, recursive:bool=True) -> dict[str,tuple[float,list[str]]]: # pylint: disable=redefined-builtin
    dir = os.path.abspath(dir)
    if directory_has_changed(dir, recursive=recursive):
        for _dir in modelloader_directories:
            try:
                if (os.path.exists(_dir) and os.path.isdir(_dir)):
                    continue
            except Exception:
                pass
            del modelloader_directories[_dir]
        for _dir, _files in walk(dir, lambda e, path: shared.log.debug(f"FS walk error: {e} {path}")):
            try:
                mtime = os.path.getmtime(_dir)
                if _dir not in modelloader_directories or mtime != modelloader_directories[_dir][0]:
                    modelloader_directories[_dir] = (mtime, [os.path.join(_dir, fn) for fn in _files])
            except Exception as e:
                shared.log.error(f"Filesystem Error: {e.__class__.__name__}({e})")
                del modelloader_directories[_dir]
    res = {}
    for _dir in modelloader_directories:
        if _dir == dir or (recursive and _dir.startswith(dir)):
            res[_dir] = modelloader_directories[_dir]
            if not recursive:
                break
    return res


def directory_mtime(dir:str, *, recursive:bool=True) -> float: # pylint: disable=redefined-builtin
    return float(max(0, *[mtime for mtime, _ in directory_directories(dir, recursive=recursive).values()]))


def directories_file_paths(directories:dict) -> list[str]:
    return sum([dat[1] for dat in directories.values()],[])


def unique_directories(directories:list[str], *, recursive:bool=True) -> list[str]:
    '''Ensure no empty, or duplicates'''
    directories = { os.path.abspath(dir): True for dir in directories if dir }.keys()
    if recursive:
        '''If we are going recursive, then directories that are children of other directories are redundant'''
        directories = [dir for dir in directories if not any(_dir != dir and dir.startswith(os.path.join(_dir,'')) for _dir in directories)]
    return directories


def unique_paths(paths:list[str]) -> list[str]:
    return { fp: True for fp in paths }.keys()


def directory_files(*directories:list[str], recursive:bool=True) -> list[str]:
    return unique_paths(sum([[*directories_file_paths(directory_directories(dir, recursive=recursive))] for dir in unique_directories(directories, recursive=recursive)],[]))


def extension_filter(ext_filter=None, ext_blacklist=None):
    if ext_filter:
        ext_filter = [*map(str.upper, ext_filter)]
    if ext_blacklist:
        ext_blacklist = [*map(str.upper, ext_blacklist)]
    def filter(fp:str): # pylint: disable=redefined-builtin
        return (not ext_filter or any(fp.upper().endswith(ew) for ew in ext_filter)) and (not ext_blacklist or not any(fp.upper().endswith(ew) for ew in ext_blacklist))
    return filter


def load_models(model_path: str, model_url: str = None, command_path: str = None, ext_filter=None, download_name=None, ext_blacklist=None) -> list:
    """
    A one-and done loader to try finding the desired models in specified directories.
    @param download_name: Specify to download from model_url immediately.
    @param model_url: If no other models are found, this will be downloaded on upscale.
    @param model_path: The location to store/find models in.
    @param command_path: A command-line argument to search for models in first.
    @param ext_filter: An optional list of filename extensions to filter by
    @return: A list of paths containing the desired model(s)
    """
    places = unique_directories([model_path, command_path])
    output = []
    try:
        output:list = [*filter(extension_filter(ext_filter, ext_blacklist), directory_files(*places))]
        if model_url is not None and len(output) == 0:
            if download_name is not None:
                from basicsr.utils.download_util import load_file_from_url
                dl = load_file_from_url(model_url, places[0], True, download_name)
                output.append(dl)
            else:
                output.append(model_url)
    except Exception as e:
        shared.log.error(f"Error listing models: {places} {e}")
    return output


def friendly_name(file: str):
    if "http" in file:
        file = urlparse(file).path

    file = os.path.basename(file)
    model_name, _extension = os.path.splitext(file)
    return model_name


def cleanup_models():
    # This code could probably be more efficient if we used a tuple list or something to store the src/destinations
    # and then enumerate that, but this works for now. In the future, it'd be nice to just have every "model" scaler
    # somehow auto-register and just do these things...
    root_path = script_path
    src_path = models_path
    dest_path = os.path.join(models_path, "Stable-diffusion")
    # move_files(src_path, dest_path, ".ckpt")
    # move_files(src_path, dest_path, ".safetensors")
    src_path = os.path.join(root_path, "ESRGAN")
    dest_path = os.path.join(models_path, "ESRGAN")
    move_files(src_path, dest_path)
    src_path = os.path.join(models_path, "BSRGAN")
    dest_path = os.path.join(models_path, "ESRGAN")
    move_files(src_path, dest_path, ".pth")
    src_path = os.path.join(root_path, "gfpgan")
    dest_path = os.path.join(models_path, "GFPGAN")
    move_files(src_path, dest_path)
    src_path = os.path.join(root_path, "SwinIR")
    dest_path = os.path.join(models_path, "SwinIR")
    move_files(src_path, dest_path)
    src_path = os.path.join(root_path, "repositories/latent-diffusion/experiments/pretrained_models/")
    dest_path = os.path.join(models_path, "LDSR")
    move_files(src_path, dest_path)
    src_path = os.path.join(root_path, "ScuNET")
    dest_path = os.path.join(models_path, "ScuNET")
    move_files(src_path, dest_path)


def move_files(src_path: str, dest_path: str, ext_filter: str = None):
    try:
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
        if os.path.exists(src_path):
            for file in os.listdir(src_path):
                fullpath = os.path.join(src_path, file)
                if os.path.isfile(fullpath):
                    if ext_filter is not None:
                        if ext_filter not in file:
                            continue
                    shared.log.warning(f"Moving {file} from {src_path} to {dest_path}.")
                    try:
                        shutil.move(fullpath, dest_path)
                    except Exception:
                        pass
            if len(os.listdir(src_path)) == 0:
                shared.log.info(f"Removing empty folder: {src_path}")
                shutil.rmtree(src_path, True)
    except Exception:
        pass



def load_upscalers():
    # We can only do this 'magic' method to dynamically load upscalers if they are referenced, so we'll try to import any _model.py files before looking in __subclasses__
    modules_dir = os.path.join(shared.script_path, "modules")
    for file in os.listdir(modules_dir):
        if "_model.py" in file:
            model_name = file.replace("_model.py", "")
            full_model = f"modules.{model_name}_model"
            try:
                importlib.import_module(full_model)
            except Exception:
                pass
    datas = []
    commandline_options = vars(shared.cmd_opts)
    # some of upscaler classes will not go away after reloading their modules, and we'll end up with two copies of those classes. The newest copy will always be the last in the list, so we go from end to beginning and ignore duplicates
    used_classes = {}
    for cls in reversed(Upscaler.__subclasses__()):
        classname = str(cls)
        if classname not in used_classes:
            used_classes[classname] = cls
    for cls in reversed(used_classes.values()):
        name = cls.__name__
        cmd_name = f"{name.lower().replace('upscaler', '')}_models_path"
        commandline_model_path = commandline_options.get(cmd_name, None)
        scaler = cls(commandline_model_path)
        scaler.user_path = commandline_model_path
        scaler.model_download_path = commandline_model_path or scaler.model_path
        datas += scaler.scalers
    shared.sd_upscalers = sorted(
        datas,
        # Special case for UpscalerNone keeps it at the beginning of the list.
        key=lambda x: x.name.lower() if not isinstance(x.scaler, (UpscalerNone, UpscalerLanczos, UpscalerNearest)) else ""
    )
